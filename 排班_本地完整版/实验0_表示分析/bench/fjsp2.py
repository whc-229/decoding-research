"""FJSP 解码 v2：在 fjsp.py 基础上
  1. 插空（insert=True）：工序放进机器上最早能容纳它的空闲段（主动调度），所有编码都用同一种排程方式；
  2. 规则步不再排序整张候选表（只取最小），稀疏编码更快；
  3. 参照值：最优值 / 已知最好上界（BKS）/ 下界分开给出。
insert=False 时与 fjsp.py 逐解相同（check_v2.py 核对）。"""
import bisect, json, math, os
import numpy as np
import fjsp as F1

ROOT = F1.ROOT
DEV_ON = 0.6
load, meta, nvar, k_slots = F1.load, F1.meta, F1.nvar, F1.k_slots


def refs(name, Mt=None):
    d = (Mt or meta())[name]
    b = d.get("bounds") or {}
    opt = d.get("optimum")
    return dict(opt=opt, bks=opt or b.get("upper"), lb=opt or b.get("lower"))


class Sched:
    __slots__ = ("inst", "insert", "nxt", "jr", "busy", "mr", "rem", "tw", "cache")

    def __init__(s, inst, insert):
        s.inst, s.insert = inst, insert
        nj, nm = inst["nj"], inst["nm"]
        s.nxt = [0] * nj; s.jr = [0] * nj; s.mr = [0] * nm
        s.busy = [[] for _ in range(nm)]          # 每台机器的 (开始, 结束)，按开始排序
        s.rem = [sum(min(p for _, p in op) for op in ops) for ops in inst["jobs"]]
        s.tw = 0
        s.cache = {}                              # (工件, 机器) → 候选元组；只有该机器或该工件变化时才重算

    def start_on(s, k, ready, p):
        if not s.insert:
            return max(ready, s.mr[k])
        prev = 0
        for a, b in s.busy[k]:
            st = max(ready, prev)
            if st + p <= a:
                return st
            prev = b
        return max(ready, prev)

    def candidates(s):
        C = []
        for j, ops in enumerate(s.inst["jobs"]):
            o = s.nxt[j]
            if o < len(ops):
                cache = s.cache
                for (k, p) in ops[o]:
                    v = cache.get((j, k))
                    if v is None:
                        st = s.start_on(k, s.jr[j], p)
                        v = cache[(j, k)] = (st + p, -s.rem[j], p, j, k, st)
                    C.append(v)
        return C

    def apply(s, c):
        end, _, p, j, k, st = c
        cache = s.cache
        for (kk, _) in s.inst["jobs"][j][s.nxt[j]]:
            cache.pop((j, kk), None)
        if True:                                  # 机器 k 的时间表变了：所有在 k 上的候选失效
            for jj in range(s.inst["nj"]):
                cache.pop((jj, k), None)
        s.jr[j] = end
        if s.insert:
            bisect.insort(s.busy[k], (st, end))
        s.mr[k] = max(s.mr[k], end); s.tw += p
        s.rem[j] -= min(pp for _, pp in s.inst["jobs"][j][s.nxt[j]])
        s.nxt[j] += 1

    def objs(s):
        return (max(s.jr), s.tw)


def decode(inst, enc, g=None, insert=True, picks=None):
    """返回 (makespan, total_workload)。picks（list）给出时记录每步选的规则排序名次（用于算规则距离）。"""
    N = inst["nops"]
    S = Sched(inst, insert)
    if enc == "rk":
        return decode_rk(inst, g, insert)
    dev = {}
    if enc.startswith("sp"):
        K = int(enc[2:])
        for k in range(K):
            p, a = g[2 * k], g[2 * k + 1]
            if a >= DEV_ON:
                dev[min(int(p * N), N - 1)] = (a - DEV_ON) / (1 - DEV_ON)
    for step in range(N):
        C = S.candidates()
        if enc == "pd":
            C.sort(); i = min(int(g[step] * len(C)), len(C) - 1); c = C[i]
        else:
            u = dev.get(step)
            if u is None or len(C) < 2:
                c = min(C); i = 0
            else:
                C.sort(); i = 1 + min(int(u * (len(C) - 1)), len(C) - 2); c = C[i]
        if picks is not None:
            picks.append(i)
        S.apply(c)
    return S.objs()


def decode_rk(inst, g, insert=True):
    N = inst["nops"]
    owner = [j for j, ops in enumerate(inst["jobs"]) for _ in ops]
    seq = [owner[i] for i in np.argsort(g[:N], kind="stable")]
    S = Sched(inst, insert)
    base = np.cumsum([0] + [len(o) for o in inst["jobs"]])
    for j in seq:
        o = S.nxt[j]; opts = inst["jobs"][j][o]
        k, p = opts[min(int(g[N + base[j] + o] * len(opts)), len(opts) - 1)]
        st = S.start_on(k, S.jr[j], p)
        S.apply((st + p, 0, p, j, k, st))
    return S.objs()
