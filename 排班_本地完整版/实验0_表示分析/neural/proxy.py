"""与 rulegen/evalrule.py 完全相同的代理打分，但规则可以是任意可调用对象（神经网络、GP 树），不经过 compile_rule。
打分 = 15 个训练实例上，固定的 3 个不偏离基因 + 64 个随机基因解码结果的归一化 HV 均值；
归一化范围取自 rulegen/out/baseline_train.json（默认规则），所以分数与 LLM 规则的分数可直接比较。
gene_idx：只用部分随机基因（ES / GP 训练时每代换一批，省时间）；None = 全部 67 个。
"""
import json, os, time
import numpy as np
import common as C
import evalrule as E

BASE = json.load(open(os.path.join(C.RULEGEN, "out", "baseline_train.json"), encoding="utf-8"))
_GEN = {}


def genomes(inst):
    if inst not in _GEN:
        _GEN[inst] = E.genomes(inst)
    return _GEN[inst]


def eval_instance(args):
    rule, inst, gene_idx = args
    sc = C.I.load(inst)
    X = genomes(inst)
    idx = range(len(X)) if gene_idx is None else sorted(set([0, 1, 2]) | set(int(i) + 3 for i in gene_idx))
    b = BASE[inst]
    objs, t, err = [], time.time(), None
    try:
        for k in idx:
            r = C.R.decode_rule(sc, X[k], rule, E.KFRAC)
            if r.obj:
                objs.append(r.obj)
    except Exception as e:     # 规则出错 → 该实例 0 分
        err = f"{type(e).__name__}: {e}"
        objs = []
    lo, hi = (b["LB"], 0.0), (b["res_span"], b["bal_max"])
    hv = E.hv(objs, lo, hi) if objs else 0.0
    rule_objs = [o for o in objs[:3]]
    return {"inst": inst, "hv": hv, "secs": time.time() - t, "n": len(idx), "feas": len(objs), "err": err,
            "dhv": hv - b["hv"]}


def score(rule, insts=None, pool=None, gene_idx=None):
    """→ (平均 HV, 各实例结果列表)。pool 为 multiprocessing.Pool 或 None（单进程）。"""
    if insts is None:
        insts = C.I.split()[0]
    args = [(rule, i, gene_idx) for i in insts]
    res = pool.map(eval_instance, args, chunksize=1) if pool is not None else [eval_instance(a) for a in args]
    return float(np.mean([r["hv"] for r in res])), res
