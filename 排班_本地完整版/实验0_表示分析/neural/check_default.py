"""自检：默认等价权重的网络规则与默认规则逐解相同（训练实例 × 16 个基因，含 3 个不偏离基因）。"""
import sys, time
import common as C
import evalrule as E
import nnrule as N

tr, te = C.I.split()
insts = sys.argv[1].split(",") if len(sys.argv) > 1 else tr
rule = N.NNRule(N.default_equiv_params())
bad = tot = 0
t0 = time.time(); tn = td = 0.0
for inst in insts:
    sc = C.I.load(inst)
    for x in E.genomes(inst)[:16]:
        t = time.time(); a = C.R.decode_rule(sc, x, C.R.default_rule); td += time.time() - t
        t = time.time(); b = C.R.decode_rule(sc, x, rule); tn += time.time() - t
        tot += 1
        if a.obj != b.obj or (a.obj and a.pheno != b.pheno):
            bad += 1
            print("不一致", inst, a.obj, b.obj)
print(f"{tot} 个解码，不一致 {bad}；耗时 默认 {td:.1f}s，网络 {tn:.1f}s（{tn / max(td, 1e-9):.2f} 倍）")
