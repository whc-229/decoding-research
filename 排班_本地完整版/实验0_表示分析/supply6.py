"""初始供给对照：dec5 / dec6 / dec6b 各 N 个均匀随机基因的资源数分布（不做局部性）。用法: python supply6.py 实例 N"""
import json, os, sys, importlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L, sde
M = L.M
inst, N = sys.argv[1], int(sys.argv[2])
path = f"{L.SRC}/requests/{inst}.json"
if not os.path.exists(path):
    path = f"{L.SRC}/requests_family/{inst}.json"
sc = M.load_scenario(path)
fb = json.load(open(f"{L.SRC}/exact/family_bounds.json", encoding="utf-8"))
LB = fb[inst]["total_lb"] if inst in fb else 9
out = {}
for d in ["dec5", "dec6", "dec6b"]:
    sde.NEW_CAP, sde.REUSE_SHARE = (False, 0.7) if d == "dec6b" else (True, 0.85)
    rng = np.random.default_rng(99); nv = L.nvar(sc, "dec5")
    R, B = [], []
    for _ in range(N):
        x = rng.uniform(0, .99, nv)
        r = L.decode(sc, x, "dec5") if d == "dec5" else sde.decode6(sc, x)
        if r.feasible:
            R.append(r.obj[0]); B.append(r.obj[1])
    R, B = np.array(R), np.array(B)
    mn = R.min()
    out[d] = dict(res_mean=float(R.mean()), res_min=float(mn), p_lb=float(np.mean(R == LB)), p_lb1=float(np.mean(R <= LB + 1)),
                  p_min=float(np.mean(R == mn)), bal_at_min_best=float(B[R == mn].min()),
                  levels=sorted(set(int(v) for v in R)))
print(json.dumps({inst: out}, ensure_ascii=False))
