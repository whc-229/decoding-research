"""抽象模型上的扫描：N=100, m=4，d 与 K 变化，PS 对照；预算 465 / 2000 / 10000；每格 20 个种子。
输出 sweep.json：{预算: {d: {"PS": 均值, K: 均值, ...}}}，值为最终最好的汉明距离（越小越好）。"""
import json, os, sys, itertools, multiprocessing as mp
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model as Mo  # noqa

N, m = 100, 4
DS = [0, 5, 10, 15, 20, 30, 40, 60, 80]
KS = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100]
BUDGETS = [465, 2000, 10000]
SEEDS = range(20)


def job(a):
    enc, d, K, s = a
    _, traj = Mo.run_encoding(enc, N, d, m, K, 1000 * d + s, evals=max(BUDGETS))
    return a, [int(traj[b - 1]) for b in BUDGETS]


if __name__ == "__main__":
    jobs = [("PS", d, 0, s) for d in DS for s in SEEDS] + [("SP", d, K, s) for d in DS for K in KS for s in SEEDS]
    with mp.Pool(2) as p:
        res = p.map(job, jobs, chunksize=20)
    out = {}
    for (enc, d, K, s), vals in res:
        for b, v in zip(BUDGETS, vals):
            out.setdefault(str(b), {}).setdefault(str(d), {}).setdefault("PS" if enc == "PS" else str(K), []).append(v)
    summ = {b: {d: {k: float(np.mean(v)) for k, v in dd.items()} for d, dd in bd.items()} for b, bd in out.items()}
    json.dump({"N": N, "m": m, "raw": out, "mean": summ}, open(os.path.join(HERE, "sweep.json"), "w"), indent=1)
    for b in summ:
        print("预算", b)
        print("d    PS   " + " ".join(f"K{K:<4d}" for K in KS) + "  最好K  K*=d/q")
        for d in map(str, DS):
            row = summ[b][d]
            bestK = min(KS, key=lambda K: row[str(K)])
            print(f"{d:3s} {row['PS']:5.1f} " + " ".join(f"{row[str(K)]:5.1f}" for K in KS) + f"   {bestK:3d}   {Mo.k_star(int(d))}")
