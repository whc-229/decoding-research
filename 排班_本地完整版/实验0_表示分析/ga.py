"""写回/可达性小对照：NSGA-II（种群 30，共 465 次评价，SBX+多项式变异），比较
  dec3f / dec5（原样）、+wb（拉马克式写回）、dec5r（强制新开带，恢复最优解可达性）、dec5r+wb。
用法: python ga.py 场景 变体[,变体...] 次数 输出.csv
输出每次运行的非支配前沿（全部已评价可行解的非支配集），格式与已有 *_runs.csv 一致。
"""
import csv, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L
M = L.M

POP, EVALS, UB = 30, 465, 0.99
BIG = (30000.0, 30000.0)


def nd_sort(F):
    n = len(F); S = [[] for _ in range(n)]; cnt = [0] * n; fronts = [[]]
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if all(a <= b for a, b in zip(F[p], F[q])) and F[p] != F[q]:
                S[p].append(q)
            elif all(b <= a for a, b in zip(F[p], F[q])) and F[p] != F[q]:
                cnt[p] += 1
        if cnt[p] == 0:
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                cnt[q] -= 1
                if cnt[q] == 0:
                    nxt.append(q)
        i += 1; fronts.append(nxt)
    return fronts[:-1]


def crowd(F, idx):
    d = {i: 0.0 for i in idx}
    for m in range(2):
        s = sorted(idx, key=lambda i: F[i][m])
        d[s[0]] = d[s[-1]] = float("inf")
        rg = F[s[-1]][m] - F[s[0]][m] or 1.0
        for k in range(1, len(s) - 1):
            d[s[k]] += (F[s[k + 1]][m] - F[s[k - 1]][m]) / rg
    return d


def sbx(a, b, rng, eta=20.0):
    c1, c2 = a.copy(), b.copy()
    if rng.random() > 0.9:
        return c1, c2
    for i in range(len(a)):
        if rng.random() <= 0.5 and abs(a[i] - b[i]) > 1e-14:
            u = rng.random()
            beta = (2 * u) ** (1 / (eta + 1)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / (eta + 1))
            c1[i] = 0.5 * ((1 + beta) * a[i] + (1 - beta) * b[i])
            c2[i] = 0.5 * ((1 - beta) * a[i] + (1 + beta) * b[i])
    return np.clip(c1, 0, UB), np.clip(c2, 0, UB)


def pm(x, rng, eta=20.0):
    n = len(x); y = x.copy()
    for i in range(n):
        if rng.random() < 1.0 / n:
            u = rng.random()
            d = (2 * u) ** (1 / (eta + 1)) - 1 if u < 0.5 else 1 - (2 * (1 - u)) ** (1 / (eta + 1))
            y[i] = y[i] + d * UB
    return np.clip(y, 0, UB)


def run(sc, variant, seed):
    dec, wb = (variant[:-3], True) if variant.endswith("+wb") else (variant, False)
    rng = np.random.default_rng(seed)
    nv = L.nvar(sc, dec)
    archive = []
    ev = [0]

    def evaluate(x):
        r = L.decode(sc, x, dec); ev[0] += 1
        if r.feasible:
            archive.append(r.obj)
            if wb:
                x2, _ = L.write_back(sc, x, r)
                if x2 is not None:
                    r2 = L.decode(sc, x2, dec)
                    if r2.feasible and r2.pheno == r.pheno:     # 写回后解码结果必须相同，否则保留原基因
                        x = x2
            return x, r.obj
        return x, BIG

    P = [evaluate(rng.uniform(0, UB, nv)) for _ in range(POP)]
    while ev[0] < EVALS:
        kids = []
        while len(kids) < POP and ev[0] + len(kids) < EVALS:
            a, b = P[rng.integers(len(P))][0], P[rng.integers(len(P))][0]
            c1, c2 = sbx(a, b, rng)
            kids += [pm(c1, rng), pm(c2, rng)]
        kids = kids[:min(POP, EVALS - ev[0])]
        Q = [evaluate(k) for k in kids]
        U = P + Q
        F = [u[1] for u in U]
        newP = []
        for fr in nd_sort(F):
            if len(newP) + len(fr) <= POP:
                newP += fr
            else:
                cd = crowd(F, fr)
                newP += sorted(fr, key=lambda i: -cd[i])[:POP - len(newP)]
                break
        P = [U[i] for i in newP]
    front = sorted(set(archive))
    nd, best = [], float("inf")
    for a, b in front:
        if b < best - 1e-12:
            nd.append((a, b)); best = b
    return nd


if __name__ == "__main__":
    scen, variants, runs, outp = sys.argv[1], sys.argv[2].split(","), int(sys.argv[3]), sys.argv[4]
    path = f"{L.SRC}/requests/{scen}.json"
    if not os.path.exists(path):
        path = f"{L.SRC}/requests_family/{scen}.json"
    sc = M.load_scenario(path)
    new = not os.path.exists(outp)
    with open(outp, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        for v in variants:
            for k in range(runs):
                t = time.time()
                fr = run(sc, v, 1000 + k)
                w.writerow([scen, v, k, f"{time.time() - t:.1f}", EVALS, L.nvar(sc, v.replace("+wb", "")),
                            ";".join(f"{int(a)}:{b:.3f}" for a, b in fr)])
                f.flush()
                print(scen, v, k, fr[:3], flush=True)
