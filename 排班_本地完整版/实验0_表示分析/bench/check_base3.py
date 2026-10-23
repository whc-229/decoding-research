"""T13 自检（必须 0 不一致）：
  1. db{ρ} 与"每步一个固定位置槽"的 sp{N}q{ρ} 逐解相同；
  2. ps{ε} 在 ε = 0 时等于规则解；hs 全选 ECT 时等于规则解；
  3. db、hs、ps 的 picks 在规则解上全为 0。"""
import numpy as np
import fjsp2 as F, fjsp_base3 as B
Mt = F.meta()
names = ["mk01", "mk05", "k1", "r-la16", "e-la01", "v-la20", "sfjs05", "mfjs03", "seti5c12" if "seti5c12" in Mt else "mk10"]
rng = np.random.default_rng(0); bad = 0; n = 0
for nm in names:
    inst = F.load(Mt[nm]["path"]); N = inst["nops"]
    rule = F.decode(inst, "sp4", np.zeros(8))
    for rho in (0.04, 0.2, 0.4):
        for _ in range(20):
            g = rng.uniform(0, 0.99, N)
            x = np.empty(2 * N); x[0::2] = (np.arange(N) + 0.5) / N; x[1::2] = g
            a = B.decode3(inst, f"db{rho}", g); b = F.decode(inst, f"sp{N}q{rho}", x)
            n += 1; bad += a != b
    pk = []
    if B.decode3(inst, "ps0.0", rng.uniform(0, 0.99, B.n_options(inst)), picks=pk) != rule or any(pk): bad += 1; print("ps0", nm)
    pk = []
    if B.decode3(inst, "hs", np.full(N, 0.05), picks=pk) != rule or any(pk): bad += 1; print("hs", nm)
    pk = []
    if B.decode3(inst, "db0.2", np.zeros(N), picks=pk) != rule or any(pk): bad += 1; print("db", nm)
    K = B.parse_spr(inst, "spr0.5")[0]
    pk = []
    if B.decode3(inst, "spr0.5", np.zeros(2 * K), picks=pk) != rule or any(pk): bad += 1; print("spr0", nm)
    # spr 的偏离位置与 sp 相同：同一基因下两者偏离的步集合相同（规则组合偏离可能与 ECT 相同，所以 spr 的偏离步 ⊆ sp 的偏离步）
    for _ in range(10):
        g = rng.uniform(0, 0.99, 2 * K)
        p1, p2 = [], []
        F.decode(inst, f"sp{K}", g, picks=p1); B.decode3(inst, "spr0.5", g, picks=p2)
        a_on = {min(int(g[2 * k] * N), N - 1) for k in range(K) if g[2 * k + 1] >= 0.6}
        bad += p1[0] != 0 and 0 not in a_on      # 第一步：没有槽时都应为规则首选
        bad += any(p2[t] != 0 for t in range(N) if t not in a_on and all(p2[s] == 0 for s in range(t)))
        n += 2
    n += 4
print(f"{n} 项核对，不一致 {bad}")
