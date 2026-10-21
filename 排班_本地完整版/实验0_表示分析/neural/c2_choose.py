"""任务 C2：在训练实例上按事先固定的规则选定最终方法的偏离密度 K（ana 环境）。
  ~/miniconda3/envs/ana/bin/python c2_choose.py
判定规则（2026-10-21 事先写死，不看测试集）：
  每个训练实例内，out/train_K.csv 的全部臂统一归一化 HV；方法层面 = 对 8 条规则（ES16 s0～s2、GP run1～5）× 5 次取平均；
  各 K（0.25、0.5）在 15 个训练实例上的平均 HV 最高者即最终 K。ES16、GP 两族也分别报告；两族不一致时以 8 条合并为准。
另报：各 K 两两配对 Wilcoxon（实例层面，Holm），dec5 作参照；C3 的 dev / 槽数与"K0.5 对 K0.25 增益"的 Spearman 相关。
输出：out/c2_choose.md、out/c2_choose.json（{"K": 选出的 K, ...}，run_C.sh 读它决定后续）
"""
import json, os, sys
import numpy as np
from scipy.stats import wilcoxon, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import analyze_methods as AM  # noqa: E402
import instances as I  # noqa: E402

KS = ["0.25", "0.5"]          # K0.75 在现有编码里表示不出来（槽被截到与 K0.5 相同、默认类型基因落进工具基因区），2026-10-21 用户决定只比这两档
FAM = {"ES16": [f"ES16(s{s})" for s in range(3)], "GP": [f"GP(run{r})" for r in range(1, 6)]}
ALL = FAM["ES16"] + FAM["GP"]


def main():
    runs = AM.load([os.path.join(OUT, "train_K.csv")])
    arms = sorted({x for _, x in runs})
    need = ["dec5"] + [f"K{k}:{r}" for k in KS for r in ALL]
    miss = [a for a in need if a not in arms]
    assert not miss, f"train_K.csv 缺臂：{miss}"
    insts = sorted({i for i, _ in runs})
    insts = [i for i in insts if all(len(runs.get((i, a), {})) == 5 for a in need)]
    H, _ = AM.normalize(runs, insts, need)
    hv = lambda i, a: float(np.mean(H[(i, a)]))
    V = {(k, f): {i: np.mean([hv(i, f"K{k}:{r}") for r in rs]) for i in insts} for k in KS for f, rs in list(FAM.items()) + [("合并", ALL)]}
    V[("dec5", "")] = {i: hv(i, "dec5") for i in insts}
    mean = lambda f, k: float(np.mean([V[(k, f)][i] for i in insts]))
    pick = {f: max(KS, key=lambda k: mean(f, k)) for f in ["合并", "ES16", "GP"]}
    final = pick["合并"]
    L = [f"# 任务 C2：训练实例上选 K（{len(insts)} 个训练实例，NSGA-II 465 次，种子 5000+次号）\n",
         "**K 由训练实例按事先固定的规则选出**：每个训练实例内全部臂统一归一化 HV，对 8 条规则 × 5 次取平均，平均 HV 最高的 K 为最终 K；"
         "两族不一致时以 8 条合并为准。测试集不参与。候选 K ∈ {0.25, 0.5}：K0.5 是现有编码能表示的最大偏离密度"
         "（K0.75 的偏离槽会被截到与 K0.5 相同，默认类型基因落进工具基因区），2026-10-21 决定不比 K0.75。\n",
         f"**选出：K = {final}**（合并）；ES16 族选 K = {pick['ES16']}，GP 族选 K = {pick['GP']}"
         + ("（两族一致）" if pick["ES16"] == pick["GP"] == final else "（两族不一致，按规则以合并为准）") + "。\n",
         "| 族 | " + " | ".join(f"K{k}" for k in KS) + " | 选出 |", "|---|" + "---|" * len(KS) + "---|"]
    for f in ["合并", "ES16", "GP"]:
        L.append(f"| {f} | " + " | ".join(f"{mean(f, k):.4f}" for k in KS) + f" | K{pick[f]} |")
    L.append(f"| 参照 dec5 | {np.mean(list(V[('dec5', '')].values())):.4f} | | |")
    L += ["\n分组（合并 8 条规则；平均 HV）：\n", "| 组 | 实例数 | dec5 | " + " | ".join(f"K{k}" for k in KS) + " |", "|---|---|---|" + "---|" * len(KS)]
    for g in "EHM":
        grp = [i for i in insts if I.group(i) == g]
        L.append(f"| {g} | {len(grp)} | {np.mean([V[('dec5', '')][i] for i in grp]):.4f} | " +
                 " | ".join(f"{np.mean([V[(k, '合并')][i] for i in grp]):.4f}" for k in KS) + " |")
    # 两两配对（合并），Holm
    pairs = [("0.5", "0.25")]
    tests = []
    for a, b in pairs:
        d = np.array([V[(a, "合并")][i] - V[(b, "合并")][i] for i in insts])
        tests.append((a, b, d.mean(), (d > 0).sum(), (d < 0).sum(), wilcoxon(d).pvalue if np.any(d != 0) else 1.0))
    adj = AM.holm([t[5] for t in tests])
    L += ["\nK0.5 对 K0.25（合并 8 条规则，实例层面配对 Wilcoxon；只有一个比较，Holm p = 原始 p）：\n", "| 比较 | 平均差 | 好/差实例数 | p | Holm p |", "|---|---|---|---|---|"]
    for (a, b, dm, up, dn, p), pa in zip(tests, adj):
        L.append(f"| K{a} − K{b} | {dm:+.4f} | {up}/{dn} | {p:.3g} | {pa:.3g} |")
    # C3：dev / 槽数 与 K0.5 对 K0.25 增益的相关
    c3 = {r["inst"]: r for r in json.load(open(os.path.join(OUT, "c3_dev.json"), encoding="utf-8"))}
    ratio = {i: np.mean([c3[i]["rules"][r]["min"] / c3[i]["slots"]["0.25"] for r in ALL]) for i in insts}
    gain = {i: V[("0.5", "合并")][i] - V[("0.25", "合并")][i] for i in insts}
    rho, p = spearmanr([ratio[i] for i in insts], [gain[i] for i in insts])
    L += ["\n## C3：规则到最近好解的距离（dev / K0.25 槽数）与 K0.5 对 K0.25 增益\n",
          "dev = dec5 好解（第 1 层非支配）重放时与规则首选不同的班次数，取最近好解、基因类型取最有利者；8 条规则平均。\n",
          "| 实例 | 组 | K0.25 槽数 | dev / 槽数（K0.25） | dev / 槽数（K0.5） | 增益 K0.5 − K0.25 |", "|---|---|---|---|---|---|"]
    for i in sorted(insts, key=lambda i: -ratio[i]):
        r5 = np.mean([c3[i]["rules"][r]["min"] / c3[i]["slots"]["0.5"] for r in ALL])
        L.append(f"| {i} | {I.group(i)} | {c3[i]['slots']['0.25']} | {ratio[i]:.2f} | {r5:.2f} | {gain[i]:+.4f} |")
    for g in "EHM":
        grp = [i for i in insts if I.group(i) == g]
        L.append(f"\n{g} 组 dev / 槽数（K0.25）：中位 {np.median([ratio[i] for i in grp]):.2f}，范围 {min(ratio[i] for i in grp):.2f}～{max(ratio[i] for i in grp):.2f}；"
                 f"> 1 的实例 {sum(ratio[i] > 1 for i in grp)}/{len(grp)}")
    L.append(f"\nSpearman（dev / 槽数 对 增益，{len(insts)} 个实例）：ρ = {rho:.2f}，p = {p:.2g}")
    open(os.path.join(OUT, "c2_choose.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"K": final, "pick": pick, "means": {f: {k: mean(f, k) for k in KS} for f in ["合并", "ES16", "GP"]},
               "spearman": [rho, p]}, open(os.path.join(OUT, "c2_choose.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
