"""paiban_dec9（dec6b + 可调偏离槽数）与 Python sde.decode6 逐解核对。用法: python check9.py C++目录 [每实例条数]"""
import sys, os, json, subprocess, tempfile, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L, sde
M = L.M
H = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
sde.NEW_CAP, sde.REUSE_SHARE = False, 0.7
rng = np.random.default_rng(31); bad = tot = 0
insts = [("requests", s) for s in ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]] + \
        [("requests_family", f[:-5]) for f in sorted(os.listdir(f"{H}/requests_family"))]
for frac, adapt in [(0.1, False), (0.5, False), (0.5, True)]:
    sde.K_FRAC, sde.SLOT_ADAPT = frac, adapt
    for sub, s in insts:
        req = f"{H}/{sub}/{s}.json"; sc = M.load_scenario(req); nv = L.nvar(sc, "dec5")
        G = [[float(np.float32(v)) for v in rng.uniform(0, .99, nv)] for _ in range(n)]
        with tempfile.TemporaryDirectory() as wd:
            json.dump(G, open(f"{wd}/g.json", "w"))
            cmd = [f"{H}/paiban_dec9", "--request", req, "--workdir", wd, "--templates", f"{H}/templates", "--eval-genes", f"{wd}/g.json",
                   "--out", f"{wd}/o.json", "--quiet", "--slot-frac", str(frac)] + (["--slot-adapt"] if adapt else [])
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            C = json.load(open(f"{wd}/o.json"))
        for g, c in zip(G, C):
            r = sde.decode6(sc, g); tot += 1
            ok = (r.feasible == c["feasible"]) and (not r.feasible or (abs(r.obj[0] - c["obj"][0]) < 1e-3 and abs(r.obj[1] - c["obj"][1]) < 1e-3 * max(1, abs(c["obj"][1]))
                                                                  and r.sim.seq == c["robots"][:len(r.sim.seq)]))
            if not ok:
                bad += 1
                if bad <= 3: print("  不一致", frac, adapt, s, r.obj, c["obj"])
    print(f"槽数比例 {frac} 自适应 {adapt}: 累计 {tot} 条，不一致 {bad}", flush=True)
