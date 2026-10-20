"""测试集验证结果：各臂在每个实例内统一归一化 HV 后比较。用法: python analyze_val.py 运行记录.csv 输出.md"""
import csv, os, sys, collections
import numpy as np
from scipy.stats import wilcoxon, mannwhitneyu
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import instances as I  # noqa: E402

inp, outp = sys.argv[1], sys.argv[2]
runs = collections.defaultdict(list)
for r in csv.DictReader(open(inp, encoding="utf-8")):
    f = r["front(资源数:均衡度;...)"]
    runs[(r["scenario"], r["variant"])].append([tuple(map(float, p.split(":"))) for p in f.split(";")] if f else [])
insts = sorted({i for i, _ in runs})
arms = sorted({a for _, a in runs}, key=lambda a: (a != "dec5", a))


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


H, RMIN = {}, {}
for i in insts:
    pts = [p for a in arms for fr in runs[(i, a)] for p in fr]
    if not pts:
        continue
    A = np.array(pts); lo, hi = A.min(0), A.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
    for a in arms:
        H[(i, a)] = [hv([tuple((np.array(p) - lo) / rg) for p in fr]) for fr in runs[(i, a)]]
        RMIN[(i, a)] = [min(p[0] for p in fr) - I.lb(i) if fr else np.nan for fr in runs[(i, a)]]
insts = [i for i in insts if all(H.get((i, a)) for a in arms)]
m = lambda D, i, a: float(np.nanmean(D[(i, a)]))
out = [f"# 规则验证：测试集 {len(insts)} 个实例，各臂 {len(H[(insts[0], arms[0])])} 次（Python NSGA-II，465 次评价）\n",
       "HV 在每个实例内用所有臂统一归一化。p：实例层面配对 Wilcoxon。显著好/差：实例内 Mann-Whitney p<0.05 的实例数。资源差：最少资源数 − 下界。\n"]
for gname, grp in [("全部", insts)] + [(g + " 组", [i for i in insts if I.group(i) == g]) for g in ["原", "E", "H", "M"]]:
    if not grp:
        continue
    out += [f"\n## {gname}（{len(grp)}）\n", "| 臂 | 平均 HV | 对 dec5 | p | 好/差 | 对默认规则 | p | 好/差 | 资源差 |", "|---|---|---|---|---|---|---|---|---|"]
    for a in arms:
        row = [a, f"{np.mean([m(H, i, a) for i in grp]):.3f}"]
        for b in ["dec5", "K0.25:default"]:
            if a == b or (b not in arms):
                row += ["—", "—", "—"]; continue
            d = np.array([m(H, i, a) - m(H, i, b) for i in grp])
            p = wilcoxon(d).pvalue if len(grp) > 1 and np.any(d != 0) else 1.0
            up = dn = 0
            for i in grp:
                try:
                    pp = mannwhitneyu(H[(i, a)], H[(i, b)]).pvalue
                except ValueError:
                    pp = 1
                if pp < 0.05:
                    up += m(H, i, a) > m(H, i, b); dn += m(H, i, a) < m(H, i, b)
            row += [f"{d.mean():+.3f}", f"{p:.3g}", f"{up}/{dn}"]
        row.append(f"{np.nanmean([m(RMIN, i, a) for i in grp]):.2f}")
        out.append("| " + " | ".join(row) + " |")
open(outp, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
