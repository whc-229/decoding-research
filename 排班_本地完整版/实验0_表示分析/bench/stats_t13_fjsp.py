"""T13 第 2 / 2b 步补算：指定臂对之间的实例层面配对 Wilcoxon（整族 Holm 校正）与逐实例 Mann-Whitney 好/差计数。
HV 口径与 analyze_fjsp2.py 相同：每个 (实例, 预算) 内用 CSV 中全部臂的解统一归一化 (makespan, workload)，参考点 1.1；
实例层面先对运行取平均。逐实例 Mann-Whitney 用各次运行的 HV（双侧，p < 0.05），按均值方向计"好"或"差"。
Holm 族 = 命令行给出的全部对比 × 全部预算。
用法: python stats_t13_fjsp.py 合并.csv 输出.md 臂:对照[,臂:对照...]
例:   python stats_t13_fjsp.py v3_big_all13.csv stats_t13_s2.md hs:sp0.5,db0.4:sp0.5,ps0.1:sp0.5,pls8:sp0.5:sp0.5"""
import csv, collections, os, sys
import numpy as np
from scipy.stats import mannwhitneyu, wilcoxon


def hv(P, ref=1.1):
    """二维 HV（最小化，归一化后参考点 ref），与 analyze_fjsp2.hv 逐字相同（那边导入时会执行命令行逻辑，所以复制一份）。"""
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2


def load(path):
    """读合并 CSV，返回 {(实例, 臂, 预算): [每次运行的前沿点列表]}。"""
    R = collections.defaultdict(list)
    for r in csv.DictReader(open(path)):
        s = r["front(makespan:workload;...)"]
        R[(r["instance"], r["encoding"], int(r["evals"]))].append([tuple(map(float, p.split(":"))) for p in s.split(";")] if s else [])
    return R


def run_hv(R):
    """每个 (实例, 预算) 内用全部臂统一归一化，返回 {(实例, 臂, 预算): 各次运行 HV 的数组} 与预算列表、实例列表。"""
    insts = sorted({k[0] for k in R}); arms = sorted({k[1] for k in R}); buds = sorted({k[2] for k in R})
    H = {}
    for b in buds:
        for n in insts:
            if not all(R.get((n, e, b)) for e in arms):
                continue
            pts = np.array([p for e in arms for fr in R[(n, e, b)] for p in fr])
            lo, hi = pts.min(0), pts.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
            for e in arms:
                H[(n, e, b)] = np.array([hv([tuple((np.array(p) - lo) / rg) for p in fr]) for fr in R[(n, e, b)]])
    return H, buds, insts


def holm(ps):
    """Holm 逐步校正，返回与输入同序的校正后 p 值。"""
    m = len(ps); order = np.argsort(ps); adj = np.empty(m); run = 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (m - i) * ps[j])); adj[j] = run
    return adj


def compare(H, buds, insts, pairs):
    """对每个 (臂, 对照, 预算) 计算平均 HV 差、配对 Wilcoxon p、赢/输实例数、逐实例 Mann-Whitney 好/差；返回行列表（Holm 前）。"""
    rows = []
    for a, c in pairs:
        for b in buds:
            ok = [n for n in insts if (n, a, b) in H and (n, c, b) in H]
            va = np.array([H[(n, a, b)].mean() for n in ok]); vc = np.array([H[(n, c, b)].mean() for n in ok])
            d = va - vc
            p = wilcoxon(d).pvalue if np.any(d) else 1.0
            good = bad = 0
            for n in ok:
                x, y = H[(n, a, b)], H[(n, c, b)]
                if np.ptp(np.concatenate([x, y])) > 0 and mannwhitneyu(x, y, alternative="two-sided").pvalue < 0.05:
                    good += x.mean() > y.mean(); bad += x.mean() < y.mean()
            rows.append(dict(arm=a, ref=c, bud=b, n=len(ok), ma=va.mean(), mc=vc.mean(), d=d.mean(), p=p,
                             win=int(np.sum(d > 0)), lose=int(np.sum(d < 0)), good=good, bad=bad))
    return rows


def main():
    """解析命令行，计算并写出 Markdown 表。"""
    inp, outp, spec = sys.argv[1], sys.argv[2], sys.argv[3]
    pairs = [tuple(s.rsplit(":", 1)) for s in spec.split(",")]
    H, buds, insts = run_hv(load(inp))
    rows = compare(H, buds, insts, pairs)
    for r, q in zip(rows, holm(np.array([r["p"] for r in rows]))):
        r["holm"] = q
    out = [f"# T13 补算：{os.path.basename(inp)}，{len(insts)} 个实例\n",
           f"HV 在每个 (实例, 预算) 内用 CSV 全部臂统一归一化；p：实例层面配对 Wilcoxon；Holm 族 = {len(pairs)} 个对比 × {len(buds)} 个预算 = {len(rows)} 个检验；"
           "MW 好/差：逐实例 Mann-Whitney（各次运行 HV，双侧 p < 0.05）显著更好/更差的实例数。\n",
           "| 臂 | 对照 | 预算 | 实例数 | 臂平均 HV | 对照平均 HV | 差 | p | Holm p | 赢/输 | MW 好/差 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['arm']} | {r['ref']} | {r['bud']} | {r['n']} | {r['ma']:.3f} | {r['mc']:.3f} | {r['d']:+.3f} | {r['p']:.2g} | {r['holm']:.2g} | {r['win']}/{r['lose']} | {r['good']}/{r['bad']} |")
    open(outp, "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
