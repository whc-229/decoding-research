"""FJSP 细分分析：逐实例 Mann-Whitney（p<0.05）显著好/差计数、按基准族、按规模、Hurink 子集（按柔性）。
用法: python analyze_detail.py 运行记录.csv（输出到标准输出）。编码固定为 rk, pd, sp0.1, sp0.25, sp0.5。"""
import csv, sys, collections, numpy as np
sys.path.insert(0, '.')
import fjsp2 as F
from scipy.stats import mannwhitneyu, wilcoxon
Mt = F.meta()
R = collections.defaultdict(list)
for r in csv.DictReader(open(sys.argv[1])):
    fr = [tuple(map(float, p.split(":"))) for p in r["front(makespan:workload;...)"].split(";")] if r["front(makespan:workload;...)"] else []
    R[(r["instance"], r["encoding"], int(r["evals"]))].append(fr)
insts = sorted({k[0] for k in R}); encs = ["rk", "pd", "sp0.1", "sp0.25", "sp0.5"]
def hv(P, ref=1.1):
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b: nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb: v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2
fam = lambda n: Mt[n]["path"].split("/")[0]
N = {n: F.load(Mt[n]["path"])["nops"] for n in insts}
for b in [465, 2000, 5000]:
    H = {}
    for n in insts:
        pts = np.array([p for e in encs for fr in R[(n, e, b)] for p in fr]); lo, hi = pts.min(0), pts.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        for e in encs: H[(n, e)] = [hv([tuple((np.array(p) - lo) / rg) for p in fr]) for fr in R[(n, e, b)]]
    def cmp(a, c):
        up = dn = 0; lose = []
        for n in insts:
            x, y = H[(n, a)], H[(n, c)]
            if np.allclose(x, y): continue
            p = mannwhitneyu(x, y).pvalue
            if p < 0.05:
                if np.mean(x) > np.mean(y): up += 1
                else: dn += 1; lose.append(n)
        return up, dn, lose
    print(f"== {b}")
    for a, c in [("sp0.5", "rk"), ("sp0.25", "rk"), ("sp0.1", "rk"), ("pd", "rk"), ("sp0.5", "sp0.25"), ("sp0.25", "sp0.1")]:
        up, dn, lose = cmp(a, c)
        d = np.array([np.mean(H[(n, a)]) - np.mean(H[(n, c)]) for n in insts])
        print(f"{a} vs {c}: diff {d.mean():+.3f} p={wilcoxon(d).pvalue:.1e} MW sig {up}/{dn}", ("lose: " + ",".join(f"{n}({fam(n)},{N[n]})" for n in lose[:12])) if a=="sp0.5" and c=="rk" else "")
    if b == 5000:
        for f in sorted({fam(n) for n in insts}):
            I = [n for n in insts if fam(n) == f]
            d = [np.mean(H[(n, "sp0.5")]) - np.mean(H[(n, "rk")]) for n in I]
            d2 = [np.mean(H[(n, "sp0.5")]) - np.mean(H[(n, "sp0.25")]) for n in I]
            print(f"  {f:12s} {len(I):3d} 实例  sp0.5-rk {np.mean(d):+.3f}  sp0.5-sp0.25 {np.mean(d2):+.3f}  ops {min(N[n] for n in I)}-{max(N[n] for n in I)}")
        # size
        for lo_, hi_ in [(0, 50), (50, 100), (100, 200), (200, 1000)]:
            I = [n for n in insts if lo_ <= N[n] < hi_]
            d = [np.mean(H[(n, "sp0.5")]) - np.mean(H[(n, "rk")]) for n in I]
            print(f"  ops [{lo_},{hi_}) {len(I)} 实例 sp0.5-rk {np.mean(d):+.3f}  rk 胜(均值) {sum(x<0 for x in d)}")
print("== hurink 子集（5000）")
for pre in ["s", "e", "r", "v"]:
    I = [n for n in insts if fam(n) == "hurink" and n.startswith(pre + "-")]
    if not I: continue
    d = [np.mean(H[(n, "sp0.5")]) - np.mean(H[(n, "rk")]) for n in I]
    gap = lambda e: np.mean([np.mean([min(p[0] for p in fr) for fr in R[(n, e, 5000)]]) / F.refs(n, Mt)["bks"] - 1 for n in I])
    flex = np.mean([np.mean([len(op) for ops in F.load(Mt[n]["path"])["jobs"] for op in ops]) for n in I])
    print(f"{pre}data {len(I)} 实例 平均可选机器 {flex:.2f}  sp0.5-rk {np.mean(d):+.3f}  rk 胜 {sum(x<0 for x in d)}  gap rk {gap('rk'):.3f} sp0.5 {gap('sp0.5'):.3f}")
