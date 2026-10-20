"""在 C++ 原模型上逐项验证各机制（NSGA2，算子序列取自请求）
用法: python run_mech.py 种群 代数 每组次数 进程数 输出前缀 [场景,逗号分隔]
变体（比较基准为"阈值解码"，同时给出相对"原解码"的结果）：
  原解码 | 阈值解码 | 阈值+排序解码 | 阈值+分级惩罚 | 阈值+仿真变异 | 阈值+规则播种 | 全部组合(排序+分级+仿真变异+播种)
每次运行用独立临时目录；MOEA_solver 用 random_device，各次运行独立（不可配对）→ Mann-Whitney 检验。
输出: <前缀>_runs.csv, <前缀>_summary.md
"""
import csv, itertools, json, os, subprocess, sys, tempfile, time
from math import erf, sqrt
from multiprocessing import Pool
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]
VARS = {
    "原解码":        ("paiban_dec0", []),
    "阈值解码":      ("paiban_dec1", []),
    "阈值+排序解码": ("paiban_dec2", []),
    "阈值+分级惩罚": ("paiban_dec1", ["--graded"]),
    "阈值+仿真变异": ("paiban_dec1", ["--sim-mutate"]),
    "阈值+规则播种": ("paiban_dec1", ["--seed-rule"]),
    "全部组合":      ("paiban_dec2", ["--graded", "--sim-mutate", "--seed-rule"]),
    "排序+仿真变异": ("paiban_dec2", ["--sim-mutate"]),
    "排序+容量预判": ("paiban_dec3", []),             # 裕度基因 ρ = 1 + x_末位
    "排序+容量预判(ρ=1)": ("paiban_dec3f", []),       # 消融：不用裕度基因
    "维修相位+容量预判": ("paiban_dec4", []),         # 剩余工时少者优先 + 容量预判（ρ=1）
    "容量预判+回溯修复": ("paiban_dec5", []),         # 排序 + 容量预判 + 回溯修复（窗口 12 班）
    "规则+稀疏偏离": ("paiban_dec6", []),                       # 实验1：dec6
    "规则+稀疏偏离b": ("paiban_dec6b", []),                     # 实验1：新开偏离不受容量预判约束，偏离中 30% 为新开
    "dec5+写回": ("paiban_dec5", ["--write-back"]),             # 实验0：拉马克式写回
    "dec5+强制新开带": ("paiban_dec5r", []),                    # 实验0：恢复被容量预判切掉的解
    "dec5+强制新开带+写回": ("paiban_dec5r", ["--write-back"]),
}
BASE = os.environ.get("BASE", "阈值解码")


def nd(P):
    P = [tuple(p) for p in P if p[0] < 29999]
    return sorted({p for p in P if not any(q[0] <= p[0] and q[1] <= p[1] and q != p for q in P)})


def job(a):
    scen, var, rep, pop, gen = a
    exe, flags = VARS[var]
    with tempfile.TemporaryDirectory() as wd:
        out = os.path.join(wd, "r.json")
        req = os.path.join(HERE, "requests", scen + ".json")
        if not os.path.exists(req):
            req = os.path.join(HERE, "requests_family", scen + ".json")
        cmd = [os.path.join(HERE, exe), "--request", req,
               "--workdir", wd, "--templates", os.path.join(HERE, "templates"),
               "--pop", str(pop), "--gen", str(gen), "--quiet", "--out", out] + flags
        t = time.time()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        r = json.load(open(out))
    return dict(scen=scen, var=var, rep=rep, secs=time.time() - t, front=nd(r["pareto_objs"]),
                evals=r.get("evaluations"), nvar=r["Nvar"])


def hv2(P, ref):
    P = sorted(p for p in P if p[0] < ref[0] and p[1] < ref[1])
    h, prev = 0.0, ref[1]
    for f1, f2 in P:
        if f2 < prev:
            h += (ref[0] - f1) * (prev - f2); prev = f2
    return h


def mw(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return float("nan")
    allv = np.concatenate([a, b]); rk = np.argsort(np.argsort(allv)) + 1.0
    for v in np.unique(allv):
        rk[allv == v] = rk[allv == v].mean()
    U = rk[:n1].sum() - n1 * (n1 + 1) / 2; mu = n1 * n2 / 2
    _, cnt = np.unique(allv, return_counts=True)
    sd = sqrt(n1 * n2 / 12 * ((n1 + n2 + 1) - (cnt ** 3 - cnt).sum() / ((n1 + n2) * (n1 + n2 - 1))))
    if sd == 0:
        return 1.0
    return 2 * (1 - .5 * (1 + erf(((abs(U - mu) - .5) / sd) / sqrt(2))))


def fmt_p(p, better):
    if p != p:
        return "—"
    mark = ("↑" if better else "↓") if p < 0.05 else ""
    return f"{p:.3f}{mark}"


if __name__ == "__main__":
    pop, gen, reps, procs, prefix = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    scens = sys.argv[6].split(",") if len(sys.argv) > 6 and sys.argv[6] != "all" else SCEN
    only = sys.argv[7].split(",") if len(sys.argv) > 7 else list(VARS)   # 只跑指定变体（用于补跑）
    VARS = {k: VARS[k] for k in only}
    jobs = list(itertools.product(scens, only, range(reps), [pop], [gen]))
    t0 = time.time()
    with Pool(procs) as p:
        res = p.map(job, jobs, chunksize=1)
    with open(prefix + "_runs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        for r in res:
            w.writerow([r["scen"], r["var"], r["rep"], round(r["secs"], 1), r["evals"], r["nvar"],
                        ";".join(f"{a:.0f}:{b:.3f}" for a, b in r["front"])])
    ev = res[0]["evals"]
    out = [f"# 各机制在 C++ 原模型上的验证（NSGA2，种群 {pop} × {gen} 代，每次约 {ev} 次评价，每组 {reps} 次独立运行）\n",
           "基准为**阈值解码**；p 为与基准的 Mann-Whitney 检验，↑ 表示显著优于基准、↓ 表示显著差于基准（p<0.05）。"
           "HV 在每个场景内用全部变体的解统一归一化（越大越好）。“最少资源数”越小越好；“该点均衡度”是每次运行最少资源那个解的均衡度，越小越好。\n"]
    rank = {v: [] for v in VARS}
    for s in scens:
        rs = [r for r in res if r["scen"] == s]
        allP = np.array([p for r in rs for p in r["front"]])
        lo, hi = allP.min(0), allP.max(0); rng = np.where(hi - lo > 1e-9, hi - lo, 1.0)
        st = {}
        for v in VARS:
            g = [r for r in rs if r["var"] == v]
            hv = [hv2([tuple((np.array(p) - lo) / rng) for p in r["front"]], (1.1, 1.1)) for r in g]
            mn = [r["front"][0][0] if r["front"] else np.nan for r in g]
            bal = [r["front"][0][1] if r["front"] else np.nan for r in g]
            st[v] = dict(hv=hv, mn=mn, bal=bal, secs=np.mean([r["secs"] for r in g]),
                         nf=sum(1 for r in g if r["front"]), n=len(g))
        for k, v in enumerate(sorted(VARS, key=lambda v: -np.mean(st[v]["hv"]))):
            rank[v].append(k + 1)
        out.append(f"## {s}\n")
        out.append("| 变体 | 有可行解 | 最少资源数 均值（最好） | p | 该点均衡度 均值 | p | HV 均值 | p | 单次用时 s |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        b = st[BASE]
        for v in VARS:
            x = st[v]
            if v == BASE:
                pm = pb = ph = "—"
            else:
                pm = fmt_p(mw(x["mn"], b["mn"]), np.nanmean(x["mn"]) < np.nanmean(b["mn"]))
                pb = fmt_p(mw(x["bal"], b["bal"]), np.nanmean(x["bal"]) < np.nanmean(b["bal"]))
                ph = fmt_p(mw(x["hv"], b["hv"]), np.mean(x["hv"]) > np.mean(b["hv"]))
            out.append(f"| {v} | {x['nf']}/{x['n']} | {np.nanmean(x['mn']):.2f}（{np.nanmin(x['mn']):.0f}） | {pm} | "
                       f"{np.nanmean(x['bal']):.2f} | {pb} | {np.mean(x['hv']):.3f} | {ph} | {x['secs']:.1f} |")
        out.append("")
    out.append("## 跨场景 HV 平均排名（越小越好）\n")
    out.append("| 变体 | 平均排名 |"); out.append("|---|---|")
    for v in sorted(VARS, key=lambda v: np.mean(rank[v])):
        out.append(f"| {v} | {np.mean(rank[v]):.2f} |")
    out.append(f"\n总用时 {time.time() - t0:.0f} s")
    open(prefix + "_summary.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
