"""模仿学习的老师数据：在训练实例上跑 MOEA（与验证相同的 NSGA-II），保存每次运行全部已评价可行解中
前 3 层非支配解（按目标值去重）的基因、目标值和派班序列。测试实例不参与。
用法: python collect.py [臂,臂,...] [次数] [进程数|auto]
  默认臂 dec5,K0.25:default，各 10 次，种子 5000+次号（与测试集验证的种子不同）。
输出: out/teacher/<实例>__<臂>__<次号>.pkl，已存在的跳过（可续跑）。
"""
import multiprocessing as mp, os, pickle, sys, time
import numpy as np
import common as C
import arms as A
import ga as G

TDIR = os.path.join(C.OUT, "teacher")


def run_keep(sc, dec, seed):
    rng = np.random.default_rng(seed)
    nv = C.L.nvar(sc, "dec5")
    archive, ev = {}, [0]

    def evaluate(x):
        r = dec(sc, x); ev[0] += 1
        if r.feasible:
            key = r.pheno
            if key not in archive:
                archive[key] = (r.obj, np.asarray(x, np.float64).copy(), list(r.sim.seq))
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
    # 按目标值去重（同一目标值保留第一次见到的排班），取前 3 层非支配
    byobj = {}
    for obj, x, seq in archive.values():
        byobj.setdefault(obj, (obj, x, seq))
    sols = list(byobj.values())
    fronts = G.nd_sort([s[0] for s in sols]) if sols else []
    keep = []
    for rank, fr in enumerate(fronts[:3]):
        for i in fr:
            obj, x, seq = sols[i]
            keep.append({"obj": obj, "x": x, "seq": seq, "rank": rank})
    return keep, len(archive)


def job(args):
    inst, arm, k = args
    path = os.path.join(TDIR, f"{inst}__{arm.replace(':', '_')}__{k}.pkl")
    if os.path.exists(path):
        return path, 0, 0.0
    sc = C.I.load(inst)
    t = time.time()
    keep, nuniq = run_keep(sc, A.decoder(arm), 5000 + k)
    d = {"inst": inst, "arm": arm, "run": k, "seed": 5000 + k, "secs": time.time() - t, "n_unique": nuniq, "sols": keep}
    tmp = path + ".tmp"
    pickle.dump(d, open(tmp, "wb"))
    os.replace(tmp, path)
    return path, len(keep), d["secs"]


def main():
    mp.freeze_support()
    arms = (sys.argv[1] if len(sys.argv) > 1 else "dec5,K0.25:default").split(",")
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    procs = C.nprocs(sys.argv[3] if len(sys.argv) > 3 else "auto")
    os.makedirs(TDIR, exist_ok=True)
    tr, _ = C.I.split()
    jobs = [(i, a, k) for k in range(reps) for i in tr for a in arms]
    jobs.sort(key=lambda j: -C.L.nvar(C.I.load(j[0]), "dec5"))
    print(f"{len(jobs)} 次运行（训练实例 {len(tr)} 个），{procs} 个进程", flush=True)
    t0 = time.time()
    with mp.Pool(procs) as p:
        for n, (path, nk, secs) in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            if n % 20 == 0 or n == len(jobs):
                print(f"{n}/{len(jobs)}  {(time.time() - t0) / 60:.1f} 分钟", flush=True)
    print("完成：", TDIR)


if __name__ == "__main__":
    main()
