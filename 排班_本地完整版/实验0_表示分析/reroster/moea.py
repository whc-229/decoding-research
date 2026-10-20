"""重排班的 MOEA 比较（Python NSGA-II，种群 30，465 次评价，算子同 ga.py）。
目标：(改动数, 均衡度)，约束：资源数 ≤ 资源预算 B。
B = 两个"修复后的原计划"（照原计划规则不偏离、dec5 编码的原计划）中资源数较少者 —— 一定可达，各臂相同。
超出预算的解按超出量加罚（约束支配）；记录的前沿只含满足预算的解（格式 资源数:改动数:均衡度）。
臂：
  dec5        逐班基因，随机初始种群（从头重排）
  dec5+seed   逐班基因，初始种群 20% = 修复后的原计划及其变异，其余随机（Shen & Yao 2015 的做法）
  plan        稀疏偏离 + 照原计划规则，随机初始种群（原排班放进表示，本文方法）
  plan+seed   同上，再放入不偏离的基因及其变异（20%）
场景：scenarios.json（gen_scenarios.py 生成）。
用法: python moea.py 臂[,臂...] 次数 进程数 输出.csv [场景编号,...|all]
"""
import csv, json, multiprocessing as mp, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C  # noqa: E402
import ga as G  # noqa: E402

BIG = (1e9, 1e9)
SEED_FRAC = 0.2


def budget(scn):
    K, _ = C.R.n_slots(scn.sc, 0.25)
    x0 = scn.plan.x.copy(); x0[1:2 * K:2] = 0.0
    a = scn.evaluate(C.decoder(scn, "plan")(x0))
    b = scn.evaluate(C.encode_dec5(scn)[1])
    f = [e[0] for e in (a, b) if e]
    return min(f) if f else None          # 两个修复方案都不可行（如 E03 资源已到上限）：该场景无解，跳过


def run(scn, arm, seed):
    rng = np.random.default_rng(seed)
    B = budget(scn)
    if B is None:
        return [], -1
    nv = scn.nv
    dname = arm.split("+")[0]
    dec = C.decoder(scn, dname)
    archive, ev = [], [0]

    def evaluate(x):
        e = scn.evaluate(dec(x)); ev[0] += 1
        if not e:
            return x, BIG
        if e[0] <= B + 1e-9:
            archive.append(e)
            return x, (e[1], e[2])
        pen = 1e6 * (e[0] - B)
        return x, (pen + e[1], pen + e[2])

    init = []
    if arm.endswith("+seed"):
        if dname == "dec5":
            x0, _ = C.encode_dec5(scn)
        else:
            K, _ = C.R.n_slots(scn.sc, 0.25)
            x0 = scn.plan.x.copy(); x0[1:2 * K:2] = 0.0
        x0 = np.clip(x0, 0, G.UB)
        init = [x0] + [G.pm(x0, rng) for _ in range(int(SEED_FRAC * G.POP) - 1)]
    init += [rng.uniform(0, G.UB, nv) for _ in range(G.POP - len(init))]
    P = [evaluate(x) for x in init]
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
    for b, c, a in sorted({(b, c, a) for a, b, c in archive}):
        if c < best - 1e-12:
            nd.append((a, b, c)); best = c
    return nd, B


SCN = None


def load_scenarios():
    return json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))


def job(args):
    sid, arm, k = args
    s = load_scenarios()[sid]
    scn = C.Scenario(s["inst"], np.load(os.path.join(HERE, "plans", s["inst"] + ".npy")), s["k"], s["ev"])
    t = time.time()
    nd, B = run(scn, arm, 1000 + k)
    return [sid, s["inst"], arm, k, f"{time.time() - t:.1f}", int(B), ";".join(f"{int(a)}:{int(b)}:{c:.3f}" for a, b, c in nd)]


if __name__ == "__main__":
    mp.freeze_support()
    arms, reps, outp = sys.argv[1].split(","), int(sys.argv[2]), sys.argv[4]
    procs = int(sys.argv[3]) if sys.argv[3].isdigit() else max(1, mp.cpu_count() - 1)     # 非数字（如 auto）= CPU 核数 − 1
    print(f"使用 {procs} 个进程", flush=True)
    S = load_scenarios()
    sel = sys.argv[5] if len(sys.argv) > 5 else "all"
    sids = list(S) if sel == "all" else sel.split(",")
    done = set()
    if os.path.exists(outp):
        for r in csv.reader(open(outp, encoding="utf-8")):
            if r and r[0] != "scenario":
                done.add((r[0], r[2], int(r[3])))
    jobs = [(s, a, k) for k in range(reps) for s in sids for a in arms if (s, a, k) not in done]
    print(f"{len(jobs)} 次运行待做（已有 {len(done)}）", flush=True)
    new = not os.path.exists(outp)
    with open(outp, "a", newline="", encoding="utf-8") as f, mp.Pool(procs) as p:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario", "inst", "variant", "run", "seconds", "budget", "front(资源数:改动数:均衡度;...)"])
        for n, row in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            w.writerow(row); f.flush()
            if n % 10 == 0 or n == len(jobs):
                print(f"{n}/{len(jobs)}", row[0], row[2], row[4] + "s", flush=True)
