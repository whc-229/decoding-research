"""神经网络规则·进化策略微调（第 1b 步）：从模仿学习权重出发，用 OpenAI-ES 直接优化代理分（强化学习的无梯度对照）。

每代：抽一批随机基因子集（3 个不偏离基因 + --genes 个随机基因），全部候选用同一批基因（公共随机数）；
采 pop/2 对对称扰动 θ ± σε，加上中心 θ 本身，一起在 15 个训练实例上打代理分；
适应度做中心化秩变换（并列取平均秩），梯度 g = Σ (F⁺ − F⁻) ε / (pop σ)，用 Adam 上升。
每 --full-every 代（以及第 0 代和最后一代）用全部 67 个基因给中心 θ 打分，按全基因分保留最好的中心 → best.npz。
特征标准化 mu/sd 与网络结构固定不变，只调权重。测试实例不参与。

成本以"全基因评价当量"计（1 当量 = 15 实例 × 67 次解码，与 LLM 规则生成的一条候选、gp.py 的计法相同）。

用法: python es.py 初始权重.npz 输出名 [进程数|auto] [--pop 32 --genes 20 --gens 60 --sigma 0.02 --lr 0.01]
  初始权重相对 neural/；写 default 用 nnrule.default_equiv_params()（只用于自检）。
输出: out/es/<输出名>/ 下 state.pkl（每代保存，可续跑）、best.npz、history.json
"""
import argparse, json, multiprocessing as mp, os, pickle, time
import numpy as np
import common as C
import nnrule as N
import proxy as PX

FULL_UNIT = 15 * 67


def centered_ranks(x):
    """并列取平均秩，映射到 [−0.5, 0.5]"""
    x = np.asarray(x)
    order = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[order] = np.arange(len(x), dtype=float)
    for v in np.unique(x):                       # 并列的取平均秩
        m = x == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r / max(1, len(x) - 1) - 0.5


_ORDER = None


def evaluate(pool, plist, gene_idx):
    """plist: 参数 dict 列表 → 各自的平均 HV（15 个训练实例）；所有 (规则, 实例) 一起并行，大实例先算"""
    global _ORDER
    if _ORDER is None:
        _ORDER = sorted(C.I.split()[0], key=lambda i: -PX.BASE[i]["secs"])
    rules = [N.NNRule(p) for p in plist]
    args = [(rules[k], i, gene_idx) for i in _ORDER for k in range(len(rules))]
    res = pool.map(PX.eval_instance, args, chunksize=1)
    hv = np.zeros((len(rules), len(_ORDER)))
    for j, x in enumerate(res):
        hv[j % len(rules), j // len(rules)] = x["hv"]
    return hv.mean(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("init"); ap.add_argument("tag")
    ap.add_argument("procs", nargs="?", default="auto")
    ap.add_argument("--pop", type=int, default=32)
    ap.add_argument("--genes", type=int, default=20)
    ap.add_argument("--gens", type=int, default=60)
    ap.add_argument("--sigma", type=float, default=0.02)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--full-every", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    assert a.pop % 2 == 0
    odir = os.path.join(C.OUT, "es", a.tag)
    os.makedirs(odir, exist_ok=True)
    spath = os.path.join(odir, "state.pkl")
    if a.init == "default":
        p0 = N.default_equiv_params()
    else:
        d = np.load(a.init if os.path.isabs(a.init) else os.path.join(C.HERE, a.init))
        p0 = {k: d[k] for k in d.files}
    sub_unit = 15 * (3 + a.genes)
    if os.path.exists(spath):
        st = pickle.load(open(spath, "rb"))
        assert {k: v for k, v in st["args"].items() if k != "procs"} == {k: v for k, v in vars(a).items() if k != "procs"}, \
            "参数与已有 state.pkl 不同"
        rng = np.random.default_rng(); rng.bit_generator.state = st["rng"]
        print(f"续跑：已完成 {st['gen'] + 1} 代", flush=True)
    else:
        th = N.flatten(p0)
        rng = np.random.default_rng(2000 + a.seed)
        st = {"args": vars(a), "gen": -1, "theta": th, "m": np.zeros_like(th), "v": np.zeros_like(th), "rng": None,
              "best": None, "hist": [], "decodes": 0, "secs": 0.0}
    print(f"{N.n_weights(p0)} 个权重，种群 {a.pop}（{a.pop // 2} 对对称扰动）+ 中心，每代 {3 + a.genes} 个基因", flush=True)
    with mp.Pool(C.nprocs(a.procs)) as pool:
        if st["best"] is None:                                  # 初始点的全基因分
            t0 = time.time()
            s0 = float(evaluate(pool, [p0], None)[0])
            st["best"] = {"score": s0, "gen": -1, "theta": st["theta"].copy()}
            st["init_full"] = s0
            st["decodes"] += FULL_UNIT; st["secs"] += time.time() - t0
            print(f"初始权重全基因代理分 {s0:.4f}", flush=True)
        while st["gen"] + 1 < a.gens:
            t0 = time.time()
            g = st["gen"] + 1
            th = st["theta"]
            gene_idx = sorted(rng.choice(64, a.genes, replace=False).tolist())
            eps = rng.standard_normal((a.pop // 2, len(th)))
            cands = [N.unflatten(p0, th + a.sigma * e) for e in eps] + [N.unflatten(p0, th - a.sigma * e) for e in eps] \
                + [N.unflatten(p0, th)]
            f = evaluate(pool, cands, gene_idx)
            st["decodes"] += len(cands) * sub_unit
            fp, fm, fc = f[:a.pop // 2], f[a.pop // 2:a.pop], float(f[-1])
            r = centered_ranks(np.concatenate([fp, fm]))
            grad = ((r[:a.pop // 2] - r[a.pop // 2:]) @ eps) / (a.pop * a.sigma)
            k = g + 1
            st["m"] = 0.9 * st["m"] + 0.1 * grad
            st["v"] = 0.999 * st["v"] + 0.001 * grad ** 2
            st["theta"] = th + a.lr * (st["m"] / (1 - 0.9 ** k)) / (np.sqrt(st["v"] / (1 - 0.999 ** k)) + 1e-8)
            full = None
            if (g + 1) % a.full_every == 0 or g + 1 == a.gens:   # 更新后的中心用全部基因打分
                full = float(evaluate(pool, [N.unflatten(p0, st["theta"])], None)[0])
                st["decodes"] += FULL_UNIT
                if full > st["best"]["score"]:
                    st["best"] = {"score": full, "gen": g, "theta": st["theta"].copy()}
            st["secs"] += time.time() - t0
            h = {"gen": g, "center_sub": fc, "pop_sub_max": float(f[:-1].max()), "pop_sub_mean": float(f[:-1].mean()),
                 "n_distinct": int(len(np.unique(f[:-1]))), "full_after": full, "best_full": st["best"]["score"],
                 "step_norm": float(np.linalg.norm(st["theta"] - th)), "equiv_evals": st["decodes"] / FULL_UNIT, "secs": st["secs"]}
            st["hist"].append(h)
            st.update(gen=g, rng=rng.bit_generator.state)
            pickle.dump(st, open(spath + ".tmp", "wb")); os.replace(spath + ".tmp", spath)
            print(f"代 {g:2d}  中心(子集) {fc:.4f}  种群最好 {h['pop_sub_max']:.4f} 均值 {h['pop_sub_mean']:.4f}  不同分数 {h['n_distinct']}"
                  f"  步长 {h['step_norm']:.3f}" + (f" | 全基因 {full:.4f}" if full is not None else "") +
                  f"  至今最好 {st['best']['score']:.4f}  当量 {h['equiv_evals']:.0f}  {time.time() - t0:.0f}s", flush=True)
    N.NNRule(N.unflatten(p0, st["best"]["theta"])).save(os.path.join(odir, "best.npz"))
    rep = {"args": vars(a), "init_full": st["init_full"], "best_score": st["best"]["score"], "best_gen": st["best"]["gen"],
           "n_weights": N.n_weights(p0), "equiv_evals": st["decodes"] / FULL_UNIT, "decodes": st["decodes"], "secs": st["secs"],
           "history": st["hist"]}
    json.dump(rep, open(os.path.join(odir, "history.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：初始 {st['init_full']:.4f} → 最好 {st['best']['score']:.4f}（第 {st['best']['gen']} 代），"
          f"累计 {rep['equiv_evals']:.0f} 当量，{st['secs'] / 60:.1f} 分钟 → {odir}/best.npz", flush=True)


if __name__ == "__main__":
    main()
