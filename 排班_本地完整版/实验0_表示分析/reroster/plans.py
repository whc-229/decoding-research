"""为每个实例生成原排班：dec5 跑一次 Python NSGA-II（种群 30，465 次评价，种子 0），取资源数最少、其次均衡度最好的解的基因。
用法: python plans.py [进程数]   输出 plans/<实例>.npy"""
import multiprocessing as mp, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen")); sys.path.insert(0, os.path.dirname(HERE))
import ga as G  # noqa: E402
import instances as I  # noqa: E402
L = G.L


def best_genome(sc, seed=0):
    rng = np.random.default_rng(seed)
    nv = L.nvar(sc, "dec5")
    best, ev = [None, None], [0]

    def evaluate(x):
        r = L.decode(sc, x, "dec5"); ev[0] += 1
        if r.feasible:
            if best[0] is None or r.obj < best[0]:
                best[0], best[1] = r.obj, x.copy()
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
    return best


def job(inst):
    out = os.path.join(HERE, "plans", inst + ".npy")
    if os.path.exists(out):
        return inst, "已有"
    obj, x = best_genome(I.load(inst))
    if x is None:
        return inst, "无可行解"
    np.save(out, x)
    return inst, obj


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "plans"), exist_ok=True)
    tr, te = I.split()
    with mp.Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as p:
        for inst, o in p.imap_unordered(job, tr + te):
            print(inst, o, flush=True)
