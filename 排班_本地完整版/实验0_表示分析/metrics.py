"""实验 0：六种解码的表示性质（冗余、好解的表示比例、局部性/级联、改写率、最优解可达性）。
用法: python metrics.py 实例名 [N 采样数] [输出目录]
实例名为 requests/ 或 requests_family/ 下的文件名（不带 .json）。
"""
import json, os, sys, time, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L
M = L.M

inst = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
outdir = sys.argv[3] if len(sys.argv) > 3 else "out"
os.makedirs(outdir, exist_ok=True)
path = f"{L.SRC}/requests/{inst}.json"
if not os.path.exists(path):
    path = f"{L.SRC}/requests_family/{inst}.json"
sc = M.load_scenario(path)
LB = 9
fb = json.load(open(f"{L.SRC}/exact/family_bounds.json", encoding="utf-8"))
if inst in fb:
    LB = fb[inst]["total_lb"]
dpf = f"{L.SRC}/exact/dp_{inst}.json"
OPT = json.load(open(dpf, encoding="utf-8")) if os.path.exists(dpf) else None


def ph_hash(r):
    return hashlib.md5(repr(r.pheno).encode()).hexdigest()


def seq_dist(a, b, j):
    """表型距离：对齐位置上机器人不同的班次数 + 长度差；级联：变异位置 j 之后（含）不同的比例"""
    m = min(len(a), len(b))
    diff = [a[k] != b[k] for k in range(m)]
    d = sum(diff) + abs(len(a) - len(b))
    tail = max(len(a), len(b)) - j
    casc = (sum(diff[j:]) + abs(len(a) - len(b))) / max(1, tail)
    return d, casc


res = dict(instance=inst, LB=LB, N=N, opt=(OPT["best"] if OPT else None), dec={})
for dec in L.DECODERS:
    t0 = time.time()
    rng = np.random.default_rng(12345)
    nv = L.nvar(sc, dec); h = nv // 2
    S = []
    for k in range(N):
        x = rng.uniform(0, 0.99, nv)            # 与 MOEA 初始化相同的分布（上界 0.99）
        r = L.decode(sc, x, dec)
        S.append((x, r))
    feas = [r for _, r in S if r.feasible]
    R = np.array([r.obj[0] for r in feas]) if feas else np.array([])
    B = np.array([r.obj[1] for r in feas]) if feas else np.array([])
    hashes = [ph_hash(r) for r in feas]
    uniq = len(set(hashes))
    cnt = {}
    for hh in hashes:
        cnt[hh] = cnt.get(hh, 0) + 1
    top = max(cnt.values()) if cnt else 0
    d = dict(
        nvar=nv,
        feasible=len(feas) / N,
        gene_used=float(np.mean([r.used for _, r in S]) / h),          # 被读到的机器人基因比例
        distinct=uniq / max(1, len(feas)),                              # 可行样本中互不相同的排班比例
        top_share=top / max(1, len(feas)),                              # 出现最多的排班占比
        res_mean=float(R.mean()) if len(R) else None,
        res_min=float(R.min()) if len(R) else None,
        p_lb=float(np.mean(R == LB)) if len(R) else 0.0,                # 随机基因解码到资源数下界的概率（≈ 初始供给）
        p_lb1=float(np.mean(R <= LB + 1)) if len(R) else 0.0,
        bal_lb_min=float(B[R == LB].min()) if np.any(R == LB) else None,
        override_rate=float(np.sum([r.override for _, r in S]) / max(1, np.sum([r.used for _, r in S]))),
        fixes_mean=float(np.mean([r.fixes for _, r in S])),
    )
    if OPT and np.any(R == LB):
        for f in (1.25, 1.5, 2.0):
            d[f"p_opt{f}"] = float(np.mean((R == LB) & (B <= f * OPT["best"] + 1e-6)))
    # 局部性：随机可行基底 100 个 + 精英基底 30 个，各做 5 次"单个机器人基因重新抽样"
    order = sorted(range(len(S)), key=lambda k: (S[k][1].obj or (1e9, 1e9)))
    feas_idx = [k for k in range(len(S)) if S[k][1].feasible]
    bases = {"random": [feas_idx[k] for k in rng.permutation(len(feas_idx))[:100]], "elite": order[:30]}
    for tag, idx in bases.items():
        neu, dist, casc, dres, dbal, worse = [], [], [], [], [], []
        for k in idx:
            x0, r0 = S[k]
            if not r0.feasible:
                continue
            a = r0.sim.seq
            for _ in range(5):
                j = int(rng.integers(0, max(1, min(r0.used, h))))
                x1 = x0.copy(); x1[j] = rng.uniform(0, 0.99)
                r1 = L.decode(sc, x1, dec)
                same = r1.feasible and r1.pheno == r0.pheno
                neu.append(same)
                if not same:
                    dd, cc = seq_dist(a, r1.sim.seq, j)
                    dist.append(dd / max(1, len(a))); casc.append(cc)
                    if r1.feasible:
                        dres.append(r1.obj[0] - r0.obj[0])
                        if r1.obj[0] == r0.obj[0]:
                            dbal.append(abs(r1.obj[1] - r0.obj[1]))
                    worse.append((not r1.feasible) or r1.obj[0] > r0.obj[0])
        d[f"loc_{tag}"] = dict(
            n=len(neu), neutral=float(np.mean(neu)) if neu else None,
            dist=float(np.mean(dist)) if dist else None,          # 非中性变异的表型距离（占班次数比例）
            cascade=float(np.mean(casc)) if casc else None,       # 变异位置之后改变的班次比例
            res_change=float(np.mean(np.array(dres) != 0)) if dres else None,
            res_worse=float(np.mean(worse)) if worse else None,   # 非中性变异中资源数变多或不可行的比例
            dbal_same_res=float(np.mean(dbal)) if dbal else None)
    if OPT:
        r0 = L.decode(sc, OPT["genes"], "dec1")
        seq, tools = L.phenotype(r0.sim)
        x, fail = L.reach_genes(sc, seq, tools, dec)
        d["opt_reachable"] = x is not None
        d["opt_fail_shift"] = fail
        if x is not None:
            r = L.decode(sc, x, dec)
            d["opt_check"] = r.obj
    d["secs"] = time.time() - t0
    res["dec"][dec] = d
    print(inst, dec, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items() if not k.startswith("loc")},
          d["loc_random"], d["loc_elite"], flush=True)
json.dump(res, open(os.path.join(outdir, f"{inst}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
