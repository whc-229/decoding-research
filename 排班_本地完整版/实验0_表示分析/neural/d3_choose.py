"""任务 D3：扩展编码下在训练实例上按事先固定的规则选 K（ana 环境；在跑 D2 之前写好并用假数据测试过）。
  ~/miniconda3/envs/ana/bin/python d3_choose.py
判定规则（2026-10-22 事先写死，不看测试集）：
  out/train_Kext.csv（15 个训练实例，NSGA-II 465 次，种子 5000+次号，扩展布局 X0.5 / X0.75 / X1.0 × 8 条规则 × 5 次）；
  每个训练实例内全部臂统一归一化 HV；方法层面对 8 条规则 × 5 次取平均；平均 HV 最高的 K 为最终 K。
  ES16、GP 两族分别报告，不一致时以合并结果为准。若最高的是边界 K1.0，报告"在 0.5～1.0 内是否单调上升"，不再往上加。
另报：
  - 自检：X0.5（新解码重跑）与任务 C 的 K0.5（out/train_K.csv，原布局）对照——班次上界为偶数的实例两种布局完全相同，前沿应逐位相同；
    奇数时原布局的默认类型基因与第 0 班工具基因共用一个数，结果可以不同；
  - 代理分（out/score_ext.json）给出的 K 排序是否与 MOEA 一致；
  - C3：规则到最近 dec5 好解的 dev（out/c3_dev.json）除以新 K 的槽数。
输出：out/d3_choose.md、out/d3_choose.json（{"K": 选出的 K, ...}）
"""
import csv, json, os, sys
import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import analyze_methods as AM  # noqa: E402
import instances as I  # noqa: E402

KS = ["0.5", "0.75", "1.0"]
FAM = {"ES16": [f"ES16(s{s})" for s in range(3)], "GP": [f"GP(run{r})" for r in range(1, 6)]}
ALL = FAM["ES16"] + FAM["GP"]


def n_slots(inst, kf):
    """与 ruledec.n_slots 相同：max(4, ceil(kf × 班次上界))；班次上界 = nvar(dec5)//2 − 1（从 train_K.csv 的 Nvar 列读）"""
    import math
    return max(4, math.ceil(kf * NMAX[inst] - 1e-9))


NMAX = {}


def main():
    path = os.path.join(OUT, "train_Kext.csv")
    for r in csv.DictReader(open(os.path.join(OUT, "train_K.csv"), encoding="utf-8")):
        if r["variant"] == "dec5":
            NMAX[r["scenario"]] = int(r["Nvar"]) // 2 - 1
    runs = AM.load([path])
    need = [f"X{k}:{r}" for k in KS for r in ALL]
    arms = sorted({x for _, x in runs})
    miss = [a for a in need if a not in arms]
    assert not miss, f"train_Kext.csv 缺臂：{miss}"
    insts = sorted({i for i, _ in runs})
    insts = [i for i in insts if all(len(runs.get((i, a), {})) == 5 for a in need)]
    H, _ = AM.normalize(runs, insts, need)
    hv = lambda i, a: float(np.mean(H[(i, a)]))
    V = {(k, f): {i: np.mean([hv(i, f"X{k}:{r}") for r in rs]) for i in insts} for k in KS for f, rs in list(FAM.items()) + [("合并", ALL)]}
    mean = lambda f, k, grp=None: float(np.mean([V[(k, f)][i] for i in (grp or insts)]))
    pick = {f: max(KS, key=lambda k: mean(f, k)) for f in ["合并", "ES16", "GP"]}
    final = pick["合并"]
    mono = mean("合并", "0.5") < mean("合并", "0.75") < mean("合并", "1.0")
    L = [f"# 任务 D3：扩展编码下在训练实例上选 K（{len(insts)} 个训练实例，NSGA-II 465 次，种子 5000+次号）\n",
         "**K 由训练实例按事先固定的规则选出**：每个训练实例内全部臂统一归一化 HV，对 8 条规则 × 5 次取平均，平均 HV 最高的 K 为最终 K；"
         "两族不一致时以合并为准；若最高的是边界 K1.0，只报告 0.5～1.0 内是否单调上升，不再往上加。测试集不参与。\n",
         f"**选出：K = {final}**（合并）；ES16 族 K = {pick['ES16']}，GP 族 K = {pick['GP']}"
         + ("（两族一致）" if pick["ES16"] == pick["GP"] == final else "（两族不一致，按规则以合并为准）") + "。"
         + (f"最高在边界 K1.0：合并结果在 0.5～1.0 内{'单调上升' if mono else '不是单调上升'}。" if final == "1.0" else "") + "\n",
         "| 族 | " + " | ".join(f"X{k}" for k in KS) + " | 选出 |", "|---|" + "---|" * len(KS) + "---|"]
    for f in ["合并", "ES16", "GP"]:
        L.append(f"| {f} | " + " | ".join(f"{mean(f, k):.4f}" for k in KS) + f" | X{pick[f]} |")
    L += ["\n分组（合并 8 条规则）：\n", "| 组 | 实例数 | " + " | ".join(f"X{k}" for k in KS) + " |", "|---|---|" + "---|" * len(KS)]
    for g in "EHM":
        grp = [i for i in insts if I.group(i) == g]
        L.append(f"| {g} | {len(grp)} | " + " | ".join(f"{mean('合并', k, grp):.4f}" for k in KS) + " |")
    pairs = [("0.75", "0.5"), ("1.0", "0.5"), ("1.0", "0.75")]
    tests = []
    for a, b in pairs:
        d = np.array([V[(a, "合并")][i] - V[(b, "合并")][i] for i in insts])
        tests.append((a, b, d.mean(), (d > 0).sum(), (d < 0).sum(), wilcoxon(d).pvalue if np.any(d != 0) else 1.0))
    adj = AM.holm([t[5] for t in tests])
    L += ["\n各 K 两两（合并，实例层面配对 Wilcoxon，3 对 Holm）：\n", "| 比较 | 平均差 | 好/差实例数 | p | Holm p |", "|---|---|---|---|---|"]
    for (a, b, dm, up, dn, p), pa in zip(tests, adj):
        L.append(f"| X{a} − X{b} | {dm:+.4f} | {up}/{dn} | {p:.3g} | {pa:.3g} |")
    # 自检：X0.5 与任务 C 的 K0.5
    old = {(r[0], r[1].replace("K0.5:", ""), r[2]): r[6] for r in csv.reader(open(os.path.join(OUT, "train_K.csv"), encoding="utf-8"))
           if r[0] != "scenario" and r[1].startswith("K0.5:")}
    new = {(r[0], r[1].replace("X0.5:", ""), r[2]): r[6] for r in csv.reader(open(path, encoding="utf-8"))
           if r[0] != "scenario" and r[1].startswith("X0.5:")}
    even = [k for k in new if NMAX[k[0]] % 2 == 0 and k in old]
    odd = [k for k in new if NMAX[k[0]] % 2 == 1 and k in old]
    L += ["\n## 自检：X0.5（新布局）与任务 C 的 K0.5（原布局）\n",
          f"班次上界为偶数的实例（{len({k[0] for k in even})} 个）：{len(even)} 次运行中前沿逐位相同 {sum(old[k] == new[k] for k in even)} 次。"
          f"奇数的实例（{len({k[0] for k in odd})} 个：{', '.join(sorted({k[0] for k in odd}))}）：{len(odd)} 次运行中逐位相同 {sum(old[k] == new[k] for k in odd)} 次"
          "（原布局 K0.5 的默认类型基因与第 0 班工具基因共用一个数，结果可以不同）。"]
    # 代理分排序
    pj = os.path.join(OUT, "score_ext.json")
    if os.path.exists(pj):
        P = json.load(open(pj, encoding="utf-8"))
        pm = {f: {k: np.mean([np.mean(list(P[f"{r}|{float(k)}"].values())) for r in rs]) for k in KS}
              for f, rs in list(FAM.items()) + [("合并", ALL)]}
        L += ["\n## 代理分（15 实例 × 67 个对应 K 的基因）与 MOEA 的 K 排序\n", "| 族 | " + " | ".join(f"代理 X{k}" for k in KS) + " | 代理排序 | MOEA 排序 |",
              "|---|" + "---|" * len(KS) + "---|---|"]
        for f in ["合并", "ES16", "GP"]:
            po = " > ".join(f"X{k}" for k in sorted(KS, key=lambda k: -pm[f][k]))
            mo = " > ".join(f"X{k}" for k in sorted(KS, key=lambda k: -mean(f, k)))
            L.append(f"| {f} | " + " | ".join(f"{pm[f][k]:.4f}" for k in KS) + f" | {po} | {mo} |")
    # C3：dev / 新 K 槽数
    c3 = {r["inst"]: r for r in json.load(open(os.path.join(OUT, "c3_dev.json"), encoding="utf-8"))}
    L += ["\n## C3：规则到最近 dec5 好解的距离 dev / 槽数（8 条规则平均）\n", "| 组 | " + " | ".join(f"K{k}：中位（范围）；> 1 的实例" for k in ["0.25"] + KS) + " |",
          "|---|" + "---|" * (len(KS) + 1)]
    for g in "EHM":
        grp = [i for i in insts if I.group(i) == g]
        cells = []
        for k in ["0.25"] + KS:
            v = [np.mean([c3[i]["rules"][r]["min"] / n_slots(i, float(k)) for r in ALL]) for i in grp]
            cells.append(f"{np.median(v):.2f}（{min(v):.2f}～{max(v):.2f}）；{sum(x > 1 for x in v)}/{len(v)}")
        L.append(f"| {g} | " + " | ".join(cells) + " |")
    open(os.path.join(OUT, "d3_choose.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"K": final, "pick": pick, "monotone": bool(mono), "means": {f: {k: mean(f, k) for k in KS} for f in ["合并", "ES16", "GP"]}},
              open(os.path.join(OUT, "d3_choose.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
