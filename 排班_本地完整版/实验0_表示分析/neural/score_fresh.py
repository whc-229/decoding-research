"""换基因复核：代理分在"选规则时用过的基因"上有乐观偏差（ES / GP 按这批基因挑最好的，LLM 规则生成也是）。
这里在 15 个训练实例上换 3 批新的随机基因重打分，与原基因上的分数比较。

基因生成方式与 evalrule.genomes 完全相同（3 个不偏离基因 + 64 个随机基因），只换随机种子：
  第 0 批 = 原基因（种子 sum(ord(实例名)) × 7919，与 evalrule.genomes 逐位相同，脚本里核对）
  第 b 批（b = 1, 2, 3）种子 = sum(ord(实例名)) × 7919 + 104729 × b
归一化范围仍用 rulegen/out/baseline_train.json（默认规则在原基因上的结果），所以各批分数在同一把尺子上。
乐观偏差 = 原基因分 − 3 批新基因分的平均。默认规则在原基因上就比新基因低（原基因偏难），所以另报
相对默认的乐观偏差 = (原 − 默认原) − (新平均 − 默认新平均)，即"对默认的领先幅度"在换基因后缩水多少。

用法: python score_fresh.py [进程数|auto]
输出: out/fresh_scores.json（每条规则 × 每批 × 每个实例的 HV）、out/fresh_scores.md（汇总表）
"""
import json, multiprocessing as mp, os, sys, time
import numpy as np
import common as C
import evalrule as E
import proxy as PX
import score_rules as SR

BATCHES = [0, 1, 2, 3]
RULES = (["默认=K0.25:default", "LLM(r47)=K0.25:out/full/best_rule.py", "LLM(r35)=K0.25:out/score/best_rule.py"]
         + [f"IL16(s{s})=K0.25:nn:out/nn_il_h16{'' if s == 0 else f'_s{s}'}.npz" for s in range(5)]
         + [f"IL32-16(s{s})=K0.25:nn:out/nn_il{'' if s == 0 else f'_s{s}'}.npz" for s in range(5)]
         + [f"ES16(s{s})=K0.25:nn:out/es/il_h16{'' if s == 0 else f'_s{s}'}/best.npz" for s in range(3)]
         + [f"GP(run{r})=K0.25:../neural/out/gp/run{r}/best_rule.py" for r in range(1, 6)])
OUTJ = os.path.join(C.OUT, "fresh_scores.json")
OUTM = os.path.join(C.OUT, "fresh_scores.md")


def genomes(inst, b, n=E.N_SAMPLES, kfrac=E.KFRAC):
    """与 evalrule.genomes 相同的生成方式，第 b 批换种子（b = 0 即原基因）"""
    sc = C.I.load(inst)
    nv = C.L.nvar(sc, "dec5")
    K, _ = C.R.n_slots(sc, kfrac)
    rng = np.random.default_rng(sum(map(ord, inst)) * 7919 + 104729 * b)
    X = []
    for g in (0.1, 0.5, 0.9):
        x = rng.random(nv); x[1:2 * K:2] = 0.0; x[2 * K] = g
        X.append(x)
    X += [rng.random(nv) for _ in range(n)]
    return X


def job(args):
    """一条规则在一个实例、一批基因上的 HV（规则出错 → 0 分，与 proxy 相同）"""
    name, spec, inst, b = args
    rule = SR.picklable(spec)
    sc = C.I.load(inst)
    base = PX.BASE[inst]
    objs, err = [], None
    try:
        for x in genomes(inst, b):
            r = C.R.decode_rule(sc, x, rule, E.KFRAC)
            if r.obj:
                objs.append(r.obj)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"; objs = []
    hv = E.hv(objs, (base["LB"], 0.0), (base["res_span"], base["bal_max"])) if objs else 0.0
    return name, inst, b, hv, err


def main():
    procs = C.nprocs(sys.argv[1] if len(sys.argv) > 1 else "auto")
    tr = C.I.split()[0]
    for inst in tr:                                   # 第 0 批必须与 evalrule.genomes 逐位相同
        assert all(np.array_equal(a, b) for a, b in zip(genomes(inst, 0), E.genomes(inst))), inst
    specs = [SR.A.parse(s) for s in RULES]
    for _, s in specs:                                # 先检查文件都在、能加载
        SR.picklable(s)
    res = json.load(open(OUTJ, encoding="utf-8")) if os.path.exists(OUTJ) else {}
    order = sorted(tr, key=lambda i: -PX.BASE[i]["secs"])
    jobs = [(n, s, i, b) for b in BATCHES for i in order for n, s in specs if str(b) not in res.get(n, {}).get(i, {})]
    print(f"{len(specs)} 条规则 × {len(BATCHES)} 批 × {len(tr)} 个实例，待算 {len(jobs)}，{procs} 个进程", flush=True)
    t0 = time.time()
    if jobs:
        with mp.Pool(procs) as p:
            for k, (n, i, b, hv, err) in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
                res.setdefault(n, {}).setdefault(i, {})[str(b)] = hv
                if err:
                    res[n].setdefault("_err", []).append(f"{i}/{b}: {err}")
                if k % 50 == 0 or k == len(jobs):
                    json.dump(res, open(OUTJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                    print(f"{k}/{len(jobs)}  {(time.time() - t0) / 60:.1f} 分钟", flush=True)
    report(res, specs, tr)


def report(res, specs, tr):
    """汇总表：每条规则的原基因分、3 批新基因分、新基因平均、乐观偏差；再按方法汇总"""
    base_new = {b: np.mean([res["默认"][i][str(b)] for i in tr]) for b in BATCHES}
    rows, out = {}, []
    for n, _ in specs:
        s = {b: float(np.mean([res[n][i][str(b)] for i in tr])) for b in BATCHES}
        fresh = float(np.mean([s[b] for b in BATCHES[1:]]))
        rows[n] = (s, fresh)
    out += ["# 换基因复核：代理分的乐观偏差（15 个训练实例）\n",
            "原 = 选规则时用过的 67 个基因（evalrule.genomes）；新1～新3 = 同样生成方式、换随机种子的 3 批新基因；"
            "归一化范围不变（baseline_train.json）。乐观偏差 = 原 − 新基因平均。"
            "\"新平均对默认\" = 新基因平均 − 默认规则在同 3 批新基因上的平均。"
            "相对默认的乐观偏差 = (原 − 默认原) − (新平均 − 默认新平均)：默认规则在原基因上就偏低（原基因偏难），这一列扣掉了这部分。\n",
            "| 规则 | 原 | 新1 | 新2 | 新3 | 新平均 | 乐观偏差 | 原对默认 | 新平均对默认 | 相对默认的乐观偏差 | 出错 |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    dfresh, dorig = rows["默认"][1], rows["默认"][0][0]
    for n, _ in specs:
        s, fresh = rows[n]
        ne = len(res[n].get("_err", []))
        out.append(f"| {n} | {s[0]:.4f} | {s[1]:.4f} | {s[2]:.4f} | {s[3]:.4f} | {fresh:.4f} | {s[0] - fresh:+.4f} | "
                   f"{s[0] - dorig:+.4f} | {fresh - dfresh:+.4f} | {(s[0] - dorig) - (fresh - dfresh):+.4f} | {ne} |")
    out += ["\n## 按方法汇总（各设计运行的平均；括号内为最小～最大）\n",
            "| 方法 | 运行数 | 原 | 新平均 | 乐观偏差 | 相对默认的乐观偏差 |", "|---|---|---|---|---|---|"]
    meth = {}
    for n, _ in specs:
        meth.setdefault(n.split("(")[0] if not n.startswith("LLM") else n, []).append(n)
    for m, ns in meth.items():
        o = [rows[n][0][0] for n in ns]; f = [rows[n][1] for n in ns]; d = [a - b for a, b in zip(o, f)]
        rg = lambda v: f"{np.mean(v):.4f}" + (f"（{min(v):.4f}～{max(v):.4f}）" if len(v) > 1 else "")
        rd = [(a - dorig) - (b - dfresh) for a, b in zip(o, f)]
        out.append(f"| {m} | {len(ns)} | {rg(o)} | {rg(f)} | {np.mean(d):+.4f} | {np.mean(rd):+.4f} |")
    out.append(f"\n默认规则各批：" + "、".join(f"{'原' if b == 0 else f'新{b}'} {base_new[b]:.4f}" for b in BATCHES))
    open(OUTM, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
