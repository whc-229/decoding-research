import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L
M = L.M
sys.path.insert(0, os.path.join(L.SRC, "dls")); import backtrack_test as BT
rng = np.random.default_rng(0); bad = 0
for s in ["原请求_paiban", "B_三类型720h"]:
    sc = M.load_scenario(f"{L.SRC}/requests/{s}.json")
    for k in range(40):
        for dec, rank, cap in [("dec1",False,None),("dec2",True,None),("dec3f",True,0.0),("dec4","phase",0.0)]:
            x = rng.uniform(0,.99,L.nvar(sc,dec))
            if k%2: x[:len(x)//2] = rng.uniform(0,.85,len(x)//2)
            o, sim = M.evaluate_genes(sc, x, rank, cap); r = L.decode(sc, x, dec)
            if (o is None) != (r.obj is None) or (o is not None and (abs(o[0]-r.obj[0])>1e-6 or abs(o[1]-r.obj[1])>1e-4)) or sim.seq != r.sim.seq: bad += 1
        if k < 15:
            x = rng.uniform(0,.99,L.nvar(sc,"dec5"))
            if k%2: x[:len(x)//2] = rng.uniform(0,.85,len(x)//2)
            o, f = BT.decode_bt(sc, x, W=12); r = L.decode(sc, x, "dec5")
            if (o is None) != (r.obj is None) or (o is not None and abs(o[1]-r.obj[1])>1e-6) or f != r.fixes: bad += 1
print("mismatches", bad)
for s in ["原请求_paiban", "B_三类型720h"]:
    sc = M.load_scenario(f"{L.SRC}/requests/{s}.json"); d = json.load(open(f"{L.SRC}/exact/dp_{s}.json"))
    r0 = L.decode(sc, d["genes"], "dec1"); seq, tools = L.phenotype(r0.sim)
    for dec in L.DECODERS:
        x, fail = L.reach_genes(sc, seq, tools, dec)
        r = L.decode(sc, x, dec) if x is not None else None
        print(s, dec, "unreachable at shift" if x is None else "ok", fail, r.obj if r else None)
