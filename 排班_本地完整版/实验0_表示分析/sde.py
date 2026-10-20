"""dec6：规则 + 稀疏偏离编码（sparse deviation encoding）。

默认规则：每班复用"出勤最少（同则剩余工时多）"的那台可用机器人；没有可用机器人时先回溯修复（同 dec5，窗口 12 班），
修复不了才新开，新开类型由一个全局"默认类型基因"决定。
基因只编码"在哪几班、怎么偏离规则"：
  机器人半段 x[0:h]：K 个偏离槽 (p_k, a_k)，再加 1 个默认类型基因 x[2K]；其余位置不用。
    a_k < 0.6 → 该槽不起作用；a_k ≥ 0.6 → 第 int(p_k·Nmax) 班偏离，u = (a_k − 0.6)/0.4：
      u < 0.85 → 改派给排名第 2…n 的可用机器人（按 u 均分；可用数 < 2 时偏离作废）；
      u ≥ 0.85 → 新开类型 int((u−0.85)/0.15·T)，与 dec5 一样受容量预判约束（现有机器人够用时偏离作废）。
    K = ⌈0.25·Nmax⌉ 个槽（至少 4 个）。
    同一班有多个槽时，编号大的槽生效。
  工具半段 x[h:]：与原来相同（第 i 班的工具基因 x[i+h]）。
与 dec5 的区别：偏离之后的班次按规则继续推进，不再由逐班基因决定，所以改一个基因只改变一个决策。
"""
import copy, math
import numpy as np
import exp0lib as L

M = L.M
TH = L.TH
NEW_CAP = __import__("os").environ.get("SDE_NEW_CAP", "1") == "1"
DEV_ON = 0.6      # a_k < 0.6 不偏离
REUSE_SHARE = float(__import__("os").environ.get("SDE_REUSE_SHARE", 0.85))  # 偏离中 85% 的取值区间是"改派给别的可用机器人"，15% 是"新开"


K_FRAC = 0.25        # 偏离槽数 K = max(4, ⌈K_FRAC·Nmax⌉)（实验3 可调，≤ 0.5）
SLOT_ADAPT = False   # True：实际启用的槽数 = max(1, ⌈K·x[末位]⌉)


def n_slots(sc):
    nmax = L.nvar(sc, "dec5") // 2 - 1
    return max(4, math.ceil(K_FRAC * nmax - 1e-9)), nmax


def devmap(sc, x):
    K, nmax = n_slots(sc)
    d = {}
    keff = max(1, math.ceil(K * float(np.float32(x[-1])) - 1e-9)) if SLOT_ADAPT else K
    h = L.nvar(sc, "dec5") // 2
    for k in range(keff):
        if 2 * k + 1 >= h:
            break
        p, a = x[2 * k], x[2 * k + 1]
        if a >= DEV_ON:
            d[min(int(p * nmax), nmax - 1)] = (a - DEV_ON) / (1.0 - DEV_ON)
    return d


def decode6(sc, x, W=12):
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x); h = n // 2
    K, nmax = n_slots(sc)
    # 与 C++ 一致：班次上界为奇数且槽数比例 0.5 时，最后一个槽放不下（只用 2k+1 < h 的槽），默认类型基因落在 x[2K]
    nty = len(sc["R"])
    dmap = devmap(sc, x)
    tdef = min(int(x[2 * K] * nty), nty - 1)

    def avail(s):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        return av

    rc = M.rep_ceil_factory(sc)

    def choose(i, nav, s=None):
        """返回 ('reuse', 排名) 或 ('new', 类型)。新开偏离与 dec5 一样受容量预判约束：现有机器人够覆盖剩余时长时不新开（偏离作废）"""
        u = dmap.get(i)
        if u is not None:
            if u < REUSE_SHARE:
                if nav >= 2:
                    return ("reuse", 1 + min(int(u / REUSE_SHARE * (nav - 1)), nav - 2))
            else:
                ty = min(int((u - REUSE_SHARE) / (1 - REUSE_SHARE) * nty), nty - 1)
                if nav == 0 or s is None or not NEW_CAP:
                    return ("new", ty)
                cap = sum(M.robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots)
                if cap + 1e-9 < sc["T"] - s.E:
                    return ("new", ty)
        if nav > 0:
            return ("reuse", 0)
        return ("new", tdef)

    def step(s, i, forced=None):
        av = avail(s)
        if forced is not None:
            return 0 if s.dispatch_reuse(av[forced], x[i + h]) else -1
        kind, v = choose(i, len(av), s)
        if kind == "reuse":
            return 0 if s.dispatch_reuse(av[v], x[i + h]) else -1
        return 1 if s.dispatch_new(v, x[i + h]) else -1

    s = M.Sim(sc, False)
    snaps, forced = [], {}
    i = fixes = 0
    while s.E < sc["T"] and i < h:
        snaps = snaps[:i] + [copy.deepcopy(s)]
        if not avail(s) and s.robots and W > 0 and choose(i, 0)[0] == "new" and i not in dmap:
            fixed = False
            for t in range(i - 1, max(-1, i - 1 - W), -1):
                base = snaps[t]
                av_t = avail(base)
                cur = forced.get(t)
                for alt in range(len(av_t)):
                    if alt == cur:
                        continue
                    trial = copy.deepcopy(base)
                    ok = True
                    for j in range(t, i):
                        if step(trial, j, alt if j == t else forced.get(j) if j < t else None) != 0:
                            ok = False; break
                    if ok and avail(trial):
                        forced = {kk: vv for kk, vv in forced.items() if kk < t}
                        forced[t] = alt
                        fixed = True; fixes += 1
                        break
                if fixed:
                    break
            if fixed:
                s2 = copy.deepcopy(snaps[t]); snaps = snaps[:t]
                for j in range(t, i):
                    snaps.append(copy.deepcopy(s2)); step(s2, j, forced.get(j))
                s = s2
                snaps.append(copy.deepcopy(s))
        if step(s, i, forced.get(i)) < 0:
            return L.Result(None, s, i + 1, 0, fixes, forced)
        i += 1
    if s.E < sc["T"] or s.failed:
        return L.Result(None, s, i, 0, fixes, forced)
    o = s.objectives()
    r = L.Result((float(o[0]), float(o[1])), s, i, 0, fixes, forced)
    return r


def used_genes(sc):
    """dec6 实际会被读到的机器人基因下标（偏离槽 + 默认类型基因）"""
    K, _ = n_slots(sc)
    return list(range(2 * K + 1))


def encode_schedule(sc, seq, tools):
    """把给定排班（派班序列 + 新建工具类型）写成 dec6 基因：与规则不同的班次记为偏离。
    返回 (基因 或 None, 需要的偏离数, 槽数)。用于检查最优解可达性。"""
    K, nmax = n_slots(sc)
    nv = L.nvar(sc, "dec5"); h = nv // 2
    nty = len(sc["R"])
    s = M.Sim(sc, True)
    devs = []
    x = np.zeros(nv)
    tdef = None
    for i, rid in enumerate(seq):
        av = s.available(); ids = [r.id for r in av]
        if rid in ids:
            k = ids.index(rid)
            if k != 0:
                devs.append((i, "reuse", k, len(av)))
            act = ("reuse", k)
        else:
            ty = int(rid.split("_")[1])
            if av:
                devs.append((i, "new", ty, len(av)))
            else:
                tdef = ty if tdef is None else tdef
                if ty != tdef:
                    devs.append((i, "new", ty, 0))
            act = ("new", ty)
        # 工具基因：沿用 exp0lib.reach_genes 的做法，搜索使新建工具类型一致的值
        ntool0 = len(s.tools); okt = None
        for tg in np.linspace(0.0005, 0.9895, 60):
            tg = float(np.float32(tg))
            t2 = copy.deepcopy(s)
            ok = t2.dispatch_reuse(t2.available()[act[1]], tg) if act[0] == "reuse" else t2.dispatch_new(act[1], tg)
            if ok and [t.type for t in t2.tools[ntool0:]] == list(tools[ntool0:len(t2.tools)]) and t2.seq[-1] == rid:
                okt = (tg, t2); break
        if okt is None:
            return None, len(devs), K
        x[i + h], s = okt
    if len(devs) > K:
        return None, len(devs), K
    x[2 * K] = ((tdef or 0) + 0.5) / nty
    for k, (i, kind, v, nav) in enumerate(devs):
        if kind == "reuse":
            u = (v - 1 + 0.5) / (nav - 1) * REUSE_SHARE
        else:
            u = REUSE_SHARE + (v + 0.5) / nty * (1 - REUSE_SHARE)
        x[2 * k] = (i + 0.5) / nmax
        x[2 * k + 1] = DEV_ON + u * (1 - DEV_ON)
    for k in range(len(devs), K):
        x[2 * k + 1] = 0.3
    return x, len(devs), K


def decode7(sc, x):
    """实验2：解码方式基因（末位）。< 0.5 按 dec5，≥ 0.5 按 dec6b（新开偏离不受容量预判约束，偏离中 30% 为新开）。"""
    global NEW_CAP, REUSE_SHARE
    if np.float32(x[-1]) < 0.5:
        return L.decode(sc, x, "dec5")
    old = (NEW_CAP, REUSE_SHARE)
    NEW_CAP, REUSE_SHARE = False, 0.7
    try:
        return decode6(sc, x)
    finally:
        NEW_CAP, REUSE_SHARE = old
