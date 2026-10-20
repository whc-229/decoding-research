"""dec8：偏离密度编码（把 dec5 的"逐班基因"和 dec6 的"稀疏偏离"统一成一个参数 d）。

每班一个机器人基因 x[i]（与 dec5 相同的位置），τ = 1 − d：
  x[i] < τ  → 按规则：复用出勤最少（同则剩余工时多）的可用机器人；没有可用机器人时先回溯修复（窗口 12 班），
              修复不了才新开，新开类型 = int(x[i]/τ · T)（每班自带类型选择）。
  x[i] ≥ τ  → 偏离：u = (x[i] − τ)/d；u < 0.7 → 改派给排名第 2…n 的可用机器人（可用数 < 2 时按规则）；
              u ≥ 0.7 → 新开类型 int((u − 0.7)/0.3 · T)（不受容量预判约束）。
随机初始化时每班偏离的概率就是 d：d 小 ≈ dec6（稀疏偏离），d 大 ≈ 每班都由基因决定。
d 的来源：固定值（按实例给定），或自适应（d = 0.02·30^x[末位]，即 0.02～0.6 的对数均匀）。
工具基因与原来相同。
"""
import copy
import numpy as np
import exp0lib as L

M = L.M
REUSE_SHARE = 0.7
D_MIN, D_MAX = 0.02, 0.6


def density_from_gene(g):
    return D_MIN * (D_MAX / D_MIN) ** float(np.float32(g))


def decode8(sc, x, d=None, W=12):
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x); h = n // 2
    nty = len(sc["R"])
    if d is None:
        d = density_from_gene(x[-1])
    tau = 1.0 - d

    def avail(s):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        return av

    def deviates(i):
        return x[i] >= tau

    def choose(i, nav):
        if deviates(i):
            u = (x[i] - tau) / d
            if u < REUSE_SHARE:
                if nav >= 2:
                    return ("reuse", 1 + min(int(u / REUSE_SHARE * (nav - 1)), nav - 2))
            else:
                return ("new", min(int((u - REUSE_SHARE) / (1 - REUSE_SHARE) * nty), nty - 1))
        if nav > 0:
            return ("reuse", 0)
        return ("new", min(int(min(x[i], tau) / tau * nty), nty - 1))

    def step(s, i, forced=None):
        av = avail(s)
        if forced is not None:
            return 0 if s.dispatch_reuse(av[forced], x[i + h]) else -1
        kind, v = choose(i, len(av))
        if kind == "reuse":
            return 0 if s.dispatch_reuse(av[v], x[i + h]) else -1
        return 1 if s.dispatch_new(v, x[i + h]) else -1

    s = M.Sim(sc, False)
    snaps, forced = [], {}
    i = fixes = 0
    while s.E < sc["T"] and i < h:
        snaps = snaps[:i] + [copy.deepcopy(s)]
        if not avail(s) and s.robots and W > 0 and not deviates(i):
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
                        if step(trial, j, alt if j == t else None) != 0:
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
    return L.Result((float(o[0]), float(o[1])), s, i, 0, fixes, forced)


def rule_solution(sc):
    """纯规则解（所有班次都不偏离，新开类型取 0 型）：用于便宜的实例特征"""
    nv = L.nvar(sc, "dec5")
    return decode8(sc, np.zeros(nv), d=0.02)
