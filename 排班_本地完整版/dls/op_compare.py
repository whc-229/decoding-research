"""算子对比（单解爬山，同评价预算）：从 MOEA 得到的最少资源解出发，只接受"资源数不增、均衡度变小"的新解
  PM-0.15  : 多项式变异，每个基因变异概率 0.15（与现有 MOEA 设置相同）
  PM-1/n   : 多项式变异，每个基因变异概率 1/n
  DLS      : 决策层单点改动——解码后随机挑一个"有其他可用机器人"的班次，改派成另一台可用机器人
             （把该班的基因写成目标机器人在可用列表中的位置；其余基因不动，后续班次照常解码）
评价用 mirror.py（与 C++ 逐解一致），解码 = 排序 + 容量预判（ρ=1）
用法: python dls/op_compare.py 预算 每个起点重复次数
"""
import glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exact"))
import mirror as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TH, UB = M.THETA, 0.99


def ev(sc, x):
    o, sim = M.evaluate_genes(sc, x, True, 0.0)
    return (None if o is None else (float(o[0]), float(o[1]))), sim


def trace(sc, x):
    """返回每班的可用机器人数与所选下标（仅复用班次）"""
    x32 = np.asarray(x, np.float32).astype(np.float64)
    s = M.Sim(sc, True); n = len(x); out = []
    i = 0
    rc = M.rep_ceil_factory(sc)
    while s.E < sc["T"] and i < n // 2:
        av = s.available()
        k = M.decode_robot_select(x32[i], len(av), len(sc["R"]))
        if av and k >= len(av):
            cap = sum(M.robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots)
            if cap + 1e-9 >= 1.0 * (sc["T"] - s.E):
                u = (x32[i] - TH) / (1 - TH); k = min(max(int(max(u, 0) * len(av)), 0), len(av) - 1)
        out.append((len(av), k))
        if k < len(av):
            s.dispatch_reuse(av[k], x32[i + n // 2])
        else:
            s.dispatch_new(k - len(av), x32[i + n // 2])
        i += 1
    return out


def pm(x, rng, pmut, eta=20.0):
    y = x.copy()
    for j in np.nonzero(rng.random(len(x)) < pmut)[0]:
        u = rng.random(); d1 = (y[j] - 0) / UB; d2 = (UB - y[j]) / UB
        if u < 0.5:
            dq = (2 * u + (1 - 2 * u) * (1 - d1) ** (eta + 1)) ** (1 / (eta + 1)) - 1
        else:
            dq = 1 - (2 * (1 - u) + 2 * (u - 0.5) * (1 - d2) ** (eta + 1)) ** (1 / (eta + 1))
        y[j] = min(max(y[j] + dq * UB, 0.0), UB)
    return y


def better(a, b):
    return a is not None and a[0] <= b[0] and (a[0] < b[0] or a[1] < b[1] - 1e-9)


def run(sc, x0, op, budget, rng):
    x = np.asarray(x0, float).copy(); f, _ = ev(sc, x)
    hist = []
    for t in range(budget):
        if op == "DLS":
            tr = trace(sc, x)
            cand = [i for i, (na, k) in enumerate(tr) if na >= 2 and k < na]
            if not cand:
                break
            i = cand[rng.integers(len(cand))]
            na, k = tr[i]
            k2 = rng.choice([j for j in range(na) if j != k])
            y = x.copy(); y[i] = (k2 + 0.5) / na * TH
        else:
            y = pm(x, rng, 0.15 if op == "PM-0.15" else 1.0 / len(x))
        g, _ = ev(sc, y)
        if better(g, f):
            x, f = y, g
        hist.append(f[1])
    return f, hist


if __name__ == "__main__":
    budget, reps = int(sys.argv[1]), int(sys.argv[2])
    rng = np.random.default_rng(7)
    rows = []
    for fn in sorted(glob.glob(os.path.join(HERE, "dls", "start_*.json"))):
        scen = os.path.basename(fn)[6:].rsplit("_", 1)[0]
        sc = M.load_scenario(os.path.join(HERE, "requests", scen + ".json"))
        r = json.load(open(fn))
        objs = [tuple(o) for o in r["pareto_objs"]]
        lvl = min(o[0] for o in objs)
        j = min((i for i, o in enumerate(objs) if o[0] == lvl), key=lambda i: objs[i][1])
        x0 = r["pareto_vars"][j]
        f0, _ = ev(sc, x0)
        for op in ["PM-0.15", "PM-1/n", "DLS"]:
            for k in range(reps):
                f, h = run(sc, x0, op, budget, rng)
                rows.append(dict(scen=scen, start=os.path.basename(fn), op=op, f0=f0, f=f,
                                 h50=h[min(49, len(h) - 1)] if h else f[1]))
        print(os.path.basename(fn), "起点", f0, " | ", "  ".join(
            f"{op}: {np.mean([q['f'][1] for q in rows if q['start']==os.path.basename(fn) and q['op']==op]):.2f}"
            for op in ["PM-0.15", "PM-1/n", "DLS"]), flush=True)
    json.dump(rows, open(os.path.join(HERE, "dls", f"op_compare_{budget}.json"), "w"), ensure_ascii=False)
    print("\n平均（各起点的均衡度改进量，越大越好；括号内为 50 次评价时）")
    for op in ["PM-0.15", "PM-1/n", "DLS"]:
        g = [q["f0"][1] - q["f"][1] for q in rows if q["op"] == op and q["f"][0] == q["f0"][0]]
        g50 = [q["f0"][1] - q["h50"] for q in rows if q["op"] == op]
        lv = sum(q["f"][0] < q["f0"][0] for q in rows if q["op"] == op)
        print(f"  {op:8s}: 均衡度改进 {np.mean(g):.2f}（{np.mean(g50):.2f}）；资源数下降的次数 {lv}")
