"""T13：最接近的已有方法作为对照。在 moea_fjsp2.py 外面加新编码（fjsp_base3.py）与一个新算法（pls），moea_fjsp2.py 本身不改。
用法与 moea_fjsp2.py 相同：
  python moea_fjsp3.py 臂[,臂...] 次数 进程数 输出.csv 实例名[,..]|实例族|main|big [最大预算=5000] [moead]
臂：
  moea_fjsp2.py 的全部编码（rk、pd、sp0.5、sp0.5q0.2 ……），NSGA-II（或 moead）
  db{ρ}、hs、ps{ε}                      新编码（见 fjsp_base3.py），NSGA-II（或 moead）
  pls{j}:{sp 编码}  例如 pls2:sp0.5     偏离空间上的 Pareto 局部搜索：从规则解（全部槽关闭）出发，每次从存档随机取一个解，
                                        重抽 j 个随机槽的两个基因（拆掉并重建 j 处偏离），不被存档支配就进存档
                                        （与存档中目标值相同的解被替换，允许中性移动）。不用种群、不用交叉。
输出 CSV 的格式与 moea_fjsp2.py 相同，可以直接与 v3_big_all.csv 合并后用 analyze_fjsp2.py 分析。
种子：第 k 次运行用 1000 + k，与 moea_fjsp2.py 相同。"""
import csv, multiprocessing as mp, os, sys, time
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import moea_fjsp2 as M2  # noqa
import fjsp2 as F  # noqa
import fjsp_base3 as B  # noqa
G = M2.G

_dec0, _nvar0 = F.decode, F.nvar


def _decode(inst, enc, g=None, insert=True, picks=None):
    if B.is_new(enc):
        return B.decode3(inst, enc, g, insert, picks)
    return _dec0(inst, enc, g, insert=insert, picks=picks)


def _nvar(inst, enc):
    return B.nvar3(inst, enc) if B.is_new(enc) else _nvar0(inst, enc)


F.decode, F.nvar = _decode, _nvar            # moea_fjsp2.run / run_moead 在调用时按模块属性取，替换后即生效


def run_pls(inst, e, seed):
    j_str, enc = e.split(":", 1)
    j = int(j_str[3:])
    rng = np.random.default_rng(seed)
    en = M2.enc_name(inst, enc)
    K = M2.F.parse_sp(en)[0]
    nv = F.nvar(inst, en)
    CHECK = M2.CHECK
    allf, best, ev, snaps = [], [None, None], [0], {}

    def evaluate(x):
        o = F.decode(inst, en, x, insert=M2.INSERT); ev[0] += 1
        allf.append(o)
        if best[0] is None or o < best[0]:
            best[0], best[1] = o, x.copy()
        if ev[0] in CHECK:
            nd, b = [], float("inf")
            for a, c in sorted(set(allf)):
                if c < b:
                    nd.append((a, c)); b = c
            pk = []; F.decode(inst, en, best[1], insert=M2.INSERT, picks=pk)
            snaps[ev[0]] = (nd, sum(1 for i in pk if i))
        return o

    x0 = np.zeros(nv)                          # 全部槽关闭 = 规则解
    arch = [(x0, evaluate(x0))]
    while ev[0] < CHECK[-1]:
        x = arch[rng.integers(len(arch))][0].copy()
        for k in rng.choice(K, size=min(j, K), replace=False):
            x[2 * k], x[2 * k + 1] = rng.uniform(0, G.UB), rng.uniform(0, G.UB)
        o = evaluate(x)
        if any(a[1][0] <= o[0] and a[1][1] <= o[1] and a[1] != o for a in arch):
            continue
        arch = [a for a in arch if not (o[0] <= a[1][0] and o[1] <= a[1][1])] + [(x, o)]
    return snaps


def job(a):
    name, path, e, k, CHECK, INSERT, ALGO = a
    M2.CHECK, M2.INSERT, M2.ALGO = CHECK, INSERT, ALGO
    inst = F.load(path)
    t = time.time()
    if e.startswith("pls"):
        snaps = run_pls(inst, e, 1000 + k)
    else:
        snaps = (M2.run_moead if ALGO == "moead" else M2.run)(inst, e, 1000 + k)
    secs = time.time() - t
    return [[name, e, k, b, f"{secs:.1f}", "" if snaps[b][1] is None else snaps[b][1],
             ";".join(f"{a}:{c}" for a, c in snaps[b][0])] for b in CHECK]


def names_of(sel, Mt):
    if sel in ("brandimarte", "kacem", "fattahi", "hurink", "dauzere", "barnes", "behnke"):
        return [n for n, d in Mt.items() if d["path"].startswith(sel)]
    if sel == "main":
        return [n for n, d in Mt.items() if not d["path"].startswith("behnke")]
    if sel == "big":
        return [n for n, d in Mt.items() if d["path"].split("/")[0] in ("brandimarte", "dauzere", "barnes", "kacem", "fattahi")]
    if sel == "pilot":                          # T13 调参用：Hurink rdata la16～la30（不在 big 集里）
        return [f"r-la{i:02d}" for i in range(16, 31)]
    return sel.split(",")


if __name__ == "__main__":
    mp.freeze_support()
    encs, reps, outp, sel = sys.argv[1].split(","), int(sys.argv[2]), sys.argv[4], sys.argv[5]
    maxe = int(sys.argv[6]) if len(sys.argv) > 6 else 5000
    CHECK = [b for b in M2.ALL_CHECK if b <= maxe]
    ALGO = "moead" if "moead" in sys.argv[7:] else "nsga2"
    procs = int(sys.argv[3]) if sys.argv[3].isdigit() else max(1, min(8, mp.cpu_count() // 2))
    Mt = F.meta()
    names = names_of(sel, Mt)
    done = set()
    if os.path.exists(outp):
        for r in csv.reader(open(outp)):
            if r and r[0] != "instance":
                done.add((r[0], r[1], int(r[2])))
    jobs = [(n, Mt[n]["path"], e, k, CHECK, True, ALGO) for k in range(reps) for n in names for e in encs if (n, e, k) not in done]
    print(f"{len(jobs)} 次运行待做（已有 {len(done)}），{procs} 个进程，算法 {ALGO}，检查点 {CHECK}", flush=True)
    new = not os.path.exists(outp)
    with open(outp, "a", newline="") as f, mp.Pool(procs) as p:
        w = csv.writer(f)
        if new:
            w.writerow(["instance", "encoding", "run", "evals", "seconds", "d_best", "front(makespan:workload;...)"])
        for n, rows in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            w.writerows(rows); f.flush()
            if n % 10 == 0 or n == len(jobs):
                print(f"{n}/{len(jobs)}", rows[0][0], rows[0][1], rows[0][4] + "s", flush=True)
