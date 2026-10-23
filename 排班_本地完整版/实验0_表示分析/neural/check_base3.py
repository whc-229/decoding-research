"""T13 排班自检：每个实例上 K(κ=1.0) = nmax，稠密基因映射后第 k 个槽恰好落在第 k 班；全零偏离基因 = 规则解（与 X1.0 全关一致）；
随机稠密基因与"手工构造的固定位置 X1.0 基因"逐解相同。"""
import numpy as np
import common as C, arms as A, base3 as B, ruledec_ext as X
tr, te = C.I.split()
spec = "nn:out/es/il_h16/best.npz"
dec_d = B.decoder("D0.4:" + spec); dec_x = A.decoder("X1.0:" + spec)
rng = np.random.default_rng(0); bad = n = 0
for inst in tr:
    sc = C.I.load(inst); K, nmax = C.R.n_slots(sc, 1.0)
    bad += K != nmax
    g = rng.uniform(0, 0.99, B.nvar("D0.4:" + spec, sc)); x = B.to_ext(sc, g)
    dm = X.devmap(sc, np.asarray(x, np.float32).astype(np.float64), 1.0, 0, 0.0)
    bad += sorted(dm) != list(range(K)); n += 2
    for _ in range(3):
        g = rng.uniform(0, 0.99, B.nvar("D0.4:" + spec, sc))
        g0 = g.copy(); g0[:K] = 0
        xo = rng.uniform(0, 0.99, X.nvar(sc, 1.0)); xo[1:2 * K:2] = 0; xo[2 * K:] = g[K:]
        a, b = dec_d(sc, g0), dec_x(sc, xo)
        bad += a.obj != b.obj; n += 1
print(f"{n} 项核对，不一致 {bad}")
