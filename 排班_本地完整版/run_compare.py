"""原解码(paiban_dec0) vs 阈值解码(paiban_dec1) 批量对比
用法: python run_compare.py 种群 代数 种子数 进程数 输出前缀 [场景名,逗号分隔]
每次运行用独立的临时工作目录；MOEA_solver 内部用 random_device，因此各次运行相互独立（不可按种子配对）。
输出: <前缀>_runs.csv（每次运行的非支配解）与 <前缀>_summary.md
"""
import csv, itertools, json, os, subprocess, sys, tempfile, time
from math import erf, sqrt
from multiprocessing import Pool
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]
DEC = {"原解码": "paiban_dec0", "阈值解码": "paiban_dec1"}


def nd(P):
    P = [tuple(p) for p in P if p[0] < 29999]
    return sorted({p for p in P if not any(q[0] <= p[0] and q[1] <= p[1] and q != p for q in P)})


def job(a):
    scen, dec, rep, pop, gen = a
    with tempfile.TemporaryDirectory() as wd:
        out = os.path.join(wd, "r.json")
        cmd = [os.path.join(HERE, DEC[dec]), "--request", os.path.join(HERE, "requests", scen + ".json"),
               "--workdir", wd, "--templates", os.path.join(HERE, "templates"),
               "--pop", str(pop), "--gen", str(gen), "--nvar", "auto", "--quiet", "--out", out]
        t = time.time()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        r = json.load(open(out))
    return dict(scen=scen, dec=dec, rep=rep, secs=time.time() - t, front=nd(r["pareto_objs"]))


def hv2(P, ref):
    P = sorted(p for p in P if p[0] < ref[0] and p[1] < ref[1])
    h, prev = 0.0, ref[1]
    for f1, f2 in P:
        if f2 < prev:
            h += (ref[0] - f1) * (prev - f2); prev = f2
    return h


def mannwhitney(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n1, n2 = len(a), len(b)
    allv = np.concatenate([a, b]); rk = np.argsort(np.argsort(allv)) + 1.0
    for v in np.unique(allv):
        rk[allv == v] = rk[allv == v].mean()
    U = rk[:n1].sum() - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    _, cnt = np.unique(allv, return_counts=True)
    sd = sqrt(n1 * n2 / 12 * ((n1 + n2 + 1) - (cnt ** 3 - cnt).sum() / ((n1 + n2) * (n1 + n2 - 1))))
    if sd == 0:
        return 1.0
    z = (abs(U - mu) - .5) / sd
    return 2 * (1 - .5 * (1 + erf(z / sqrt(2))))


if __name__ == "__main__":
    pop, gen, reps, procs, prefix = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    scens = sys.argv[6].split(",") if len(sys.argv) > 6 else SCEN
    jobs = list(itertools.product(scens, DEC, range(reps), [pop], [gen]))
    t0 = time.time()
    with Pool(procs) as p:
        res = p.map(job, jobs, chunksize=1)
    with open(prefix + "_runs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["scenario", "decoder", "run", "seconds", "front(资源数:均衡度;...)"])
        for r in res:
            w.writerow([r["scen"], r["dec"], r["rep"], round(r["secs"], 1), ";".join(f"{a:.0f}:{b:.3f}" for a, b in r["front"])])
    out = [f"# 原解码 vs 阈值解码：C++ 原模型（NSGA2，种群 {pop} × {gen} 代 = {pop*gen} 次评价，每组 {reps} 次独立运行）\n",
           "HV 在每个场景内用两组全部解统一归一化（越大越好）。p 为 Mann-Whitney 秩和检验（独立运行，不配对）。\n",
           "| 场景 | 解码 | 有可行解的运行 | 最少资源数 均值（最好） | 最少资源处的均衡度 均值 | HV 均值 | p(HV) | p(最少资源数) | 单次用时 s |",
           "|---|---|---|---|---|---|---|---|---|"]
    for s in scens:
        rs = [r for r in res if r["scen"] == s]
        allP = [p for r in rs for p in r["front"]]
        if not allP:
            out.append(f"| {s} | — | 0 | — | — | — | — | — | — |"); continue
        A = np.array(allP); lo, hi = A.min(0), A.max(0)
        rng = np.where(hi - lo > 1e-9, hi - lo, 1.0)
        stats = {}
        for d in DEC:
            g = [r for r in rs if r["dec"] == d]
            hv = [hv2([tuple((np.array(p) - lo) / rng) for p in r["front"]], (1.1, 1.1)) for r in g]
            mn = [r["front"][0][0] if r["front"] else np.nan for r in g]
            bal = [r["front"][0][1] if r["front"] else np.nan for r in g]
            stats[d] = (hv, mn, bal, sum(1 for r in g if r["front"]), np.mean([r["secs"] for r in g]))
        for d in DEC:
            hv, mn, bal, nf, secs = stats[d]
            if d == "原解码":
                p1 = p2 = "—"
            else:
                p1 = f"{mannwhitney(stats[d][0], stats['原解码'][0]):.3f}"
                a, b = [x for x in mn if x == x], [x for x in stats['原解码'][1] if x == x]
                p2 = f"{mannwhitney(a, b):.3f}" if a and b else "—"
            out.append(f"| {s} | {d} | {nf}/{len(hv)} | {np.nanmean(mn):.2f}（{np.nanmin(mn):.0f}） | {np.nanmean(bal):.2f} | "
                       f"{np.mean(hv):.3f} | {p1} | {p2} | {secs:.1f} |")
    out.append(f"\n总用时 {time.time()-t0:.0f} s")
    open(prefix + "_summary.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
