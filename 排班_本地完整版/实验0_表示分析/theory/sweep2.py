"""有偏逐位编码（PS0.6，模拟 dec5）与稀疏偏离的比较：N=100, m=4，每格 10 个种子。"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as Mo
N, m = 100, 4
DS = [5, 10, 20, 30, 40, 60]
ARMS = ["PS0.6", "SP10", "SP25", "SP50"]
B = [465, 2000, 10000]
out = {}
for d in DS:
    for a in ARMS:
        vals = []
        for s in range(10):
            enc, K = ("PS0.6", 0) if a.startswith("PS") else ("SP", int(a[2:]))
            _, tr = Mo.run_encoding(enc, N, d, m, K, 1000 * d + s, evals=B[-1])
            vals.append([int(tr[b - 1]) for b in B])
        out[f"{d}|{a}"] = np.mean(vals, 0).tolist()
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep2.json"), "w"), indent=1)
for b_i, b in enumerate(B):
    print("预算", b, "  d:", "  ".join(f"{a:>6s}" for a in ARMS))
    for d in DS:
        print(f"   d={d:3d}  " + "  ".join(f"{out[f'{d}|{a}'][b_i]:6.1f}" for a in ARMS))
