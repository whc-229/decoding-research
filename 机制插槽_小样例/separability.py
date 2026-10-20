"""特征可分性检验：只看运行前 20% 预算里的在线状态，能否判断"这个问题该不该开劣解 archive（IA）"？

每个实例 × 种子跑三次：
  A: 只开精英复用（RE），5 万次评价            -> 最终 IGD，前 20% 的被动状态特征
  B: RE + IA，5 万次评价                       -> 最终 IGD
  C: 探针：前 20% 预算内，IA 隔代开/关          -> "IA 开的那几代成功率 − 关的那几代成功率"
标签（实例级）：effect = mean log10 IGD(B) − mean log10 IGD(A)；effect > 0.1 记为"IA 有害"。
评估：留一问题族交叉验证（同族实例整体留出），逻辑回归 / 最近质心；并换算成"按预测开关 IA"后的 IGD 代价。

用法: python separability.py [种子数] [进程数]
输出: separability_runs.csv, separability_summary.md
"""
import csv, itertools, sys
from multiprocessing import Pool
import numpy as np
import instances  # noqa: F401  注册扩充实例
import slot_moea as s

SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
PROCS = int(sys.argv[2]) if len(sys.argv) > 2 else 2
GENS, PROBE = 500, 100
FEATS = ["succ_mean", "succ_late", "rank1_late", "arch_frac", "stall_frac", "probe_diff"]


def job(a):
    p, seed = a
    # A：IA 关（p_ia=0，但仍维护劣解 archive 以保持随机流程一致），RE 开
    A = s.run(p, inf=lambda st: 0.0, reuse=True, gens=GENS, seed=seed, trace=True)
    B = s.run(p, inf=True, reuse=True, gens=GENS, seed=seed)
    C = s.run(p, inf=lambda st: float(st["gen"] % 2 == 0), reuse=True, gens=PROBE,
              seed=seed + 1000, trace=True)
    tr = np.array(A["trace"][:PROBE])           # g, F, succ, rank1, p_ia, p_re, stall, arch
    tc = np.array(C["trace"])
    on, off = tc[tc[:, 4] > .5, 2], tc[tc[:, 4] < .5, 2]
    feats = [tr[:, 2].mean(), tr[50:, 2].mean(), tr[50:, 3].mean(), tr[-1, 7],
             (tr[:, 6] > 0).mean(), on[10:].mean() - off[10:].mean()]
    return [p, seed, A["igd"], B["igd"]] + [float(x) for x in feats]


def logreg(X, y, l2=1.0, it=3000, lr=0.1):
    w = np.zeros(X.shape[1]); b = 0.0
    for _ in range(it):
        z = 1 / (1 + np.exp(-(X @ w + b)))
        w -= lr * (X.T @ (z - y) / len(y) + l2 * w / len(y)); b -= lr * (z - y).mean()
    return w, b


if __name__ == "__main__":
    probs = list(s.PROBLEMS)
    with Pool(PROCS) as pool:
        rows = pool.map(job, list(itertools.product(probs, range(SEEDS))), chunksize=1)
    with open("separability_runs.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["problem", "seed", "igd_noIA", "igd_IA"] + FEATS); w.writerows(rows)

    fam = instances.FAMILY
    eff, lab = {}, {}
    for p in probs:
        r = [x for x in rows if x[0] == p]
        eff[p] = np.mean(np.log10([x[3] for x in r])) - np.mean(np.log10([x[2] for x in r]))
        lab[p] = int(eff[p] > 0.1)
    X = np.array([x[4:] for x in rows]); P = [x[0] for x in rows]
    y = np.array([lab[p] for p in P])

    out = [f"# 特征可分性检验（{len(probs)} 个实例 × {SEEDS} 种子，5 万次评价；特征只取前 20% 预算）\n",
           "## 1. 各实例上劣解 archive（IA）的真实效应\n",
           "effect = log10 IGD(开IA) − log10 IGD(关IA)，两者都开精英复用。> 0.1 记为“有害”（IGD 变差 > 26%）。\n",
           "| 实例 | IGD 关IA | IGD 开IA | effect | 标签 | " + " | ".join(FEATS) + " |",
           "|---" * (6 + len(FEATS)) + "|"]
    for p in sorted(probs, key=eff.get):
        r = np.array([x[2:] for x in rows if x[0] == p], float)
        out.append(f"| {p} | {np.mean(r[:,0]):.4g} | {np.mean(r[:,1]):.4g} | {eff[p]:+.2f} | "
                   f"{'有害' if lab[p] else '无害/有益'} | " + " | ".join(f"{v:.3f}" for v in r[:, 2:].mean(0)) + " |")

    # 单特征 AUC（单次运行级别）
    def auc(sc, yy):
        pos, neg = sc[yy == 1], sc[yy == 0]
        return ((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())
    out.append("\n## 2. 单特征区分度（单次运行级 AUC；0.5 = 无信息，越偏离 0.5 越好）\n")
    out.append("| 特征 | AUC |"); out.append("|---|---|")
    for j, f in enumerate(FEATS):
        out.append(f"| {f} | {auc(X[:, j], y):.2f} |")

    # 留一问题族交叉验证
    fams = sorted(set(fam[p] for p in probs))
    pred = np.zeros(len(y)); pred_nc = np.zeros(len(y))
    for F in fams:
        te = np.array([fam[p] == F for p in P]); tr_ = ~te
        mu, sd = X[tr_].mean(0), X[tr_].std(0) + 1e-9
        Z = (X - mu) / sd
        if len(set(y[tr_])) < 2:
            pred[te] = pred_nc[te] = y[tr_][0]; continue
        w, b = logreg(Z[tr_], y[tr_])
        pred[te] = (Z[te] @ w + b > 0)
        c1, c0 = Z[tr_][y[tr_] == 1].mean(0), Z[tr_][y[tr_] == 0].mean(0)
        pred_nc[te] = ((Z[te] - c1) ** 2).sum(1) < ((Z[te] - c0) ** 2).sum(1)
    base = max(y.mean(), 1 - y.mean())
    out.append("\n## 3. 留一问题族交叉验证（单次运行级：一次运行只看自己的前 20% 特征）\n")
    out.append(f"- 多数类基线准确率：{base:.2f}")
    out.append(f"- 逻辑回归：{(pred == y).mean():.2f}；最近质心：{(pred_nc == y).mean():.2f}")
    out.append(f"- 有害实例的召回（逻辑回归）：{(pred[y == 1] == 1).mean():.2f}；无害实例上误关 IA 的比例：{(pred[y == 0] == 1).mean():.2f}")

    # 决策代价：按预测决定开/关 IA
    def cost(choice):     # 每次运行选用 noIA(1) 或 IA(0)，返回平均 log10 IGD
        return np.mean([np.log10(x[2] if c else x[3]) for x, c in zip(rows, choice)])
    allon, alloff = cost(np.zeros(len(y))), cost(np.ones(len(y)))
    oracle = cost(np.array([lab[p] for p in P]))
    learned = cost(pred)
    out.append("\n## 4. 换算成效果：平均 log10 IGD（越小越好，跨 16 个实例平均）\n")
    out.append("| 策略 | 平均 log10 IGD |"); out.append("|---|---|")
    for nm, v in [("始终开 IA", allon), ("始终关 IA", alloff), ("按前 20% 特征预测开/关（逻辑回归）", learned),
                  ("按实例事后最优（上界）", oracle)]:
        out.append(f"| {nm} | {v:+.3f} |")
    gap = (min(allon, alloff) - learned) / (min(allon, alloff) - oracle + 1e-12)
    out.append(f"\n预测策略拿到了“最好固定策略 → 上界”之间差距的 **{gap:.0%}**。")
    open("separability_summary.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
