"""自检（任务 D1）：原布局基因映射到扩展布局后，ruledec_ext.decode_rule 与 rulegen/ruledec.decode_rule 逐解相同。
15 个训练实例 × 16 个基因（evalrule.genomes(实例, kfrac) 的前 16 个，含 3 个不偏离基因）× K ∈ {0.25, 0.5} × 规则（默认、ES16 s0、GP run4）。
用法: python check_ext.py [进程数]
"""
import multiprocessing as mp, sys
import common as C
import evalrule as E
import score_rules as SR
import ruledec_ext as X

RULES = ["K0.25:default", "K0.25:nn:out/es/il_h16/best.npz", "K0.25:../neural/out/gp/run4/best_rule.py"]


def job(inst):
    """一个实例上的核对 → (实例, 解码数, 不一致数, 不一致示例)"""
    sc = C.I.load(inst)
    tot = bad = 0; ex = []
    for spec in RULES:
        rule = SR.picklable(spec)
        for kf in (0.25, 0.5):
            for x in E.genomes(inst, kfrac=kf)[:16]:
                a = C.R.decode_rule(sc, x, rule, kf)
                xn = X.from_old(sc, x, kf)
                assert len(xn) == X.nvar(sc, kf)
                b = X.decode_rule(sc, xn, rule, kf)
                tot += 1
                if a.obj != b.obj or (a.obj and a.pheno != b.pheno):
                    bad += 1; ex.append((spec, kf, a.obj, b.obj))
    return inst, tot, bad, ex[:2]


if __name__ == "__main__":
    with mp.Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as p:
        res = p.map(job, C.I.split()[0])
    for r in res:
        if r[2]:
            print("不一致", r)
    print(f"{sum(r[1] for r in res)} 个解码，不一致 {sum(r[2] for r in res)}")
