"""评估 llm_rules/ 下的每个步长规则，与内置规则（fixed / sha / heavy / state）在同一骨架下对比。
用法: python evaluate_rules.py [种子数] [劣解archive 0/1] [精英复用 0/1] [进程数]
输出: rules_results.csv, rules_summary.md
"""
import csv, glob, importlib.util, itertools, os, sys
from multiprocessing import Pool
import numpy as np
import slot_moea as s

SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
INF = sys.argv[2] == "1" if len(sys.argv) > 2 else True
REUSE = sys.argv[3] == "1" if len(sys.argv) > 3 else True
PROCS = int(sys.argv[4]) if len(sys.argv) > 4 else 2


def load(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.rule


LLM = {"llm:" + os.path.basename(p)[:-3]: p for p in sorted(glob.glob("llm_rules/*.py"))}
NAMES = ["fixed", "sha", "heavy", "state"] + list(LLM)


def job(a):
    p, nm, seed = a
    rule = load(LLM[nm]) if nm in LLM else None
    r = s.run(p, step=nm if rule is None else "fixed", step_rule=rule,
              inf=INF, reuse=REUSE, seed=seed)
    return p, nm, seed, r["igd"]


if __name__ == "__main__":
    jobs = list(itertools.product(s.PROBLEMS, NAMES, range(SEEDS)))
    with Pool(PROCS) as pool:
        rows = pool.map(job, jobs, chunksize=4)
    with open("rules_results.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["problem", "rule", "seed", "igd"]); w.writerows(rows)
    out = [f"# 步长规则对比（IA={'开' if INF else '关'}，精英复用={'开' if REUSE else '关'}，{SEEDS} 种子，平均 IGD）\n",
           "| 问题 | " + " | ".join(NAMES) + " |", "|---" * (len(NAMES) + 1) + "|"]
    ranks = {n: [] for n in NAMES}
    for p in s.PROBLEMS:
        m = {n: np.mean([r[3] for r in rows if r[0] == p and r[1] == n]) for n in NAMES}
        order = sorted(NAMES, key=m.get)
        for k, n in enumerate(order):
            ranks[n].append(k + 1)
        out.append(f"| {p} | " + " | ".join(("**%.4g**" if n == order[0] else "%.4g") % m[n] for n in NAMES) + " |")
    out.append("| 平均排名 | " + " | ".join(f"{np.mean(ranks[n]):.2f}" for n in NAMES) + " |")
    open("rules_summary.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
