"""重排班结果分析。用法: python analyze.py 运行记录.csv 输出.md
目标 (改动数, 均衡度)，资源数 ≤ 预算（moea.py 中定义）。每个场景内用所有臂的解统一归一化后算 HV；另报：
  最少改动：满足预算的解中最少的改动数；改动≤3 的比例：运行中找到"几乎不改"（≤3 班）方案的比例。
实例层面（场景）配对 Wilcoxon，对照 dec5+seed（已有方法）。"""
import csv, json, os, sys, collections
import numpy as np
from scipy.stats import wilcoxon, mannwhitneyu

HERE = os.path.dirname(os.path.abspath(__file__))
inp, outp = sys.argv[1], sys.argv[2]
S = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
runs = collections.defaultdict(list)
for r in csv.DictReader(open(inp, encoding="utf-8")):
    fr = [tuple(map(float, p.split(":")))[1:] for p in r["front(资源数:改动数:均衡度;...)"].split(";")] if r["front(资源数:改动数:均衡度;...)"] else []
    runs[(r["scenario"], r["variant"])].append(fr)
sids = sorted({s for s, _ in runs})
arms = [a for a in ["dec5", "dec5+seed", "sparse", "plan", "plan+seed"] if any((s, a) in runs for s in sids)]


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


H, MINCH, MINRES = {}, {}, {}
for s in sids:
    pts = [p for a in arms for fr in runs.get((s, a), []) for p in fr]
    if not pts:
        continue
    A = np.array([p[:2] for p in pts]); lo, hi = A.min(0), A.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
    for a in arms:
        H[(s, a)] = [hv([tuple((np.array(p[:2]) - lo) / rg) for p in fr]) for fr in runs.get((s, a), [])]
        MINCH[(s, a)] = [min([p[0] for p in fr], default=np.nan) for fr in runs.get((s, a), [])]
        MINRES[(s, a)] = [float(any(p[0] <= 3 for p in fr)) for fr in runs.get((s, a), [])]
sids = [s for s in sids if all(H.get((s, a)) for a in arms)]


def m(D, s, a):
    return float(np.nanmean(D[(s, a)])) if D[(s, a)] and not np.all(np.isnan(D[(s, a)])) else np.nan


out = [f"# 重排班：{len(sids)} 个场景，各臂 {len(next(iter(H.values())))} 次（{os.path.basename(inp)}）\n",
       "HV：每个场景内按 (改动数, 均衡度) 统一归一化（满分 1）。p：场景层面配对 Wilcoxon，对照 dec5+seed。\n"]
for grp_name, grp in [("全部", sids)] + [(t, [s for s in sids if S[s]["ev"]["type"] == t]) for t in ["breakdown", "early_maint", "delay"]] + \
        [(f"发生在 {f}", [s for s in sids if s.endswith("|" + f)]) for f in ["0.3", "0.6"]]:
    if not grp:
        continue
    out += [f"\n## {grp_name}（{len(grp)} 个场景）\n", "| 臂 | 平均 HV | 对 dec5+seed | p | 显著好/差（场景内） | 最少改动 | 找到改动≤3 方案的比例 |", "|---|---|---|---|---|---|---|"]
    base = [m(H, s, "dec5+seed") for s in grp] if "dec5+seed" in arms else None
    for a in arms:
        v = [m(H, s, a) for s in grp]
        if base is not None and a != "dec5+seed":
            d = np.array(v) - np.array(base)
            p = wilcoxon(d).pvalue if np.any(d != 0) else 1.0
            up = dn = 0
            for s in grp:
                try:
                    pp = mannwhitneyu(H[(s, a)], H[(s, "dec5+seed")]).pvalue
                except ValueError:
                    pp = 1
                if pp < 0.05:
                    up += m(H, s, a) > m(H, s, "dec5+seed"); dn += m(H, s, a) < m(H, s, "dec5+seed")
            cmp = f"{np.mean(d):+.3f} | {p:.3g} | {up}/{dn}"
        else:
            cmp = "— | — | —"
        out.append(f"| {a} | {np.mean(v):.3f} | {cmp} | {np.nanmean([m(MINCH, s, a) for s in grp]):.1f} | {np.nanmean([m(MINRES, s, a) for s in grp]):.2f} |")
open(outp, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
