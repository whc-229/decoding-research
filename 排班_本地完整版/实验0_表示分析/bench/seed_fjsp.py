"""双段随机键（rk）的启发式初始化，用于"规则放进初始种群 vs 规则放进解码器"的对照（T9）。
  rule_genome：把规则解（ECT+MWKR，与稀疏编码全不偏离时相同）编码成 rk 基因——工序键按规则的排程顺序递增，机器基因指向规则选的机器。
               rk 解码按同一顺序、同一机器逐个插空，状态完全相同，所以解出的就是规则解（check_seed.py 核对）。
  glr_genome：Zhang, Gao & Shi (2011, Expert Syst. Appl. 38:3563) 的 GLR 初始化——机器分配按 全局选择 GS 60%、局部选择 LS 30%、随机 RS 10%；
              工序顺序随机（工序键均匀随机）。
    GS：全局负荷数组（所有工件共用），工件随机顺序，每道工序选 负荷+加工时间 最小的机器（并列取第一个），再把加工时间加到该机器负荷上；
    LS：同 GS，但每个工件开始时负荷数组清零，工件按编号顺序；
    RS：每道工序随机选一台可选机器。
初始种群（种群 30）：rk+seed = 1 个规则解 + 29 个均匀随机；rk+glr = 30 个 GLR；rk+glr+seed = 1 个规则解 + 29 个 GLR。"""
import numpy as np
import fjsp2 as F

UB = 0.99


def _layout(inst):
    base = np.cumsum([0] + [len(o) for o in inst["jobs"]])
    return inst["nops"], base


def _mgene(idx, n):
    return (idx + 0.5) / n                     # int(g × n) = idx


def rule_genome(inst):
    N, base = _layout(inst)
    S = F.Sched(inst, True)
    g = np.zeros(2 * N)
    used = [0] * inst["nj"]
    for t in range(N):
        c = min(S.candidates())
        _, _, p, j, k, _ = c
        o = S.nxt[j]
        opts = inst["jobs"][j][o]
        idx = next(i for i, (kk, pp) in enumerate(opts) if kk == k and pp == p)
        g[base[j] + used[j]] = (t + 0.5) / N * UB  # 工件 j 的第 used[j] 个位置 ↔ 它的第 o 道工序（used[j] == o）
        used[j] += 1
        g[N + base[j] + o] = _mgene(idx, len(opts))
        S.apply(c)
    return g


def glr_genome(inst, rng, mode=None):
    N, base = _layout(inst)
    if mode is None:
        u = rng.random()
        mode = "GS" if u < 0.6 else ("LS" if u < 0.9 else "RS")
    g = np.empty(2 * N)
    g[:N] = rng.uniform(0, UB, N)
    jobs = inst["jobs"]
    order = rng.permutation(len(jobs)) if mode == "GS" else range(len(jobs))
    load = {}
    for j in order:
        if mode == "LS":
            load = {}
        for o, opts in enumerate(jobs[j]):
            if mode == "RS":
                idx = int(rng.integers(len(opts)))
            else:
                idx = min(range(len(opts)), key=lambda i: load.get(opts[i][0], 0) + opts[i][1])
                k, p = opts[idx]
                load[k] = load.get(k, 0) + p
            g[N + base[j] + o] = _mgene(idx, len(opts))
    return g


def init_pop(inst, arm, rng, pop, nv):
    """arm ∈ rk+seed, rk+glr, rk+glr+seed；返回 pop 个基因。"""
    seed = arm.endswith("+seed")
    glr = "+glr" in arm
    P = [rule_genome(inst)] if seed else []
    while len(P) < pop:
        P.append(glr_genome(inst, rng) if glr else rng.uniform(0, UB, nv))
    return P
