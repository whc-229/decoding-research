"""偏置–自由度的抽象模型（规则距离模型）。

问题：N 个决策位，每位 m 种取值；规则串 R = 全 0；目标 T 与 R 在 d 个位置不同（取值为 1..m-1 之一）。
f(x) = 解码结果与 T 的汉明距离（最小化）。不建模级联（实验 0～2 表明局部性不是决定因素）。

两种编码（基因都在 [0,1)）：
  PS（逐位基因，dec5 的抽象）：n = N，第 i 位取值 floor(g_i·m)。
  SP_K（稀疏偏离，dec6/dec9 的抽象）：n = 2K，第 k 个槽 (p, a)：a ≥ 0.6 时生效（随机基因生效概率 q = 0.4），
         在位置 floor(p·N) 偏离，取值 1 + floor(u·(m−1))，u = (a−0.6)/0.4；同一位置多个槽时后面的覆盖前面的。

理论量：
  init_dist_PS = N(1−1/m)
  init_dist_SP = (N−d)π + d(1 − π/(m−1))，π = 1 − (1 − q/N)^K
  目标的冗余度（随机基因恰好解码成 T 的概率，忽略碰撞）：
     r_SP(K) = C(K,d)·d!·(q/(N(m−1)))^d·(1−q)^(K−d)   （K ≥ d，否则为 0）
     r_PS    = m^(−N)
  r_SP(K) 对 K 的最大值在 K* ≈ d/q − 1 附近（相邻比值 r(K+1)/r(K) = (K+1)(1−q)/(K+1−d) = 1 处）。
"""
import math
import numpy as np

Q = 0.4
DEV_ON = 0.6


def make_target(N, d, m, rng):
    T = np.zeros(N, dtype=int)
    pos = rng.choice(N, d, replace=False)
    T[pos] = rng.integers(1, m, d)
    return T


def decode_ps(g, N, m, rho=None):
    """rho=None：均匀（取到规则值的概率 1/m）；rho 给定：以概率 rho 取规则值 0，否则在 1..m-1 中均匀（有偏的逐位编码，dec5 实测 rho≈0.55～0.65）"""
    if rho is None:
        return np.minimum((g * m).astype(int), m - 1)
    return np.where(g < rho, 0, 1 + np.minimum(((g - rho) / (1 - rho) * (m - 1)).astype(int), m - 2))


def decode_sp(g, N, m, K):
    x = np.zeros(N, dtype=int)
    p, a = g[0:2 * K:2], g[1:2 * K:2]
    on = a >= DEV_ON
    pos = np.minimum((p * N).astype(int), N - 1)
    u = (a - DEV_ON) / (1 - DEV_ON)
    val = 1 + np.minimum((u * (m - 1)).astype(int), m - 2)
    for k in np.nonzero(on)[0]:          # 顺序覆盖，与 devmap 的 dict 赋值一致
        x[pos[k]] = val[k]
    return x


def init_dist_ps(N, d, m, rho=None):
    rho = 1 / m if rho is None else rho
    return (N - d) * (1 - rho) + d * (1 - (1 - rho) / (m - 1))


def init_dist_sp(N, d, m, K, q=Q):
    pi = 1 - (1 - q / N) ** K
    return (N - d) * pi + d * (1 - pi / (m - 1))


def log_redundancy_sp(N, d, m, K, q=Q):
    if K < d:
        return -math.inf
    return (math.lgamma(K + 1) - math.lgamma(K - d + 1) + d * math.log(q / (N * (m - 1))) + (K - d) * math.log(1 - q))


def log_redundancy_ps(N, m):
    return -N * math.log(m)


def stirling2(n, k):
    S = [[0] * (k + 1) for _ in range(n + 1)]
    S[0][0] = 1
    for i in range(1, n + 1):
        for j in range(1, min(i, k) + 1):
            S[i][j] = j * S[i - 1][j] + S[i - 1][j - 1]
    return S[n][k]


def redundancy_sp_exact(N, d, m, K, q=Q):
    """随机基因恰好解码成 T 的精确概率（同一位置多槽时后者覆盖）：
    Σ_{J≥d} C(K,J) q^J (1−q)^(K−J) · N^(−J) · d!·S(J,d) · (m−1)^(−d)，S 为第二类 Stirling 数。
    含义：J 个生效槽必须全部落在 d 个目标位置上、覆盖每一个，且每个位置最后写入的取值正确。"""
    if d == 0:
        return (1 - q) ** K
    tot = 0.0
    for J in range(d, K + 1):
        tot += math.comb(K, J) * q ** J * (1 - q) ** (K - J) * N ** (-J) * math.factorial(d) * stirling2(J, d)
    return tot * (m - 1) ** (-d)


def k_star_exact(N, d, m, q=Q, kmax=None):
    kmax = kmax or max(4 * d, 10)
    return max(range(max(d, 1), kmax + 1), key=lambda K: redundancy_sp_exact(N, d, m, K, q))


def k_star(d, q=Q):
    """r_SP(K) 最大的 K：r(K+1)/r(K) = (K+1)(1−q)/(K+1−d) ≥ 1 ⇔ K+1 ≤ d/q"""
    return max(d, int(math.floor(d / q)) - 1)


# ---------------- 与 ga.py 相同的 GA（SBX η=20 p=0.9、多项式变异 η=20 每位 1/n、截断选择） ----------------
UB = 0.99


def sbx(a, b, rng, eta=20.0):
    c1, c2 = a.copy(), b.copy()
    if rng.random() > 0.9:
        return c1, c2
    n = len(a)
    mask = (rng.random(n) <= 0.5) & (np.abs(a - b) > 1e-14)
    u = rng.random(n)
    beta = np.where(u <= 0.5, (2 * u) ** (1 / (eta + 1)), (1 / (2 * (1 - u))) ** (1 / (eta + 1)))
    c1 = np.where(mask, 0.5 * ((1 + beta) * a + (1 - beta) * b), a)
    c2 = np.where(mask, 0.5 * ((1 - beta) * a + (1 + beta) * b), b)
    return np.clip(c1, 0, UB), np.clip(c2, 0, UB)


def pm(x, rng, eta=20.0):
    n = len(x)
    mask = rng.random(n) < 1.0 / n
    u = rng.random(n)
    dlt = np.where(u < 0.5, (2 * u) ** (1 / (eta + 1)) - 1, 1 - (2 * (1 - u)) ** (1 / (eta + 1)))
    return np.clip(np.where(mask, x + dlt * UB, x), 0, UB)


def run_ga(fit, n, rng, pop=30, evals=465):
    """单目标版本（NSGA-II 在单目标下即按目标值截断）。返回 (最终最好值, 每次评价后的最好值轨迹)"""
    P = [rng.uniform(0, UB, n) for _ in range(pop)]
    F = [fit(x) for x in P]
    traj = list(np.minimum.accumulate(F))
    ev = pop
    while ev < evals:
        kids = []
        while len(kids) < pop and ev + len(kids) < evals:
            a, b = P[rng.integers(pop)], P[rng.integers(pop)]
            c1, c2 = sbx(a, b, rng)
            kids += [pm(c1, rng), pm(c2, rng)]
        kids = kids[:min(pop, evals - ev)]
        FK = [fit(x) for x in kids]
        for f in FK:
            traj.append(min(traj[-1], f))
        ev += len(kids)
        U = P + kids; FU = F + FK
        idx = np.argsort(FU, kind="stable")[:pop]
        P = [U[i] for i in idx]; F = [FU[i] for i in idx]
    return min(F), traj


def run_encoding(enc, N, d, m, K, seed, evals=465):
    rng = np.random.default_rng(seed)
    T = make_target(N, d, m, rng)
    if enc.startswith("PS"):
        rho = float(enc[2:]) if len(enc) > 2 else None
        fit = lambda g: int(np.sum(decode_ps(g, N, m, rho) != T))
        n = N
    else:
        fit = lambda g: int(np.sum(decode_sp(g, N, m, K) != T))
        n = 2 * K
    return run_ga(fit, n, rng, evals=evals)
