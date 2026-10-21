"""测试集 MOEA 验证（任务 A / B）：NSGA-II（任意评价次数、可在多个检查点记录前沿）或 MOEA/D，臂的写法同 arms.py。

NSGA-II：与 rulegen/ga_rule.run 逐行相同（种群 30、SBX + 多项式变异、种子 1000+次号），只是评价次数可调，并在检查点
  记录"到此为止全部已评价可行解的非支配集"。一次 2000 次评价的运行在第 465 次时的前沿与 465 次的运行逐位相同
  （最后一代的子代先全部生成再依次评价，前 15 个子代用的随机数相同），用 val_server.csv 自检。
MOEA/D：照 bench/moea_fjsp2.py 的 run_moead——30 个权向量 (i/29, 1−i/29)、邻域 6、每个子问题每代 1 个子代（邻域内两个父代 SBX
  取第一个子代再多项式变异）、归一化 Tchebycheff（理想点 / 最差点取当前种群与子代）、最多替换 2 个邻居。
  与 FJSP 不同之处：排班有不可行解（目标记为 BIG）。为免 BIG 把归一化拉坏，理想点 / 最差点只用可行解计算；
  不可行解的 Tchebycheff 值记为 +∞（比任何可行解都差，不可行子代不会替换可行邻居；两个都不可行时也不替换）。
  记录口径与 NSGA-II 相同：检查点时全部已评价可行解的非支配集。

用法: python moea_any.py 臂[,臂...] 次数 进程数|auto 输出.csv [test|train|实例,...] [--algo nsga2|moead] [--checks 465,2000]
  最后一个检查点 = 评价次数。输出列与 ga_any.py 相同，evaluations 列 = 检查点；每次运行每个检查点一行。
  可续跑：(实例, 臂, 次号) 在最后一个检查点已有记录的跳过。
"""
import argparse, csv, multiprocessing as mp, os, time
import numpy as np
import common as C
import arms as A
import ga as G

BIG = G.BIG


def front_of(archive):
    """全部可行解目标值 → 非支配集（与 ga_rule.run 结尾相同）"""
    nd, best = [], float("inf")
    for a, b in sorted(set(archive)):
        if b < best - 1e-12:
            nd.append((a, b)); best = b
    return nd


def run_nsga2(sc, dec, seed, checks):
    """ga_rule.run 的逐行复制，评价次数 = checks[-1]，在每个检查点保存前沿 → {检查点: 前沿}"""
    EVALS = checks[-1]
    rng = np.random.default_rng(seed)
    nv = C.L.nvar(sc, "dec5")
    archive, ev, snaps = [], [0], {}

    def evaluate(x):
        r = dec(sc, x); ev[0] += 1
        out = (x, r.obj) if r.feasible else (x, BIG)
        if r.feasible:
            archive.append(r.obj)
        if ev[0] in checks:
            snaps[ev[0]] = front_of(archive)
        return out

    P = [evaluate(rng.uniform(0, G.UB, nv)) for _ in range(G.POP)]
    while ev[0] < EVALS:
        kids = []
        while len(kids) < G.POP and ev[0] + len(kids) < EVALS:
            a, b = P[rng.integers(len(P))][0], P[rng.integers(len(P))][0]
            c1, c2 = G.sbx(a, b, rng)
            kids += [G.pm(c1, rng), G.pm(c2, rng)]
        kids = kids[:min(G.POP, EVALS - ev[0])]
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
    return snaps


def run_moead(sc, dec, seed, checks, T=6, nr=2):
    """MOEA/D（见文件说明）→ {检查点: 前沿}"""
    EVALS = checks[-1]
    POP = G.POP
    rng = np.random.default_rng(seed)
    nv = C.L.nvar(sc, "dec5")
    archive, ev, snaps = [], [0], {}

    def evaluate(x):
        r = dec(sc, x); ev[0] += 1
        if r.feasible:
            archive.append(r.obj)
        if ev[0] in checks:
            snaps[ev[0]] = front_of(archive)
        return r.obj if r.feasible else None

    W = np.array([[i / (POP - 1), 1 - i / (POP - 1)] for i in range(POP)])
    dist = np.linalg.norm(W[:, None, :] - W[None, :, :], axis=2)
    B = np.argsort(dist, axis=1)[:, :T]
    X = [rng.uniform(0, G.UB, nv) for _ in range(POP)]
    Fv = [evaluate(x) for x in X]

    def tch(f, w, z, zn):
        if f is None:
            return float("inf")
        f = np.asarray(f, float)
        rg = np.where(zn - z > 1e-9, zn - z, 1.0)
        return float(np.max(np.maximum(w, 1e-6) * (f - z) / rg))
    while ev[0] < EVALS:
        for i in rng.permutation(POP):
            if ev[0] >= EVALS:
                break
            a, b = rng.choice(B[i], 2, replace=False)
            c1, _ = G.sbx(X[a], X[b], rng)
            y = G.pm(c1, rng)
            fy = evaluate(y)
            feas = [f for f in Fv if f is not None] + ([fy] if fy is not None else [])
            if feas:
                A_ = np.array(feas, float); z, zn = A_.min(0), A_.max(0)
            else:
                z = zn = np.zeros(2)
            c = 0
            for j in rng.permutation(B[i]):
                if c >= nr:
                    break
                if fy is not None and tch(fy, W[j], z, zn) <= tch(Fv[j], W[j], z, zn):
                    X[j], Fv[j] = y.copy(), fy; c += 1
    return snaps


def job(args):
    inst, name, spec, k, algo, checks = args
    sc = C.I.load(inst)
    t = time.time()
    snaps = (run_moead if algo == "moead" else run_nsga2)(sc, A.decoder(spec), 1000 + k, checks)
    secs = f"{time.time() - t:.1f}"
    nv = C.L.nvar(sc, "dec5")
    return [[inst, name, k, secs, c, nv, ";".join(f"{int(a)}:{b:.3f}" for a, b in snaps[c])] for c in checks]


def main():
    mp.freeze_support()
    ap = argparse.ArgumentParser()
    ap.add_argument("arms"); ap.add_argument("reps", type=int); ap.add_argument("procs"); ap.add_argument("out")
    ap.add_argument("sel", nargs="?", default="test")
    ap.add_argument("--algo", default="nsga2", choices=["nsga2", "moead"])
    ap.add_argument("--checks", default="465")
    a = ap.parse_args()
    arms = [A.parse(s) for s in a.arms.split(",")]
    checks = sorted(int(c) for c in a.checks.split(","))
    tr, te = C.I.split()
    insts = {"test": te, "train": tr}.get(a.sel) or a.sel.split(",")
    done = set()
    if os.path.exists(a.out):
        for r in csv.reader(open(a.out, encoding="utf-8")):
            if r and r[0] != "scenario" and int(r[4]) == checks[-1]:
                done.add((r[0], r[1], int(r[2])))
    for _, spec in arms:
        if spec != "dec5":
            A.rule_of(spec)
    jobs = [(i, n, s, k, a.algo, checks) for k in range(a.reps) for i in insts for n, s in arms if (i, n, k) not in done]
    jobs.sort(key=lambda j: -C.L.nvar(C.I.load(j[0]), "dec5"))
    procs = C.nprocs(a.procs)
    print(f"{a.algo}，检查点 {checks}：{len(jobs)} 次运行待做（已有 {len(done)}），{procs} 个进程", flush=True)
    new = not os.path.exists(a.out)
    t0 = time.time()
    with open(a.out, "a", newline="", encoding="utf-8") as f, mp.Pool(procs) as p:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        for n, rows in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            w.writerows(rows); f.flush()
            if n % 20 == 0 or n == len(jobs):
                el = time.time() - t0
                print(f"{n}/{len(jobs)}  已用 {el / 60:.0f} 分钟，预计还要 {el / n * (len(jobs) - n) / 60:.0f} 分钟", flush=True)


if __name__ == "__main__":
    main()
