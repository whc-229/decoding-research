"""dec8：C++ paiban_dec8 与 Python ddec.decode8 逐解核对（固定 d 与自适应 d）。用法: python check8.py C++目录 [每实例条数]"""
import sys, os, json, subprocess, tempfile, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L, ddec
M = L.M
H = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
rng = np.random.default_rng(21); bad = tot = fx = 0
insts = [("requests", s) for s in ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]] + \
        [("requests_family", f[:-5]) for f in sorted(os.listdir(f"{H}/requests_family"))]
for d in [None, 0.05, 0.3]:
    for sub, s in insts:
        req = f"{H}/{sub}/{s}.json"; sc = M.load_scenario(req); nv = L.nvar(sc, "dec5")
        G = [[float(np.float32(v)) for v in rng.uniform(0, .99, nv)] for _ in range(n)]
        with tempfile.TemporaryDirectory() as wd:
            json.dump(G, open(f"{wd}/g.json", "w"))
            cmd = [f"{H}/paiban_dec8", "--request", req, "--workdir", wd, "--templates", f"{H}/templates", "--eval-genes", f"{wd}/g.json", "--out", f"{wd}/o.json", "--quiet"]
            if d is not None:
                cmd += ["--dev-density", str(d)]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            C = json.load(open(f"{wd}/o.json"))
        b = 0
        for g, c in zip(G, C):
            r = ddec.decode8(sc, g, d); tot += 1; fx += r.fixes
            ok = (r.feasible == c["feasible"]) and (not r.feasible or (abs(r.obj[0] - c["obj"][0]) < 1e-3 and abs(r.obj[1] - c["obj"][1]) < 1e-3 * max(1, abs(c["obj"][1]))
                                                                  and r.sim.seq == c["robots"][:len(r.sim.seq)]))
            if not ok:
                b += 1
                if b <= 2: print("  不一致", d, s, r.obj, r.fixes, c["obj"], c.get("bt_fixes"))
        bad += b
    print(f"d={d}: 累计 {tot} 条，不一致 {bad}", flush=True)
print(f"共 {tot} 条，回溯修复 {fx} 次，不一致 {bad}")
