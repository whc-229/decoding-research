"""任务 D5：训练与测试两条 K—HV 曲线（ana 环境）。测试集只作敏感性分析，不用于选择 K。
  ~/miniconda3/envs/ana/bin/python d5_curves.py
测试：val_server.csv（K0.25、K0.5 原布局臂，dec5）+ val_Kext.csv（X0.75、X1.0）合并，每个实例内全部臂统一归一化；
     每个 K 对 8 条规则（ES16 s0～s2、GP run1～5）× 5 次取平均。K0.5 用原布局臂（与 X0.5 只在班次上界为奇数的实例上不同）。
训练：train_K.csv（K0.25、K0.5、dec5）与 train_Kext.csv（X0.5、X0.75、X1.0）是两个文件、各自归一化；这里合并两者统一归一化，
     K0.5 用 train_Kext.csv 的 X0.5（新布局），K0.25 用 train_K.csv。
p：实例层面配对 Wilcoxon（相邻 K 与 K0.5 对比，信息性，未用于选择）。
输出：out/d5_curves.md、out/d5_curves.png
"""
import os, sys
import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import analyze_methods as AM  # noqa: E402
import instances as I  # noqa: E402

RULES = [f"ES16(s{s})" for s in range(3)] + [f"GP(run{r})" for r in range(1, 6)]
FAM = {"合并": RULES, "ES16": RULES[:3], "GP": RULES[3:]}
KS = ["0.25", "0.5", "0.75", "1.0"]


def curve(files, arm_of):
    """→ (实例列表, {(K, 族): {实例: HV}}, {实例: dec5 HV})；arm_of(K, 规则) 给出臂名"""
    runs = AM.load(files)
    need = ["dec5"] + [arm_of(k, r) for k in KS for r in RULES]
    arms = sorted({x for _, x in runs})
    miss = [a for a in need if a not in arms]
    assert not miss, f"缺臂：{miss[:5]}"
    insts = sorted({i for i, _ in runs if all(len(runs.get((i, a), {})) == 5 for a in need)})
    H, _ = AM.normalize(runs, insts, arms)
    hv = lambda i, a: float(np.mean(H[(i, a)]))
    V = {(k, f): {i: np.mean([hv(i, arm_of(k, r)) for r in rs]) for i in insts} for k in KS for f, rs in FAM.items()}
    return insts, V, {i: hv(i, "dec5") for i in insts}, len(arms)


def table(title, insts, V, D, narm):
    """K—HV 表（全部与 E/H/M）+ 相邻 K 的配对检验"""
    L = [f"\n## {title}（{len(insts)} 个实例，{narm} 个臂统一归一化）\n",
         "| 族 | 组 | dec5 | " + " | ".join(f"K{k}" for k in KS) + " | 最高 |", "|---|---|---|" + "---|" * len(KS) + "---|"]
    for f in FAM:
        for g in [None, "原", "E", "H", "M"]:
            grp = [i for i in insts if g is None or I.group(i) == g]
            if not grp:
                continue
            m = {k: np.mean([V[(k, f)][i] for i in grp]) for k in KS}
            L.append(f"| {f} | {g or '全部'} | {np.mean([D[i] for i in grp]):.3f} | " + " | ".join(f"{m[k]:.3f}" for k in KS)
                     + f" | K{max(KS, key=lambda k: m[k])} |")
    L += ["\n相邻 K（合并 8 条规则，全部实例；配对 Wilcoxon，信息性）：\n", "| 比较 | 平均差 | 好/差实例数 | p |", "|---|---|---|---|"]
    for a, b in [("0.5", "0.25"), ("0.75", "0.5"), ("1.0", "0.75"), ("1.0", "0.5")]:
        d = np.array([V[(a, "合并")][i] - V[(b, "合并")][i] for i in insts])
        L.append(f"| K{a} − K{b} | {d.mean():+.4f} | {(d > 0).sum()}/{(d < 0).sum()} | {wilcoxon(d).pvalue if np.any(d != 0) else 1:.3g} |")
    return L


def main():
    te_arm = lambda k, r: f"K{k}:{r}" if k in ("0.25", "0.5") else f"X{k}:{r}"
    tr_arm = lambda k, r: f"K{k}:{r}" if k == "0.25" else f"X{k}:{r}"
    te = curve([os.path.join(OUT, "val_server.csv"), os.path.join(OUT, "val_Kext.csv")], te_arm)
    tr = curve([os.path.join(OUT, "train_K.csv"), os.path.join(OUT, "train_Kext.csv")], tr_arm)
    L = ["# 任务 D5：K—HV 曲线（训练实例选 K；测试集只作敏感性分析，不用于选择 K）\n",
         "训练：train_K.csv + train_Kext.csv 合并统一归一化（K0.25 原布局，K0.5～1.0 扩展布局），种子 5000+次号。"
         "测试：val_server.csv + val_Kext.csv 合并统一归一化（K0.25、K0.5 原布局，K0.75、K1.0 扩展布局），种子 1000+次号。"
         "每个 K 的值 = 8 条规则（或族内规则）× 5 次的平均。"]
    L += table("训练实例", *tr)
    L += table("测试实例（敏感性分析，不用于选择 K）", *te)
    open(os.path.join(OUT, "d5_curves.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    plot(tr, te)


def plot(tr, te):
    """训练 / 测试两张小图，每张画全部与 E/H/M 四条 K—HV 线（合并 8 条规则），dec5 用虚线标出"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "DejaVu Sans"]
    col = {"全部": "#2a78d6", "E": "#eb6834", "H": "#1baf7a", "M": "#eda100"}
    ink, muted, grid = "#0b0b0b", "#52514e", "#e6e5e0"
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), dpi=150, sharey=True)
    fig.patch.set_facecolor("#fcfcfb")
    x = [float(k) for k in KS]
    for ax, (title, (insts, V, D, _)) in zip(axes, [("训练实例（选 K 用）", tr), ("测试实例（敏感性分析）", te)]):
        ax.set_facecolor("#fcfcfb")
        ends = []
        for g in ["全部", "E", "H", "M"]:
            grp = [i for i in insts if g == "全部" or I.group(i) == g]
            y = [np.mean([V[(k, "合并")][i] for i in grp]) for k in KS]
            ax.plot(x, y, color=col[g], lw=2, marker="o", ms=6, mec="#fcfcfb", mew=1.5, label=f"{g}（{len(grp)}）")
            ends.append([g, y[-1]])
            ax.axhline(np.mean([D[i] for i in grp]), color=col[g], lw=1, ls=(0, (4, 3)), alpha=0.7)
        ends.sort(key=lambda t: t[1])                        # 线尾标签按 y 排开，相邻至少隔 0.018
        for k in range(1, len(ends)):
            ends[k][1] = max(ends[k][1], ends[k - 1][1] + 0.018)
        for g, ye in ends:
            ax.annotate(g, (x[-1], ye), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=ink)
        ax.set_title(title, loc="left", fontsize=10.5, color=ink)
        ax.set_xticks(x); ax.set_xticklabels([f"K{k}" for k in KS])
        ax.set_xlim(0.18, 1.12)
        ax.grid(True, color=grid, lw=0.8); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(grid)
        ax.tick_params(colors=muted, labelsize=8.5)
    axes[0].set_ylabel("平均 HV（8 条规则 × 5 次；各自统一归一化）", color=muted, fontsize=9)
    axes[1].legend(loc="lower right", fontsize=8, frameon=False, title="组（实例数）；虚线 = dec5", title_fontsize=8)
    fig.suptitle("偏离密度 K 与 HV（K0.25 原布局；K0.5 训练为扩展布局、测试为原布局；K0.75、K1.0 扩展布局）", fontsize=10, color=ink, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "d5_curves.png"), facecolor=fig.get_facecolor())


if __name__ == "__main__":
    main()
