"""算法库筛选结果分析：按算法排名，并按"生成子代方式 / 环境选择方式"汇总（库里多数算法是这两类模块的组合）
用法: python analyze_lib.py 输出.md 基准算法 a_runs.csv [...]
"""
import csv, json, os, sys, collections
import numpy as np
from run_mech import hv2, mw

HERE = os.path.dirname(os.path.abspath(__file__))
out_md, base, files = sys.argv[1], sys.argv[2], sys.argv[3:]
mods = json.load(open(os.path.join(HERE, "lib_modules.json"), encoding="utf-8"))
groups = json.load(open(os.path.join(HERE, "lib_groups.json"), encoding="utf-8"))["groups"]
alias = {g[0]: g[1:] for g in groups}
LB = {"原请求_paiban": 9, "B_三类型720h": 9, "C_三类型1440h": 9, "D_三类型资源紧": 9}
fb = os.path.join(HERE, "exact", "family_bounds.json")
if os.path.exists(fb):
    LB.update({k: v["total_lb"] for k, v in json.load(open(fb, encoding="utf-8")).items()})
OPT = {s: json.load(open(os.path.join(HERE, "exact", f"dp_{s}.json"), encoding="utf-8"))["best"]
       for s in LB if os.path.exists(os.path.join(HERE, "exact", f"dp_{s}.json"))}

rows = []
for f in files:
    for r in csv.DictReader(open(f, encoding="utf-8")):
        fr = r["front(资源数:均衡度;...)"]
        rows.append(dict(scen=r["scenario"], alg=r["variant"], ok=r.get("ok", "1") == "1",
                         front=sorted(tuple(map(float, x.split(":"))) for x in fr.split(";")) if fr else []))
scens = list(dict.fromkeys(r["scen"] for r in rows))
algs = list(dict.fromkeys(r["alg"] for r in rows))
stat = {a: collections.defaultdict(list) for a in algs}
for s in scens:
    rs = [r for r in rows if r["scen"] == s and r["front"]]
    P = np.array([p for r in rs for p in r["front"]]); lo, hi = P.min(0), P.max(0)
    rng = np.where(hi - lo > 1e-9, hi - lo, 1)
    per = collections.defaultdict(list)
    for r in [r for r in rows if r["scen"] == s]:
        hv = hv2([tuple((np.array(p) - lo) / rng) for p in r["front"]], (1.1, 1.1)) if r["front"] else 0.0
        per[r["alg"]].append(hv)
        b9 = next((b for a, b in r["front"] if a == LB.get(s)), None)
        stat[r["alg"]]["reach"].append(b9 is not None)
        if b9 is not None:
            stat[r["alg"]]["b9"].append(b9)
            if s in OPT:
                stat[r["alg"]]["ratio"].append(b9 / OPT[s])
        stat[r["alg"]]["fail"].append(not r["ok"])
    order = sorted(per, key=lambda a: -np.mean(per[a]))
    for k, a in enumerate(order):
        stat[a]["rank"].append(k + 1)
        stat[a]["hv"].extend(per[a])
        stat[a]["hv_" + s] = per[a]

def mean(x):
    return float(np.mean(x)) if len(x) else float("nan")

tab = sorted(algs, key=lambda a: mean(stat[a]["rank"]))
out = [f"# 算法库在排班问题上的筛选（{', '.join(scens)}；每算法 {len(stat[algs[0]]['reach']) // len(scens)} 次/场景）\n",
       f"HV 每个场景内对全部算法统一归一化；p 为与 **{base}** 的 Mann-Whitney（HV，所有场景合并）。"
       "“到达下界”= 前沿含资源数 = 下界的解；“÷最优”= 下界层均衡度 ÷ 精确最优。"
       "生成/选择列取自算法源码里实际调用的模块（库中多数算法由这两类模块组合而成）。\n",
       "| 排名 | 算法（同实现的别名） | 平均 HV 排名 | HV 均值 | p | 到达下界 | 下界层均衡度 均值 | ÷最优 | 生成子代 | 环境选择 |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for i, a in enumerate(tab):
    S = stat[a]
    p = "—" if a == base else f"{min(1.0, mw(S['hv'], stat[base]['hv'])):.3f}" + ("↑" if mean(S["hv"]) > mean(stat[base]["hv"]) else "↓")
    m = mods.get(a, {})
    nm = a + (f"（={'/'.join(alias[a])}）" if alias.get(a) else "")
    out.append(f"| {i+1} | {nm} | {mean(S['rank']):.1f} | {mean(S['hv']):.3f} | {p} | {np.mean(S['reach']):.0%} | "
               f"{mean(S['b9']):.2f} | {mean(S['ratio']):.2f} | {'+'.join(x.replace('Generate','').replace('Offspring','') for x in m.get('gen', [])) or '自带'} | "
               f"{'+'.join(x.replace('EnvironmentalSelection','') for x in m.get('sel', [])) or '自带'} |")
# 模块汇总
for key, title in [("gen", "生成子代方式"), ("sel", "环境选择方式")]:
    agg = collections.defaultdict(list)
    for a in algs:
        k = "+".join(mods.get(a, {}).get(key, [])) or "（算法自带实现）"
        agg[k].append(mean(stat[a]["rank"]))
    out += [f"\n## 按{title}汇总（使用该模块的算法的平均排名，越小越好）\n", "| 模块 | 算法数 | 平均排名 | 最好排名 |", "|---|---|---|---|"]
    for k in sorted(agg, key=lambda k: np.mean(agg[k])):
        out.append(f"| {k} | {len(agg[k])} | {np.mean(agg[k]):.1f} | {min(agg[k]):.1f} |")
open(out_md, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out[:40]))
