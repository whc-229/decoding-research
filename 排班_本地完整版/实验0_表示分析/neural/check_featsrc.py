"""自检（GP 用）：
1) featsrc.FEAT_SRC 的特征与 features.featurize 逐位相同（解码过程中每次规则调用都比对）；
2) 手工构造的"默认等价"两棵树经 compile_rule 后与默认规则逐解相同；
3) 随机树：导出版（折叠常数）与搜索时评价的版本逐解相同。
用法: python check_featsrc.py [实例,...]（默认全部训练实例，每个实例 8 个基因）
"""
import sys
import numpy as np
import common as C
import evalrule as E
import features as F
import featsrc as FS
import gp as GP

tr, _ = C.I.split()
insts = sys.argv[1].split(",") if len(sys.argv) > 1 else tr
ns = {"__builtins__": C.R.SAFE_BUILTINS}
exec(FS.FEAT_SRC, ns)
feats = ns["feats"]
nchk = [0, 0]


def checking_rule(ctx):
    """默认规则，但顺便比对两种特征计算"""
    a1, X = F.featurize(ctx)
    a2, rows = feats(ctx)
    nchk[0] += 1
    same = len(a1) == len(a2) and all(x[0] == y[0] and x[1] is y[1] for x, y in zip(a1, a2))
    if not same or (len(rows) and not np.array_equal(X, np.asarray([FS.full_row(a, r) for a, r in zip(a2, rows)]))):
        nchk[1] += 1
    return C.R.default_rule(ctx)


# 默认等价树：复用分 = 1 − 可用列表中的名次（∈[0,1]）；新开分 = 0.5·是否基因类型 − 0.1·类型偏移 − 100
dflt = (("sub", ("c", 1.0), ("v", "r_rank_avail")),
        ("sub", ("sub", ("mul", ("c", 0.5), ("v", "n_is_gene_type")), ("mul", ("c", 0.1), ("v", "n_gene_offset"))), ("c", 100.0)))
rd = GP.SrcRule(GP.to_src(dflt))
rng = np.random.default_rng(7)
rand = [(GP.rand_tree(rng, 0, 4, False), GP.rand_tree(rng, 1, 4, False)) for _ in range(4)]
rand = [ind for ind in rand if GP.to_src(ind) != GP.to_src(ind, True)] or rand
bad_d = bad_f = tot = 0
for inst in insts:
    sc = C.I.load(inst)
    for x in E.genomes(inst)[:8]:
        a = C.R.decode_rule(sc, x, checking_rule)
        b = C.R.decode_rule(sc, x, rd)
        tot += 1
        if a.obj != b.obj or (a.obj and a.pheno != b.pheno):
            bad_d += 1; print("默认等价树不一致", inst, a.obj, b.obj)
        for ind in rand[:2]:
            u = C.R.decode_rule(sc, x, C.R.compile_rule(GP.to_src(ind)))
            v = C.R.decode_rule(sc, x, C.R.compile_rule(GP.to_src(ind, True)))
            if u.obj != v.obj or (u.obj and u.pheno != v.pheno):
                bad_f += 1; print("折叠前后不一致", inst, u.obj, v.obj)
print(f"特征比对 {nchk[0]} 次规则调用，不一致 {nchk[1]}；默认等价树 {tot} 个解码，不一致 {bad_d}；"
      f"折叠前后 {2 * tot} 个解码，不一致 {bad_f}")
