"""分析 results.csv -> summary.md
1) 每个问题 16 个组合的平均 IGD 与排名
2) 最佳组合 vs 基线(fixed,无劣解,无复用) 的配对 Wilcoxon 检验（numpy 正态近似）
3) log-IGD 方差分解：主效应 vs 交互作用（交互占比高 => 机制不可分，外层组合搜索才有意义）
4) 交互示例：劣解 archive 的效应在不同步长规则下是否翻转符号
"""
import csv, itertools, sys
import numpy as np

fn = sys.argv[1] if len(sys.argv) > 1 else "results.csv"
rows = list(csv.DictReader(open(fn)))
for r in rows:
    r["igd"] = float(r["igd"]); r["seed"] = int(r["seed"])
probs = list(dict.fromkeys(r["problem"] for r in rows))
steps = list(dict.fromkeys(r["step"] for r in rows))
cfgs = [(st, i, u) for st in steps for i in "01" for u in "01"]
name = lambda c: f"{c[0]}|{'IA' if c[1]=='1' else '--'}|{'RE' if c[2]=='1' else '--'}"


def get(p, c):
    v = sorted((r["seed"], r["igd"]) for r in rows
               if r["problem"] == p and (r["step"], r["inf"], r["reuse"]) == c)
    return np.array([x[1] for x in v])


def wilcoxon(a, b):
    """配对符号秩检验，双侧，正态近似（含连续性校正）"""
    d = a - b
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return 1.0
    rk = np.argsort(np.argsort(np.abs(d))) + 1.0
    # 平均秩处理并列
    absd = np.abs(d)
    for v in np.unique(absd):
        m = absd == v
        rk[m] = rk[m].mean()
    W = rk[d > 0].sum()
    mu, sd = n * (n + 1) / 4, np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (abs(W - mu) - 0.5) / sd
    from math import erf, sqrt
    return 2 * (1 - 0.5 * (1 + erf(z / sqrt(2))))


def anova_share(p):
    """对 log IGD 做三因子线性模型，返回 (主效应R2, 全模型R2, 交互占已解释方差比例)"""
    sub = [r for r in rows if r["problem"] == p]
    y = np.log10(np.array([r["igd"] for r in sub]))
    S = np.array([[r["step"] == s for s in steps[1:]] for r in sub], float)
    I = np.array([[r["inf"] == "1"] for r in sub], float)
    U = np.array([[r["reuse"] == "1"] for r in sub], float)
    one = np.ones((len(sub), 1))
    main = np.hstack([one, S, I, U])
    inter = [S * I, S * U, I * U, S * I * U]
    full = np.hstack([main] + inter)
    sst = ((y - y.mean()) ** 2).sum()
    def r2(Xm):
        b, *_ = np.linalg.lstsq(Xm, y, rcond=None)
        return 1 - ((y - Xm @ b) ** 2).sum() / sst
    r2m, r2f = r2(main), r2(full)
    return r2m, r2f, (r2f - r2m) / r2f if r2f > 0 else 0


out = ["# 结果摘要（自动生成，analyze.py）\n",
       f"配置记号：`步长规则|IA=劣解archive|RE=精英复用`；基线 = `fixed|--|--`（DE + NSGA-II 选择）。"
       f"预算 N=100 × 100 代 = 1 万次评价；种子数 {len(get(probs[0], cfgs[0]))}；指标 IGD（越小越好），在外部 archive 上计算。\n"]

# ---- 1. 每问题排名
out.append("## 1. 各问题最好的 3 个组合 vs 基线\n")
out.append("| 问题 | 基线 IGD | 第1 | 第2 | 第3 | 最好单插槽改动 | 最佳组合 vs 基线 p |")
out.append("|---|---|---|---|---|---|---|")
avg_rank = {c: [] for c in cfgs}
base = ("fixed", "0", "0")
for p in probs:
    means = {c: get(p, c).mean() for c in cfgs}
    order = sorted(cfgs, key=means.get)
    for k, c in enumerate(order):
        avg_rank[c].append(k + 1)
    single = [c for c in cfgs if sum([c[0] != "fixed", c[1] == "1", c[2] == "1"]) == 1]
    bs = min(single, key=means.get)
    pv = wilcoxon(get(p, order[0]), get(p, base))
    fmt = lambda c: f"`{name(c)}` {means[c]:.4g}"
    out.append(f"| {p} | {means[base]:.4g} | {fmt(order[0])} | {fmt(order[1])} | {fmt(order[2])} | {fmt(bs)} | {pv:.1e} |")

out.append("\n## 2. 跨问题平均排名（16 个组合，越小越好）\n")
out.append("| 组合 | 平均排名 |")
out.append("|---|---|")
for c in sorted(cfgs, key=lambda c: np.mean(avg_rank[c])):
    out.append(f"| `{name(c)}` | {np.mean(avg_rank[c]):.2f} |")

# ---- 3. 方差分解
out.append("\n## 3. log10(IGD) 方差分解：机制之间是否可分\n")
out.append("交互占比 =（全模型 R² − 主效应 R²）/ 全模型 R²。占比高，说明“单个插槽各自调到最好”≠“组合最好”，需要外层组合搜索。\n")
out.append("| 问题 | 主效应 R² | 含交互 R² | 交互占已解释方差 |")
out.append("|---|---|---|---|")
for p in probs:
    a, b, c = anova_share(p)
    out.append(f"| {p} | {a:.2f} | {b:.2f} | {c:.0%} |")

# ---- 4. 交互示例
out.append("\n## 4. 劣解 archive（IA）的效应随步长规则变化\n")
out.append("表中为 log10 IGD 的差（IA 开 − IA 关，精英复用关）；负数 = IA 有帮助。同一行出现正负号翻转，就是机制交互。\n")
out.append("| 问题 | " + " | ".join(steps) + " |")
out.append("|---" * (len(steps) + 1) + "|")
for p in probs:
    cells = []
    for st in steps:
        d = np.log10(get(p, (st, "1", "0"))).mean() - np.log10(get(p, (st, "0", "0"))).mean()
        cells.append(f"{d:+.2f}")
    out.append(f"| {p} | " + " | ".join(cells) + " |")

open("summary.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
