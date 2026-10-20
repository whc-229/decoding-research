"""规则确定后的验证：在测试集上跑 MOEA（Python NSGA-II，种群 30，465 次评价，与 ga.py 相同的算子），比较各臂。
臂的写法：
  dec5                          逐班基因（容量预判 + 回溯修复）
  K0.25:default                 稀疏偏离 K=0.25 + 默认规则（= dec9）
  K0.25:out/full/best_rule.py   稀疏偏离 K=0.25 + 规则文件
用法: python ga_rule.py 臂[,臂...] 次数 进程数 输出.csv [实例,...|test|train]
输出与 *_runs.csv 相同的格式（variant 列为臂名），可续跑（已有的 (实例, 臂, 次) 跳过）。
"""
import csv, multiprocessing as mp, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import ga as G  # noqa: E402
import instances as I  # noqa: E402
import ruledec as R  # noqa: E402

L = R.L
_rules = {}


def decoder(arm):
    if arm == "dec5":
        return lambda sc, x: L.decode(sc, x, "dec5")
    k, src = arm.split(":", 1)
    kf = float(k[1:])
    if src == "default":
        rule = R.default_rule
    else:
        if src not in _rules:
            _rules[src] = R.compile_rule(open(os.path.join(HERE, src) if not os.path.isabs(src) else src, encoding="utf-8").read())
        rule = _rules[src]
    return lambda sc, x: R.decode_rule(sc, x, rule, kf)


def run(sc, dec, seed):
    rng = np.random.default_rng(seed)
    nv = L.nvar(sc, "dec5")
    archive, ev = [], [0]

    def evaluate(x):
        r = dec(sc, x); ev[0] += 1
        if r.feasible:
            archive.append(r.obj)
            return x, r.obj
        return x, G.BIG

    P = [evaluate(rng.uniform(0, G.UB, nv)) for _ in range(G.POP)]
    while ev[0] < G.EVALS:
        kids = []
        while len(kids) < G.POP and ev[0] + len(kids) < G.EVALS:
            a, b = P[rng.integers(len(P))][0], P[rng.integers(len(P))][0]
            c1, c2 = G.sbx(a, b, rng)
            kids += [G.pm(c1, rng), G.pm(c2, rng)]
        kids = kids[:min(G.POP, G.EVALS - ev[0])]
        U = P + [evaluate(k) for k in kids]
        F = [u[1] for u in U]
        newP = []
        for fr in G.nd_sort(F):
            if len(newP) + len(fr) <= G.POP:
                newP += fr
            else:
                cd = G.crowd(F, fr)
                newP += sorted(fr, key=lambda i: -cd[i])[:G.POP - len(newP)]
                break
        P = [U[i] for i in newP]
    nd, best = [], float("inf")
    for a, b in sorted(set(archive)):
        if b < best - 1e-12:
            nd.append((a, b)); best = b
    return nd


def job(args):
    inst, arm, k = args
    sc = I.load(inst)
    t = time.time()
    fr = run(sc, decoder(arm), 1000 + k)
    return [inst, arm, k, f"{time.time() - t:.1f}", G.EVALS, L.nvar(sc, "dec5"), ";".join(f"{int(a)}:{b:.3f}" for a, b in fr)]


if __name__ == "__main__":
    mp.freeze_support()
    arms, reps, procs, outp = sys.argv[1].split(","), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    sel = sys.argv[5] if len(sys.argv) > 5 else "test"
    tr, te = I.split()
    insts = {"test": te, "train": tr}.get(sel) or sel.split(",")
    done = set()
    if os.path.exists(outp):
        for r in csv.reader(open(outp, encoding="utf-8")):
            if r and r[0] != "scenario":
                done.add((r[0], r[1], int(r[2])))
    jobs = [(i, a, k) for k in range(reps) for i in insts for a in arms if (i, a, k) not in done]
    print(f"{len(jobs)} 次运行待做（已有 {len(done)}）", flush=True)
    new = not os.path.exists(outp)
    with open(outp, "a", newline="", encoding="utf-8") as f, mp.Pool(procs) as p:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        for n, row in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            w.writerow(row); f.flush()
            if n % 10 == 0 or n == len(jobs):
                print(f"{n}/{len(jobs)}", row[0], row[1], row[3] + "s", flush=True)
