"""写回 / 可达性小对照的统计。用法: python analyze_ga.py 输出.md a.csv [b.csv ...]"""
import csv, json, os, sys
import numpy as np
from scipy.stats import mannwhitneyu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L
S = L.SRC
LB = {k: 9 for k in ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]}
for k, v in json.load(open(f"{S}/exact/family_bounds.json", encoding="utf-8")).items():
    LB[k] = v["total_lb"]
OPT = {s: json.load(open(f"{S}/exact/dp_{s}.json", encoding="utf-8"))["best"] for s in LB if os.path.exists(f"{S}/exact/dp_{s}.json")}


def hv2(P, ref):
    P = sorted(set(P)); nd, best = [], float("inf")
    for a, b in P:
        if b < best:
            nd.append((a, b)); best = b
    v, pb = 0.0, ref[1]
    for a, b in nd:
        if a < ref[0] and b < pb:
            v += (ref[0] - a) * (pb - b); pb = b
    return v

out_md, files = sys.argv[1], sys.argv[2:]
NAME = {"dec3f": "排序+容量预判", "dec3f+wb": "排序+容量预判 + 写回", "dec3fr": "排序+容量预判 + 强制新开带",
        "dec5": "回溯修复（dec5）", "dec5+wb": "dec5 + 写回", "dec5r": "dec5 + 强制新开带", "dec5r+wb": "dec5 + 强制新开带 + 写回"}
runs = []
for f in files:
    for r in csv.DictReader(open(f, encoding="utf-8")):
        fr = r["front(资源数:均衡度;...)"]
        runs.append(dict(inst=r["scenario"], v=r["variant"], secs=float(r["seconds"]),
                         front=sorted(tuple(map(float, x.split(":"))) for x in fr.split(";")) if fr else []))
md = ["# 写回与可达性小对照（C++ 原模型，NSGA2，种群 30 × 10 代 ≈ 465 次评价，每组 20 次）\n",
      "基准 = dec5（容量预判+回溯修复）。p 为 Mann-Whitney 双侧检验，↑/↓ = 显著优于/差于基准（p<0.05）；均衡度检验中未到达下界的运行记为最差。“找到最优”= 下界层均衡度 ≤ 精确最优 × 1.001 的运行数。\n"]
for inst in dict.fromkeys(r["inst"] for r in runs):
    rs = [r for r in runs if r["inst"] == inst]
    allP = np.array([p for r in rs for p in r["front"]])
    lo, hi = allP.min(0), allP.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    opt, lb = OPT.get(inst), LB[inst]
    md += [f"## {inst}（下界 {lb}" + (f"，精确最优 {opt:.3f}）\n" if opt else "）\n"),
           "| 变体 | 次数 | 到达下界 | 下界层均衡 均值（最好） | ÷最优 | 找到最优 | p(均衡) | HV | p(HV) | 单次 s |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    st = {}
    for v in dict.fromkeys(r["v"] for r in rs):
        g = [r for r in rs if r["v"] == v]
        hv = [hv2([tuple((np.array(p) - lo) / rg) for p in r["front"]], (1.1, 1.1)) for r in g]
        atlb = [next((b for a, b in r["front"] if a == lb), None) for r in g]
        # 未到达下界的运行在均衡比较里记为最差（+inf 的秩）
        balk = [x if x is not None else 1e9 for x in atlb]
        st[v] = dict(g=g, hv=hv, atlb=[x for x in atlb if x is not None], balk=balk)
    base = st.get("dec5") or st.get("容量预判+回溯修复")
    for v, x in st.items():
        pb = ph = "—"
        if base and x is not base:
            p1 = mannwhitneyu(x['balk'], base['balk']).pvalue
            p2 = mannwhitneyu(x['hv'], base['hv']).pvalue
            pb = f"{p1:.3f}" + (("↑" if np.median(x['balk']) < np.median(base['balk']) else "↓") if p1 < 0.05 else "")
            ph = f"{p2:.3f}" + (("↑" if np.mean(x['hv']) > np.mean(base['hv']) else "↓") if p2 < 0.05 else "")
        a = x["atlb"]
        fo = sum(b <= opt * 1.001 for b in a) if opt else "—"
        md.append(f"| {NAME.get(v, v)} | {len(x['g'])} | {len(a)}/{len(x['g'])} | "
                  + (f"{np.mean(a):.2f}（{min(a):.3f}）" if a else "—") + " | "
                  + (f"{np.mean(a) / opt:.2f}" if (a and opt) else "—") + f" | {fo} | {pb} | {np.mean(x['hv']):.3f} | {ph} | "
                  f"{np.mean([r['secs'] for r in x['g']]):.1f} |")
    md.append("")
open(out_md, "w", encoding="utf-8").write("\n".join(md))
print("\n".join(md))
