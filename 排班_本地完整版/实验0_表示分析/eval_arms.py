"""实验3：各档偏离密度 / 偏离槽数的 MOEA 结果汇总，以及"为每个实例选档"的策略离线评价。
用法: python eval_arms.py 运行记录目录 特征目录(dec9 初始供给, out9) 输出.md [llm_choice_*.json ...]
臂：
  dec5、dec7（实验2 自适应解码）
  dec8 d=0.05/0.1/0.2（逐班阈值的偏离密度）
  K=0.1/0.25/0.5（dec6b，偏离槽数 = 比例 × Nmax；0.25 即实验1 的 dec6b）、K=自适应（启用槽数由基因决定，上限 0.5）
每个实例内用全部运行的解统一归一化 HV。策略在 K 三档和 dec5 这四档里选；策略值 = 选中档的 HV 均值。
oracle 在同一批运行上挑最好的档，偏乐观，只作上界参考。
"""
import csv, json, os, sys
import numpy as np
from scipy.stats import mannwhitneyu

rdir, fdir, outp = sys.argv[1], sys.argv[2], sys.argv[3]
llm_files = sys.argv[4:]
SRC = [("dec5", ["cmp7_main_runs.csv", "cmp7_fam_runs.csv"], "容量预判+回溯修复"),
       ("dec7", ["cmp7_main_runs.csv", "cmp7_fam_runs.csv"], "自适应(dec5/dec6b)"),
       ("d=0.05", ["dd_0.05_runs.csv"], None), ("d=0.1", ["dd_0.1_runs.csv"], None), ("d=0.2", ["dd_0.2_runs.csv"], None),
       ("K=0.1", ["sl_0.1_runs.csv"], None), ("K=0.25", ["cmp6b_main_runs.csv", "cmp6b_fam_runs.csv"], "规则+稀疏偏离b"),
       ("K=0.5", ["sl_0.5_runs.csv"], None), ("K=自适应", ["sl_adapt_runs.csv"], None)]
KARMS = ["K=0.1", "K=0.25", "K=0.5", "dec5"]   # dec5 = 每班都由基因决定，作为偏离密度最大的一端


def hv2(P, ref=(1.1, 1.1)):
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref[1]
    for a, c in nd:
        if a < ref[0] and c < pb:
            v += (ref[0] - a) * (pb - c); pb = c
    return v


runs = []
for arm, files, var in SRC:
    for f in files:
        fp = os.path.join(rdir, f)
        if not os.path.exists(fp):
            continue
        for r in csv.DictReader(open(fp, encoding="utf-8")):
            if var and r["variant"] != var:
                continue
            fr = r["front(资源数:均衡度;...)"]
            runs.append((r["scenario"], arm, [tuple(map(float, x.split(":"))) for x in fr.split(";")] if fr else [], float(r["seconds"]),
                         float(r["d_mean_front"]) if r.get("d_mean_front") else None))
arms = [a for a, _, _ in SRC if any(r[1] == a for r in runs)]
insts = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"] + sorted({r[0] for r in runs} - {"原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"})
HV, SECS, DM = {}, {}, {}
for inst in insts:
    rs = [r for r in runs if r[0] == inst]
    allP = np.array([p for r in rs for p in r[2]]); lo, hi = allP.min(0), allP.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
    for r in rs:
        HV.setdefault((inst, r[1]), []).append(hv2([tuple((np.array(p) - lo) / rg) for p in r[2]]))
        SECS.setdefault((inst, r[1]), []).append(r[3])
        if r[4] is not None:
            DM.setdefault((inst, r[1]), []).append(r[4])


def m(i, a):
    return float(np.mean(HV[(i, a)]))


def sig(i, a, b="dec5"):
    p = mannwhitneyu(HV[(i, a)], HV[(i, b)]).pvalue
    return ("↑" if m(i, a) > m(i, b) else "↓") if p < 0.05 else ""


out = ["# 实验3：偏离密度 / 偏离槽数（C++，NSGA2，种群 30 × 10 代 ≈ 465 次评价）\n",
       "每个实例内 HV 统一归一化（越大越好）。↑/↓ = 与 dec5 相比显著更好/更差（Mann-Whitney，p<0.05）。粗体为 K 三档与 dec5 中最好的一档。"
       "运行次数：dec5、dec7、K=0.25 为 4 个场景各 20 次、实例族各 8 次；其余为 12 次 / 6 次。\n",
       "## 各臂 HV 均值\n",
       "| 实例 | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
for i in insts:
    bk = max(KARMS, key=lambda a: m(i, a)) if all((i, a) in HV for a in KARMS) else None
    row = [i]
    for a in arms:
        if (i, a) not in HV:
            row.append("—"); continue
        c = f"{m(i, a):.3f}" + (sig(i, a) if a != "dec5" else "")
        if a == "K=自适应" and (i, a) in DM:
            c += f"（{np.mean(DM[(i, a)]):.2f}）"
        row.append(f"**{c}**" if a == bk else c)
    out.append("| " + " | ".join(row) + " |")
out.append("")
out += ["## 各臂汇总（16 个实例）\n", "| 臂 | 平均 HV | 相对 dec5 | 显著更好 | 显著更差 | 平均单次 s |", "|---|---|---|---|---|---|"]
base = np.mean([m(i, "dec5") for i in insts])
for a in arms:
    v = [m(i, a) for i in insts if (i, a) in HV]
    up = sum(sig(i, a) == "↑" for i in insts if (i, a) in HV and a != "dec5")
    dn = sum(sig(i, a) == "↓" for i in insts if (i, a) in HV and a != "dec5")
    out.append(f"| {a} | {np.mean(v):.3f} | {np.mean(v) - base:+.3f} | {up} | {dn} | {np.mean([np.mean(SECS[(i, a)]) for i in insts if (i, a) in SECS]):.1f} |")
out.append("")

# ---- 选档策略（在 K 三档中选） ----
feats = {}
for i in insts:
    fp = os.path.join(fdir, f"{i}.json")
    if os.path.exists(fp):
        feats[i] = json.load(open(fp, encoding="utf-8"))
pol = {f"固定 {a}": {i: a for i in insts} for a in KARMS}
pol["oracle（事后最好档，上界）"] = {i: max(KARMS, key=lambda a: m(i, a)) for i in insts}
if len(feats) == len(insts):
    def key(i, a):
        k = "1.0" if a == "dec5" else str(float(a[2:]))
        return feats[i]["supply"][k]
    pol["按初始供给选（≤下界+1 比例最高）"] = {i: max(KARMS, key=lambda a: (key(i, a)["p_lb1"], key(i, a)["p_lb"], -KARMS.index(a))) for i in insts}
    pol["按随机样本最好解选"] = {i: min(KARMS, key=lambda a: (key(i, a)["res_min"], key(i, a)["bal_at_min"], KARMS.index(a))) for i in insts}
# 交叉验证版 oracle 与"试跑"：按运行序号分两半，一半用于选档，另一半用于评价（两个方向取平均）
HALF = {}
for (i, a), v in HV.items():
    HALF[(i, a)] = (v[0::2], v[1::2])
def cv_value(i, chooser):
    vals = []
    for s in (0, 1):
        pick = chooser(i, lambda a: float(np.mean(HALF[(i, a)][s])))
        vals.append(float(np.mean(HALF[(i, pick)][1 - s])))
    return float(np.mean(vals))
CV = {"oracle 交叉验证（用一半运行选、另一半评价）": lambda i, f: max(KARMS, key=f),
      "试跑选档（每档先跑 1 次，按 HV 选）": None}
for lf in llm_files:
    ch = json.load(open(lf, encoding="utf-8"))
    name = "LLM（" + os.path.basename(lf)[11:-5] + "）"
    p = {}
    for i in insts:
        ds = [str(c["d"]) for c in ch.get(i, []) if c.get("d") is not None]
        if ds:
            vals, cnt = np.unique(ds, return_counts=True)
            v = str(vals[np.argmax(cnt)])
            p[i] = "dec5" if v in ("1.0", "1", "dec5") else "K=" + v
    if len(p) == len(insts):
        pol[name] = p
out += ["## 选档策略（在 K=0.1 / 0.25 / 0.5 / dec5 中为每个实例选一档；选择列里 5 表示 dec5）\n",
        "| 策略 | 平均 HV | 相对 dec5 | 选中 oracle 档的比例 | 显著优于 dec5 | 显著差于 dec5 | 各实例的选择 |", "|---|---|---|---|---|---|---|"]
orc = pol["oracle（事后最好档，上界）"]
for name, p in list(pol.items()) + [("K=自适应（基因）", {i: "K=自适应" for i in insts}), ("dec7（实验2）", {i: "dec7" for i in insts})]:
    if any((i, p[i]) not in HV for i in insts):
        continue
    v = [m(i, p[i]) for i in insts]
    win = np.mean([p[i] == orc[i] for i in insts])
    up = sum(sig(i, p[i]) == "↑" for i in insts); dn = sum(sig(i, p[i]) == "↓" for i in insts)
    choice = "" if name.startswith(("固定", "K=自适应", "dec7")) else " ".join(f"{i.split('_')[0]}:{'5' if p[i] == 'dec5' else p[i][2:]}" for i in insts)
    out.append(f"| {name} | {np.mean(v):.3f} | {np.mean(v) - base:+.3f} | {win:.2f} | {up} | {dn} | {choice} |")
# 交叉验证与试跑两行（值是对"未用于选档"的运行求的平均）
for name in CV:
    vals, up = [], 0
    for i in insts:
        if name.startswith("oracle"):
            vals.append(cv_value(i, CV[name]))
        else:   # 试跑：用第 k 次运行的 HV 选档，在其余运行上评价，k 取遍前 6 次
            vv = []
            for k in range(6):
                pick = max(KARMS, key=lambda a: HV[(i, a)][k] if k < len(HV[(i, a)]) else -1)
                rest = [h for j, h in enumerate(HV[(i, pick)]) if j != k]
                vv.append(float(np.mean(rest)))
            vals.append(float(np.mean(vv)))
    out.append(f"| {name} | {np.mean(vals):.3f} | {np.mean(vals) - base:+.3f} | — | — | — | 评价只用未参与选档的运行；试跑的代价是每档多跑 1 次 |")
open(outp, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
