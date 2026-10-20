"""核对回溯修复解码：C++ paiban_dec5 与 Python 原型 dls/backtrack_test.decode_bt 逐解比较（目标值、派班序列、修复次数）
用法: python dls/validate_bt.py 每场景条数 [实例目录]
"""
import json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "exact")); sys.path.insert(0, os.path.join(HERE, "dls"))
import mirror as M, backtrack_test as BT
n = int(sys.argv[1]); reqdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "requests")
scens = [f[:-5] for f in sorted(os.listdir(reqdir)) if f.endswith(".json")] if len(sys.argv) > 2 else \
    ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]
rng = np.random.default_rng(11); tot = 0
for s in scens:
    req = os.path.join(reqdir, s + ".json"); sc = M.load_scenario(req); nv = M.nvar_auto(sc, True); h = nv // 2
    G = []
    for k in range(n):
        x = rng.uniform(0, 0.99, nv)
        if k % 2: 
            m = rng.random(h) < [0.03, 0.1, 0.3][k % 3]; x[:h] = np.where(m, rng.uniform(0, 0.85, h), 0.0)
        G.append([float(np.float32(v)) for v in x])
    with tempfile.TemporaryDirectory() as wd:
        gp, op = os.path.join(wd, "g.json"), os.path.join(wd, "o.json"); json.dump(G, open(gp, "w"))
        subprocess.run([os.path.join(HERE, "paiban_dec5"), "--request", req, "--workdir", wd, "--templates",
                        os.path.join(HERE, "templates"), "--eval-genes", gp, "--out", op, "--quiet"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        C = json.load(open(op))
    bad = feas = fx = 0
    for g, c in zip(G, C):
        o, f = BT.decode_bt(sc, g, W=12)
        same = (o is not None) == c["feasible"]
        if same and o is not None:
            feas += 1
            same = abs(o[0] - c["obj"][0]) < 1e-3 and abs(o[1] - c["obj"][1]) < 1e-3 * max(1, abs(c["obj"][1])) \
                and BT.decode_bt.last_seq == c["robots"] and f == c["bt_fixes"]
        fx += c["bt_fixes"]
        if not same:
            bad += 1
            if bad <= 2: print("  不一致", s, o, f, "| cpp", c["obj"], c["feasible"], c["bt_fixes"])
    tot += bad
    print(f"{s:14s}: {n} 条，可行 {feas}，回溯修复共 {fx} 次，不一致 {bad}", flush=True)
print("全部一致" if tot == 0 else f"共 {tot} 条不一致")
