"""核对：默认规则下 ruledec.decode_rule 与 sde.decode6（= C++ paiban_dec9）逐解相同。
用法: python check_ruledec.py [每实例样本数=20]"""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import ruledec as R  # noqa: E402
import sde  # noqa: E402
import instances as I  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
rule_from_src = R.compile_rule(R.DEFAULT_RULE_SRC)
bad = tot = 0
t0 = time.time()
for inst in ["原请求_paiban", "D_三类型资源紧", "E13_1080h", "H15_1080h", "M20_1080h", "M17_480h", "H04_480h"]:
    sc = I.load(inst)
    nv = L = R.L.nvar(sc, "dec5")
    rng = np.random.default_rng(7)
    for kf in (0.25, 0.5):
        sde.K_FRAC = kf
        for k in range(n):
            x = rng.random(nv)
            if k % 4 == 0:
                x[1:2 * 40:2] = rng.random(40) * 0.6     # 少量偏离
            a = sde.decode6(sc, x)
            b = R.decode_rule(sc, x, R.default_rule, kf)
            c = R.decode_rule(sc, x, rule_from_src, kf)
            tot += 1
            if not (a.obj == b.obj == c.obj and (not a.feasible or a.pheno == b.pheno == c.pheno)):
                bad += 1
                print("不一致", inst, kf, k, a.obj, b.obj, c.obj)
print(f"核对 {tot} 条，不一致 {bad} 条，用时 {time.time() - t0:.0f}s")
