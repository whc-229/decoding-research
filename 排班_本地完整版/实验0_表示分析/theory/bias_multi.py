"""T11：在规则距离模型（model.py）上检验两种"最优槽数 K 大于 d"的候选解释。

A. 偏离值有偏：生效偏离以概率 β 取"规则的次优值"（固定记为值 1），以 1 − β 在其余 m − 2 个值（2..m−1）中均匀取；
   目标 T 在与 R 不同的 d 个位置上，以概率 γ 取值 1，否则在 2..m−1 中均匀取。β = 1/(m−1) 时与原模型逐位相同。
   单目标 GA（model.run_ga，与 ga.py 相同的算子），f = 解码结果与 T 的汉明距离。
B. 多个目标：t 个目标 T_1..T_t，各与 R 相差 d_i 个位置；NSGA-II（种群 30，与 ga.py 同样的非支配排序 + 拥挤度），
   目标向量 = (到 T_1 的距离, …, 到 T_t 的距离)；指标 = 各目标"已评价解中的最小距离"的平均（越小越好），
   对应 HV 要覆盖整条前沿。目标的偏离位置可以相互独立（indep），也可以嵌套（nest：近目标的偏离是远目标的子集）。
D（额外，不在待检验文档的要求里）：多余偏离的代价 λ < 1，f = 目标位置上的错误数 + λ·非目标位置上的偏离数。
   用来对照"多余的槽在真实问题里不是满额噪声"这一解释。

用法: python bias_multi.py test            自检（β = 1/(m−1) 时与 model.decode_sp 逐解相同）
      python bias_multi.py A|B|D 进程数     扫描，结果写 t11_<A|B|D>.json（原始值，分析见 analyze_t11.py）
"""
import json, math, os, sys, itertools, multiprocessing as mp
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model as Mo  # noqa

N, M_VAL = 100, 4
KS = [2, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 80]
BUDGETS = [465, 2000]
SEEDS = range(20)
POP = 30


# ---------------- 解码与目标 ----------------
def decode_sp_bias(g, N, m, K, beta):
    """稀疏偏离解码，偏离取值有偏：u < β 取值 1（规则的次优值），否则在 2..m−1 中均匀；其余同 model.decode_sp。
    β = 1/(m−1) 时取值映射与 decode_sp 的 1 + floor(u·(m−1)) 相同。"""
    x = np.zeros(N, dtype=int)
    p, a = g[0:2 * K:2], g[1:2 * K:2]
    on = a >= Mo.DEV_ON
    pos = np.minimum((p * N).astype(int), N - 1)
    u = (a - Mo.DEV_ON) / (1 - Mo.DEV_ON)
    if m == 2:
        val = np.ones(K, dtype=int)
    else:
        rest = 2 + np.minimum(((u - beta) / (1 - beta) * (m - 2)).astype(int), m - 3)
        val = np.where(u < beta, 1, rest)
    for k in np.nonzero(on)[0]:          # 顺序覆盖，与 decode_sp 一致
        x[pos[k]] = val[k]
    return x


def make_target_bias(N, d, m, gamma, rng, pos=None):
    """目标串：在 d 个位置偏离（pos 给定时用给定位置），取值以概率 γ 为 1，否则在 2..m−1 中均匀"""
    T = np.zeros(N, dtype=int)
    if pos is None:
        pos = rng.choice(N, d, replace=False)
    v = rng.random(len(pos))
    other = 2 + rng.integers(0, max(m - 2, 1), len(pos)) if m > 2 else np.ones(len(pos), dtype=int)
    T[pos] = np.where(v < gamma, 1, other)
    return T


def p_hit(m, beta, gamma):
    """一个生效偏离落在目标位置上时，取值恰好正确的概率（平均场模型里替换原来的 1/(m−1)）"""
    if m == 2:
        return 1.0
    return gamma * beta + (1 - gamma) * (1 - beta) / (m - 2)


# ---------------- 多目标 NSGA-II（与 ga.py 相同的选择规则，向量化） ----------------
def nd_sort(F):
    """非支配排序：F 为 (n, M) 数组，返回各层的下标列表（与 ga.nd_sort 结果相同，层内顺序按下标）"""
    le = np.all(F[:, None, :] <= F[None, :, :], axis=2)
    lt = np.any(F[:, None, :] < F[None, :, :], axis=2)
    dom = le & lt                        # dom[p, q]：p 支配 q
    cnt = dom.sum(0)
    fronts, left = [], np.ones(len(F), bool)
    while left.any():
        fr = np.nonzero(left & (cnt == 0))[0]
        fronts.append(list(fr))
        left[fr] = False
        cnt = cnt - dom[fr].sum(0)
    return fronts


def crowd(F, idx):
    """拥挤距离（任意目标数，与 ga.crowd 的二目标版本同一定义）"""
    d = {i: 0.0 for i in idx}
    for j in range(F.shape[1]):
        s = sorted(idx, key=lambda i: F[i, j])
        d[s[0]] = d[s[-1]] = float("inf")
        rg = F[s[-1], j] - F[s[0], j] or 1.0
        for k in range(1, len(s) - 1):
            d[s[k]] += (F[s[k + 1], j] - F[s[k - 1], j]) / rg
    return d


def run_nsga(fvec, n, rng, evals):
    """NSGA-II（种群 30、SBX + 多项式变异，同 model/ga.py）。fvec(g) 返回各目标的距离向量。
    返回：每个检查点上"各目标在已评价解中的最小距离"（列表的列表）"""
    P = [rng.uniform(0, Mo.UB, n) for _ in range(POP)]
    F = [fvec(x) for x in P]
    best = np.min(np.array(F), axis=0)
    ev = POP
    out = {}
    while ev < evals:
        kids = []
        while len(kids) < POP and ev + len(kids) < evals:
            a, b = P[rng.integers(POP)], P[rng.integers(POP)]
            c1, c2 = Mo.sbx(a, b, rng)
            kids += [Mo.pm(c1, rng), Mo.pm(c2, rng)]
        kids = kids[:min(POP, evals - ev)]
        FK = [fvec(x) for x in kids]
        for f in FK:
            ev += 1
            best = np.minimum(best, f)
            if ev in BUDGETS:
                out[ev] = best.tolist()
        U = P + kids; FU = np.array(F + FK, dtype=float)
        newP = []
        for fr in nd_sort(FU):
            if len(newP) + len(fr) <= POP:
                newP += fr
            else:
                cd = crowd(FU, fr)
                newP += sorted(fr, key=lambda i: -cd[i])[:POP - len(newP)]
                break
        P = [U[i] for i in newP]; F = [FU[i] for i in newP]
    return out


# ---------------- 扫描任务 ----------------
A_BG = [(1 / 3, None), (0.5, 0.0), (0.5, 0.5), (0.5, 1.0), (0.85, 0.0), (0.85, 0.5), (0.85, 1.0)]   # (β, γ)；β=1/3 即均匀，γ 无关
A_DS = [2, 5, 10, 20, 40]
# B：目标集合（名称, 各目标 d_i, 结构）
B_SETS = [("t1_d2", [2], "indep"), ("t1_d10", [10], "indep"), ("t1_d20", [20], "indep"), ("t1_d40", [40], "indep"),
          ("2,2", [2, 2], "indep"), ("2,10", [2, 10], "indep"), ("2,20", [2, 20], "indep"), ("2,40", [2, 40], "indep"),
          ("10,10", [10, 10], "indep"), ("10,40", [10, 40], "indep"),
          ("2⊂10", [2, 10], "nest"), ("2⊂20", [2, 20], "nest"), ("2⊂40", [2, 40], "nest"),
          ("2,10,30", [2, 10, 30], "indep"), ("2,20,40", [2, 20, 40], "indep"), ("2⊂20⊂40", [2, 20, 40], "nest")]
D_LAM = [1.0, 0.5, 0.25, 0.1]
D_DS = [2, 5, 10, 20]


def job_A(arg):
    """检验 A 的一格：(β, γ, d, K, 种子) → 各预算下的最终最好汉明距离"""
    beta, gamma, d, K, s = arg
    rng_t = np.random.default_rng(1000 * d + s)                  # 同 (d, 种子) 下各 K、各 β 共用目标位置
    pos = rng_t.choice(N, d, replace=False)
    T = make_target_bias(N, d, M_VAL, 1 / 3 if gamma is None else gamma, rng_t, pos)
    rng = np.random.default_rng(7919 * s + 13 * K + d)
    fit = lambda g: int(np.sum(decode_sp_bias(g, N, M_VAL, K, beta) != T))
    _, traj = Mo.run_ga(fit, 2 * K, rng, evals=max(BUDGETS))
    return arg, [int(traj[b - 1]) for b in BUDGETS]


def targets_B(ds, kind, s):
    """B 的目标集合：indep 时各目标位置独立抽；nest 时按 d 从小到大嵌套（大目标包含小目标的全部偏离，且取值相同）"""
    rng = np.random.default_rng(500000 + 1000 * sum(ds) + 37 * len(ds) + s)
    Ts = []
    if kind == "indep":
        for d in ds:
            Ts.append(make_target_bias(N, d, M_VAL, 1 / 3, rng))
    else:
        order = rng.permutation(N)
        vals = 1 + rng.integers(0, M_VAL - 1, N)
        for d in ds:
            T = np.zeros(N, dtype=int); T[order[:d]] = vals[order[:d]]; Ts.append(T)
    return np.array(Ts)


def job_B(arg):
    """检验 B 的一格：(集合名, K, 种子) → 各预算下各目标的最小距离"""
    name, K, s = arg
    ds, kind = next((ds, k) for n, ds, k in B_SETS if n == name)
    Ts = targets_B(ds, kind, s)
    rng = np.random.default_rng(7919 * s + 13 * K + 101 * len(ds))
    fvec = lambda g: np.sum(Mo.decode_sp(g, N, M_VAL, K)[None, :] != Ts, axis=1).astype(float)
    out = run_nsga(fvec, 2 * K, rng, max(BUDGETS))
    return arg, [out[b] for b in BUDGETS]


def job_D(arg):
    """额外检验 D 的一格：(λ, d, K, 种子) → 各预算下的最好 f 与其中"目标位置错误数"(按 f 最好的解记)"""
    lam, d, K, s = arg
    rng_t = np.random.default_rng(1000 * d + s)
    T = Mo.make_target(N, d, M_VAL, rng_t)
    tgt = T != 0
    rng = np.random.default_rng(7919 * s + 13 * K + d)

    def fit(g):
        x = Mo.decode_sp(g, N, M_VAL, K)
        return float(np.sum((x != T) & tgt) + lam * np.sum((x != 0) & ~tgt))
    _, traj = Mo.run_ga(fit, 2 * K, rng, evals=max(BUDGETS))
    return arg, [float(traj[b - 1]) for b in BUDGETS]


def selftest():
    """自检：β = 1/(m−1) 时 decode_sp_bias 与 model.decode_sp 逐解相同；nd_sort 与 ga.nd_sort 相同"""
    rng = np.random.default_rng(0); bad = 0
    for m in (3, 4, 5):
        for K in (1, 5, 30, 80):
            for _ in range(2000):
                g = rng.uniform(0, Mo.UB, 2 * K)
                bad += int(np.any(decode_sp_bias(g, N, m, K, 1 / (m - 1)) != Mo.decode_sp(g, N, m, K)))
    print("decode_sp_bias 与 decode_sp 不一致:", bad)
    sys.path.insert(0, os.path.dirname(HERE))
    import importlib.util
    spec = importlib.util.spec_from_file_location("ga_ref", os.path.join(os.path.dirname(HERE), "ga.py"))
    src = open(spec.origin, encoding="utf-8").read()
    ns = {}
    exec(src[src.index("def nd_sort"):src.index("def sbx")], ns)   # 只取 ga.py 的 nd_sort / crowd，避免导入 exp0lib
    bad2 = 0
    for _ in range(300):
        F = rng.integers(0, 6, (60, 2)).astype(float)
        a = [sorted(f) for f in nd_sort(F)]
        b = [sorted(f) for f in ns["nd_sort"]([tuple(r) for r in F.tolist()])]
        bad2 += int(a != b)
        idx = a[0]
        c1, c2 = crowd(F, idx), ns["crowd"]([tuple(r) for r in F.tolist()], idx)
        bad2 += int(any(abs(c1[i] - c2[i]) > 1e-9 if math.isfinite(c2[i]) else math.isfinite(c1[i]) for i in idx))
    print("nd_sort / crowd 与 ga.py 不一致:", bad2)
    # p_hit 在 β = 1/(m−1) 时等于 1/(m−1)
    print("p_hit(4, 1/3, γ) =", [round(p_hit(4, 1 / 3, g), 4) for g in (0, .5, 1)])
    # 经验命中率：随机生效偏离在目标位置上取对值的频率
    for beta, gamma in [(0.85, 1.0), (0.85, 0.0), (0.5, 0.5)]:
        hit = tot = 0
        for s in range(300):
            T = make_target_bias(N, 20, 4, gamma, np.random.default_rng(s))
            g = np.random.default_rng(10 ** 6 + s).uniform(0, Mo.UB, 2 * 50)
            x = decode_sp_bias(g, N, 4, 50, beta)
            msk = (T != 0) & (x != 0)
            hit += int(np.sum(x[msk] == T[msk])); tot += int(msk.sum())
        print(f"β={beta} γ={gamma}: 经验命中率 {hit / tot:.3f}，p_hit = {p_hit(4, beta, gamma):.3f}")
    return bad + bad2


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "test":
        sys.exit(1 if selftest() else 0)
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    if mode == "A":
        jobs = [(b, g, d, K, s) for b, g in A_BG for d in A_DS for K in KS for s in SEEDS]; fn = job_A
    elif mode == "B":
        jobs = [(n, K, s) for n, _, _ in B_SETS for K in KS for s in SEEDS]; fn = job_B
    else:
        jobs = [(l, d, K, s) for l in D_LAM for d in D_DS for K in KS for s in SEEDS]; fn = job_D
    jobs.sort(key=lambda a: -a[-2])          # 大 K 先跑，负载均衡
    with mp.Pool(procs) as p:
        res = p.map(fn, jobs, chunksize=4)
    json.dump({"N": N, "m": M_VAL, "KS": KS, "BUDGETS": BUDGETS, "rows": [[list(a), v] for a, v in res]},
              open(os.path.join(HERE, f"t11_{mode}.json"), "w"), ensure_ascii=False)
    print("done", mode, len(res))
