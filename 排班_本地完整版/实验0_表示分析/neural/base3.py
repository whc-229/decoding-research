"""T13（排班部分）：最接近的已有方法作为对照（2026-10-23）。不修改已有文件，只在 ruledec_ext / moea_any 外面加两种臂。

  D{q}:<规则写法>        稠密有偏逐班编码（HBSS / LDS 思想的逐班版本）：每班一个偏离基因 a_i，a_i ≥ 1 − q 时在该班偏离，
                        偏离的取值 u = (a_i − 1 + q)/q，语义与 RDD 完全相同（改派 / 新开、容量判断、回溯修复都相同）。
                        实现：映射成 κ = 1.0 的扩展布局，第 k 个槽的位置基因固定指向第 k 班（槽数 K = 班次上界 nmax），
                        所以与 X1.0q{q} 的唯一区别是"偏离位置不可进化、每班恰有一个槽"。基因长度 = K + 1 + (nmax + 1)。
                        规则写法同 arms.py 的 K/X 开头写法中冒号后的部分，例如 D0.4:nn:out/es/il_h16/best.npz。
  P{j}:<X 臂写法>        偏离空间上的 Pareto 局部搜索（LNS / 迭代贪心思想）：编码与该 X 臂相同（例如 P2:X1.0:nn:...），
                        从规则解（全部槽关闭，类型基因与工具基因随机）出发；每步从存档里随机取一个可行解，重抽 j 个随机槽的两个基因，
                        并以 1/2 的概率再重抽一个随机的非槽基因（类型或工具基因）；可行且不被存档支配就进存档（目标值相同的替换）。
                        存档为空（起点不可行且还没有可行解）时，从均匀随机基因重新开始。
用法同 moea_any.py：python base3.py 臂[,臂...] 次数 进程数 输出.csv [train|test|实例,...] [--checks 465] [--seed-base 1000]
输出格式与 moea_any.py 相同，可与 val_Kext.csv 等合并分析（同一台机器上跑）。"""
import argparse, csv, multiprocessing as mp, os, time
import numpy as np
import common as C
import arms as A
import ga as G
import moea_any as MA
import ruledec_ext as X

R = C.R


def is_dense(spec):
    return spec[0] == "D" and spec[1].isdigit()


def is_pls(spec):
    return spec[0] == "P" and spec[1].isdigit()


def dense_q(spec):
    return float(spec.split(":", 1)[0][1:])


def nvar(spec, sc):
    if is_dense(spec):
        K, nmax = R.n_slots(sc, 1.0)
        return K + 1 + nmax + 1
    if is_pls(spec):
        return A.nvar(spec.split(":", 1)[1], sc)
    return A.nvar(spec, sc)


def to_ext(sc, g):
    """稠密基因 [K 个偏离基因][类型][工具] → κ = 1.0 扩展布局 [p_0, a_0, …][类型][工具]，p_k 固定指向第 k 班"""
    K, nmax = R.n_slots(sc, 1.0)
    x = np.empty(2 * K + 1 + nmax + 1)
    x[0:2 * K:2] = (np.arange(K) + 0.5) / max(1, nmax)
    x[1:2 * K:2] = g[:K]
    x[2 * K:] = g[K:]
    return x


def decoder(spec):
    if is_dense(spec):
        q = dense_q(spec)
        rule = A.rule_of("X1.0:" + spec.split(":", 1)[1])
        on = round(1.0 - q, 10)
        return lambda sc, g: X.decode_rule(sc, to_ext(sc, g), rule, 1.0, dev_on=on)
    if is_pls(spec):
        return A.decoder(spec.split(":", 1)[1])
    return A.decoder(spec)


def run_pls(sc, dec, seed, checks, nv, K, j):
    EVALS = checks[-1]
    rng = np.random.default_rng(seed)
    allf, ev, snaps = [], [0], {}

    def evaluate(x):
        r = dec(sc, x); ev[0] += 1
        if r.feasible:
            allf.append(r.obj)
        if ev[0] in checks:
            snaps[ev[0]] = MA.front_of(allf)
        return r.obj if r.feasible else None

    x0 = rng.uniform(0, G.UB, nv); x0[1:2 * K:2] = 0.0        # 全部槽关闭 = 规则解
    o0 = evaluate(x0)
    arch = [(x0, o0)] if o0 is not None else []
    while ev[0] < EVALS:
        if not arch:
            x = rng.uniform(0, G.UB, nv)
        else:
            x = arch[rng.integers(len(arch))][0].copy()
            for k in rng.choice(K, size=min(j, K), replace=False):
                x[2 * k], x[2 * k + 1] = rng.uniform(0, G.UB), rng.uniform(0, G.UB)
            if rng.random() < 0.5:
                x[2 * K + rng.integers(nv - 2 * K)] = rng.uniform(0, G.UB)
        o = evaluate(x)
        if o is None or any(a[1][0] <= o[0] and a[1][1] <= o[1] and a[1] != o for a in arch):
            continue
        arch = [a for a in arch if not (o[0] <= a[1][0] and o[1] <= a[1][1])] + [(x, o)]
    return snaps


def job(args):
    inst, name, spec, k, checks, seed_base = args
    sc = C.I.load(inst)
    t = time.time()
    nv = nvar(spec, sc)
    if is_pls(spec):
        j = int(spec.split(":", 1)[0][1:])
        inner = spec.split(":", 1)[1]
        K, _ = R.n_slots(sc, A.kq_of(inner)[0])
        snaps = run_pls(sc, decoder(spec), seed_base + k, checks, nv, K, j)
    else:
        snaps = MA.run_nsga2(sc, decoder(spec), seed_base + k, checks, nv=nv)
    secs = f"{time.time() - t:.1f}"
    return [[inst, name, k, secs, c, nv, ";".join(f"{int(a)}:{b:.3f}" for a, b in snaps[c])] for c in checks]


def main():
    mp.freeze_support()
    ap = argparse.ArgumentParser()
    ap.add_argument("arms"); ap.add_argument("reps", type=int); ap.add_argument("procs"); ap.add_argument("out")
    ap.add_argument("sel", nargs="?", default="train")
    ap.add_argument("--checks", default="465")
    ap.add_argument("--seed-base", type=int, default=1000)
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
    jobs = [(i, n, s, k, checks, a.seed_base) for k in range(a.reps) for i in insts for n, s in arms if (i, n, k) not in done]
    jobs.sort(key=lambda j: -C.L.nvar(C.I.load(j[0]), "dec5"))
    procs = C.nprocs(a.procs)
    print(f"T13 排班：{len(jobs)} 次运行待做（已有 {len(done)}），{procs} 个进程，检查点 {checks}", flush=True)
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
