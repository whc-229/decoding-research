"""T3 分析：FJSP 上槽数比例 f × 生效概率 q 的扫描（bench/v3_qk.csv）。
检验解析模型的三条预测：
  P1 最好解实际用到的偏离数 ≈ q·K（编码自带的偏离数先验）；
  P2 表现主要取决于期望生效槽数 q·K，而不是 K 或 q 单独（不同 q 的曲线按 q·f 对齐）；
  P3 最优的 q·f 随预算增大。
用法: python analyze_qk.py ../bench/v3_qk.csv 输出.md"""
import csv, collections, os, sys
import numpy as np
from scipy.stats import wilcoxon, spearmanr
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench"))
import fjsp2 as F  # noqa

inp, outp = sys.argv[1], sys.argv[2]
Mt = F.meta()
R = collections.defaultdict(list); D = collections.defaultdict(list)
for r in csv.DictReader(open(inp)):
    fr = [tuple(map(float, p.split(":"))) for p in r["front(makespan:workload;...)"].split(";")]
    key = (r["instance"], r["encoding"], int(r["evals"]))
    R[key].append(fr)
    if r["d_best"] != "":
        D[key].append(int(r["d_best"]))
insts = sorted({k[0] for k in R}); budgets = sorted({k[2] for k in R})
FR = [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]; QS = [0.2, 0.4, 0.6]
enc = lambda f, q: f"sp{f}q{q}"
N = {n: F.load(Mt[n]["path"])["nops"] for n in insts}
K = {(n, f): F.k_slots(F.load(Mt[n]["path"]), f) for n in insts for f in FR}


def hv(P, ref=1.1):
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2


H = {}
for b in budgets:
    for n in insts:
        pts = np.array([p for k in R if k[0] == n and k[2] == b for fr in R[k] for p in fr])
        lo, hi = pts.min(0), pts.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        for e in ["rk"] + [enc(f, q) for f in FR for q in QS]:
            H[(n, e, b)] = np.mean([hv([tuple((np.array(p) - lo) / rg) for p in fr]) for fr in R[(n, e, b)]])
out = [f"# T3 分析：FJSP 槽数比例 f × 生效概率 q（{len(insts)} 个实例 × 22 种编码 × 5 次）\n",
       "HV 在每个 (实例, 预算) 内用 22 种编码统一归一化。f = 槽数 / 工序数，q = 随机基因下每槽生效的概率，q·f = 期望生效槽数 / 工序数。\n"]

# P1：偏离数 / K
out += ["\n## P1 最好解的偏离数 / 槽数（理论：≈ q）\n", "| 预算 | " + " | ".join(f"q={q}" for q in QS) + " |", "|---|" + "---|" * len(QS)]
for b in budgets:
    row = []
    for q in QS:
        v = [np.mean(D[(n, enc(f, q), b)]) / K[(n, f)] for n in insts for f in FR]
        row.append(f"{np.mean(v):.3f}（{np.percentile(v, 10):.2f}～{np.percentile(v, 90):.2f}）")
    out.append(f"| {b} | " + " | ".join(row) + " |")
out.append("\n按 f 分开（预算 20000）：")
out += ["| f | " + " | ".join(f"q={q}" for q in QS) + " |", "|---|" + "---|" * len(QS)]
for f in FR:
    out.append(f"| {f} | " + " | ".join(f"{np.mean([np.mean(D[(n, enc(f, q), budgets[-1])]) / K[(n, f)] for n in insts]):.3f}" for q in QS) + " |")

# 平均 HV 表
for b in budgets:
    out += [f"\n## 平均 HV（预算 {b}；rk = {np.mean([H[(n, 'rk', b)] for n in insts]):.3f}）\n", "| f \\ q | " + " | ".join(str(q) for q in QS) + " |", "|---|" + "---|" * len(QS)]
    for f in FR:
        out.append(f"| {f} | " + " | ".join(f"{np.mean([H[(n, enc(f, q), b)] for n in insts]):.3f}" for q in QS) + " |")

# P2：按 q·f 对齐
PAIRS = [((0.1, 0.2), (0.05, 0.4)), ((0.2, 0.2), (0.1, 0.4)), ((1.0, 0.2), (0.5, 0.4)), ((0.75, 0.4), (0.5, 0.6))]
out += ["\n## P2 期望生效槽数 q·f 相同的编码表现是否相同\n",
        "成对比较 q·f 相同、但 K 与 q 不同的两种编码（实例层面配对 Wilcoxon）；作为参照，列出 q 相同、f 差一档（q·f 不同）的平均差。\n",
        "| 预算 | " + " | ".join(f"{a[0]}q{a[1]} vs {c[0]}q{c[1]}（q·f={a[0]*a[1]:.2f}）" for a, c in PAIRS) + " |", "|---|" + "---|" * len(PAIRS)]
for b in budgets:
    cells = []
    for a, c in PAIRS:
        d = np.array([H[(n, enc(*a), b)] - H[(n, enc(*c), b)] for n in insts])
        p = wilcoxon(d).pvalue if np.any(d) else 1
        cells.append(f"{d.mean():+.3f}（p={p:.2g}）")
    out.append(f"| {b} | " + " | ".join(cells) + " |")
out.append("\n参照：同一 q、相邻两档 f 的平均 |HV 差|（q·f 不同）：")
for b in budgets:
    ref = [abs(np.mean([H[(n, enc(FR[i + 1], q), b)] - H[(n, enc(FR[i], q), b)] for n in insts])) for q in QS for i in range(len(FR) - 1)]
    out.append(f"- 预算 {b}：{np.mean(ref):.3f}")
# 解释力：每个 (实例, 预算) 上 HV 对 log(q·f) 的拟合 vs 对 (log f, log q) 的拟合
out.append("\n每个 (实例, 预算) 内，用 log(q·f) 的二次函数拟合 21 种稀疏编码的 HV，再看加入 log q 后残差还能下降多少（平均 R²）：")
out += ["| 预算 | 只用 log(q·f) | 再加 log q、log q·log(q·f) | 只用 log f |", "|---|---|---|---|"]
for b in budgets:
    r1, rr2, r3 = [], [], []
    for n in insts:
        y = np.array([H[(n, enc(f, q), b)] for f in FR for q in QS])
        x = np.log(np.array([f * q for f in FR for q in QS])); lq = np.log(np.array([q for f in FR for q in QS])); lf = np.log(np.array([f for f in FR for q in QS]))
        ss = np.sum((y - y.mean()) ** 2) or 1e-12
        def r2(*cols):
            A = np.column_stack([np.ones_like(y)] + list(cols)); res = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
            return 1 - np.sum(res ** 2) / ss
        r1.append(r2(x, x ** 2)); rr2.append(r2(x, x ** 2, lq, lq * x)); r3.append(r2(lf, lf ** 2))
    out.append(f"| {b} | {np.mean(r1):.3f} | {np.mean(rr2):.3f} | {np.mean(r3):.3f} |")

# P3：最优 q·f 随预算
out += ["\n## P3 每个实例最好的编码：q·f 随预算的变化\n", "| 预算 | 最好编码的 q·f 中位数 | 平均 | q=0.2 时最好的 f | q=0.4 | q=0.6 | f·q（三档 q 各自最好 f 乘 q）均值 |", "|---|---|---|---|---|---|---|"]
for b in budgets:
    best = [max([(f, q) for f in FR for q in QS], key=lambda fq: H[(n, enc(*fq), b)]) for n in insts]
    qf = [f * q for f, q in best]
    bf = {q: [max(FR, key=lambda f: H[(n, enc(f, q), b)]) for n in insts] for q in QS}
    prod = {q: np.mean([f * q for f in bf[q]]) for q in QS}
    out.append(f"| {b} | {np.median(qf):.3f} | {np.mean(qf):.3f} | " + " | ".join(f"{np.median(bf[q]):.2f}（均值 {np.mean(bf[q]):.2f}）" for q in QS) +
               " | " + " / ".join(f"{prod[q]:.3f}" for q in QS) + " |")
# 稀疏 vs rk
out += ["\n## 参照：最好的固定编码对 rk\n"]
for b in budgets:
    cand = [enc(f, q) for f in FR for q in QS]
    be = max(cand, key=lambda e: np.mean([H[(n, e, b)] for n in insts]))
    d = np.array([H[(n, be, b)] - H[(n, "rk", b)] for n in insts])
    out.append(f"- 预算 {b}：平均最好的固定编码 {be}，对 rk {d.mean():+.3f}，赢/输 {np.sum(d > 0)}/{np.sum(d < 0)}")
open(outp, "w").write("\n".join(out) + "\n")
print("\n".join(out))
