"""从已有的 MOEA 运行记录（NSGA2，种群 30 × 10 代 ≈ 465 次评价）整理各解码的性能。
输出 perf.json：{实例: {解码: {reach, res_mean, bal_lb_mean, bal_ratio, hv_mean, n}}}
"""
import csv, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L

S = L.SRC
FILES = [("机制验证明细_生产档.csv", {"原解码": "dec0"}),
         ("cap_prod_runs.csv", {"阈值解码": "dec1", "阈值+排序解码": "dec2", "排序+容量预判(ρ=1)": "dec3f"}),
         ("dec4_prod_runs.csv", {"维修相位+容量预判": "dec4"}),
         ("dec5_prod_runs.csv", {"容量预判+回溯修复": "dec5"}),
         ("cap_fam_runs.csv", {"阈值+排序解码": "dec2", "排序+容量预判(ρ=1)": "dec3f"}),
         ("dec4_fam_runs.csv", {"维修相位+容量预判": "dec4"}),
         ("dec5_fam_runs.csv", {"容量预判+回溯修复": "dec5"})]
LB = {k: 9 for k in ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]}
for k, v in json.load(open(f"{S}/exact/family_bounds.json", encoding="utf-8")).items():
    LB[k] = v["total_lb"]
OPT = {}
for s in LB:
    f = f"{S}/exact/dp_{s}.json"
    if os.path.exists(f):
        OPT[s] = json.load(open(f, encoding="utf-8"))["best"]


def hv2(P, ref):
    P = sorted(set(P))
    nd, best = [], float("inf")
    for a, b in P:
        if b < best:
            nd.append((a, b)); best = b
    v, prev_b = 0.0, ref[1]
    for a, b in nd:
        if a < ref[0] and b < prev_b:
            v += (ref[0] - a) * (prev_b - b); prev_b = b
    return v


runs = []
for fn, mp in FILES:
    for r in csv.DictReader(open(f"{S}/{fn}", encoding="utf-8")):
        if r["variant"] not in mp:
            continue
        fr = r["front(资源数:均衡度;...)"]
        front = sorted(tuple(map(float, x.split(":"))) for x in fr.split(";")) if fr else []
        runs.append(dict(inst=r["scenario"], dec=mp[r["variant"]], front=front, ev=int(r["evaluations"])))
out = {}
for inst in dict.fromkeys(r["inst"] for r in runs):
    rs = [r for r in runs if r["inst"] == inst]
    allP = np.array([p for r in rs for p in r["front"]])
    lo, hi = allP.min(0), allP.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    out[inst] = {}
    for dec in L.DECODERS:
        g = [r for r in rs if r["dec"] == dec]
        if not g:
            continue
        hv = [hv2([tuple((np.array(p) - lo) / rg) for p in r["front"]], (1.1, 1.1)) for r in g]
        atlb = [next((b for a, b in r["front"] if a == LB[inst]), None) for r in g]
        atlb_v = [x for x in atlb if x is not None]
        out[inst][dec] = dict(n=len(g), evals=int(np.mean([r["ev"] for r in g])),
                              reach=float(np.mean([x is not None for x in atlb])),
                              res_mean=float(np.mean([r["front"][0][0] for r in g if r["front"]])), n_empty=sum(not r["front"] for r in g),
                              bal_lb_mean=float(np.mean(atlb_v)) if atlb_v else None,
                              bal_lb_best=float(min(atlb_v)) if atlb_v else None,
                              bal_ratio=float(np.mean(atlb_v) / OPT[inst]) if (atlb_v and inst in OPT) else None,
                              hv_mean=float(np.mean(hv)))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "perf.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for inst, d in out.items():
    print(inst, LB[inst], OPT.get(inst))
    for dec, v in d.items():
        print("   ", dec, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items()})
