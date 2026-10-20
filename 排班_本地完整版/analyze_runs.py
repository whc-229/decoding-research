"""合并若干 *_runs.csv（run_mech.py 的输出）并重新统计，用于补跑变体后与已有数据一起比较
用法: python analyze_runs.py 输出.md a_runs.csv b_runs.csv ...
"""
import csv, sys
import numpy as np
from run_mech import hv2, mw, fmt_p, BASE

out_md, files = sys.argv[1], sys.argv[2:]
res = []
for f in files:
    for r in csv.DictReader(open(f, encoding="utf-8")):
        fr = r["front(资源数:均衡度;...)"]
        front = sorted(tuple(map(float, x.split(":"))) for x in fr.split(";")) if fr else []
        res.append(dict(scen=r["scenario"], var=r["variant"], secs=float(r["seconds"]), front=front,
                        evals=r["evaluations"]))
scens = list(dict.fromkeys(r["scen"] for r in res))
vars_ = list(dict.fromkeys(r["var"] for r in res))
reps = max(sum(1 for r in res if r["scen"] == scens[0] and r["var"] == v) for v in vars_)
out = [f"# 各机制在 C++ 原模型上的验证（合并统计；每次约 {res[0]['evals']} 次评价，每组 {reps} 次独立运行）\n",
       "基准为**阈值解码**；p 为与基准的 Mann-Whitney 检验，↑/↓ 表示显著优于/差于基准（p<0.05）。"
       "HV 在每个场景内用全部变体的解统一归一化（越大越好）；最少资源数、该点均衡度越小越好。\n"]
rank = {v: [] for v in vars_}
for s in scens:
    rs = [r for r in res if r["scen"] == s]
    allP = np.array([p for r in rs for p in r["front"]])
    lo, hi = allP.min(0), allP.max(0); rng = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    st = {}
    for v in vars_:
        g = [r for r in rs if r["var"] == v]
        st[v] = dict(hv=[hv2([tuple((np.array(p) - lo) / rng) for p in r["front"]], (1.1, 1.1)) for r in g],
                     mn=[r["front"][0][0] if r["front"] else np.nan for r in g],
                     bal=[r["front"][0][1] if r["front"] else np.nan for r in g],
                     secs=np.mean([r["secs"] for r in g]), nf=sum(1 for r in g if r["front"]), n=len(g))
    for k, v in enumerate(sorted(vars_, key=lambda v: -np.mean(st[v]["hv"]))):
        rank[v].append(k + 1)
    out += [f"## {s}\n", "| 变体 | 有可行解 | 最少资源数 均值（最好） | p | 该点均衡度 均值 | p | HV 均值 | p | 单次用时 s |",
            "|---|---|---|---|---|---|---|---|---|"]
    b = st[BASE]
    for v in vars_:
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
out += ["## 跨场景 HV 平均排名（越小越好）\n", "| 变体 | 平均排名 |", "|---|---|"]
for v in sorted(vars_, key=lambda v: np.mean(rank[v])):
    out.append(f"| {v} | {np.mean(rank[v]):.2f} |")
open(out_md, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
