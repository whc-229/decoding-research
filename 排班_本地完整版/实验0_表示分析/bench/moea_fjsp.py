"""FJSP 上的 MOEA 比较：NSGA-II（种群 30，算子同 ga.py），目标 (makespan, total workload)。
一次运行跑到最大预算，在各检查点（465 / 2000 / 5000 次评价）记录全部已评价可行解的非支配集。
另记录到该检查点为止 makespan 最好的那个解相对规则的偏离步数 d（pd 与 sp 编码可算）。
用法: python moea_fjsp.py 编码[,编码...] 次数 进程数 输出.csv 实例名[,..]|brandimarte|kacem|fattahi|all
编码: pd, rk, sp0.1, sp0.25, sp0.5（稀疏槽数 = 比例 × 工序数）
"""
import csv, multiprocessing as mp, os, sys, time
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):   # 每个进程只用 1 个线程，避免几十个进程各开一堆线程把内存吃光
    os.environ.setdefault(_v, "1")
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
for _p in (os.path.dirname(HERE), "/home/claude/exp0/scripts"):   # ga.py 所在目录：放在 实验0_表示分析/bench/ 时是上一级
    if os.path.exists(os.path.join(_p, "ga.py")):
        sys.path.insert(0, _p); break
import fjsp as F  # noqa
import ga as G  # noqa

CHECK = [465, 2000, 5000]
POP = 30


def enc_name(inst, e):
    return f"sp{F.k_slots(inst, float(e[2:]))}" if e.startswith("sp") else e


def run(inst, e, seed):
    rng = np.random.default_rng(seed)
    en = enc_name(inst, e)
    nv = F.nvar(inst, en)
    arch, best, ev, snaps = [], [None, None], [0], {}

    def evaluate(x):
        o = F.decode(inst, en, x); ev[0] += 1
        arch.append(o)
        if best[0] is None or o < best[0]:
            best[0], best[1] = o, x.copy()
        if ev[0] in CHECK:
            nd, b = [], float("inf")
            for a, c in sorted(set(arch)):
                if c < b:
                    nd.append((a, c)); b = c
            d = None
            if en == "pd":
                d = F.rule_distance(inst, F.build(inst, lambda s, C: min(int(best[1][s] * len(C)), len(C) - 1))[2])
            snaps[ev[0]] = (nd, d)
        return x, o
    P = [evaluate(rng.uniform(0, G.UB, nv)) for _ in range(POP)]
    while ev[0] < CHECK[-1]:
        kids = []
        while len(kids) < POP and ev[0] + len(kids) < CHECK[-1]:
            a, b = P[rng.integers(len(P))][0], P[rng.integers(len(P))][0]
            c1, c2 = G.sbx(a, b, rng)
            kids += [G.pm(c1, rng), G.pm(c2, rng)]
        kids = kids[:min(POP, CHECK[-1] - ev[0])]
        U = P + [evaluate(k) for k in kids]
        Fv = [u[1] for u in U]
        newP = []
        for fr in G.nd_sort(Fv):
            if len(newP) + len(fr) <= POP:
                newP += fr
            else:
                cd = G.crowd(Fv, fr)
                newP += sorted(fr, key=lambda i: -cd[i])[:POP - len(newP)]
                break
        P = [U[i] for i in newP]
    return snaps


def job(a):
    name, path, e, k = a
    inst = F.load(path)
    t = time.time()
    snaps = run(inst, e, 1000 + k)
    secs = time.time() - t
    return [[name, e, k, b, f"{secs:.1f}", "" if snaps[b][1] is None else snaps[b][1],
             ";".join(f"{a}:{c}" for a, c in snaps[b][0])] for b in CHECK]


if __name__ == "__main__":
    mp.freeze_support()
    encs, reps, outp, sel = sys.argv[1].split(","), int(sys.argv[2]), sys.argv[4], sys.argv[5]
    procs = int(sys.argv[3]) if sys.argv[3].isdigit() else max(1, min(8, mp.cpu_count() // 2))   # auto：至多 8 个进程
    Mt = F.meta()
    if sel in ("brandimarte", "kacem", "fattahi", "hurink", "dauzere", "barnes", "behnke"):
        names = [n for n, d in Mt.items() if d["path"].startswith(sel)]
    elif sel == "all":
        names = list(Mt)
    else:
        names = sel.split(",")
    done = set()
    if os.path.exists(outp):
        for r in csv.reader(open(outp)):
            if r and r[0] != "instance":
                done.add((r[0], r[1], int(r[2])))
    jobs = [(n, Mt[n]["path"], e, k) for k in range(reps) for n in names for e in encs if (n, e, k) not in done]
    print(f"{len(jobs)} 次运行待做（已有 {len(done)}），{procs} 个进程", flush=True)
    new = not os.path.exists(outp)
    with open(outp, "a", newline="") as f, mp.Pool(procs) as p:
        w = csv.writer(f)
        if new:
            w.writerow(["instance", "encoding", "run", "evals", "seconds", "d_best", "front(makespan:workload;...)"])
        for n, rows in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            w.writerows(rows); f.flush()
            if n % 10 == 0 or n == len(jobs):
                print(f"{n}/{len(jobs)}", rows[0][0], rows[0][1], rows[0][4] + "s", flush=True)
