"""全因子实验：4 步长规则 × 劣解 archive(开/关) × 精英复用(开/关) × 7 问题 × 15 种子
用法:  python experiment.py [种子数] [进程数]
输出:  results.csv
"""
import csv, itertools, sys, time
from multiprocessing import Pool
import slot_moea as s

STEPS = ["fixed", "sha", "heavy", "state"]
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 15
PROCS = int(sys.argv[2]) if len(sys.argv) > 2 else 2


def job(args):
    p, st, inf, reuse, seed = args
    r = s.run(p, step=st, inf=inf, reuse=reuse, seed=seed)
    return (p, st, int(inf), int(reuse), seed, r["igd"])


if __name__ == "__main__":
    jobs = list(itertools.product(s.PROBLEMS, STEPS, [False, True], [False, True], range(SEEDS)))
    t = time.time()
    with Pool(PROCS) as pool:
        rows = pool.map(job, jobs, chunksize=8)
    with open("results.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["problem", "step", "inf", "reuse", "seed", "igd"])
        w.writerows(rows)
    print(f"{len(rows)} runs in {time.time() - t:.0f}s")
