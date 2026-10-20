"""核对 Python 等价模型与 C++ 原目标函数：同一批基因向量，比较目标值与每班派出的机器人编号
用法: python exact/validate_mirror.py [每场景条数] [只核对的程序名,逗号分隔]
  paiban_dec1 阈值解码 / paiban_dec2 排序解码 / paiban_dec3 排序+容量预判（裕度基因）/ paiban_dec3f 排序+容量预判（ρ=1）
"""
import json, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCEN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]
DECS = [("paiban_dec1", False, None), ("paiban_dec2", True, None), ("paiban_dec3", True, 1.0), ("paiban_dec3f", True, 0.0), ("paiban_dec4", "phase", 0.0)]
n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
reqdir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "requests")
scens = [f[:-5] for f in sorted(os.listdir(reqdir)) if f.endswith(".json")] if len(sys.argv) > 3 else SCEN
rng = np.random.default_rng(1)
tot_bad = 0
for s in scens:
    req = os.path.join(reqdir, s + ".json")
    sc = M.load_scenario(req)
    for dec, rank, cap in DECS:
        if only and dec not in only:
            continue
        nv = M.nvar_auto(sc, cap is not None)
        G = []
        for k in range(n):
            x = rng.uniform(0, 0.99, nv)
            mode = k % 3
            if mode == 1:      # 偏向复用，产生较多可行解
                m = rng.random(nv // 2) < 0.9
                x[:nv // 2][m] = rng.uniform(0, 0.85, m.sum())
            elif mode == 2:    # 几乎全部复用
                x[:nv // 2] = rng.uniform(0, 0.85, nv // 2)
                x[rng.integers(0, nv // 2, 3)] = rng.uniform(0.85, 0.99, 3)
            G.append([float(np.float32(v)) for v in x])
        with tempfile.TemporaryDirectory() as wd:
            gp, op = os.path.join(wd, "g.json"), os.path.join(wd, "o.json")
            json.dump(G, open(gp, "w"))
            subprocess.run([os.path.join(HERE, dec), "--request", req, "--workdir", wd, "--templates",
                            os.path.join(HERE, "templates"), "--eval-genes", gp, "--out", op, "--quiet"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            C = json.load(open(op))
        bad = feas = ovr = 0
        for g, c in zip(G, C):
            o, sim = M.evaluate_genes(sc, g, rank, cap)
            pf = o is not None
            same = pf == c["feasible"]
            if same and pf:
                feas += 1
                same = abs(o[0] - c["obj"][0]) < 1e-3 and abs(o[1] - c["obj"][1]) < 1e-3 * max(1, abs(c["obj"][1]))
            if same:
                same = sim.seq == c["robots"][:len(sim.seq)]
            if same and cap is not None:
                same = getattr(sim, "cap_override", 0) == c.get("cap_override", 0)
                ovr += c.get("cap_override", 0)
            if not same:
                bad += 1
                if bad <= 2:
                    print("  不一致:", s, dec, "py", o, sim.seq[:12], getattr(sim, "cap_override", None),
                          "| cpp", c["obj"], c["feasible"], c["robots"][:12], c.get("cap_override"))
        tot_bad += bad
        extra = f"，容量预判改写 {ovr} 次" if cap is not None else ""
        print(f"{s:16s} {dec:13s}: {n} 条，可行 {feas}，不一致 {bad}{extra}", flush=True)
print("全部一致" if tot_bad == 0 else f"共 {tot_bad} 条不一致")
