"""核对：fjsp2 在不插空时与 fjsp 逐解相同；并比较插空前后的纯规则与随机样本、耗时。"""
import time, numpy as np, fjsp as F1, fjsp2 as F2
Mt = F1.meta(); bad = tot = 0
for nm in ["mk01", "mk04", "mk08", "mk10", "la01", "la21", "k1", "mfjs05"]:
    if nm not in Mt: continue
    I = F1.load(Mt[nm]["path"]); rng = np.random.default_rng(0)
    for enc in ["pd", f"sp{F1.k_slots(I,0.25)}", "rk"]:
        for _ in range(20):
            g = rng.random(F1.nvar(I, enc)); tot += 1
            bad += F1.decode(I, enc, g) != F2.decode(I, enc, g, insert=False)
    t = time.time(); [F2.decode(I, f"sp{F1.k_slots(I,0.25)}", rng.random(2*F1.k_slots(I,0.25)), insert=False) for _ in range(20)]; ta = (time.time()-t)/20
    t = time.time(); [F2.decode(I, f"sp{F1.k_slots(I,0.25)}", rng.random(2*F1.k_slots(I,0.25)), insert=True) for _ in range(20)]; ti = (time.time()-t)/20
    t = time.time(); [F1.decode(I, f"sp{F1.k_slots(I,0.25)}", rng.random(2*F1.k_slots(I,0.25))) for _ in range(20)]; t1 = (time.time()-t)/20
    r = F2.refs(nm, Mt)
    print(nm, I["nops"], "BKS", r["bks"], "规则 不插空", F2.decode(I, "sp4", np.zeros(8), insert=False)[0], "插空", F2.decode(I, "sp4", np.zeros(8))[0],
          f"耗时 v1 {t1*1000:.1f}ms v2不插空 {ta*1000:.1f}ms v2插空 {ti*1000:.1f}ms")
print(f"不插空核对 {tot} 条，不一致 {bad}")
