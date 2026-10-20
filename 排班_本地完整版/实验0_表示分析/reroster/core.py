"""重排班（执行中扰动）模拟器。

流程：原排班（plan） → 按原排班执行到第 k 班（前 k 班冻结） → 施加扰动事件 → 从该状态对剩余时域重排。
重排的目标：(1) 资源数（机器人 + 工具，含扰动前已开启的）；(2) 改动数 = 扰动后各班派出的机器人与原计划不同的班数；
另外报告均衡度（原模型的第二目标）。

解码方式（基因长度都与原实例相同，可直接用同一个 MOEA）：
  plan   稀疏偏离 K=0.25 + "照原计划"规则：原计划的机器人能去就派它，原计划这班新开就新开同型；否则按默认规则。
         即把原排班放进表示本身作为偏置（本文方法）。
  sparse 稀疏偏离 K=0.25 + 默认规则（不看原计划）。
  dec5   逐班基因（容量预判 + 回溯修复），从中间状态继续。
  种子（Shen & Yao 2015 的做法）不是解码方式，而是初始种群的构造：encode_dec5 把（修复后的）原计划编码成 dec5 基因，见 moea.py。
"""
import copy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen")); sys.path.insert(0, os.path.dirname(HERE))
import ruledec as R  # noqa: E402
import instances as I  # noqa: E402

L, M = R.L, R.M
TH = M.THETA
INF = 1e18


# ---------------- 原排班 ----------------
def rid(r):
    return (r.type, r.serial)


def duties_of(sim):
    """[(值岗开始, 结束, (类型, 编号))]，按开始时刻排序"""
    out = [(b, e, rid(r)) for r in sim.robots for b, e in r.duties]
    return sorted(out)


class Plan:
    """原排班：由一个 dec5 基因解码得到；记录逐班派出的机器人和工具基因，可以逐班重放。"""

    def __init__(s, sc, x):
        s.sc, s.x = sc, np.asarray(x, np.float32).astype(np.float64)
        r = L.decode(sc, s.x, "dec5")
        assert r.feasible, "原排班必须可行"
        s.obj = r.obj
        s.duties = duties_of(r.sim)            # 每班 (开始, 结束, 机器人)
        s.h = len(s.x) // 2
        s.starts = np.array([d[0] for d in s.duties])
        first = {}
        for k, d in enumerate(s.duties):
            first.setdefault(d[2], k)
        s.first_use = first                    # 机器人 → 它第一次出勤的班号（= 原计划里新开它的那班）

    def replay(s, k):
        """按原计划执行前 k 班，返回状态"""
        sim = M.Sim(s.sc, False)
        for i in range(k):
            who = s.duties[i][2]
            r = next((r for r in sim.robots if rid(r) == who), None)
            ok = sim.dispatch_reuse(r, s.x[i + s.h]) if r is not None else sim.dispatch_new(who[0], s.x[i + s.h])
            assert ok and (r is not None or rid(sim.robots[-1]) == who), "重放与原计划不一致"
        return sim

    def planned_at(s, t):
        """原计划里开始时刻离 t 最近的那一班的 (班号, 机器人)"""
        k = int(np.argmin(np.abs(s.starts - t)))
        return k, s.duties[k][2]


# ---------------- 扰动事件 ----------------
EVENT_TYPES = ["breakdown", "early_maint", "delay", "overrun", "tool_loss"]


def apply_event(sc, sim, plan, k, ev):
    """在执行完前 k 班的状态上施加事件（就地修改 sim）。ev = dict(type=..., 参数...)。返回事件描述。
    - breakdown：原计划下一班要派的机器人故障，停用 D 小时，修好后工作预算恢复满额（相当于做了一次维修）；
    - early_maint：原计划下一班要派的机器人必须先去维修（子任务顺序改变：维修提前到这一班之前）；
    - delay：原计划下一班要派的机器人返程/充电延误 δ 小时；
    - overrun：正在值岗的那一班超时 δ 小时（后续所有班整体后移）；
    - tool_loss：一件工具损坏报废（仍计入资源数，但不能再用）。"""
    nxt = plan.duties[k][2] if k < len(plan.duties) else None
    robot = next((r for r in sim.robots if rid(r) == nxt), None)
    t = sim.E
    typ = ev["type"]
    if typ == "none":
        return "无事件"
    if typ in ("breakdown", "early_maint", "delay") and robot is None:
        return None                                            # 下一班原计划新开机器人，这类事件不适用
    if typ == "breakdown":
        robot.ready = max(robot.ready, t) + ev["D"]
        robot.remain = sc["R"][robot.type]["continue_max_work"]
        return f"{nxt} 故障停用 {ev['D']:.0f} h"
    if typ == "early_maint":
        P = sc["R"][robot.type]
        if robot.first_rep is None:
            robot.first_rep = max(robot.ready, t)
        robot.ready = max(robot.ready, t) + P["maintenance_time"]
        robot.remain = P["continue_max_work"]
        return f"{nxt} 提前维修 {P['maintenance_time']:.0f} h"
    if typ == "delay":
        robot.ready = max(robot.ready, t) + ev["d"]
        return f"{nxt} 延误 {ev['d']:.0f} h"
    if typ == "overrun":
        if k == 0:
            return None
        cur = next(r for r in sim.robots if rid(r) == plan.duties[k - 1][2])
        b, e = cur.duties[-1]
        cur.duties[-1] = (b, e + ev["d"])
        cur.dur += ev["d"]; cur.ready += ev["d"]
        sim.E += ev["d"]
        return f"{rid(cur)} 值岗超时 {ev['d']:.0f} h"
    if typ == "tool_loss":
        if not sim.tools:
            return None
        tl = min(sim.tools, key=lambda q: (q.ready, q.type, q.serial))     # 最快可用的那件
        tl.ready = INF
        return f"工具 {tl.type}_{tl.serial} 报废"
    raise ValueError(typ)


class Scenario:
    """一个重排班场景：实例 + 原排班 + 在第 k 班施加的事件"""

    def __init__(s, inst, plan_x, k, ev):
        s.inst, s.sc = inst, I.load(inst)
        s.plan = Plan(s.sc, plan_x)
        s.k, s.ev = k, ev
        st = s.plan.replay(k)
        s.desc = apply_event(s.sc, st, s.plan, k, ev)
        s.state = st
        s.t0 = st.E
        s.nv = L.nvar(s.sc, "dec5")
        s.n_left = len(s.plan.duties) - k                       # 原计划剩余班数

    @property
    def valid(s):
        return s.desc is not None

    def changes(s, sim):
        """扰动后每一班派出的机器人与原计划（时刻最近的那班）不同的班数"""
        c = 0
        for b, e, who in duties_of(sim):
            if b + 1e-9 >= s.t0:
                c += s.plan.planned_at(b)[1] != who
        return c

    def evaluate(s, res):
        """解码结果 → (资源数, 改动数, 均衡度)；不可行返回 None"""
        if not res.feasible:
            return None
        return (res.obj[0], float(s.changes(res.sim)), res.obj[1])


# ---------------- 解码 ----------------
def plan_rule_factory(sc_obj):
    plan = sc_obj.plan

    def rule(ctx):
        k, who = plan.planned_at(ctx.t)
        for r in ctx.available:
            if (r.type, r.serial) == who:
                return [("reuse", r)] + [("reuse", q) for q in ctx.available if q is not r] + [("new", ctx.gene_type)]
        if plan.first_use.get(who) == k and not any((r.type, r.serial) == who for r in ctx.robots):
            return [("new", who[0])] + [("reuse", q) for q in ctx.available]     # 原计划这班新开
        return R.default_rule(ctx)
    return rule


def dec5_from(sc, x, start, W=12):
    """dec5（与 exp0lib._bt 相同的逻辑），从中间状态 start=(状态, i0) 继续；回溯不越过 i0"""
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x); h = n // 2
    rc = M.rep_ceil_factory(sc)
    nty = len(sc["R"])

    def avail(s):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        return av

    def step(s, i, forced=None):
        av = avail(s)
        if forced is not None:
            return 0 if s.dispatch_reuse(av[forced], x[i + h]) else -1
        k = M.decode_robot_select(x[i], len(av), nty)
        if av and k >= len(av):
            c = sum(M.robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots)
            if c + 1e-9 >= sc["T"] - s.E:
                u = (x[i] - TH) / (1 - TH); k = min(max(int(max(u, 0) * len(av)), 0), len(av) - 1)
        if k < len(av):
            return 0 if s.dispatch_reuse(av[k], x[i + h]) else -1
        return 1 if s.dispatch_new(k - len(av), x[i + h]) else -1

    s0, i0 = start
    s = copy.deepcopy(s0)
    snaps, forced = {}, {}
    i, fixes = i0, 0
    while s.E < sc["T"] and i < h:
        for kk in [kk for kk in snaps if kk > i]:
            del snaps[kk]
        snaps[i] = copy.deepcopy(s)
        if not avail(s) and s.robots and W > 0:
            fixed = False
            for t in range(i - 1, max(i0 - 1, i - 1 - W), -1):
                base = snaps[t]
                av_t = avail(base)
                cur = forced.get(t)
                for alt in range(len(av_t)):
                    if alt == cur:
                        continue
                    trial = copy.deepcopy(base)
                    ok = True
                    newf = dict(forced); newf[t] = alt
                    for j in range(t, i):
                        if step(trial, j, alt if j == t else None) != 0:
                            ok = False; break
                    if ok and avail(trial):
                        forced = {kk: vv for kk, vv in newf.items() if kk <= t}
                        fixed = True; fixes += 1
                        break
                if fixed:
                    break
            if fixed:
                s2 = copy.deepcopy(snaps[t])
                for j in range(t, i):
                    snaps[j] = copy.deepcopy(s2); step(s2, j, forced.get(j))
                s = s2
                snaps[i] = copy.deepcopy(s)
        if step(s, i, forced.get(i)) < 0:
            return L.Result(None, s, i + 1, 0, fixes, forced)
        i += 1
    if s.E < sc["T"] or s.failed:
        return L.Result(None, s, i, 0, fixes, forced)
    o = s.objectives()
    return L.Result((float(o[0]), float(o[1])), s, i, 0, fixes, forced)


def decoder(scn, name):
    start = (scn.state, scn.k)
    if name == "plan":
        rule = plan_rule_factory(scn)
        return lambda x: R.decode_rule(scn.sc, x, rule, 0.25, start=start)
    if name == "sparse":
        return lambda x: R.decode_rule(scn.sc, x, R.default_rule, 0.25, start=start)
    if name == "dec5":
        return lambda x: dec5_from(scn.sc, x, start)
    raise ValueError(name)


def encode_dec5(scn, rng=None):
    """把原计划（剩余部分）编码成 dec5 基因：每班选原计划的机器人；原计划的机器人去不了时退回默认（派排第一的可用机器人），
    即"修复后的原计划"。工具基因沿用原计划。用 dec5_from 解码核对，返回 (基因, 结果)。"""
    sc, plan = scn.sc, scn.plan
    x = plan.x.copy()
    h = len(x) // 2
    nty = len(sc["R"])
    s = copy.deepcopy(scn.state)
    i = scn.k
    while s.E < sc["T"] and i < h:
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        k, who = plan.planned_at(s.E)
        idx = next((j for j, r in enumerate(av) if rid(r) == who), None)
        if idx is not None:
            x[i] = (idx + 0.5) / len(av) * TH
        elif av:
            x[i] = 0.5 / len(av) * TH
        else:
            ty = who[0] if plan.first_use.get(who) == k else 0
            x[i] = TH + (ty + 0.5) / nty * (1 - TH)
        # 逐班推进（与 dec5_from 的单步一致，不含回溯）
        kk = M.decode_robot_select(x[i], len(av), nty)
        ok = s.dispatch_reuse(av[kk], x[i + h]) if kk < len(av) else s.dispatch_new(kk - len(av), x[i + h])
        if not ok:
            break
        i += 1
    return x, dec5_from(sc, x, (scn.state, scn.k))
