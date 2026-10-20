"""
机制插槽 MOEA 小样例（numpy-only，便于在任何机器上复现）

把一个 MOEA 写成固定骨架 + 3 个"窄接口"插槽：
  slot_step   : 步长（DE 的 F）控制器      state -> F（每个子代一个值）
  slot_inf    : 劣解 archive（JADE 式）    被环境选择淘汰的解存起来，作为差分向量端点
  slot_reuse  : 精英 archive 复用           繁殖时以概率 p 从精英 archive 取基向量

骨架：DE/rand/1/bin + 多项式变异 + 非支配排序/拥挤距离环境选择（NSGA-II 式），
始终维护一个容量为 N 的外部非支配 archive，最终指标在 archive 上计算（所有配置一致）。

步长控制器统一接口（这正是 LLM 要填写的"窄接口"）：
    def rule(state: dict, n: int, rng) -> np.ndarray   # 返回 n 个 F
    state 字段见 SearchState，全是 MOEA 运行时廉价可得的量。
"""
import numpy as np

# ---------------------------------------------------------------- problems
def zdt(name, n):
    def f(X):
        x1 = X[:, 0]
        if name in ("ZDT1", "ZDT2", "ZDT3"):
            g = 1 + 9 * X[:, 1:].mean(1)
        elif name == "ZDT4":
            r = X[:, 1:]
            g = 1 + 10 * (n - 1) + (r ** 2 - 10 * np.cos(4 * np.pi * r)).sum(1)
        elif name == "ZDT6":
            x1 = 1 - np.exp(-4 * X[:, 0]) * np.sin(6 * np.pi * X[:, 0]) ** 6
            g = 1 + 9 * (X[:, 1:].sum(1) / (n - 1)) ** 0.25
        if name in ("ZDT1", "ZDT4"):
            h = 1 - np.sqrt(x1 / g)
        elif name in ("ZDT2", "ZDT6"):
            h = 1 - (x1 / g) ** 2
        elif name == "ZDT3":
            h = 1 - np.sqrt(x1 / g) - (x1 / g) * np.sin(10 * np.pi * x1)
        return np.stack([x1, g * h], 1)
    lb = np.zeros(n); ub = np.ones(n)
    if name == "ZDT4":
        lb[1:] = -5; ub[1:] = 5
    return f, lb, ub


def dtlz(name, M=3, k=None):
    k = k or (5 if name == "DTLZ1" else 10)
    n = M - 1 + k
    def f(X):
        xm = X[:, M - 1:]
        if name == "DTLZ1":
            g = 100 * (k + ((xm - .5) ** 2 - np.cos(20 * np.pi * (xm - .5))).sum(1))
            F = np.ones((len(X), M)) * 0.5 * (1 + g)[:, None]
            for i in range(M):
                F[:, i] *= np.prod(X[:, :M - 1 - i], 1)
                if i > 0:
                    F[:, i] *= 1 - X[:, M - 1 - i]
            return F
        g = ((xm - .5) ** 2).sum(1)
        F = np.ones((len(X), M)) * (1 + g)[:, None]
        for i in range(M):
            F[:, i] *= np.prod(np.cos(X[:, :M - 1 - i] * np.pi / 2), 1)
            if i > 0:
                F[:, i] *= np.sin(X[:, M - 1 - i] * np.pi / 2)
        return F
    return f, np.zeros(n), np.ones(n)


def true_front(name, npts=2000):
    t = np.linspace(0, 1, npts)
    if name in ("ZDT1", "ZDT4"):
        return np.stack([t, 1 - np.sqrt(t)], 1)
    if name == "ZDT2":
        return np.stack([t, 1 - t ** 2], 1)
    if name == "ZDT6":
        t = np.linspace(0.2807753191, 1, npts)
        return np.stack([t, 1 - t ** 2], 1)
    if name == "ZDT3":
        P = np.stack([t, 1 - np.sqrt(t) - t * np.sin(10 * np.pi * t)], 1)
        return P[nondominated_mask(P)]
    # 3-obj simplex / sphere via uniform grid on simplex
    H = 40
    W = np.array([[i, j, H - i - j] for i in range(H + 1) for j in range(H + 1 - i)]) / H
    if name == "DTLZ1":
        return 0.5 * W
    return W / np.linalg.norm(W, axis=1, keepdims=True)


PROBLEMS = {
    "ZDT1": lambda: zdt("ZDT1", 30), "ZDT2": lambda: zdt("ZDT2", 30),
    "ZDT3": lambda: zdt("ZDT3", 30), "ZDT4": lambda: zdt("ZDT4", 10),
    "ZDT6": lambda: zdt("ZDT6", 10), "DTLZ1": lambda: dtlz("DTLZ1"),
    "DTLZ2": lambda: dtlz("DTLZ2"),
}

# ---------------------------------------------------------------- MOO utils
def dominance_matrix(F):
    le = (F[:, None, :] <= F[None, :, :]).all(2)
    lt = (F[:, None, :] < F[None, :, :]).any(2)
    return le & lt          # D[i,j] = i dominates j


def nondominated_mask(F):
    return ~dominance_matrix(F).any(0)


def nd_sort(F):
    D = dominance_matrix(F)
    cnt = D.sum(0)
    rank = np.full(len(F), -1)
    r, cur = 0, np.where(cnt == 0)[0]
    while len(cur):
        rank[cur] = r
        cnt = cnt - D[cur].sum(0)
        cnt[rank >= 0] = -1
        cur = np.where(cnt == 0)[0]
        r += 1
    return rank


def crowding(F):
    n, m = F.shape
    d = np.zeros(n)
    if n <= 2:
        return np.full(n, np.inf)
    for j in range(m):
        o = np.argsort(F[:, j])
        rng = F[o[-1], j] - F[o[0], j]
        d[o[0]] = d[o[-1]] = np.inf
        if rng > 0:
            d[o[1:-1]] += (F[o[2:], j] - F[o[:-2], j]) / rng
    return d


def env_select(F, N):
    """NSGA-II 环境选择，返回保留下标（长度 N）"""
    rank = nd_sort(F)
    keep = []
    for r in range(rank.max() + 1):
        idx = np.where(rank == r)[0]
        if len(keep) + len(idx) <= N:
            keep.extend(idx)
        else:
            cd = crowding(F[idx])
            keep.extend(idx[np.argsort(-cd)[: N - len(keep)]])
            break
    return np.array(keep), rank


def truncate_archive(X, F, N):
    m = nondominated_mask(F)
    X, F = X[m], F[m]
    # 去重
    _, u = np.unique(np.round(F, 12), axis=0, return_index=True)
    X, F = X[u], F[u]
    while len(F) > N:                       # 逐个删除拥挤距离最小者
        cd = crowding(F)
        i = np.argmin(cd)
        X, F = np.delete(X, i, 0), np.delete(F, i, 0)
    return X, F


def igd(A, P):
    d = np.sqrt(((P[:, None, :] - A[None, :, :]) ** 2).sum(2)).min(1)
    return d.mean()

# ---------------------------------------------------------------- step rules
class SHA:
    """JADE 式成功历史均值 + Cauchy 采样（有状态）"""
    def __init__(self):
        self.mu = 0.5
    def __call__(self, state, n, rng):
        F = self.mu + 0.1 * rng.standard_cauchy(n)
        while (F <= 0).any():
            bad = F <= 0
            F[bad] = self.mu + 0.1 * rng.standard_cauchy(bad.sum())
        return np.minimum(F, 1.0)
    def feedback(self, F_succ):
        if len(F_succ):
            self.mu = 0.9 * self.mu + 0.1 * (F_succ ** 2).sum() / F_succ.sum()


def rule_fixed(state, n, rng):
    return np.full(n, 0.5)


def rule_heavy(state, n, rng):
    # 幂律（Pareto, alpha=1.5）步长，中位数约 0.4，无需调参 [M8]
    return np.clip(0.25 * (1 - rng.random(n)) ** (-1 / 1.5), 0.05, 1.2)


def rule_state(state, n, rng):
    # 状态驱动规则（LLM 候选规则的人工替身）：
    # 种群大多已非支配 -> 收敛停滞风险，放大步长探索；成功率很低 -> 再放大
    F = 0.25 + 0.65 * state["rank1_frac"]
    if state["succ"] < 0.05:
        F += 0.2
    return np.clip(F + 0.05 * rng.standard_normal(n), 0.05, 1.2)


STEP_RULES = {"fixed": rule_fixed, "sha": "SHA", "heavy": rule_heavy, "state": rule_state}

# ---------------------------------------------------------------- algorithm
def run(problem, step="fixed", inf=False, reuse=False, N=100, gens=100,
        CR=0.9, p_reuse=0.3, seed=0, step_rule=None, trace=False):
    rng = np.random.default_rng(seed)
    f, lb, ub = PROBLEMS[problem]()
    n = len(lb)
    rule = step_rule or STEP_RULES[step]
    if rule == "SHA":
        rule = SHA()
    X = lb + rng.random((N, n)) * (ub - lb)
    F = f(X)
    AX, AF = truncate_archive(X, F, N)
    IA = np.empty((0, n))
    state = {"gen": 0, "progress": 0.0, "succ": 0.2, "rank1_frac": 0.0,
             "stall": 0, "arch_frac": len(AF) / N}
    hist = []
    # inf / reuse 可以是 bool（静态开关），也可以是 callable(state)->概率（在线调度）
    p_ia_fn = inf if callable(inf) else (lambda s, v=1.0 if inf else 0.0: v)
    p_re_fn = reuse if callable(reuse) else (lambda s, v=p_reuse if reuse else 0.0: v)
    keep_ia = bool(inf)                      # 只要可能用到就维护劣解 archive
    for g in range(gens):
        state["gen"], state["progress"] = g, g / gens
        Fs = np.asarray(rule(state, N, rng), float)
        p_ia, p_re = float(p_ia_fn(state)), float(p_re_fn(state))
        # ---- variation: DE/rand/1/bin
        pool = np.vstack([X, IA]) if (keep_ia and len(IA)) else X
        r0 = rng.integers(0, N, N)
        r1 = rng.integers(0, N, N)
        r2 = rng.integers(0, N, N)
        from_pool = rng.random(N) < p_ia     # 以概率 p_ia 从 种群∪劣解archive 取差分端点
        r2[from_pool] = rng.integers(0, len(pool), from_pool.sum())
        base = X[r0].copy()
        use = rng.random(N) < p_re
        if use.any():
            base[use] = AX[rng.integers(0, len(AX), use.sum())]
        V = base + Fs[:, None] * (X[r1] - pool[r2])
        cross = rng.random((N, n)) < CR
        cross[np.arange(N), rng.integers(0, n, N)] = True
        U = np.where(cross, V, X)
        # polynomial mutation (eta=20, pm=1/n)
        pm = rng.random((N, n)) < 1.0 / n
        u = rng.random((N, n))
        delta = np.where(u < .5, (2 * u) ** (1 / 21) - 1, 1 - (2 * (1 - u)) ** (1 / 21))
        U = np.where(pm, U + delta * (ub - lb), U)
        U = np.clip(U, lb, ub)
        FU = f(U)
        # ---- environmental selection
        allX, allF = np.vstack([X, U]), np.vstack([F, FU])
        keep, rank = env_select(allF, N)
        survived = keep[keep >= N] - N
        succ = len(survived) / N
        if isinstance(rule, SHA):
            rule.feedback(Fs[survived])
        if keep_ia:
            dropped = np.setdiff1d(np.arange(2 * N), keep)
            IA = np.vstack([IA, allX[dropped]])
            if len(IA) > N:
                IA = IA[rng.choice(len(IA), N, replace=False)]
        X, F = allX[keep], allF[keep]
        # ---- archive
        old = len(AF)
        AX, AF = truncate_archive(np.vstack([AX, U]), np.vstack([AF, FU]), N)
        state["succ"] = succ
        state["rank1_frac"] = float((rank[keep] == 0).mean())
        state["arch_frac"] = len(AF) / N
        state["stall"] = 0 if succ > 0.05 else state["stall"] + 1
        if trace:
            hist.append((g, float(np.mean(Fs)), succ, state["rank1_frac"], p_ia, p_re,
                         state["stall"], state["arch_frac"]))
    out = {"AF": AF, "igd": igd(AF, true_front(problem))}
    if trace:
        out["trace"] = hist
    return out


if __name__ == "__main__":
    import time
    t = time.time()
    r = run("ZDT1", step="sha", inf=True, reuse=True, seed=1)
    print("ZDT1 IGD", r["igd"], "time", time.time() - t)
