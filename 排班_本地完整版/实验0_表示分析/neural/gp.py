"""遗传规划规则（第 2 步）：标准树形多树 GP 超启发式（Zhang, Mei, Nguyen, Zhang, TEVC 2024 综述中的常规设置）。

个体 = 两棵树：复用优先级树（终端 = 全局 + 类型 + 机器人特征，22 个）和新开优先级树（终端 = 全局 + 类型 + 新开特征，17 个），
外加随机常数。每个候选动作用对应的树打分，所有候选（复用和新开一起）按分数从高到低排成规则的偏好列表
（第一个 = 不偏离时的动作，与神经网络规则的接法相同；所以 GP 也能学到"有可用机器人时仍新开"）。
函数集 + − × 保护除法 max min；初始化 ramped half-and-half（深度 2～6），最大深度 8；锦标赛 7；交叉 0.80、变异 0.15、复制 0.05，
精英 2；多树交叉 / 变异每次随机选一棵树、两个父代在同一棵树上操作。

适应度 = proxy 代理分（与 LLM 规则同一打分），每代全部个体用同一批随机基因子集（3 个不偏离基因 + 16 个随机基因）；
每代把子集上最好的个体再用全部 67 个基因打分，记录"累计代理评价成本 → 至今最好全基因分"曲线（成本以全基因评价当量计，
1 当量 = 15 实例 × 67 次解码，LLM 规则生成每条候选正好 1 当量，便于对齐）；最后从这些个体和末代前 10 名里按全基因分选出最终规则。

个体在内存里就是规则源码（FEAT_SRC + 两个打分函数），评价时经 rulegen 的 compile_rule 受限执行，
所以导出的 best_rule.py 与搜索时评价的完全是同一段代码，可直接走 ga_any.py 的 K0.25:<规则.py> 写法。

用法: python gp.py 运行号 [进程数|auto] [--pop 64 --gens 30 --genes 16]
输出: out/gp/run<运行号>/ 下 state.pkl（每代保存，可续跑）、history.json、best_rule.py、report.json
"""
import argparse, json, math, multiprocessing as mp, os, pickle, sys, time
import numpy as np
import common as C
import proxy as PX
import featsrc as FS

OPS = {"add": "+", "sub": "-", "mul": "*", "pdiv": None, "max": None, "min": None}
TERMS = [FS.REUSE_TERMS, FS.NEW_TERMS]
TREE_NAMES = ["pr_reuse", "pr_new"]
MAX_DEPTH, INIT_DEPTH, MUT_DEPTH = 8, (2, 6), 4
TOUR, P_X, P_M, ELITE = 7, 0.80, 0.15, 2
FULL_UNIT = 15 * 67          # 1 个全基因评价当量的解码次数

RULE_TAIL = '''

def pdiv(a, b):
    # 保护除法：分母接近 0 时取 1
    return a / b if abs(b) > 1e-6 else 1.0


def rule(ctx):
    # 复用候选用 pr_reuse 打分、新开候选用 pr_new 打分，全部按分数从高到低排序（并列保持原顺序）
    acts, rows = feats(ctx)
    if len(acts) <= 1:
        return acts if acts else [("new", ctx.gene_type)]
    sc = []
    for a, x in zip(acts, rows):
        s = pr_reuse(*x) if a[0] == "reuse" else pr_new(*x)
        if not (s == s and abs(s) < 1e300):
            s = -1e300
        sc.append(s)
    order = sorted(range(len(acts)), key=lambda i: -sc[i])
    return [acts[i] for i in order]
'''


# ---------------- 树：嵌套 tuple，('op', 左, 右) / ('v', 特征名) / ('c', 常数) ----------------
def rand_leaf(rng, k):
    """随机终端：特征或随机常数（常数与每个特征等概率）"""
    terms = TERMS[k]
    j = int(rng.integers(len(terms) + 1))
    if j == len(terms):
        return ("c", round(float(rng.uniform(-1, 1)), 3))
    return ("v", terms[j])


def rand_tree(rng, k, depth, full):
    """full=True 生成满树，否则 grow；depth = 剩余深度（叶子深度 0）"""
    if depth == 0 or (not full and rng.random() < len(TERMS[k]) / (len(TERMS[k]) + len(OPS))):
        return rand_leaf(rng, k)
    op = list(OPS)[int(rng.integers(len(OPS)))]
    return (op, rand_tree(rng, k, depth - 1, full), rand_tree(rng, k, depth - 1, full))


def depth(t):
    return 0 if t[0] in ("v", "c") else 1 + max(depth(t[1]), depth(t[2]))


def size(t):
    return 1 if t[0] in ("v", "c") else 1 + size(t[1]) + size(t[2])


def paths(t, p=()):
    """→ [(路径, 是否函数节点)]"""
    if t[0] in ("v", "c"):
        return [(p, False)]
    return [(p, True)] + paths(t[1], p + (1,)) + paths(t[2], p + (2,))


def get(t, p):
    for i in p:
        t = t[i]
    return t


def put(t, p, s):
    if not p:
        return s
    i = p[0]
    l = list(t); l[i] = put(t[i], p[1:], s)
    return tuple(l)


def pick(rng, t):
    """Koza 选点：90% 函数节点，10% 叶子"""
    ps = paths(t)
    fn = [p for p, f in ps if f]
    lf = [p for p, f in ps if not f]
    pool = fn if fn and rng.random() < 0.9 else lf
    return pool[int(rng.integers(len(pool)))]


def crossover(rng, a, b):
    """多树子树交叉：随机选一棵树，两个父代在这棵树上交换子树；超过最大深度的子代换回父代"""
    k = int(rng.integers(2))
    pa, pb = pick(rng, a[k]), pick(rng, b[k])
    ca, cb = put(a[k], pa, get(b[k], pb)), put(b[k], pb, get(a[k], pa))
    ka = list(a); kb = list(b)
    ka[k] = ca if depth(ca) <= MAX_DEPTH else a[k]
    kb[k] = cb if depth(cb) <= MAX_DEPTH else b[k]
    return tuple(ka), tuple(kb)


def mutate(rng, a):
    """子树变异：随机选一棵树的一个节点，换成 grow 生成的随机子树（深度 ≤ 4）"""
    k = int(rng.integers(2))
    p = pick(rng, a[k])
    c = put(a[k], p, rand_tree(rng, k, int(rng.integers(1, MUT_DEPTH + 1)), False))
    l = list(a)
    l[k] = c if depth(c) <= MAX_DEPTH else a[k]
    return tuple(l)


def init_pop(rng, n):
    """ramped half-and-half：深度 2～6 均分，每个深度一半满树一半 grow；去重"""
    pop, seen, ds = [], set(), list(range(INIT_DEPTH[0], INIT_DEPTH[1] + 1))
    i = 0
    while len(pop) < n:
        d, full = ds[i % len(ds)], (i // len(ds)) % 2 == 0
        ind = (rand_tree(rng, 0, d, full), rand_tree(rng, 1, d, full))
        i += 1
        if ind not in seen:
            seen.add(ind); pop.append(ind)
    return pop


def expr(t):
    if t[0] == "v":
        return t[1]
    if t[0] == "c":
        return repr(t[1])
    a, b = expr(t[1]), expr(t[2])
    if OPS[t[0]]:
        return f"({a} {OPS[t[0]]} {b})"
    return f"{t[0]}({a}, {b})"


def fold(t):
    """常数子树折叠（只用于导出可读版本；IEEE 运算相同，结果逐位不变）"""
    if t[0] in ("v", "c"):
        return t
    a, b = fold(t[1]), fold(t[2])
    if a[0] == "c" and b[0] == "c":
        x, y = a[1], b[1]
        v = {"add": x + y, "sub": x - y, "mul": x * y, "pdiv": x / y if abs(y) > 1e-6 else 1.0,
             "max": max(x, y), "min": min(x, y)}[t[0]]
        return ("c", v)
    return (t[0], a, b)


def to_src(ind, folded=False):
    """个体 → 规则源码（可直接交给 compile_rule）"""
    out = [FS.FEAT_SRC]
    for k in range(2):
        t = fold(ind[k]) if folded else ind[k]
        out.append(f"\n\ndef {TREE_NAMES[k]}({', '.join(TERMS[k])}):\n    return {expr(t)}\n")
    return "".join(out) + RULE_TAIL


class SrcRule:
    """可 pickle 的规则：只传源码，在工作进程里编译一次"""

    def __init__(self, src):
        self.src, self.f = src, None

    def __getstate__(self):
        return {"src": self.src}

    def __setstate__(self, d):
        self.src, self.f = d["src"], None

    def __call__(self, ctx):
        if self.f is None:
            self.f = C.R.compile_rule(self.src)
        return self.f(ctx)


# ---------------- 评价 ----------------
_ORDER = None


def evaluate(pool, srcs, gene_idx):
    """srcs: 规则源码列表 → 各自的平均 HV（15 个训练实例）。所有 (规则, 实例) 一起并行，大实例先算。"""
    global _ORDER
    tr = C.I.split()[0]
    if _ORDER is None:
        _ORDER = sorted(tr, key=lambda i: -PX.BASE[i]["secs"])
    args = [(SrcRule(s), i, gene_idx) for i in _ORDER for s in srcs]
    res = pool.map(PX.eval_instance, args, chunksize=1)
    hv = {}
    for (r, _, _), x in zip(args, res):
        hv.setdefault(r.src, []).append(x["hv"])
    return [float(np.mean(hv[s])) for s in srcs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=int)
    ap.add_argument("procs", nargs="?", default="auto")
    ap.add_argument("--pop", type=int, default=64)
    ap.add_argument("--gens", type=int, default=30)
    ap.add_argument("--genes", type=int, default=16, help="每代随机基因子集大小（另加 3 个不偏离基因）")
    ap.add_argument("--final-top", type=int, default=10)
    a = ap.parse_args()
    odir = os.path.join(C.OUT, "gp", f"run{a.run}")
    os.makedirs(odir, exist_ok=True)
    spath = os.path.join(odir, "state.pkl")
    sub_unit = 15 * (3 + a.genes)
    if os.path.exists(spath):
        st = pickle.load(open(spath, "rb"))
        assert st["args"] == vars(a) | {"procs": st["args"]["procs"]}, "参数与已有 state.pkl 不同"
        rng = np.random.default_rng(); rng.bit_generator.state = st["rng"]
        print(f"续跑：已完成 {st['gen'] + 1} 代", flush=True)
    else:
        rng = np.random.default_rng(1000 + a.run)
        st = {"args": vars(a), "gen": -1, "pop": init_pop(rng, a.pop), "fit": None, "rng": None,
              "full": {}, "hist": [], "decodes": 0, "secs": 0.0}
    with mp.Pool(C.nprocs(a.procs)) as pool:
        while st["gen"] + 1 < a.gens:
            t0 = time.time()
            g = st["gen"] + 1
            if g > 0:                                           # 用上一代的适应度繁殖
                st["pop"] = breed(rng, st["pop"], st["fit"], a.pop)
            gene_idx = sorted(rng.choice(64, a.genes, replace=False).tolist())
            srcs = [to_src(ind) for ind in st["pop"]]
            uniq = list(dict.fromkeys(srcs))
            fu = dict(zip(uniq, evaluate(pool, uniq, gene_idx)))
            fit = [fu[s] for s in srcs]
            st["decodes"] += len(uniq) * sub_unit
            b = int(np.argmax(fit))
            if srcs[b] not in st["full"]:
                st["full"][srcs[b]] = {"score": evaluate(pool, [srcs[b]], None)[0], "gen": g, "ind": st["pop"][b]}
                st["decodes"] += FULL_UNIT
            best_full = max(v["score"] for v in st["full"].values())
            st["secs"] += time.time() - t0
            st["hist"].append({"gen": g, "sub_best": fit[b], "sub_mean": float(np.mean(fit)), "gen_best_full": st["full"][srcs[b]]["score"],
                               "best_full_so_far": best_full, "equiv_evals": st["decodes"] / FULL_UNIT, "uniq": len(uniq),
                               "size_best": size(st["pop"][b][0]) + size(st["pop"][b][1]), "secs": st["secs"]})
            st.update(gen=g, fit=fit, rng=rng.bit_generator.state)
            pickle.dump(st, open(spath + ".tmp", "wb")); os.replace(spath + ".tmp", spath)
            h = st["hist"][-1]
            print(f"代 {g:2d}  子集最好 {h['sub_best']:.4f} 均值 {h['sub_mean']:.4f} | 本代最好全基因 {h['gen_best_full']:.4f} "
                  f"至今 {best_full:.4f} | 当量 {h['equiv_evals']:.1f}  不同个体 {len(uniq)}  大小 {h['size_best']}  "
                  f"{time.time() - t0:.0f}s", flush=True)
        # 末代前若干名补全基因分，最终按全基因分选
        if not st.get("done"):
            order = np.argsort(-np.asarray(st["fit"]), kind="stable")
            cand = []
            for i in order:
                s = to_src(st["pop"][i])
                if s not in st["full"] and s not in [c[0] for c in cand]:
                    cand.append((s, st["pop"][i]))
                if len(cand) >= a.final_top:
                    break
            if cand:
                for (s, ind), v in zip(cand, evaluate(pool, [c[0] for c in cand], None)):
                    st["full"][s] = {"score": v, "gen": st["gen"], "ind": ind}
                st["decodes"] += len(cand) * FULL_UNIT
            st["done"] = True
            pickle.dump(st, open(spath + ".tmp", "wb")); os.replace(spath + ".tmp", spath)
    best = max(st["full"].values(), key=lambda v: v["score"])
    ind = best["ind"]
    src = to_src(ind, folded=True)
    head = (f"# GP 规则：运行 {a.run}，第 {best['gen']} 代，代理分（15 个训练实例 × 67 个基因）{best['score']:.4f}\n"
            f"# 复用树 {size(ind[0])} 个节点、深度 {depth(ind[0])}；新开树 {size(ind[1])} 个节点、深度 {depth(ind[1])}（导出时已折叠常数子树）\n")
    open(os.path.join(odir, "best_rule.py"), "w", encoding="utf-8").write(head + src)
    rep = {"run": a.run, "args": vars(a), "best_score": best["score"], "best_gen": best["gen"],
           "size": [size(ind[0]), size(ind[1])], "depth": [depth(ind[0]), depth(ind[1])],
           "expr": [expr(fold(ind[0])), expr(fold(ind[1]))], "equiv_evals": st["decodes"] / FULL_UNIT,
           "decodes": st["decodes"], "secs": st["secs"], "n_full_evaluated": len(st["full"]), "history": st["hist"]}
    json.dump(rep, open(os.path.join(odir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：最好代理分 {best['score']:.4f}（第 {best['gen']} 代），累计 {rep['equiv_evals']:.1f} 个全基因评价当量，"
          f"{st['secs'] / 60:.1f} 分钟 → {odir}/best_rule.py", flush=True)


def breed(rng, pop, fit, n):
    """精英 + 锦标赛选择 + 交叉 / 变异 / 复制"""
    fit = np.asarray(fit)
    order = np.argsort(-fit, kind="stable")
    new = [pop[i] for i in order[:ELITE]]

    def tour():
        c = rng.choice(len(pop), TOUR, replace=False)
        return pop[c[int(np.argmax(fit[c]))]]
    while len(new) < n:
        u = rng.random()
        if u < P_X:
            new += list(crossover(rng, tour(), tour()))
        elif u < P_X + P_M:
            new.append(mutate(rng, tour()))
        else:
            new.append(tour())
    return new[:n]


if __name__ == "__main__":
    main()
