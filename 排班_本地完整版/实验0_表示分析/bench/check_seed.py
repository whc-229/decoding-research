"""核对 seed_fjsp.rule_genome：rk 解码出的解与规则解（sp 编码全不偏离）完全相同；GLR 基因解码出的机器分配与预期一致。全部实例。"""
import sys, numpy as np
import fjsp2 as F, seed_fjsp as SD
M = F.meta(); bad = 0; n = 0
for name, d in M.items():
    inst = F.load(d["path"])
    a = F.decode(inst, "rk", SD.rule_genome(inst))
    b = F.decode(inst, "sp4", np.zeros(8))
    n += 1
    if a != b:
        bad += 1; print("不一致", name, a, b)
    rng = np.random.default_rng(0)
    for mode in ("GS", "LS", "RS"):
        g = SD.glr_genome(inst, rng, mode)
        N = inst["nops"]; assert g.shape == (2 * N,) and g.max() < 1 and g.min() >= 0
print(f"{n} 个实例，规则解不一致 {bad}")
