"""实验 1：dec6（规则 + 稀疏偏离）与 dec3f / dec5 的表示指标对比。
用法: python metrics6.py 实例名 [N] [输出目录]
局部性用两种扰动：
  single — 重抽样一个"会被读到的"机器人基因（dec6 为偏离槽或默认类型基因；其余为已用班次的基因）
  pm     — MOEA 实际用的多项式变异（每个变量以 0.15 概率变异，η=20，作用于整条基因）
级联 = 第一个不同的班次之后，派班不同的班次比例（对各解码统一按表型计算）。
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L
import sde
M = L.M

inst = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
outdir = sys.argv[3] if len(sys.argv) > 3 else "out6"
os.makedirs(outdir, exist_ok=True)
path = f"{L.SRC}/requests/{inst}.json"
if not os.path.exists(path):
    path = f"{L.SRC}/requests_family/{inst}.json"
sc = M.load_scenario(path)
fb = json.load(open(f"{L.SRC}/exact/family_bounds.json", encoding="utf-8"))
LB = fb[inst]["total_lb"] if inst in fb else 9
dpf = f"{L.SRC}/exact/dp_{inst}.json"
OPT = json.load(open(dpf, encoding="utf-8")) if os.path.exists(dpf) else None


def dec(x, d):
    return sde.decode6(sc, x) if d == "dec6" else L.decode(sc, x, d)


def pm(x, rng, p=0.15, eta=20.0, ub=0.99):
    y = x.copy()
    for i in range(len(y)):
        if rng.random() <= p:
            d1, d2 = y[i] / ub, (ub - y[i]) / ub
            u = rng.random(); mp = 1 / (eta + 1)
            if u <= 0.5:
                v = 2 * u + (1 - 2 * u) * (1 - d1) ** (eta + 1); dq = v ** mp - 1
            else:
                v = 2 * (1 - u) + 2 * (u - 0.5) * (1 - d2) ** (eta + 1); dq = 1 - v ** mp
            y[i] = min(max(y[i] + dq * ub, 0.0), ub)
    return y


def compare(r0, r1):
    a, b = r0.sim.seq, r1.sim.seq
    m = min(len(a), len(b))
    first = next((k for k in range(m) if a[k] != b[k]), m if len(a) != len(b) else None)
    if first is None:
        return 0.0, 0.0
    diff = sum(a[k] != b[k] for k in range(first, m)) + abs(len(a) - len(b))
    return (diff) / max(1, len(a)), diff / max(1, max(len(a), len(b)) - first)


res = dict(instance=inst, LB=LB, opt=(OPT["best"] if OPT else None), dec={})
for d in ["dec3f", "dec5", "dec6"]:
    t0 = time.time()
    rng = np.random.default_rng(777)
    nv = L.nvar(sc, "dec5"); h = nv // 2
    S = [(x, dec(x, d)) for x in (rng.uniform(0, 0.99, nv) for _ in range(N))]
    feas = [r for _, r in S if r.feasible]
    R = np.array([r.obj[0] for r in feas]); B = np.array([r.obj[1] for r in feas])
    out = dict(feasible=len(feas) / N, res_mean=float(R.mean()), p_lb=float(np.mean(R == LB)),
               p_lb1=float(np.mean(R <= LB + 1)), bal_lb_min=float(B[R == LB].min()) if np.any(R == LB) else None,
               bal_lb_med=float(np.median(B[R == LB])) if np.any(R == LB) else None)
    if OPT:
        for f in (1.25, 1.5, 2.0):
            out[f"p_opt{f}"] = float(np.mean((R == LB) & (B <= f * OPT["best"] + 1e-6)))
    order = sorted(range(N), key=lambda k: (S[k][1].obj or (1e9, 1e9)))
    fidx = [k for k in range(N) if S[k][1].feasible]
    bases = {"random": [fidx[k] for k in rng.permutation(len(fidx))[:100]], "elite": order[:30]}
    used6 = sde.used_genes(sc)
    for tag, idx in bases.items():
        for op in ("single", "pm"):
            neu, dist, casc, same_res, dbal, worse, better = [], [], [], [], [], [], []
            for k in idx:
                x0, r0 = S[k]
                for _ in range(5):
                    if op == "single":
                        j = int(rng.choice(used6)) if d == "dec6" else int(rng.integers(0, max(1, min(r0.used, h))))
                        x1 = x0.copy(); x1[j] = rng.uniform(0, 0.99)
                    else:
                        x1 = pm(x0, rng)
                    r1 = dec(x1, d)
                    same = r1.feasible and r1.pheno == r0.pheno
                    neu.append(same)
                    if same:
                        continue
                    ds, cc = compare(r0, r1); dist.append(ds); casc.append(cc)
                    if r1.feasible:
                        same_res.append(r1.obj[0] == r0.obj[0])
                        if r1.obj[0] == r0.obj[0]:
                            dbal.append(abs(r1.obj[1] - r0.obj[1]))
                        better.append(r1.obj[0] < r0.obj[0] or (r1.obj[0] == r0.obj[0] and r1.obj[1] < r0.obj[1] - 1e-9))
                    worse.append((not r1.feasible) or r1.obj[0] > r0.obj[0])
            mean = lambda v: float(np.mean(v)) if v else None
            out[f"{tag}_{op}"] = dict(n=len(neu), neutral=mean(neu), dist=mean(dist), cascade=mean(casc),
                                     same_res=mean(same_res), dbal=float(np.median(dbal)) if dbal else None,
                                     worse=mean(worse), better=mean(better))
    out["secs"] = time.time() - t0
    res["dec"][d] = out
    print(inst, d, json.dumps(out, ensure_ascii=False)[:600], flush=True)
json.dump(res, open(os.path.join(outdir, f"{inst}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
