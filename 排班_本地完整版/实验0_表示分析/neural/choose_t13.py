"""T13 第 3 步判定（在看到训练结果之前写好）：15 个训练实例上，稠密有偏编码 D{q} 取 q ∈ {0.2, 0.4, 0.6}、
Pareto 局部搜索 P{j} 取 j ∈ {1, 2, 4} 中平均 HV 最高者。HV：每个实例内用 train_t13.csv 全部臂统一归一化（不可行运行 HV = 0）；
方法层面对 8 条规则 × 5 次取平均，再对实例取平均。并列取写在前面的参数。
用法（neural/ 下）: python choose_t13.py out/train_t13.csv → 打印并写 out/choose_t13.json"""
import csv, json, sys, collections, re
import numpy as np


def hv(P, ref=1.1):
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2


FAM = {"D": ["D0.2", "D0.4", "D0.6"], "P": ["P1", "P2", "P4"]}

if __name__ == "__main__":
    R = collections.defaultdict(list)
    for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
        s = r["front(资源数:均衡度;...)"]
        R[(r["scenario"], r["variant"])].append([tuple(map(float, p.split(":"))) for p in s.split(";")] if s else [])
    insts = sorted({k[0] for k in R}); arms = sorted({k[1] for k in R})
    fam_of = lambda a: a.split(":")[0]                     # 臂名写成 D0.4:ES16(s0) / P2:GP(run1)
    M = collections.defaultdict(list)
    for n in insts:
        pts = np.array([p for a in arms for fr in R[(n, a)] for p in fr]); lo, hi = pts.min(0), pts.max(0)
        rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        per = collections.defaultdict(list)
        for a in arms:
            per[fam_of(a)] += [hv([tuple((np.array(p) - lo) / rg) for p in fr]) if fr else 0.0 for fr in R[(n, a)]]
        for f, v in per.items():
            M[f].append(np.mean(v))
    mean = {f: float(np.mean(v)) for f, v in M.items()}
    pick = {}
    for f, cand in FAM.items():
        best = cand[0]
        for c in cand[1:]:
            if mean.get(c, -1) > mean.get(best, -1) + 1e-9:
                best = c
        pick[f] = best
    for f in sorted(mean, key=lambda f: -mean[f]):
        print(f"{f:6s} {mean[f]:.3f}")
    print("选中：", pick)
    json.dump(dict(mean=mean, pick=pick, n_inst=len(insts)), open("out/choose_t13.json", "w"), ensure_ascii=False, indent=1)
