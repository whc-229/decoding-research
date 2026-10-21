"""任务 A3：优化器与预算的普适性分析（ana 环境）。
  ~/miniconda3/envs/ana/bin/python analyze_A.py
1) 自检：val_big.csv 第 465 次检查点的前沿与 val_server.csv 同名臂逐位相同；
2) MOEA/D-465（val_moead.csv）、NSGA-II-2000（val_big.csv 的 2000 检查点）各自统一归一化，用 analyze_methods 出主表、两两表（Holm）；
   为了对照，再把 val_server.csv 中同一组 13 个臂单独归一化（NSGA-II-465）；
3) 大预算下 K0.5 对 K0.25（ES16 s0～s2 逐条配对：同一条规则的两档；以及方法层面），NSGA-II-465 与 2000 各一份。
输出：out/val_A_moead.md、out/val_A_big2000.md、out/val_A_nsga465.md、out/val_A_K.md
"""
import csv, os, sys, subprocess
import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import analyze_methods as AM  # noqa: E402
import instances as I  # noqa: E402

PY = sys.executable


def rows(path):
    return [r for r in csv.reader(open(path, encoding="utf-8")) if r and r[0] != "scenario"]


def write(path, rs):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        w.writerows(rs)


def analyze(csvp, out):
    subprocess.run([PY, os.path.join(HERE, "analyze_methods.py"), csvp, "--out", out], check=True, stdout=subprocess.DEVNULL)


def k_compare(csvp, title):
    """ES16 的 K0.5 对 K0.25：同一条规则配对（每个实例 5 次平均），三条一起（方法层面）"""
    runs = AM.load([csvp])
    arms = sorted({x for _, x in runs})
    insts = sorted({i for i, _ in runs if all(runs.get((i, a)) for a in arms)})
    H, _ = AM.normalize(runs, insts, arms)
    L = [f"\n### {title}（{len(insts)} 个实例，{len(arms)} 个臂统一归一化）\n", "| 比较 | 全部 | 原 | E | H | M |", "|---|---|---|---|---|---|"]
    pairs = [(f"K0.5:ES16(s{s})", f"K0.25:ES16(s{s})") for s in range(3)]
    for lab, sel in [(f"ES16(s{s})", [pairs[s]]) for s in range(3)] + [("ES16 三条平均", pairs)]:
        cells = []
        for g in [None, "原", "E", "H", "M"]:
            grp = [i for i in insts if g is None or I.group(i) == g]
            d = np.array([np.mean([np.mean(H[(i, a)]) - np.mean(H[(i, b)]) for a, b in sel]) for i in grp])
            p = wilcoxon(d).pvalue if len(grp) > 1 and np.any(d != 0) else 1.0
            cells.append(f"{d.mean():+.3f}（p={p:.2g}）")
        L.append(f"| {lab}：K0.5 − K0.25 | " + " | ".join(cells) + " |")
    return L


def main():
    big = rows(os.path.join(OUT, "val_big.csv"))
    srv = {(r[0], r[1], r[2]): r[6] for r in rows(os.path.join(OUT, "val_server.csv")) if r[4] == "465"}
    b465 = [r for r in big if r[4] == "465"]
    same = [srv.get((r[0], r[1], r[2])) == r[6] for r in b465 if (r[0], r[1], r[2]) in srv]
    chk = f"自检：val_big.csv 第 465 次检查点 {len(same)} 行可与 val_server.csv 对照，逐位相同 {sum(same)} 行"
    print(chk)
    p2000 = os.path.join(OUT, "val_big_2000.csv"); write(p2000, [r for r in big if r[4] == "2000"])
    p465b = os.path.join(OUT, "val_big_465.csv"); write(p465b, b465)
    arms13 = {r[1] for r in rows(os.path.join(OUT, "val_moead.csv"))}
    p465 = os.path.join(OUT, "val_A_nsga465.csv"); write(p465, [r for r in rows(os.path.join(OUT, "val_server.csv")) if r[1] in arms13 and r[4] == "465"])
    analyze(os.path.join(OUT, "val_moead.csv"), os.path.join(OUT, "val_A_moead.md"))
    analyze(p2000, os.path.join(OUT, "val_A_big2000.md"))
    analyze(p465, os.path.join(OUT, "val_A_nsga465.md"))
    L = ["# 大预算下 K0.5 对 K0.25（ES16 规则）\n", chk + "。\n", "差 = 同一条规则 K0.5 臂减 K0.25 臂（每个实例先对 5 次取平均）；p = 实例层面配对 Wilcoxon（未校正）。"]
    L += k_compare(p465b, "NSGA-II 465 次（val_big.csv 的 465 检查点）")
    L += k_compare(p2000, "NSGA-II 2000 次")
    open(os.path.join(OUT, "val_A_K.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
