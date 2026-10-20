import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L
M = L.M
rng = np.random.default_rng(1)
for s in ["原请求_paiban", "B_三类型720h"]:
    sc = M.load_scenario(f"{L.SRC}/requests/{s}.json")
    for dec in ["dec3f", "dec3fr", "dec5", "dec5r"]:
        bad = ch = fx = n = 0
        for k in range(25):
            x = rng.uniform(0, .99, L.nvar(sc, dec))
            if k % 2: x[:len(x)//2] = np.where(rng.random(len(x)//2) < .1, rng.uniform(0, .99, len(x)//2), 0.0)
            r = L.decode(sc, x, dec)
            if not r.feasible: continue
            x2, c = L.write_back(sc, x, r)
            r2 = L.decode(sc, x2, dec)
            n += 1; ch += c; fx += r2.fixes + r2.override
            if r2.pheno != r.pheno: bad += 1
        print(s, dec, "n", n, "mismatch", bad, "avg changed genes", ch / max(1, n), "residual repairs/overrides", fx)
