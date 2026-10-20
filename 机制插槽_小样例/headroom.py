"""提升空间实验：在线调度 vs 静态配置（劣解archive IA + 精英复用 RE）
问题：把"用不用 IA/RE"从固定开关改成随运行状态变化，能否超过
      (a) 全局最好的静态配置；(b) 每个问题事后挑出的最好静态配置（静态上界）？
如果连简单调度都有明显提升空间，这个方向才值得做；否则停在静态机制即可。

用法: python headroom.py [种子数] [进程数] [代数]
输出: headroom_results.csv, headroom_summary.md
"""
import csv, itertools, sys
from multiprocessing import Pool
import numpy as np
import slot_moea as s
from math import erf, sqrt


def wilcoxon(a, b):
    """配对符号秩检验，双侧，正态近似（与 analyze.py 相同）"""
    d = a - b
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return 1.0
    absd = np.abs(d)
    rk = np.argsort(np.argsort(absd)) + 1.0
    for v in np.unique(absd):
        rk[absd == v] = rk[absd == v].mean()
    W = rk[d > 0].sum()
    mu, sd = n * (n + 1) / 4, np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (abs(W - mu) - 0.5) / sd
    return 2 * (1 - 0.5 * (1 + erf(z / sqrt(2))))

SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
PROCS = int(sys.argv[2]) if len(sys.argv) > 2 else 2
GENS = int(sys.argv[3]) if len(sys.argv) > 3 else 500     # N=100 -> 5 万次评价


def on_if(cond):
    """cond(state)->bool；为真时 IA 全开、RE=0.3，否则都关"""
    return (lambda st: 1.0 if cond(st) else 0.0), (lambda st: 0.3 if cond(st) else 0.0)


DYN = {
    "前半开": on_if(lambda st: st["progress"] < 0.5),
    "后半开": on_if(lambda st: st["progress"] >= 0.5),
    "停滞时开": on_if(lambda st: st["stall"] >= 2),
    "饱和时开": on_if(lambda st: st["rank1_frac"] > 0.9),
}
STATIC = {"静态:都关": (False, False), "静态:仅IA": (True, False),
          "静态:仅RE": (False, True), "静态:都开": (True, True)}
NAMES = list(STATIC) + list(DYN)


def job(a):
    p, nm, seed = a
    inf, reuse = STATIC[nm] if nm in STATIC else DYN[nm]
    return p, nm, seed, s.run(p, step="fixed", inf=inf, reuse=reuse, gens=GENS, seed=seed)["igd"]


if __name__ == "__main__":
    jobs = list(itertools.product(s.PROBLEMS, NAMES, range(SEEDS)))
    with Pool(PROCS) as pool:
        rows = pool.map(job, jobs, chunksize=2)
    with open("headroom_results.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["problem", "schedule", "seed", "igd"]); w.writerows(rows)

    get = lambda p, n: np.array([r[3] for r in sorted(rows, key=lambda r: r[2]) if r[0] == p and r[1] == n])
    probs = list(s.PROBLEMS)
    ranks = {n: [] for n in NAMES}
    for p in probs:
        m = {n: get(p, n).mean() for n in NAMES}
        for k, n in enumerate(sorted(NAMES, key=m.get)):
            ranks[n].append(k + 1)
    glob_static = min(STATIC, key=lambda n: np.mean(ranks[n]))
    out = [f"# 提升空间实验（{GENS * 100} 次评价，{SEEDS} 种子，步长固定 F=0.5，平均 IGD）\n",
           f"全局最好的静态配置（按平均排名）：**{glob_static}**。"
           "“静态上界”= 每个问题事后挑出的最好静态配置。p 值为最好调度 vs 全局最好静态，配对 Wilcoxon。\n",
           "| 问题 | " + " | ".join(NAMES) + " | 静态上界/全局静态 | 最好调度/全局静态 | p |",
           "|---" * (len(NAMES) + 4) + "|"]
    for p in probs:
        m = {n: get(p, n).mean() for n in NAMES}
        best_all = min(m.values())
        ub = min(m[n] for n in STATIC)
        bd = min(DYN, key=m.get)
        pv = wilcoxon(get(p, bd), get(p, glob_static))
        cells = [("**%.4g**" if m[n] == best_all else "%.4g") % m[n] for n in NAMES]
        out.append(f"| {p} | " + " | ".join(cells) +
                   f" | {ub / m[glob_static]:.2f} | {m[bd] / m[glob_static]:.2f} ({bd}) | {pv:.2g} |")
    out.append("| 平均排名 | " + " | ".join(f"{np.mean(ranks[n]):.2f}" for n in NAMES) + " | | | |")
    out.append("\n比值 < 1 表示比全局最好的静态配置更好。")
    open("headroom_summary.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
