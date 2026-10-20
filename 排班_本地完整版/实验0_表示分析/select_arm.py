"""实验3 扩充：为每个实例选择解码档（dec5 / K=0.25 / K=0.5）的各种方法，在 64 个实例上做留一实例评价。
用法: python select_arm.py 运行记录目录 特征目录 输出.md [llm_choice_*.json ...]
运行记录：原 16 个实例取 cmp7_*（dec5）、cmp6b_*（K=0.25）、sl_0.5（K=0.5）；新 48 个实例取 x_<臂>_runs.csv。
每个实例内只用这三档的运行统一归一化 HV。方法的值 = 选中档的 HV 均值（各实例平均），另给"选中最好档"的比例、
相对 dec5 的平均差，以及与最好档的平均差距（后悔值）。
学习型选择器都用留一实例：训练时不看被评价的实例。
"""
import csv, json, os, sys
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

rdir, fdir, outp = sys.argv[1], sys.argv[2], sys.argv[3]
llm_files = sys.argv[4:]
ARMS = ["dec5", "K=0.25", "K=0.5"]
FKEY = {"dec5": "1.0", "K=0.25": "0.25", "K=0.5": "0.5"}
SRC = [("dec5", "cmp7_main_runs.csv", "容量预判+回溯修复"), ("dec5", "cmp7_fam_runs.csv", "容量预判+回溯修复"),
       ("K=0.25", "cmp6b_main_runs.csv", "规则+稀疏偏离b"), ("K=0.25", "cmp6b_fam_runs.csv", "规则+稀疏偏离b"),
       ("K=0.5", "sl_0.5_runs.csv", None),
       ("dec5", "x_dec5_runs.csv", None), ("K=0.25", "x_K=0.25_runs.csv", None), ("K=0.5", "x_K=0.5_runs.csv", None),
       ("dec5_gen20", "x_dec5_gen20_runs.csv", None)]   # 同预算对照：dec5 跑 20 代 ≈ 765 次评价 = 465 + 选档用的 300 次随机解码


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
for arm, f, var in SRC:
    fp = os.path.join(rdir, f)
    if not os.path.exists(fp):
        continue
    for r in csv.DictReader(open(fp, encoding="utf-8")):
        if var and r["variant"] != var:
            continue
        fr = r["front(资源数:均衡度;...)"]
        runs.append((r["scenario"], arm, [tuple(map(float, x.split(":"))) for x in fr.split(";")] if fr else []))
insts = sorted({r[0] for r in runs})
insts = [i for i in insts if all(any(r[0] == i and r[1] == a for r in runs) for a in ARMS) and os.path.exists(os.path.join(fdir, f"{i}.json"))]
HV = {}
dropped = [i for i in insts if not any(r[2] for r in runs if r[0] == i)]   # 三档所有运行都没有可行解的实例
insts = [i for i in insts if i not in dropped]
for i in insts:
    rs = [r for r in runs if r[0] == i]
    allP = np.array([p for r in rs for p in r[2]]); lo, hi = allP.min(0), allP.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
    for r in rs:
        HV.setdefault((i, r[1]), []).append(hv2([tuple((np.array(p) - lo) / rg) for p in r[2]]))
V = np.array([[np.mean(HV[(i, a)]) for a in ARMS] for i in insts])          # 实例 × 臂
best = V.argmax(1)


def cv_split_value():
    """一半运行选档、另一半评价（两个方向取平均）：现实的上限"""
    out = []
    for k, i in enumerate(insts):
        vs = []
        for s in (0, 1):
            pick = int(np.argmax([np.mean(HV[(i, a)][s::2]) for a in ARMS]))
            vs.append(np.mean(HV[(i, ARMS[pick])][1 - s::2]))
        out.append(np.mean(vs))
    return np.array(out)


# ---- 特征 ----
def feat(i):
    f = json.load(open(os.path.join(fdir, f"{i}.json"), encoding="utf-8"))
    S = f["supply"]
    x = dict(T=f["T"], nmax=f["nmax"], n_rob=f["n_robot_types"], n_tool=f["n_tool_types"], LB=f["LB"],
             rule_gap=f["rule_gap"] if f["rule_gap"] is not None else 20, rule_bal=f["rule_bal"] or 0, rule_fix=f["rule_fixes"])
    for a in ARMS:
        s = S[FKEY[a]]
        x[f"p_lb_{a}"] = s["p_lb"]; x[f"p_lb1_{a}"] = s["p_lb1"]
        x[f"gapmin_{a}"] = min(s["res_min"] - f["LB"], 20); x[f"balmin_{a}"] = min(s["bal_at_min"], 200)
    for a in ARMS[1:]:
        x[f"d_gapmin_{a}"] = x[f"gapmin_{a}"] - x["gapmin_dec5"]
        x[f"d_balmin_{a}"] = x[f"balmin_{a}"] - x["balmin_dec5"]
        x[f"d_plb1_{a}"] = x[f"p_lb1_{a}"] - x["p_lb1_dec5"]
    return x


F = [feat(i) for i in insts]
names = list(F[0])
X = np.array([[f[n] for n in names] for f in F], float)


def loo(model_fn):
    pick = np.zeros(len(insts), int)
    for k in range(len(insts)):
        tr = np.arange(len(insts)) != k
        y = best[tr]
        if len(set(y)) == 1:
            pick[k] = y[0]; continue
        m = model_fn(); m.fit(X[tr], y); pick[k] = int(m.predict(X[k:k + 1])[0])
    return pick


methods = {}
for j, a in enumerate(ARMS):
    methods[f"固定 {a}"] = np.full(len(insts), j)
methods["按随机样本最好解选（先比资源数再比均衡度）"] = np.array([min(range(3), key=lambda j: (F[k][f"gapmin_{ARMS[j]}"], F[k][f"balmin_{ARMS[j]}"])) for k in range(len(insts))])
methods["留一：决策树（深度 2）"] = loo(lambda: DecisionTreeClassifier(max_depth=2, random_state=0))
methods["留一：逻辑回归"] = loo(lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.5)))
methods["留一：最近邻（k=5）"] = loo(lambda: make_pipeline(StandardScaler(), KNeighborsClassifier(5)))
for lf in llm_files:
    ch = json.load(open(lf, encoding="utf-8"))
    pk = []
    for i in insts:
        ds = [c["d"] for c in ch.get(i, []) if c.get("d") is not None]
        if not ds:
            pk = None; break
        vals, cnt = np.unique([str(float(d)) for d in ds], return_counts=True)
        v = float(vals[np.argmax(cnt)])
        pk.append(0 if v >= 1.0 else (1 if abs(v - 0.25) < 1e-6 else 2 if abs(v - 0.5) < 1e-6 else 1 if v < 0.25 else 2))
    if pk is not None:
        methods["LLM（" + os.path.basename(lf)[11:-5] + "）"] = np.array(pk)

base = V[:, 0]
from scipy.stats import wilcoxon, mannwhitneyu
ORIG = np.array([not (i[0] in "EHM" and i[1:3].isdigit() and int(i[1:3]) >= 11) for i in insts])
def detail(pick):
    val = V[np.arange(len(insts)), pick]
    d = val - base
    try:
        pw = wilcoxon(val, base).pvalue if np.any(d != 0) else 1.0
    except ValueError:
        pw = 1.0
    up = dn = 0
    for k, i in enumerate(insts):
        if pick[k] == 0:
            continue
        p = mannwhitneyu(HV[(i, ARMS[pick[k]])], HV[(i, "dec5")]).pvalue
        if p < 0.05:
            up += d[k] > 0; dn += d[k] < 0
    return d[ORIG].mean(), d[~ORIG].mean(), pw, up, dn
rows = []
for name, pick in methods.items():
    val = V[np.arange(len(insts)), pick]
    rows.append((name, val.mean(), (val - base).mean(), np.mean(pick == best), (V.max(1) - val).mean(),
                 np.bincount(pick, minlength=3), detail(pick)))
cv = cv_split_value()
grp = lambda i: "原16" if not i[1:3].isdigit() or int(i[1:3]) < 11 or i[0] not in "EHM" else "新48"
out = [f"# 选择解码档（dec5 / K=0.25 / K=0.5）：{len(insts)} 个实例上的比较\n",
       "每个实例内只用这三档的运行统一归一化 HV。值 = 选中档的 HV 均值的实例平均；后悔值 = 与该实例最好档的差。学习型选择器为留一实例。\n",
       (f"三档所有运行都没有可行解、已排除的实例：{'、'.join(dropped)}\n" if dropped else ""),
       f"各档成为最好档的实例数：" + "、".join(f"{a} {int((best == j).sum())}" for j, a in enumerate(ARMS)) + "\n",
       "相对 dec5 的差另按原 16 个实例 / 新 46 个实例分开给出；p(Wilcoxon) 为实例层面的配对符号秩检验；"
       "显著好/差 = 选了非 dec5 档的实例中，该档与 dec5 的运行结果 Mann-Whitney p<0.05 的实例数。\n",
       "| 方法 | 平均 HV | 相对 dec5 | 其中 原16 / 新46 | p(Wilcoxon) | 显著好/差 | 选中最好档的比例 | 平均后悔值 | 选择分布（dec5/0.25/0.5） |",
       "|---|---|---|---|---|---|---|---|---|"]
for name, v, dv, acc, reg, bc, (d1, d2, pw, up, dn) in rows:
    out.append(f"| {name} | {v:.3f} | {dv:+.3f} | {d1:+.3f} / {d2:+.3f} | {pw:.3g} | {up}/{dn} | {acc:.2f} | {reg:.3f} | {bc[0]}/{bc[1]}/{bc[2]} |")
if all((i, "dec5_gen20") in HV for i in insts):
    g20 = np.array([np.mean(HV[(i, "dec5_gen20")]) for i in insts])
    pick_bs = methods["按随机样本最好解选（先比资源数再比均衡度）"]
    vbs = V[np.arange(len(insts)), pick_bs]
    pw = wilcoxon(vbs, g20).pvalue
    up = sum(mannwhitneyu(HV[(i, ARMS[pick_bs[k]])], HV[(i, "dec5_gen20")]).pvalue < 0.05 and vbs[k] > g20[k] for k, i in enumerate(insts))
    dn = sum(mannwhitneyu(HV[(i, ARMS[pick_bs[k]])], HV[(i, "dec5_gen20")]).pvalue < 0.05 and vbs[k] < g20[k] for k, i in enumerate(insts))
    out.append(f"| 固定 dec5，20 代（≈765 次评价，与「按随机样本最好解选」同预算） | {g20.mean():.3f} | {(g20 - base).mean():+.3f} | "
               f"{(g20 - base)[ORIG].mean():+.3f} / {(g20 - base)[~ORIG].mean():+.3f} | — | — | — | — | — |")
    out.append(f"| ↳ 「按随机样本最好解选」对 20 代 dec5 | 差 {(vbs - g20).mean():+.3f} | | 原16 {(vbs - g20)[ORIG].mean():+.3f} / 新46 {(vbs - g20)[~ORIG].mean():+.3f} | {pw:.3g} | {up}/{dn}（逐实例全部比较） | | | |")
out.append(f"| 事后最好档（oracle，偏乐观） | {V.max(1).mean():.3f} | {(V.max(1) - base).mean():+.3f} | — | — | — | 1.00 | 0 | {np.bincount(best, minlength=3)[0]}/{np.bincount(best, minlength=3)[1]}/{np.bincount(best, minlength=3)[2]} |")
out.append(f"| 一半运行选、另一半评价 | {cv.mean():.3f} | {(cv - base).mean():+.3f} | — | — | — | — | — | — |")
# 决策树全量拟合，看它用了哪些特征
t = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X, best)
from sklearn.tree import export_text
out += ["", "## 决策树（深度 2，全部实例拟合，仅用于看规律）\n", "```", export_text(t, feature_names=names, class_names=ARMS), "```", "",
        "## 各实例\n", "| 实例 | " + " | ".join(ARMS) + " | 最好 |", "|---|---|---|---|---|"]
for k, i in enumerate(insts):
    out.append(f"| {i} | " + " | ".join(f"{V[k, j]:.3f}" for j in range(3)) + f" | {ARMS[best[k]]} |")
open(outp, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out[:20 + len(rows)]))
