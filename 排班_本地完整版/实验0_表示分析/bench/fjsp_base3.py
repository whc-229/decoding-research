"""T13：最接近的已有方法作为对照（2026-10-23）。不修改 fjsp2.py / moea_fjsp2.py，只在它们外面加新编码。
所有编码都用 fjsp2.Sched（插空、同一规则 ECT+MWKR+SPT、同一候选集）。

新编码（基因都在 [0, 0.99]）：
  db{ρ}    稠密有偏逐步编码（HBSS / LDS 思想的逐步版本）：每步一个基因 g；g ≥ 1 − ρ 时偏离，u = (g − 1 + ρ)/ρ 在规则排序中
           首选以外的候选里均匀选（与 sp 的偏离语义相同），否则取规则首选。随机基因下每步以概率 ρ 偏离，期望偏离率与 sp 相同。
           等价于"每步一个固定位置的偏离槽"：与 sp 的唯一区别是偏离的位置不可进化、槽数 = 工序数。
  hs       启发式空间（Storer, Wu & Vaccari 1992；Dorndorf & Pesch 1995 的优先规则 GA）：每步一个基因，选 6 条规则之一，
           按该规则在候选里取最优：ECT、SPT、MWKR、LWKR、EST（最早开始）、MOR（剩余工序最多）。并列时都再按 ECT。
  ps{ε}    问题空间（Storer, Wu & Vaccari 1992）：每个 (工序, 可选机器) 一个基因，扰动加工时间 p' = p·(1 + ε(2g/0.99 − 1))；
           在扰动后的数据上按 ECT+MWKR 规则逐步构造，记下每步选的 (工件, 机器)，再用真实加工时间按同样顺序、同样机器插空重放得到目标值。
           ε → 0 时就是规则解。

新算法（在 moea_fjsp3.py）：pls —— 偏离空间上的 Pareto 局部搜索（LNS / 迭代贪心思想）：从规则解出发，每次从存档里随机取一个解，
  重抽 j 个偏离槽（"拆掉并重建" j 处偏离），非支配则进存档。编码用 sp（同 ρ），只换搜索算法。

decode3(inst, enc, g, picks) 返回 (makespan, total_workload)；picks 给出时记每步所选候选在"真实数据上的规则排序"中的名次（0 = 规则首选），
口径与 fjsp2.decode 相同，用来数相对规则的偏离步数。"""
import numpy as np
import fjsp2 as F

UB = 0.99
RULES = ("ECT", "SPT", "MWKR", "LWKR", "EST", "MOR")


def is_new(enc):
    return enc == "hs" or enc.startswith("db") or enc.startswith("ps")


def n_options(inst):
    return sum(len(op) for ops in inst["jobs"] for op in ops)


def nvar3(inst, enc):
    if enc.startswith("ps"):
        return n_options(inst)
    return inst["nops"]                         # db、hs：每步一个基因


def _rank_true(C, c):
    """c 在规则排序 sorted(C) 中的名次"""
    return sorted(C).index(c)


def _key(rule, c, S):
    end, mrem, p, j, k, st = c
    if rule == "ECT":
        return c
    if rule == "SPT":
        return (p, c)
    if rule == "MWKR":
        return (mrem, c)
    if rule == "LWKR":
        return (-mrem, c)
    if rule == "EST":
        return (st, c)
    if rule == "MOR":
        return (-(len(S.inst["jobs"][j]) - S.nxt[j]), c)
    raise ValueError(rule)


def decode3(inst, enc, g, insert=True, picks=None):
    N = inst["nops"]
    if enc.startswith("ps"):
        return _decode_ps(inst, float(enc[2:]), g, insert, picks)
    S = F.Sched(inst, insert)
    if enc.startswith("db"):
        rho = float(enc[2:]); on = 1.0 - rho
    for step in range(N):
        C = S.candidates()
        if enc == "hs":
            r = RULES[min(int(g[step] / UB * len(RULES)), len(RULES) - 1)]
            c = min(C, key=lambda cc: _key(r, cc, S))
        else:
            a = g[step]
            if a >= on and len(C) >= 2:
                u = (a - on) / (1.0 - on)            # 与 fjsp2.decode 的 sp 相同
                Cs = sorted(C); c = Cs[1 + min(int(u * (len(C) - 1)), len(C) - 2)]
            else:
                c = min(C)
        if picks is not None:
            picks.append(_rank_true(C, c))
        S.apply(c)
    return S.objs()


def _perturbed(inst, eps, g):
    jobs, i = [], 0
    for ops in inst["jobs"]:
        jo = []
        for op in ops:
            oo = []
            for (k, p) in op:
                oo.append((k, p * (1.0 + eps * (2.0 * g[i] / UB - 1.0)))); i += 1
            jo.append(oo)
        jobs.append(jo)
    return dict(inst, jobs=jobs)


def _decode_ps(inst, eps, g, insert, picks):
    """扰动数据上按规则构造 → 记下 (工件, 机器) 顺序 → 真实数据上重放"""
    P = _perturbed(inst, eps, g)
    S1 = F.Sched(P, insert)
    seq = []
    for _ in range(inst["nops"]):
        c = min(S1.candidates())
        seq.append((c[3], c[4])); S1.apply(c)
    S = F.Sched(inst, insert)
    for (j, k) in seq:
        C = S.candidates()
        c = next(cc for cc in C if cc[3] == j and cc[4] == k)
        if picks is not None:
            picks.append(_rank_true(C, c))
        S.apply(c)
    return S.objs()
