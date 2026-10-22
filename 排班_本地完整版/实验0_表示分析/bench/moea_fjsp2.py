"""v2（插空解码，见 fjsp2.py）。FJSP 上的 MOEA 比较：NSGA-II（种群 30，算子同 ga.py），目标 (makespan, total workload)。
一次运行跑到最大预算，在各检查点（465 / 2000 / 5000 次评价）记录全部已评价可行解的非支配集。
另记录到该检查点为止 makespan 最好的那个解相对规则的偏离步数 d（pd 与 sp 编码可算）。
用法: python moea_fjsp2.py 编码[,编码...] 次数 进程数(auto) 输出.csv 实例名[,..]|实例族|all|main|big [最大预算=5000] [noins] [moead]
  moead：改用 MOEA/D（Tchebycheff 分解，30 个权向量，邻域 6，同样的 SBX/多项式变异），检验结论与搜索算法无关
  main = 除 Behnke 外的 276 个实例；big = Brandimarte、Dauzère、Barnes、Kacem、Fattahi（78 个，用于大预算）
编码: pd, rk, sp0.1, sp0.25, sp0.5（稀疏槽数 = 比例 × 工序数）；rk+seed, rk+glr, rk+glr+seed（rk 加启发式初始化，见 seed_fjsp.py）
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
import fjsp2 as F  # noqa
import ga as G  # noqa
import seed_fjsp as SD  # noqa

ALL_CHECK = [465, 2000, 5000, 10000, 20000, 50000]
CHECK = [465, 2000, 5000]          # 由命令行的最大预算决定
INSERT = True
ALGO = "nsga2"
POP = 30


def enc_name(inst, e):
    """命令行编码名 → 解码用名：sp0.25 → sp{K}；sp0.25q0.2 → sp{K}q0.2（q 为每槽随机生效概率，默认 0.4）；
    rk+seed / rk+glr / rk+glr+seed → rk（只是初始种群不同，见 seed_fjsp.py）"""
    if e.startswith("rk+"):
        return "rk"
    if not e.startswith("sp"):
        return e
    frac, q = (e[2:].split("q") + [None])[:2]
    K = F.k_slots(inst, float(frac))
    return f"sp{K}" + (f"q{q}" if q else "")


def run(inst, e, seed):
    rng = np.random.default_rng(seed)
    en = enc_name(inst, e)
    nv = F.nvar(inst, en)
    arch, best, ev, snaps = [], [None, None], [0], {}

    def evaluate(x):
        o = F.decode(inst, en, x, insert=INSERT); ev[0] += 1
        arch.append(o)
        if best[0] is None or o < best[0]:
            best[0], best[1] = o, x.copy()
        if ev[0] in CHECK:
            nd, b = [], float("inf")
            for a, c in sorted(set(arch)):
                if c < b:
                    nd.append((a, c)); b = c
            d = None
            if en != "rk":                       # 当前 makespan 最好的解相对规则偏离了几步（规则距离的上界估计）
                pk = []; F.decode(inst, en, best[1], insert=INSERT, picks=pk); d = sum(1 for i in pk if i)
            snaps[ev[0]] = (nd, d)
        return x, o
    X0 = SD.init_pop(inst, e, rng, POP, nv) if e.startswith("rk+") else [rng.uniform(0, G.UB, nv) for _ in range(POP)]
    P = [evaluate(x) for x in X0]
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


def run_moead(inst, e, seed, T=6, nr=2):
    """MOEA/D：权向量 (i/(POP−1), 1−i/(POP−1))，归一化 Tchebycheff（理想点与最差点取当前种群），每个子问题每代生成 1 个子代，
    最多替换 nr 个邻居。记录口径与 NSGA-II 相同：检查点时全部已评价解的非支配集。"""
    rng = np.random.default_rng(seed)
    en = enc_name(inst, e)
    nv = F.nvar(inst, en)
    arch, best, ev, snaps = [], [None, None], [0], {}

    def evaluate(x):
        o = F.decode(inst, en, x, insert=INSERT); ev[0] += 1
        arch.append(o)
        if best[0] is None or o < best[0]:
            best[0], best[1] = o, x.copy()
        if ev[0] in CHECK:
            nd, b = [], float("inf")
            for a, c in sorted(set(arch)):
                if c < b:
                    nd.append((a, c)); b = c
            d = None
            if en != "rk":
                pk = []; F.decode(inst, en, best[1], insert=INSERT, picks=pk); d = sum(1 for i in pk if i)
            snaps[ev[0]] = (nd, d)
        return o
    W = np.array([[i / (POP - 1), 1 - i / (POP - 1)] for i in range(POP)])
    dist = np.linalg.norm(W[:, None, :] - W[None, :, :], axis=2)
    B = np.argsort(dist, axis=1)[:, :T]
    X = SD.init_pop(inst, e, rng, POP, nv) if e.startswith("rk+") else [rng.uniform(0, G.UB, nv) for _ in range(POP)]
    Fv = np.array([evaluate(x) for x in X], dtype=float)

    def tch(f, w, z, zn):
        rg = np.where(zn - z > 1e-9, zn - z, 1.0)
        return np.max(np.maximum(w, 1e-6) * (f - z) / rg)
    while ev[0] < CHECK[-1]:
        for i in rng.permutation(POP):
            if ev[0] >= CHECK[-1]:
                break
            a, b = rng.choice(B[i], 2, replace=False)
            c1, _ = G.sbx(X[a], X[b], rng)
            y = G.pm(c1, rng)
            fy = np.array(evaluate(y), dtype=float)
            z, zn = np.minimum(Fv.min(0), fy), np.maximum(Fv.max(0), fy)
            c = 0
            for j in rng.permutation(B[i]):
                if c >= nr:
                    break
                if tch(fy, W[j], z, zn) <= tch(Fv[j], W[j], z, zn):
                    X[j], Fv[j] = y.copy(), fy; c += 1
    return snaps


def job(a):
    global CHECK, INSERT, ALGO
    name, path, e, k, CHECK, INSERT, ALGO = a
    inst = F.load(path)
    t = time.time()
    snaps = (run_moead if ALGO == "moead" else run)(inst, e, 1000 + k)
    secs = time.time() - t
    return [[name, e, k, b, f"{secs:.1f}", "" if snaps[b][1] is None else snaps[b][1],
             ";".join(f"{a}:{c}" for a, c in snaps[b][0])] for b in CHECK]


if __name__ == "__main__":
    mp.freeze_support()
    encs, reps, outp, sel = sys.argv[1].split(","), int(sys.argv[2]), sys.argv[4], sys.argv[5]
    maxe = int(sys.argv[6]) if len(sys.argv) > 6 else 5000
    CHECK = [b for b in ALL_CHECK if b <= maxe]
    INSERT = "noins" not in sys.argv[7:]
    ALGO = "moead" if "moead" in sys.argv[7:] else "nsga2"
    procs = int(sys.argv[3]) if sys.argv[3].isdigit() else max(1, min(8, mp.cpu_count() // 2))   # auto：至多 8 个进程
    Mt = F.meta()
    if sel in ("brandimarte", "kacem", "fattahi", "hurink", "dauzere", "barnes", "behnke"):
        names = [n for n, d in Mt.items() if d["path"].startswith(sel)]
    elif sel == "all":
        names = list(Mt)
    elif sel == "main":
        names = [n for n, d in Mt.items() if not d["path"].startswith("behnke")]
    elif sel == "big":
        names = [n for n, d in Mt.items() if d["path"].split("/")[0] in ("brandimarte", "dauzere", "barnes", "kacem", "fattahi")]
    else:
        names = sel.split(",")
    done = set()
    if os.path.exists(outp):
        for r in csv.reader(open(outp)):
            if r and r[0] != "instance":
                done.add((r[0], r[1], int(r[2])))
    jobs = [(n, Mt[n]["path"], e, k, CHECK, INSERT, ALGO) for k in range(reps) for n in names for e in encs if (n, e, k) not in done]
    print(f"{len(jobs)} 次运行待做（已有 {len(done)}），{procs} 个进程，算法 {ALGO}，{'插空' if INSERT else '不插空'}，检查点 {CHECK}", flush=True)
    new = not os.path.exists(outp)
    with open(outp, "a", newline="") as f, mp.Pool(procs) as p:
        w = csv.writer(f)
        if new:
            w.writerow(["instance", "encoding", "run", "evals", "seconds", "d_best", "front(makespan:workload;...)"])
        for n, rows in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            w.writerows(rows); f.flush()
            if n % 10 == 0 or n == len(jobs):
                print(f"{n}/{len(jobs)}", rows[0][0], rows[0][1], rows[0][4] + "s", flush=True)
