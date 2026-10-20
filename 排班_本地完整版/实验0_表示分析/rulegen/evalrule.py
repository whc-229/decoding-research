"""给一条规则打分（规则生成时用的廉价代理指标），并给出喂回 LLM 的诊断。

每个实例：
  - 纯规则解：所有偏离槽关闭（a=0），默认类型基因取 3 个值，取其中最好的 → 规则离下界多远（规则距离）；
  - 随机样本：N 个均匀随机基因（各候选规则用同一批随机数），稀疏偏离 K=0.25 解码；
  - 得分：纯规则解 + 随机样本的非支配集在固定归一化下的 HV。归一化范围由默认规则在同一批基因上的结果确定（baseline），
    所以不同规则的得分可以直接比较；得分高 = 规则给搜索的起点更好。
实验 3b 表明"随机样本最好解"能预测 MOEA 的表现，这是用它做代理指标的依据；规则确定后再用真正的 MOEA 在测试集上验证。
"""
import json, multiprocessing as mp, os, sys, time, traceback
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import ruledec as R  # noqa: E402
import instances as I  # noqa: E402

N_SAMPLES = 64
KFRAC = 0.25
BIG = 1e9


def genomes(inst, n=N_SAMPLES, kfrac=KFRAC):
    sc = I.load(inst)
    nv = R.L.nvar(sc, "dec5")
    K, _ = R.n_slots(sc, kfrac)
    rng = np.random.default_rng(sum(map(ord, inst)) * 7919)      # 固定种子：所有候选规则用同一批基因
    X = []
    for g in (0.1, 0.5, 0.9):                    # 纯规则解
        x = rng.random(nv); x[1:2 * K:2] = 0.0; x[2 * K] = g
        X.append(x)
    X += [rng.random(nv) for _ in range(n)]
    return X


def hv(points, lo, hi, ref=1.1):
    P = sorted({((a - lo[0]) / hi[0], (b - lo[1]) / hi[1]) for a, b in points})
    nd, best = [], float("inf")
    for p in P:
        if p[1] < best:
            nd.append(p); best = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / (ref * ref)


def eval_instance(args):
    """worker：返回该实例的指标 dict；规则出错返回 {'error': ...}"""
    src, inst, n, kfrac, bounds = args
    try:
        rule = R.compile_rule(src) if src else R.default_rule
    except Exception as e:
        return {"inst": inst, "error": f"编译失败：{e}"}
    sc = I.load(inst)
    LB = I.lb(inst)
    X = genomes(inst, n, kfrac)
    objs, stats, t = [], {}, time.time()
    try:
        for x in X:
            r = R.decode_rule(sc, x, rule, kfrac, stats=stats)
            objs.append(r.obj)
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()
        return {"inst": inst, "error": f"运行出错：{type(e).__name__}: {e}（{tb[-2].strip() if len(tb) > 1 else ''}）"}
    rule_objs = [o for o in objs[:3] if o]
    samp = [o for o in objs[3:] if o]
    feas = [o for o in objs if o]
    out = {"inst": inst, "LB": LB, "secs": time.time() - t,
           "feas_rate": len(samp) / max(1, len(objs) - 3),
           "rule_gap": (min(rule_objs)[0] - LB) if rule_objs else None,
           "rule_bal": min(rule_objs)[1] if rule_objs else None,
           "best_gap": (min(feas)[0] - LB) if feas else None,
           "best_bal": min(feas)[1] if feas else None,
           "rule_new_per_decode": stats.get("rule_new", 0) / len(objs),
           "points": sorted(set(feas))}
    if bounds is not None:
        lo = (LB, 0.0); hi = (bounds["res_span"], bounds["bal_max"])
        out["hv"] = hv(feas, lo, hi) if feas else 0.0
    return out


_POOL = None


def pool(procs):
    global _POOL
    if _POOL is None:
        _POOL = mp.Pool(procs)
    return _POOL


def reset_pool():
    global _POOL
    if _POOL is not None:
        _POOL.terminate(); _POOL = None


def baseline(insts, procs, cache, n=N_SAMPLES, kfrac=KFRAC):
    """默认规则在各实例上的结果，并据此确定每个实例的归一化范围。结果缓存到 cache 文件。"""
    if os.path.exists(cache):
        b = json.load(open(cache, encoding="utf-8"))
        if all(i in b for i in insts) and b.get("_n") == n and b.get("_k") == kfrac:
            return b
    res = pool(procs).map(eval_instance, [(None, i, n, kfrac, None) for i in insts], chunksize=1)
    b = {"_n": n, "_k": kfrac}
    for r in res:
        pts = r["points"]
        span = max(2.0, max(p[0] for p in pts) - r["LB"]) if pts else 4.0
        bal = max(p[1] for p in pts) if pts else 100.0
        r["res_span"], r["bal_max"] = span, bal
        lo = (r["LB"], 0.0)
        r["hv"] = hv(pts, lo, (span, bal)) if pts else 0.0
        b[r["inst"]] = {k: v for k, v in r.items() if k != "points"}
    json.dump(b, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return b


def score(src, insts, base, procs, n=N_SAMPLES, kfrac=KFRAC, timeout=None):
    """→ (总分 = 各实例 HV 均值, 各实例指标列表, 错误信息或 None)"""
    if timeout is None:
        timeout = 60 + 8 * sum(base[i]["secs"] for i in insts) / max(1, procs)
    args = [(src, i, n, kfrac, base[i]) for i in insts]
    try:
        res = pool(procs).map_async(eval_instance, args, chunksize=1).get(timeout)
    except mp.TimeoutError:
        reset_pool()
        return None, [], f"超时：评价超过 {timeout:.0f} 秒（规则太慢，或者有很大的循环）"
    errs = [r for r in res if "error" in r]
    if errs:
        return None, res, f"{errs[0]['inst']}: {errs[0]['error']}"
    for r in res:
        r.pop("points", None)
    return float(np.mean([r["hv"] for r in res])), res, None


def diagnose(res, base):
    """按组汇总，用于喂回 LLM 和打印。"""
    rows = {}
    for r in res:
        g = I.group(r["inst"])
        b = base[r["inst"]]
        d = rows.setdefault(g, {"n": 0, "hv": 0, "dhv": 0, "rule_gap": 0, "rule_bal": 0, "best_gap": 0, "feas": 0, "new": 0, "nrg": 0})
        d["n"] += 1; d["hv"] += r["hv"]; d["dhv"] += r["hv"] - b["hv"]; d["feas"] += r["feas_rate"]; d["new"] += r["rule_new_per_decode"]
        if r["rule_gap"] is not None:
            d["rule_gap"] += r["rule_gap"]; d["rule_bal"] += r["rule_bal"]; d["nrg"] += 1
        d["best_gap"] += r["best_gap"] if r["best_gap"] is not None else 9
    out = {}
    for g, d in sorted(rows.items()):
        k = d["n"]
        out[g] = {"instances": k, "score": round(d["hv"] / k, 4), "vs_default": round(d["dhv"] / k, 4),
                  "rule_only_extra_resources": round(d["rule_gap"] / d["nrg"], 2) if d["nrg"] else None,
                  "rule_only_imbalance": round(d["rule_bal"] / d["nrg"], 2) if d["nrg"] else None,
                  "rule_only_feasible_instances": f"{d['nrg']}/{k}",
                  "best_sample_extra_resources": round(d["best_gap"] / k, 2),
                  "random_genome_feasible_rate": round(d["feas"] / k, 3),
                  "rule_opens_new_while_robots_available_per_decode": round(d["new"] / k, 2)}
    return out


if __name__ == "__main__":
    # 自测：默认规则与一条示例规则在训练集上的得分
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, mp.cpu_count() - 1)
    tr, _ = I.split()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    t = time.time()
    base = baseline(tr, procs, os.path.join(HERE, "out", "baseline_train.json"))
    print("baseline", f"{time.time() - t:.0f}s", round(np.mean([base[i]["hv"] for i in tr]), 4))
    demo = '''def rule(ctx):
    # 示例：优先派下次维修前剩余班次最多的机器人
    av = sorted(ctx.available, key=lambda r: (-r.duties_left, r.count))
    return [("reuse", r) for r in av] + [("new", ctx.gene_type)]
'''
    for name, src in [("default", R.DEFAULT_RULE_SRC), ("demo", demo)]:
        t = time.time()
        s, res, err = score(src, tr, base, procs)
        print(name, s, err, f"{time.time() - t:.0f}s")
        if res:
            print(json.dumps(diagnose(res, base), ensure_ascii=False, indent=1))
    reset_pool()
