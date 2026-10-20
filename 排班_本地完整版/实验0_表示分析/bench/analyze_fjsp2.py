"""FJSP 结果分析（v2：间隙相对已知最好解 BKS，另报相对下界）。用法: python analyze_fjsp.py 运行记录.csv 输出.md
每个 (实例, 预算) 内用所有编码的解统一归一化 (makespan, workload) 后算 HV；
另报最好 makespan 相对最优值（或下界）的间隙。实例层面配对 Wilcoxon，对照 rk（文献常用的双段随机键）。"""
import csv, os, sys, collections
import numpy as np
from scipy.stats import wilcoxon
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fjsp2 as F  # noqa

inp, outp = sys.argv[1], sys.argv[2]
Mt = F.meta()
R = collections.defaultdict(list)
for r in csv.DictReader(open(inp)):
    fr = [tuple(map(float, p.split(":"))) for p in r["front(makespan:workload;...)"].split(";")] if r["front(makespan:workload;...)"] else []
    R[(r["instance"], r["encoding"], int(r["evals"]))].append(fr)
insts = sorted({k[0] for k in R}); _order = ["rk", "pd", "sp0.1", "sp0.25", "sp0.5"]
encs = [e for e in _order if any(k[1] == e for k in R)] + sorted({k[1] for k in R} - set(_order))   # 其他编码（如 sp0.35q0.2）排在后面
budgets = sorted({k[2] for k in R})


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


def ref_val(n):
    return F.refs(n, Mt)["bks"]


def lb_val(n):
    return F.refs(n, Mt)["lb"]


out = [f"# FJSP：{len(insts)} 个实例，编码 {', '.join(encs)}（{os.path.basename(inp)}）\n",
       "HV：每个 (实例, 预算) 内统一归一化 (makespan, total workload)。间隙 = 最好 makespan / 已知最好解（BKS，有最优值时即最优值）− 1。p：实例层面配对 Wilcoxon，对照 rk。\n"]
rule_gap = []
for n in insts:
    rv = ref_val(n)
    if rv:
        rule_gap.append(F.decode(F.load(Mt[n]["path"]), "sp4", np.zeros(8))[0] / rv - 1)
out.append(f"纯规则（ECT+MWKR）相对 BKS 的平均间隙：{np.mean(rule_gap):.3f}\n")
for b in budgets:
    HV, GAP = {}, {}
    ok = []
    for n in insts:
        if not all(R.get((n, e, b)) for e in encs):
            continue
        ok.append(n)
        pts = np.array([p for e in encs for fr in R[(n, e, b)] for p in fr])
        lo, hi = pts.min(0), pts.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        rv = ref_val(n)
        for e in encs:
            HV[(n, e)] = np.mean([hv([tuple((np.array(p) - lo) / rg) for p in fr]) for fr in R[(n, e, b)]])
            GAP[(n, e)] = np.mean([min(p[0] for p in fr) / rv - 1 for fr in R[(n, e, b)]]) if rv else np.nan
    out += [f"\n## 预算 {b} 次评价（{len(ok)} 个实例）\n", "| 编码 | 平均 HV | 对 rk | p | 赢/输实例数 | 平均间隙 | 最好编码的实例数 |", "|---|---|---|---|---|---|---|"]
    best = collections.Counter(max(encs, key=lambda e: HV[(n, e)]) for n in ok)
    for e in encs:
        v = np.array([HV[(n, e)] for n in ok]); base = np.array([HV[(n, "rk")] for n in ok])
        d = v - base
        p = wilcoxon(d).pvalue if e != "rk" and np.any(d) else None
        out.append(f"| {e} | {v.mean():.3f} | {d.mean():+.3f} | {'—' if p is None else f'{p:.2g}'} | {np.sum(d > 0)}/{np.sum(d < 0)} | {np.nanmean([GAP[(n, e)] for n in ok]):.3f} | {best[e]} |")
open(outp, "w").write("\n".join(out) + "\n")
print("\n".join(out))
