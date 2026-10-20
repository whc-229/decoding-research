"""可解释性（第 7 步）：
  A. GP 各次的最终表达式（导出时已折叠常数）与用到的终端；
  B. ES16 网络的置换特征重要性，两种量法：
     B1 首选翻转率——在测试实例的决策状态上，把一个特征换成同类候选（复用 / 新开）里随机抽的值，网络首选动作改变的比例；
     B2 代理分下降——训练实例上（3 个不偏离 + 16 个随机基因），推理时同样替换该特征，代理分比不替换时低多少；
  C. 首选一致率——在测试实例上用默认规则解码（evalrule.genomes 同样方式的 3 个不偏离 + 前 4 个随机基因），
     走到的每个决策状态上问所有规则"首选什么"，统计与默认规则、r47、GP run4 首选相同的比例。
     状态集合是默认规则走到的状态（各规则共用同一组状态，便于比较；不是各规则自己会走到的状态）。
测试实例只用于事后分析，不参与任何训练或选择。
用法: python interp.py [进程数]   输出: out/interp.md、out/interp.json
"""
import json, multiprocessing as mp, os, sys
import numpy as np
import common as C
import evalrule as E
import features as F
import nnrule as N
import proxy as PX
import score_rules as SR

ROOT_R = C.RULEGEN
ARMS = (["默认=K0.25:default", "LLM-full(r47)=K0.25:out/full/best_rule.py", "LLM-score(r35)=K0.25:out/score/best_rule.py"]
        + [f"LLM-full({t})=K0.25:out/full_{t}/best_rule.py" for t in ("s2", "s3")]
        + [f"LLM-score({t})=K0.25:out/score_{t}/best_rule.py" for t in ("s2", "s3")]
        + [f"EoH(run{r})=K0.25:../neural/out/eoh/run{r}/best_rule.py" for r in (1, 2, 3)]
        + [f"GP(run{r})=K0.25:../neural/out/gp/run{r}/best_rule.py" for r in range(1, 6)]
        + [f"IL16(s{s})=K0.25:nn:out/nn_il_h16{'' if s == 0 else f'_s{s}'}.npz" for s in range(5)]
        + [f"ES16(s{s})=K0.25:nn:out/es/il_h16{'' if s == 0 else f'_s{s}'}/best.npz" for s in range(3)]
        + [f"IL32-16(s{s})=K0.25:nn:out/nn_il{'' if s == 0 else f'_s{s}'}.npz" for s in range(5)])
REFS = ["默认", "LLM-full(r47)", "GP(run4)"]
ES = [f"ES16(s{s})" for s in range(3)]
ROBOT_IDX = [F.NAMES.index(n) for n in F.ROBOT]
NEW_IDX = [F.NAMES.index(n) for n in F.NEW]


def key(a):
    """动作的可比较标识：复用按机器人开启顺序，新开按类型"""
    return ("reuse", a[1].idx) if a[0] == "reuse" else ("new", int(a[1]))


def states_job(inst):
    """C：一个测试实例上，默认规则解码走到的每个状态，记录所有规则的首选；另存 ES16 的特征矩阵（给 B1）"""
    rules = [(n, SR.picklable(s)) for n, s in map(SR.A.parse, ARMS)]
    sc = C.I.load(inst)
    X = E.genomes(inst)[:7]
    firsts, mats = [], []

    def rule(ctx):
        row = []
        for n, r in rules:
            try:
                first, _, _ = C.R._normalize(r(ctx), ctx, len(sc["R"]))
                row.append(key(first))
            except Exception:
                row.append(None)
        firsts.append(row)
        acts, M = F.featurize(ctx)
        if len(acts) > 1:
            mats.append(M)
        return C.R.default_rule(ctx)
    for x in X:
        C.R.decode_rule(sc, x, rule)
    names = [n for n, _ in rules]
    return inst, names, firsts, mats


class PermNN:
    """推理时把特征 j 换成同类候选的经验分布里随机抽的值（B2 用）"""

    def __init__(self, params, j, vals, seed):
        self.p, self.j, self.vals, self.seed, self.rng = params, j, vals, seed, None

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k != "rng"}

    def __setstate__(self, d):
        self.__dict__.update(d); self.rng = None

    def __call__(self, ctx):
        if self.rng is None:
            self.rng = np.random.default_rng(self.seed)
        acts, X = F.featurize(ctx)
        if len(acts) <= 1:
            return acts if acts else [("new", ctx.gene_type)]
        X = X.copy()
        rows = rows_of(X, self.j)
        if rows.any():
            X[rows, self.j] = self.rng.choice(self.vals, rows.sum())
        s = N.forward(self.p, X)
        return [acts[i] for i in np.argsort(-s, kind="stable")]


def rows_of(X, j):
    """特征 j 适用的候选行：机器人特征只看复用候选，新开特征只看新开候选，其余全部"""
    isnew = X[:, F.I_IS_NEW] > 0.5
    if j in ROBOT_IDX:
        return ~isnew
    if j in NEW_IDX:
        return isnew
    return np.ones(len(X), bool)


def main():
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    tr, te = C.I.split()
    res = {}
    # A. GP
    gp = []
    for r in range(1, 6):
        d = json.load(open(os.path.join(C.OUT, "gp", f"run{r}", "report.json"), encoding="utf-8"))
        used = [sorted({t for t in F.NAMES if t in e}) for e in d["expr"]]
        gp.append({"run": r, "score": d["best_score"], "size": d["size"], "expr": d["expr"], "terms": used})
    res["gp"] = gp
    # C 与 B1 的状态
    with mp.Pool(procs) as pool:
        out = pool.map(states_job, sorted(te, key=lambda i: -C.L.nvar(C.I.load(i), "dec5")), chunksize=1)
    names = out[0][1]
    F_all = [row for _, _, f, _ in out for row in f]
    mats = [m for _, _, _, ms in out for m in ms]
    n_all = len(mats)
    if len(mats) > 20000:                         # B1 只用随机抽的 2 万个多候选状态（省时间）
        sel = np.random.default_rng(1).choice(len(mats), 20000, replace=False)
        mats = [mats[i] for i in sel]
    agree = {}
    for ref in REFS:
        jr = names.index(ref)
        agree[ref] = {n: float(np.mean([row[k] == row[jr] for row in F_all if row[k] is not None and row[jr] is not None]))
                      for k, n in enumerate(names)}
    res["agree"] = agree; res["n_states"] = len(F_all)
    # B1：首选翻转率（测试状态上）
    il = np.load(os.path.join(C.OUT, "il_data.npz"))["X"]
    isnew_il = il[:, F.I_IS_NEW] > 0.5
    rng = np.random.default_rng(0)
    flip = {}
    for es in ES:
        p = SR.A.rule_of(dict(map(SR.A.parse, ARMS))[es]).p
        base = [int(np.argmax(N.forward(p, M))) for M in mats]
        fr = []
        for j in range(F.NF):
            if j == F.I_IS_NEW:
                fr.append(None); continue
            vals = il[~isnew_il, j] if j in ROBOT_IDX else il[isnew_il, j] if j in NEW_IDX else il[:, j]
            ch = 0
            for M, b in zip(mats, base):
                Mp = M.copy(); rows = rows_of(Mp, j)
                if rows.any():
                    Mp[rows, j] = rng.choice(vals, rows.sum())
                ch += int(np.argmax(N.forward(p, Mp))) != b
            fr.append(ch / len(mats))
        flip[es] = fr
    res["flip"] = flip; res["n_mats"] = len(mats); res["n_mats_all"] = n_all
    # B2：代理分下降（训练实例，3 + 16 个基因）
    gidx = list(range(16))
    drop = {}
    with mp.Pool(procs) as pool:
        for es in ES:
            p = SR.A.rule_of(dict(map(SR.A.parse, ARMS))[es]).p
            base, _ = PX.score(N.NNRule(p), pool=pool, gene_idx=gidx)
            d = []
            for j in range(F.NF):
                if j == F.I_IS_NEW:
                    d.append(None); continue
                vals = il[~isnew_il, j] if j in ROBOT_IDX else il[isnew_il, j] if j in NEW_IDX else il[:, j]
                sc, _ = PX.score(PermNN(p, j, vals, 100 + j), pool=pool, gene_idx=gidx)
                d.append(base - sc)
            drop[es] = {"base": base, "drop": d}
            print(es, "完成", flush=True)
    res["drop"] = drop
    json.dump(res, open(os.path.join(C.OUT, "interp.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(res, names)


def report(res, names):
    L = ["# 可解释性\n", "## A. GP 各次的最终规则（导出时已折叠常数）\n",
         "| 运行 | 代理分 | 节点数（复用 / 新开） | 复用树 | 新开树 | 用到的终端 |", "|---|---|---|---|---|---|"]
    for g in res["gp"]:
        L.append(f"| run{g['run']} | {g['score']:.4f} | {g['size'][0]} / {g['size'][1]} | `{g['expr'][0]}` | `{g['expr'][1]}` | "
                 f"{', '.join(sorted(set(g['terms'][0]) | set(g['terms'][1])))} |")
    L += ["\n## B. ES16 的置换特征重要性\n",
          f"B1 首选翻转率：测试实例上默认规则走到的多候选状态（共 {res['n_mats_all']} 个，随机抽 {res['n_mats']} 个），把该特征换成同类候选经验分布（IL 数据）里随机抽的值后，"
          "网络首选改变的比例。B2 代理分下降：训练实例、3 个不偏离 + 16 个随机基因，推理时同样替换后代理分的下降（正 = 重要）。\n",
          "| 特征 | " + " | ".join(f"B1 {e}" for e in ES) + " | B1 平均 | " + " | ".join(f"B2 {e}" for e in ES) + " | B2 平均 |",
          "|---|" + "---|" * (2 * len(ES) + 2)]
    rows = []
    for j, nm in enumerate(F.NAMES):
        if j == F.I_IS_NEW:
            continue
        b1 = [res["flip"][e][j] for e in ES]; b2 = [res["drop"][e]["drop"][j] for e in ES]
        rows.append((np.mean(b1), nm, b1, b2))
    for m1, nm, b1, b2 in sorted(rows, reverse=True):
        L.append(f"| {nm} | " + " | ".join(f"{v:.3f}" for v in b1) + f" | **{m1:.3f}** | " + " | ".join(f"{v:+.4f}" for v in b2)
                 + f" | **{np.mean(b2):+.4f}** |")
    L.append("\nB2 基准（不替换）的代理分：" + "、".join(f"{e} {res['drop'][e]['base']:.4f}" for e in ES))
    L += [f"\n## C. 首选一致率（测试实例上默认规则走到的 {res['n_states']} 个决策状态，含回溯修复时的重放）\n",
          "| 规则 | " + " | ".join(f"与 {r}" for r in REFS) + " |", "|---|" + "---|" * len(REFS)]
    for n in names:
        L.append(f"| {n} | " + " | ".join(f"{res['agree'][r][n]:.3f}" for r in REFS) + " |")
    open(os.path.join(C.OUT, "interp.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
