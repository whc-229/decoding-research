"""对照下界 / 精确最优统计各变体：到达资源数下界的比例、下界层上的均衡度（与精确最优之比）、HV
用法: python analyze_gap.py 输出.md 基准变体 a_runs.csv [b_runs.csv ...]
下界取自 exact/family_bounds.json 与 4 个手工场景的证明（均为 9）；精确最优均衡度取自 exact/dp_<场景>.json（若有）。
"""
import csv, json, os, sys
import numpy as np
from run_mech import hv2, mw, fmt_p

HERE = os.path.dirname(os.path.abspath(__file__))
out_md, base, files = sys.argv[1], sys.argv[2], sys.argv[3:]
LB = {"原请求_paiban": 9, "B_三类型720h": 9, "C_三类型1440h": 9, "D_三类型资源紧": 9}
fb = os.path.join(HERE, "exact", "family_bounds.json")
if os.path.exists(fb):
    for k, v in json.load(open(fb, encoding="utf-8")).items():
        LB[k] = v["total_lb"]
OPT = {}
for s in LB:
    f = os.path.join(HERE, "exact", f"dp_{s}.json")
    if os.path.exists(f):
        OPT[s] = json.load(open(f, encoding="utf-8"))["best"]

res = []
for f in files:
    for r in csv.DictReader(open(f, encoding="utf-8")):
        fr = r["front(资源数:均衡度;...)"]
        front = sorted(tuple(map(float, x.split(":"))) for x in fr.split(";")) if fr else []
        res.append(dict(scen=r["scenario"], var=r["variant"], front=front, secs=float(r["seconds"])))
scens = list(dict.fromkeys(r["scen"] for r in res))
vars_ = list(dict.fromkeys(r["var"] for r in res))
out = ["# 对照下界 / 精确最优的比较\n",
       f"基准：**{base}**。p 为与基准的 Mann-Whitney 检验（↑/↓ 显著优于/差于基准，p<0.05）。",
       "“到达下界”= 该次运行的前沿包含资源数 = 下界的解；“下界层均衡度”只在到达下界的运行上统计；"
       "“÷最优”= 下界层均衡度均值 ÷ 精确最优均衡度（只有已求出精确最优的场景才有）。HV 在每个场景内统一归一化。\n"]
summary = {v: dict(reach=[], ratio=[], hvrank=[]) for v in vars_}
for s in scens:
    rs = [r for r in res if r["scen"] == s]
    allP = np.array([p for r in rs for p in r["front"]])
    lo, hi = allP.min(0), allP.max(0); rng = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    lb = LB.get(s); opt = OPT.get(s)
    st = {}
    for v in vars_:
        g = [r for r in rs if r["var"] == v]
        hv = [hv2([tuple((np.array(p) - lo) / rng) for p in r["front"]], (1.1, 1.1)) for r in g]
        mn = [r["front"][0][0] if r["front"] else np.nan for r in g]
        atlb = [next((b for a, b in r["front"] if a == lb), None) for r in g]
        st[v] = dict(hv=hv, mn=mn, atlb=[x for x in atlb if x is not None], n=len(g), secs=np.mean([r["secs"] for r in g]),
                     reach=sum(x is not None for x in atlb))
    order = sorted(vars_, key=lambda v: -np.mean(st[v]["hv"]))
    for k, v in enumerate(order):
        summary[v]["hvrank"].append(k + 1)
    out += [f"## {s}（资源数下界 {lb}" + (f"，下界层精确最优均衡度 {opt:.3f}）\n" if opt else "）\n"),
            "| 变体 | 到达下界 | 最少资源数 均值 | p | 下界层均衡度 均值（最好） | ÷最优 | HV 均值 | p | 单次 s |",
            "|---|---|---|---|---|---|---|---|---|"]
    b = st[base]
    for v in vars_:
        x = st[v]
        summary[v]["reach"].append(x["reach"] / x["n"])
        bal = f"{np.mean(x['atlb']):.2f}（{min(x['atlb']):.2f}）" if x["atlb"] else "—"
        ratio = f"{np.mean(x['atlb']) / opt:.2f}" if (opt and x["atlb"]) else "—"
        if opt and x["atlb"]:
            summary[v]["ratio"].append(np.mean(x["atlb"]) / opt)
        if v == base:
            pm = ph = "—"
        else:
            pm = fmt_p(mw(x["mn"], b["mn"]), np.nanmean(x["mn"]) < np.nanmean(b["mn"]))
            ph = fmt_p(mw(x["hv"], b["hv"]), np.mean(x["hv"]) > np.mean(b["hv"]))
        out.append(f"| {v} | {x['reach']}/{x['n']} | {np.nanmean(x['mn']):.2f} | {pm} | {bal} | {ratio} | "
                   f"{np.mean(x['hv']):.3f} | {ph} | {x['secs']:.1f} |")
    out.append("")
out += ["## 汇总\n", "| 变体 | 平均到达下界比例 | 下界层均衡度 ÷ 最优（有最优的场景平均） | 平均 HV 排名 |", "|---|---|---|---|"]
for v in sorted(vars_, key=lambda v: np.mean(summary[v]["hvrank"])):
    S = summary[v]
    out.append(f"| {v} | {np.mean(S['reach']):.0%} | {np.mean(S['ratio']):.2f} | {np.mean(S['hvrank']):.2f} |"
               if S["ratio"] else f"| {v} | {np.mean(S['reach']):.0%} | — | {np.mean(S['hvrank']):.2f} |")
open(out_md, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
