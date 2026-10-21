"""设计成本表 + 训练集"成本—代理分"曲线（第 7 步）。用 ana 环境运行（需要 matplotlib）：
    ~/miniconda3/envs/ana/bin/python cost_table.py

口径：
  - 代理评价当量：1 当量 = 15 个训练实例 × 67 个基因 = 1005 次解码（LLM 规则生成里一条候选的完整打分）。
    GP / ES 每代用基因子集，按实际解码次数折算；rulegen 出错后让 LLM 修的那次评价也算；EoH 抽不出代码的样本不评价、不计。
  - 网络（IL、ES）另计老师数据：collect.py 300 次 MOEA × 465 次评价 = 139500 次解码 ≈ 138.8 当量（所有网络共用一份）。
  - 墙钟时间：各脚本自己记录的秒数。机器负载不同（Windows 原运行、服务器上与其他任务共用 CPU），只作量级参考，比较以解码次数为准。
  - LLM：调用次数照实；输出 token 只有 EoH 记录了（rulegen 的接口只存回复文本，这里报回复字符数）。
曲线：横轴累计当量（对数），纵轴至今最好的训练集代理分（原 67 个基因，即各方法挑选时用的分数）。
输出：out/design_cost.md、out/cost_curve.png、out/cost_curve.csv（曲线数据，作图表的表格视图）
"""
import csv, glob, json, os, pickle
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
RG = os.path.join(os.path.dirname(HERE), "rulegen", "out")
UNIT = 15 * 67
TEACHER_DECODES = 300 * 465
TEACHER = TEACHER_DECODES / UNIT
DEFAULT = 0.7630


def teacher_secs():
    """老师数据采集的 CPU 时间（各次 MOEA 运行秒数之和）"""
    return sum(pickle.load(open(p, "rb"))["secs"] for p in glob.glob(os.path.join(OUT, "teacher", "*.pkl")))


def rulegen_run(tag):
    """rulegen 一次运行 → 成本与曲线（候选按生成顺序 r0, r1, …；每条候选 1 当量，修复评价另加 1）"""
    st = json.load(open(os.path.join(RG, tag, "state.json"), encoding="utf-8"))
    log = [json.loads(l) for l in open(os.path.join(RG, tag, "llm_log.jsonl"), encoding="utf-8")]
    nfix = sum(1 for l in log if l["op"] == "fix")
    cands = sorted(st["cands"].items(), key=lambda kv: int(kv[0][1:]))
    xs, ys, best, n = [], [], -1, 0
    for cid, c in cands:
        n += 1
        if c["score"] is not None and not c["error"]:
            best = max(best, c["score"])
        if best >= 0:
            xs.append(n); ys.append(best)
    return {"equiv": len(cands) + nfix, "calls": st["calls"], "secs_eval": sum(c["secs"] for c in st["cands"].values()),
            "secs_llm": None, "out_tokens": None, "resp_chars": sum(len(l["response"]) for l in log),
            "best": best, "curve": (xs, ys)}


def eoh_run(r):
    """EoH 一次运行 → 成本与曲线（有代码的样本各 1 当量）"""
    st = json.load(open(os.path.join(OUT, "eoh", f"run{r}", "state.json"), encoding="utf-8"))
    log = [json.loads(l) for l in open(os.path.join(OUT, "eoh", f"run{r}", "llm_log.jsonl"), encoding="utf-8")]
    xs, ys, best, n = [], [], -1, 0
    for s in st["samples"]:
        if s["code"] is None:
            continue
        n += 1
        if s["score"] is not None:
            best = max(best, s["score"])
        if best >= 0:
            xs.append(n); ys.append(best)
    return {"equiv": n, "calls": st["calls"], "secs_eval": st["secs_eval"], "secs_llm": st["secs_llm"],
            "out_tokens": st["tokens"]["completion"], "resp_chars": sum(len(l["response"]) for l in log),
            "best": best, "curve": (xs, ys)}


def gp_run(r):
    d = json.load(open(os.path.join(OUT, "gp", f"run{r}", "report.json"), encoding="utf-8"))
    h = d["history"]
    return {"equiv": d["equiv_evals"], "decodes": d["decodes"], "secs": d["secs"], "best": d["best_score"],
            "curve": ([x["equiv_evals"] for x in h], [x["best_full_so_far"] for x in h])}


def es_run(tag, offset):
    """ES 一次运行；offset = 起点之前已花的当量（IL 预热 = 老师数据）"""
    d = json.load(open(os.path.join(OUT, "es", tag, "history.json"), encoding="utf-8"))
    xs, ys = [offset + 1], [d["init_full"]]
    for h in d["history"]:
        if h["full_after"] is not None:
            xs.append(offset + h["equiv_evals"]); ys.append(h["best_full"])
    return {"equiv": d["equiv_evals"], "decodes": d["decodes"], "secs": d["secs"], "best": d["best_score"],
            "init": d["init_full"], "curve": (xs, ys)}


def il_runs():
    """IL16 五个种子：训练时间与代理分（代理分来自 proxy_scores.json）"""
    ps = json.load(open(os.path.join(OUT, "proxy_scores.json"), encoding="utf-8"))
    out = []
    for s in range(5):
        f = "nn_il_h16" + ("" if s == 0 else f"_s{s}")
        info = json.load(open(os.path.join(OUT, f + ".json"), encoding="utf-8"))
        sc = next(v["score"] for k, v in ps.items() if f"out/{f}.npz@" in k)
        out.append({"secs": info["seconds"], "best": sc})
    return out


def rng(v, fmt="{:.0f}"):
    """均值（最小～最大）"""
    v = [x for x in v if x is not None]
    if not v:
        return "—"
    return fmt.format(np.mean(v)) + (f"（{fmt.format(min(v))}～{fmt.format(max(v))}）" if len(v) > 1 and max(v) > min(v) else "")


def main():
    ts = teacher_secs()
    R = {"LLM-full": [rulegen_run(t) for t in ("full", "full_s2", "full_s3")],
         "LLM-score": [rulegen_run(t) for t in ("score", "score_s2", "score_s3")],
         "EoH": [eoh_run(r) for r in (1, 2, 3)]}
    G = [gp_run(r) for r in range(1, 6)]
    E = [es_run(t, TEACHER) for t in ("il_h16", "il_h16_s1", "il_h16_s2")]
    ER = [es_run(f"rand_h16_s{s}", 0) for s in range(3) if os.path.exists(os.path.join(OUT, "es", f"rand_h16_s{s}", "history.json"))]
    IL = il_runs()
    L = ["# 设计成本（训练集，每次设计运行；均值，括号内为最小～最大）\n",
         "1 当量 = 15 个训练实例 × 67 个基因 = 1005 次解码。网络另计老师数据 "
         f"{TEACHER:.1f} 当量（{TEACHER_DECODES} 次解码，CPU {ts / 3600:.1f} 小时，所有网络共用）。"
         "墙钟时间受机器负载影响（原 rulegen 在 Windows 上，服务器上与其他任务共用 CPU），只作量级参考。"
         "rulegen 的接口不返回 token 数，只报回复字符数；EoH 的输出 token 是接口返回的 completion_tokens，"
         "远多于回复字符（EoH 每次约 53 万 token 对 10 万字符，模型的推理 token 计费但不出现在回复里），所以不能用字符数折算 rulegen 的 token。\n",
         "| 方法 | 设计运行 | 代理评价当量 | 另计老师数据 | 解码次数（万） | 墙钟：评价 / LLM（分钟） | LLM 调用 | 输出 token（万） | 回复字符（万） | 最好代理分 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for m, runs in R.items():
        L.append(f"| {m} | {len(runs)} | {rng([r['equiv'] for r in runs])} | — | {rng([r['equiv'] * UNIT / 1e4 for r in runs], '{:.1f}')} | "
                 f"{rng([r['secs_eval'] / 60 for r in runs], '{:.0f}')} / {rng([r['secs_llm'] / 60 if r['secs_llm'] else None for r in runs], '{:.0f}')} | "
                 f"{rng([r['calls'] for r in runs])} | {rng([r['out_tokens'] / 1e4 if r['out_tokens'] else None for r in runs], '{:.0f}')} | "
                 f"{rng([r['resp_chars'] / 1e4 for r in runs], '{:.1f}')} | {rng([r['best'] for r in runs], '{:.4f}')} |")
    L.append(f"| GP | {len(G)} | {rng([g['equiv'] for g in G])} | — | {rng([g['decodes'] / 1e4 for g in G], '{:.1f}')} | "
             f"{rng([g['secs'] / 60 for g in G])} / — | 0 | — | — | {rng([g['best'] for g in G], '{:.4f}')} |")
    L.append(f"| IL16 | 5 | 0 | {TEACHER:.0f} | {TEACHER_DECODES / 1e4:.1f} | 训练 {rng([i['secs'] / 60 for i in IL], '{:.1f}')} / — | 0 | — | — | "
             f"{rng([i['best'] for i in IL], '{:.4f}')} |")
    L.append(f"| ES16（IL 预热） | {len(E)} | {rng([e['equiv'] for e in E])} | {TEACHER:.0f} | "
             f"{rng([(e['decodes'] + TEACHER_DECODES) / 1e4 for e in E], '{:.1f}')} | {rng([e['secs'] / 60 for e in E])} / — | 0 | — | — | "
             f"{rng([e['best'] for e in E], '{:.4f}')} |")
    if ER:
        L.append(f"| ES16（随机初始化） | {len(ER)} | {rng([e['equiv'] for e in ER])} | — | {rng([e['decodes'] / 1e4 for e in ER], '{:.1f}')} | "
                 f"{rng([e['secs'] / 60 for e in ER])} / — | 0 | — | — | {rng([e['best'] for e in ER], '{:.4f}')} |")
    L += ["\n另：网络结构选择（线性 / 16 / 32-16 / 全部老师、5 个种子）共打了 12 次全基因代理分（12 当量，一次性）；"
          "rulegen 与 EoH 的候选数都是 54（含 rulegen 的默认规则 r0）。",
          f"\n曲线图：out/cost_curve.png；曲线数据（表格视图）：out/cost_curve.csv。"]
    open(os.path.join(OUT, "design_cost.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    plot(R, G, E, ER, IL)


def plot(R, G, E, ER, IL):
    """成本—代理分曲线：同一方法各次运行同色细线，线尾直接标注方法名"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    col = {"LLM-full": "#2a78d6", "LLM-score": "#eb6834", "EoH": "#1baf7a", "GP": "#eda100",
           "IL16": "#e87ba4", "ES16（IL 预热）": "#008300", "ES16（随机初始化）": "#6250d6"}
    ink, muted, grid = "#0b0b0b", "#52514e", "#e6e5e0"
    series = [(m, [r["curve"] for r in runs]) for m, runs in R.items()] + [("GP", [g["curve"] for g in G]),
              ("ES16（IL 预热）", [e["curve"] for e in E])] + ([("ES16（随机初始化）", [e["curve"] for e in ER])] if ER else [])
    fig, ax = plt.subplots(figsize=(9, 5.4), dpi=150)
    fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
    rows, labels = [], []
    for m, curves in series:
        for k, (xs, ys) in enumerate(curves):
            ax.step(xs, ys, where="post", color=col[m], lw=2 if k == 0 else 1.2, alpha=1 if k == 0 else 0.55,
                    label=m if k == 0 else None, solid_capstyle="round")
            rows += [(m, k + 1, x, y) for x, y in zip(xs, ys)]
        ye = float(np.mean([c[1][-1] for c in curves]))
        if ye < 0.70:                                   # 有的运行一直在坐标范围外（随机初始化种子 0 始终为 0）：标在最好那次的线尾
            ye = max(c[1][-1] for c in curves)
        labels.append([m, max(c[0][-1] for c in curves), ye])
    labels = [l for l in labels if l[0] != "ES16（随机初始化）"] + [l for l in labels if l[0] == "ES16（随机初始化）"]
    labels.sort(key=lambda t: t[2])                     # 线尾位置相近（横向差 < 0.2 个数量级）的标签按 y 排开，至少隔 0.0045
    for k in range(1, len(labels)):
        near = [l for l in labels[:k] if abs(np.log10(l[1]) - np.log10(labels[k][1])) < 0.2 and l[0] != "ES16（随机初始化）"]
        if near:
            labels[k][2] = max(labels[k][2], max(l[2] for l in near) + 0.0045)
    for m, xe, ye in labels:
        if m == "ES16（随机初始化）":                        # 线尾挤在 GP、IL 预热 ES 中间：标在紫线尾的下方
            continue
        ax.annotate(m, (xe, ye), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=ink)
    if ER:
        c = max((e["curve"] for e in ER), key=lambda c: c[1][-1])
        ax.annotate("ES16（随机初始化）", (c[0][-1], c[1][-1]), xytext=(4, -16), textcoords="offset points",
                    va="center", ha="center", fontsize=8.5, color=ink)
    ax.scatter([TEACHER] * len(IL), [i["best"] for i in IL], s=36, color=col["IL16"], edgecolor="#fcfcfb", linewidth=1.5,
               zorder=5, label="IL16（老师数据 139 当量）")
    rows += [("IL16", k + 1, TEACHER, i["best"]) for k, i in enumerate(IL)]
    ax.axhline(DEFAULT, color=muted, lw=1, ls=(0, (4, 3)))
    ax.annotate("默认规则 0.7630", (1, DEFAULT), xytext=(2, -11), textcoords="offset points", fontsize=8, color=muted)
    ax.set_xscale("log"); ax.set_xlim(0.9, 3000); ax.set_ylim(0.70, 0.845)
    ax.set_xlabel("累计代理评价当量（1 当量 = 15 实例 × 67 基因的解码；网络计入老师数据）", color=muted, fontsize=9)
    ax.set_ylabel("至今最好的训练集代理分（原 67 个基因）", color=muted, fontsize=9)
    ax.set_title("设计成本—代理分：每种方法的各次设计运行（粗线为第 1 次；随机初始化 ES 种子 0 始终为 0，在图外）", color=ink, fontsize=11, loc="left")
    ax.grid(True, which="major", color=grid, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(grid)
    ax.tick_params(colors=muted, labelsize=8.5)
    ax.legend(loc="lower right", fontsize=8.5, frameon=False, labelcolor=ink)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "cost_curve.png"), facecolor=fig.get_facecolor())
    with open(os.path.join(OUT, "cost_curve.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["方法", "设计运行", "累计当量", "至今最好代理分"]); w.writerows(rows)


if __name__ == "__main__":
    main()
