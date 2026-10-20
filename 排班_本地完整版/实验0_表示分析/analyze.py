"""汇总实验 0：表示指标 × 已有 MOEA 性能。输出 Markdown 表和实例内秩相关。
用法: python analyze.py 指标目录 输出.md
"""
import json, os, sys, glob
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L

d_in, out_md = sys.argv[1], sys.argv[2]
perf = json.load(open(os.path.join(d_in, "perf.json"), encoding="utf-8"))
MET = {}
for f in sorted(glob.glob(os.path.join(d_in, "*.json"))):
    if f.endswith("perf.json"):
        continue
    m = json.load(open(f, encoding="utf-8")); MET[m["instance"]] = m
MAIN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]
insts = [i for i in MAIN if i in MET] + sorted(i for i in MET if i not in MAIN)


def g(d, *ks):
    for k in ks:
        if d is None:
            return None
        d = d.get(k)
    return d


def f3(v, p=3):
    return "—" if v is None else (f"{v:.{p}f}" if isinstance(v, float) else str(v))


FEATS = [("p_lb1", ("p_lb1",), "随机基因解码到 ≤下界+1 的概率"),
         ("res_mean", ("res_mean",), "随机基因的平均资源数"),
         ("neutral_rand", ("loc_random", "neutral"), "单基因变异不改变排班的概率（随机基底）"),
         ("neutral_elite", ("loc_elite", "neutral"), "同上（精英基底）"),
         ("cascade_elite", ("loc_elite", "cascade"), "非中性变异后，变异位置之后改变的班次比例（精英基底）"),
         ("worse_elite", ("loc_elite", "res_worse"), "非中性变异中资源数变多或不可行的比例（精英基底）"),
         ("override", ("override_rate",), "解码改写基因含义的班次比例（容量预判）"),
         ("fixes", ("fixes_mean",), "每次解码的回溯修复次数")]
PERF = [("hv", "hv_mean"), ("reach", "reach"), ("res", "res_mean")]

L_ = ["# 实验 0：六种解码的表示指标与已有 MOEA 性能\n",
      "指标在 Python 等价模型上计算（每个实例×解码 1000 个随机基因；局部性用 100 个随机可行基底 + 30 个精英基底 × 5 次单基因重抽样）。"
      "性能取自已有 C++ 运行记录（NSGA2，种群 30 × 10 代 ≈ 465 次评价；4 个场景各 20 次，实例族各 8 次）。HV 在每个实例内统一归一化。\n"]
for inst in insts:
    m = MET[inst]; p = perf.get(inst, {})
    L_ += [f"## {inst}（资源数下界 {m['LB']}" + (f"，下界层精确最优均衡度 {m['opt']:.3f}" if m.get("opt") else "") + "）\n",
           "| 解码 | 读到的基因 | P(≤下界+1) | 随机平均资源 | 中性率 随机/精英 | 级联 精英 | 变坏率 精英 | 改写率 | 修复/次 | 最优解可达 | HV | 到达下界 | 均衡÷最优 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for dec in L.DECODERS:
        x = m["dec"].get(dec); q = p.get(dec)
        if x is None:
            continue
        reach = "—" if "opt_reachable" not in x else ("是" if x["opt_reachable"] else f"否（第 {x['opt_fail_shift']} 班）")
        L_.append(f"| {dec} {L.DEC_NAME[dec]} | {x['gene_used']:.2f} | {x['p_lb1']:.3f} | {f3(x['res_mean'],1)} | "
                  f"{f3(g(x,'loc_random','neutral'),2)} / {f3(g(x,'loc_elite','neutral'),2)} | {f3(g(x,'loc_elite','cascade'),2)} | "
                  f"{f3(g(x,'loc_elite','res_worse'),2)} | {x['override_rate']:.3f} | {x['fixes_mean']:.2f} | {reach} | "
                  f"{f3(g(q,'hv_mean'),3)} | {f3(g(q,'reach'),2)} | {f3(g(q,'bal_ratio'),2)} |")
    L_.append("")

# 实例内秩相关（解码之间），再跨实例取中位数
L_ += ["## 指标能否解释解码之间的性能排序\n",
       "对每个实例，在有性能记录的解码之间计算 Spearman 秩相关（4 个场景 6 个解码，实例族 4 个解码）；表中为跨实例的中位数，括号内为同号实例数 / 有效实例数。\n",
       "| 指标 | 含义 | ρ(指标, HV) | ρ(指标, 到达下界) | ρ(指标, 最少资源) |", "|---|---|---|---|---|"]
for name, path, desc in FEATS:
    row = [name, desc]
    for pn, pk in PERF:
        rs = []
        for inst in insts:
            p = perf.get(inst, {})
            decs = [d for d in L.DECODERS if d in p and d in MET[inst]["dec"]]
            a = [g(MET[inst]["dec"][d], *path) for d in decs]
            b = [p[d][pk] for d in decs]
            if len(decs) >= 4 and None not in a and len(set(a)) > 1 and len(set(b)) > 1:
                rs.append(spearmanr(a, b).correlation)
        if rs:
            med = float(np.median(rs)); same = sum(np.sign(r) == np.sign(med) for r in rs)
            row.append(f"{med:+.2f}（{same}/{len(rs)}）")
        else:
            row.append("—")
    L_.append("| " + " | ".join(row) + " |")
L_.append("")
open(out_md, "w", encoding="utf-8").write("\n".join(L_))
print("\n".join(L_))
