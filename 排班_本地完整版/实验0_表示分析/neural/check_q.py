"""自检（R0-1）：ruledec_ext 加了生效阈值 dev_on 之后，
  1. 15 个训练实例 × 16 个扩展布局基因（13 个随机 + 3 个不偏离）× 规则（默认、ES16 s0、GP run4），K = 1.0：
     原写法 X1.0（不传 dev_on）、显式 dev_on = 0.6、臂写法 X1.0q0.4 三者逐解相同（目标值与表型）——必须 0 不一致；
  2. 随机基因下生效槽的比例 ≈ q（q = 0.4 / 0.6 / 0.8），以及各 q 下的可行率（只报告，不判定）。
MOEA 部分（2 个训练实例上重跑 X1.0，与 train_Kext.csv 逐位相同）由 moea_q.py 跑、compare_q04() 比较：
  python check_q.py [进程数]        → 第 1、2 项
  python check_q.py cmp 文件.csv     → 文件中的 X1.0 前沿与 out/train_Kext.csv 逐位比较
"""
import csv, multiprocessing as mp, os, sys
import numpy as np
import common as C
import arms as A
import ruledec_ext as X

RULES = ["default", "nn:out/es/il_h16/best.npz", "../neural/out/gp/run4/best_rule.py"]


def genes(sc, inst):
    """扩展布局 K = 1.0 的 16 个基因：前 3 个不偏离（全部开关基因 = 0），后 13 个均匀随机（种子固定）"""
    n = X.nvar(sc, 1.0)
    K, _ = C.R.n_slots(sc, 1.0)
    rng = np.random.default_rng([2026, 1023, sum(map(ord, inst))])
    G = [rng.uniform(0, 0.99, n) for _ in range(16)]
    for g in G[:3]:
        g[1:2 * K:2] = 0.0
    return G


def job(inst):
    """一个实例：三种写法逐解比较 + 各 q 下的生效比例与可行率"""
    sc = C.I.load(inst)
    tot = bad = 0; ex = []
    for src in RULES:
        d_old = A.decoder(f"X1.0:{src}")
        d_q04 = A.decoder(f"X1.0q0.4:{src}")
        rule = A.rule_of(f"X1.0:{src}")
        for x in genes(sc, inst):
            a = d_old(sc, x)
            b = X.decode_rule(sc, x, rule, 1.0, dev_on=0.6)
            c = d_q04(sc, x)
            tot += 1
            if not (a.obj == b.obj == c.obj) or (a.obj and not (a.pheno == b.pheno == c.pheno)):
                bad += 1; ex.append((src, a.obj, b.obj, c.obj))
    K, _ = C.R.n_slots(sc, 1.0)
    frac, feas = {}, {}
    rng = np.random.default_rng([7, sum(map(ord, inst))])
    for q in (0.4, 0.6, 0.8):
        dec = A.decoder(f"X1.0q{q}:default")
        xs = [rng.uniform(0, 0.99, X.nvar(sc, 1.0)) for _ in range(10)]
        frac[q] = float(np.mean([np.mean(np.asarray(x[1:2 * K:2], np.float32) >= round(1 - q, 10)) for x in xs]))
        feas[q] = float(np.mean([dec(sc, x).feasible for x in xs]))
    return inst, tot, bad, ex[:2], frac, feas


def compare_q04(path):
    """path 中 X1.0 臂（名字 X1.0:规则）的前沿与 out/train_Kext.csv 逐位比较 → (比较次数, 不一致次数)"""
    ref = {(r[0], r[1], r[2]): r[6] for r in csv.reader(open(os.path.join(C.OUT, "train_Kext.csv"), encoding="utf-8")) if r[0] != "scenario"}
    n = bad = 0
    for r in csv.reader(open(path, encoding="utf-8")):
        if r[0] == "scenario":
            continue
        n += 1
        if ref.get((r[0], r[1], r[2])) != r[6]:
            bad += 1; print("不一致", r[:3], ref.get((r[0], r[1], r[2])), r[6])
    print(f"{path}：与 train_Kext.csv 比较 {n} 次运行，不一致 {bad}")
    return n, bad


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cmp":
        compare_q04(sys.argv[2]); sys.exit(0)
    with mp.Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as p:
        res = p.map(job, C.I.split()[0])
    for r in res:
        if r[2]:
            print("不一致", r[:4])
    print(f"{sum(r[1] for r in res)} 个解码，不一致 {sum(r[2] for r in res)}")
    for q in (0.4, 0.6, 0.8):
        print(f"q = {q}：随机基因生效槽比例 {np.mean([r[4][q] for r in res]):.3f}，可行率 {np.mean([r[5][q] for r in res]):.2f}")
