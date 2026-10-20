"""C++ 排班目标函数（robot_arrangement_moea）的 Python 等价实现，用于下界推导、精确搜索与构造解。
逐条对应 problem.cpp 的语义（已用 --eval-genes 与 C++ 逐解核对，见 validate_mirror.py）：
  · 可用判定：机器人 Next_Ready ≤ E − 去程（首班 E=0 时要求 ≤0）；剩余工时 ≥ 单次工时
  · 值岗对齐：首班从 0 开始（安装+去程+值岗），之后每班值岗开始 = 上一班值岗结束 E，E += 本班值岗时长
  · 机器人就绪 = 值岗结束 + 返程 + max(所带工具拆卸) + 充电/维修（剩余工时 − 单次 < 单次 → 维修并重置）
  · 工具：先复用"就绪 ≤ max(0, E − 机器人去程)"的同类兼容工具（按就绪时间排序取前 carry_num 个），不足再按基因新建
          工具就绪 = 机器人安装开始(E − 去程 − max安装) + 安装 + 去程 + 值岗 + 返程 + 拆卸 + 休息
  · 均衡度 = 0.3·std(出勤次数) + 0.4·std(值岗总时长) + 0.3·std(首次维修开始时间的相邻间隔)
"""
import json, math
import numpy as np

THETA = 0.85


def load_scenario(path):
    d = json.load(open(path, encoding="utf-8"))
    ents = d["entityDataList"]
    if "workflow" in d and "entityDataList" not in d:          # 兼容原请求的嵌套格式
        pass
    if not any(e.get("englishName") == "Robot" for e in ents):
        node = [n for n in d["workflow"]["nodeList"]
                if n.get("algorithmMetadata", {}).get("algorithmEnglishName") == "Evaluate_Update"][0]
        ents = node["entityDataList"]
    R, Tl, T = {}, {}, None
    for e in ents:
        for ex in e.get("exampleList", []):
            p = {q["paramEnglishName"]: q["inputValue"] for q in ex["paramList"]}
            if e.get("englishName") == "Robot":
                R.setdefault(int(p["type"]), dict(p, limit=0))["limit"] += 1
            elif e.get("englishName") == "Tool":
                Tl.setdefault(int(p["type"]), dict(p, limit=0))["limit"] += 1
            elif "task_duration" in p:
                T = p["task_duration"]
    # 与 C++ 一致：limit 取 limit_num 参数（各实例相同）
    for dct in (R, Tl):
        for k, v in dct.items():
            v["limit"] = int(v.get("limit_num", v["limit"]))
    nR, nT = max(R) + 1, max(Tl) + 1
    for k in range(nR):
        R.setdefault(k, None)
    return dict(R=[R[k] for k in range(nR)], Tl=[Tl.get(k) for k in range(nT)], T=T)


class Robot:
    __slots__ = ("type", "serial", "ready", "remain", "count", "dur", "first_rep", "duties")

    def __init__(s, ty, serial, remain):
        s.type, s.serial, s.ready, s.remain = ty, serial, 0.0, remain
        s.count, s.dur, s.first_rep, s.duties = 0, 0.0, None, []

    @property
    def id(s):
        return f"Robot_{s.type}_{s.serial}"


class Tool:
    __slots__ = ("type", "serial", "ready", "uses")

    def __init__(s, ty, serial):
        s.type, s.serial, s.ready, s.uses = ty, serial, 0.0, 0


class Sim:
    """逐班推进的状态机。decide 由外部给出：('reuse', 可用列表下标) 或 ('new', 类型)；新建工具类型由 tool_gene 决定。"""

    def __init__(s, sc, rank=False):
        s.sc, s.rank = sc, rank
        s.E, s.robots, s.tools = 0.0, [], []
        s.resR = [r["limit"] if r else 0 for r in sc["R"]]
        s.resT = [t["limit"] if t else 0 for t in sc["Tl"]]
        s.shift, s.failed, s.seq = 0, False, []

    def done(s):
        return s.E >= s.sc["T"]

    def available(s):
        av = []
        for r in s.robots:
            P = s.sc["R"][r.type]
            ok = (r.ready <= 0.0) if s.E == 0 else (r.ready <= (s.E - P["out_travel_time"]) + 1e-9)
            if ok and r.remain >= P["single_work_time"]:
                av.append(r)
        if s.rank == "phase":
            av.sort(key=lambda r: (r.remain, r.count))       # 维修相位排序（ROBOT_DECODER=4）
        elif s.rank:
            av.sort(key=lambda r: (r.count, -r.remain))      # 稳定排序：已执行班次升序，剩余工时降序
        return av

    def new_type(s, t):
        """entity_remain：所选类型用完则顺延到下一类型；全部用完返回 None"""
        n = len(s.sc["R"])
        for _ in range(n):
            if s.resR[t] <= 0:
                t = (t + 1) % n
            else:
                return t
        return None

    def step(s, robot, tool_gene):
        """对已选定（已存在或刚新建）的机器人执行一个班次。返回 False 表示工具不足（不可行）。"""
        sc, P = s.sc, s.sc["R"][robot.type]
        E = s.E
        target = max(0.0, E - P["out_travel_time"])
        lst = P["cargo_type_list"]
        cand = [t for t in s.tools if t.type in lst and t.ready <= target + 1e-9]
        cand.sort(key=lambda t: t.ready)
        carry = int(P["carry_num"])
        use = cand[:carry]
        ctn = int(P["cargo_type_num"])
        sel = int(tool_gene * (ctn - 1))
        if sel >= ctn:
            sel = 0
        while len(use) < carry:
            indd, picked = sel, None
            for _ in range(ctn):
                if indd >= ctn or indd < 0:
                    indd = 0
                if s.resT[int(lst[indd])] > 0:
                    picked = int(lst[indd]); break
                indd += 1
            if picked is None:
                return False
            s.resT[picked] -= 1
            t = Tool(picked, sc["Tl"][picked]["limit"] - s.resT[picked])
            s.tools.append(t)
            use.append(t)
        ins = max(sc["Tl"][t.type]["install_time"] for t in use)
        rem = max(sc["Tl"][t.type]["removal_time"] for t in use)
        d = P["work_time"]
        if E == 0:
            install_begin, duty_begin = 0.0, ins + P["out_travel_time"]
        else:
            install_begin, duty_begin = E - ins - P["out_travel_time"], E
        duty_end = duty_begin + d
        back = duty_end + P["return_travel_time"] + rem
        robot.remain -= P["single_work_time"]
        if robot.remain >= P["single_work_time"]:
            robot.ready = back + P["charge_time"]
        else:
            if robot.first_rep is None:
                robot.first_rep = back
            robot.ready = back + P["maintenance_time"]
            robot.remain = P["continue_max_work"]
        robot.count += 1
        robot.dur += d
        robot.duties.append((duty_begin, duty_end))
        for t in use:
            Q = sc["Tl"][t.type]
            t.ready = install_begin + Q["install_time"] + Q["tool_out_time"] + Q["tool_work_time"] + \
                Q["tool_return_time"] + Q["removal_time"] + Q["tool_rest_time"]
            t.uses += 1
        s.E = duty_end
        s.shift += 1
        s.seq.append(robot.id)
        return True

    def create(s, ty):
        s.resR[ty] -= 1
        r = Robot(ty, s.sc["R"][ty]["limit"] - s.resR[ty], s.sc["R"][ty]["continue_max_work"])
        return r

    def dispatch_new(s, ty, tool_gene):
        ty = s.new_type(ty)
        if ty is None:
            s.failed = True; return False
        r = s.create(ty)
        ok = s.step(r, tool_gene)
        if not ok:
            s.failed = True; return False
        s.robots.append(r)              # C++：流程成功后才加入 order_id
        return True

    def dispatch_reuse(s, r, tool_gene):
        if not s.step(r, tool_gene):
            s.failed = True; return False
        return True

    def objectives(s):
        if s.failed or not s.done():
            return None
        return objectives_of(s.robots, len(s.robots) + len(s.tools))


def std(v):
    v = np.asarray(v, float)
    return 0.0 if len(v) <= 1 else float(np.sqrt(((v - v.mean()) ** 2).mean()))


def objectives_of(robots, n_res):
    cnt = [r.count for r in robots]
    dur = [r.dur for r in robots]
    rep = sorted(r.first_rep for r in robots if r.first_rep is not None)
    iv = std(np.diff(rep)) if len(rep) > 1 else 0.0
    bal = 0.3 * std(cnt) + 0.4 * std(dur) + 0.3 * iv
    return (float(n_res), bal)


def objectives_of_simple(cnt, dur, reps):
    reps = sorted(reps)
    iv = std(np.diff(reps)) if len(reps) > 1 else 0.0
    return 0.3 * std(cnt) + 0.4 * std(dur) + 0.3 * iv


def decode_robot_select(x, n_avail, n_types):
    th = THETA
    if n_avail > 0 and x < th:
        s = int(x / th * n_avail)
        return min(max(s, 0), n_avail - 1)
    u = (x - th) / (1.0 - th) if n_avail > 0 else x
    t = int(max(u, 0.0) * n_types)
    return n_avail + min(max(t, 0), n_types - 1)


def rep_ceil_factory(sc):
    """空档向上取到"各类型值岗时长的非负整数组合"中不小于它的最小值（与 C++ rep_ceil 相同）"""
    durs = [int(round(P["work_time"])) for P in sc["R"] if P and P["limit"] > 0]
    rep = [True]

    def f(g):
        if g <= 1e-9:
            return 0.0
        need = math.ceil(g - 1e-9)
        t = need
        while True:
            while len(rep) <= t:
                k = len(rep)
                rep.append(any(dd > 0 and k >= dd and rep[k - dd] for dd in durs))
            if rep[t]:
                return float(t)
            t += 1
    return f


def robot_capacity_hours(sc, r, E, T, rep_ceil):
    P = sc["R"][r.type]
    rm = [sc["Tl"][int(t)]["removal_time"] for t in P["cargo_type_list"] if sc["Tl"][int(t)] and sc["Tl"][int(t)]["limit"] > 0]
    remmin = min(rm) if rm else 0.0
    remain, hours = r.remain, 0.0
    s = E + rep_ceil(r.ready + P["out_travel_time"] - E)
    while s < T:
        hours += min(P["work_time"], T - s)
        end = s + P["work_time"]
        remain -= P["single_work_time"]
        ready = end + P["return_travel_time"] + remmin
        if remain >= P["single_work_time"]:
            ready += P["charge_time"]
        else:
            ready += P["maintenance_time"]; remain = P["continue_max_work"]
        s = end + rep_ceil(ready + P["out_travel_time"] - end)
    return hours


def evaluate_genes(sc, x, rank=False, cap_span=None):
    """与 robot_arrangement_moea 完全相同的基因解码（阈值解码 / rank=True 为排序解码 /
    cap_span 不为 None 时为容量预判解码 ROBOT_DECODER=3，裕度基因为末位，ρ = 1 + cap_span·x[-1]）"""
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x)
    s = Sim(sc, rank)
    s.cap_override = 0
    nty = len(sc["R"])
    rc = rep_ceil_factory(sc) if cap_span is not None else None
    i = 0
    while s.E < sc["T"] and i < n // 2:
        av = s.available()
        k = decode_robot_select(x[i], len(av), nty)
        if cap_span is not None and av and k >= len(av):
            cap = sum(robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots)
            rho = 1.0 + cap_span * x[n - 1]
            if cap + 1e-9 >= rho * (sc["T"] - s.E):
                u = (x[i] - THETA) / (1.0 - THETA)
                k = min(max(int(max(u, 0.0) * len(av)), 0), len(av) - 1)
                s.cap_override += 1
        if k < len(av):
            if not s.dispatch_reuse(av[k], x[i + n // 2]):
                return None, s
        else:
            if not s.dispatch_new(k - len(av), x[i + n // 2]):
                return None, s
        i += 1
    if s.E < sc["T"]:
        return None, s
    o = s.objectives()
    return (np.float32(o[0]), np.float32(o[1])), s


def nvar_auto(sc, cap=False):
    dmin = min(r["work_time"] for r in sc["R"] if r)
    return 2 * max(math.ceil(sc["T"] / dmin - 1e-9), 1) + (2 if cap else 0)
