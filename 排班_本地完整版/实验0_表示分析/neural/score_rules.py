"""代理分对照表：任意规则（臂写法见 arms.py，可写"显示名=写法"）在 15 个训练实例 × 67 个基因上的代理分，
与默认规则（0.7630）、LLM 规则 r47（full 反馈，0.8234）、r35（score 反馈，0.8191）放在同一张表里。
结果缓存在 out/proxy_scores.json（按写法 + 文件修改时间），重复调用不重算。
用法: python score_rules.py 臂[,臂...] [进程数|auto]
"""
import json, multiprocessing as mp, os, sys, time
import numpy as np
import common as C
import arms as A
import proxy as PX
import gp as GP

CACHE = os.path.join(C.OUT, "proxy_scores.json")
REF = ["默认=K0.25:default", "LLM(r47)=K0.25:out/full/best_rule.py", "LLM(r35)=K0.25:out/score/best_rule.py"]


def stamp(spec):
    """写法 → 缓存键（含规则文件的修改时间，文件改了会重算）"""
    src = spec.split(":", 1)[1]
    if src == "default":
        return spec
    p = src[3:] if src.startswith("nn:") else src
    base = C.HERE if src.startswith("nn:") else C.RULEGEN
    p = p if os.path.isabs(p) else os.path.join(base, p)
    return f"{spec}@{os.path.getmtime(p):.0f}"


def picklable(spec):
    """规则文件 → 可 pickle 的 SrcRule（compile_rule 编出的函数不能传给工作进程）；网络规则、默认规则原样"""
    src = spec.split(":", 1)[1]
    if src == "default" or src.startswith("nn:"):
        return A.rule_of(spec)
    p = src if os.path.isabs(src) else os.path.join(C.RULEGEN, src)
    return GP.SrcRule(open(p, encoding="utf-8").read())


def main():
    extra = [s for s in sys.argv[1].split(",") if s] if len(sys.argv) > 1 else []
    specs = [A.parse(s) for s in REF + extra]
    procs = C.nprocs(sys.argv[2] if len(sys.argv) > 2 else "auto")
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [(n, s) for n, s in specs if stamp(s) not in cache]
    if todo:
        with mp.Pool(procs) as pool:
            for n, s in todo:
                t = time.time()
                sc, res = PX.score(picklable(s), pool=pool)
                cache[stamp(s)] = {"score": sc, "secs": time.time() - t, "per_inst": {r["inst"]: r["hv"] for r in res},
                                   "errors": [r["err"] for r in res if r["err"]]}
                json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print(f"  {n}: {sc:.4f}（{time.time() - t:.0f}s）", flush=True)
    base = {k: v["hv"] for k, v in PX.BASE.items() if not k.startswith("_")}
    print("| 规则 | 代理分 | 对默认 | E 组 | H 组 | M 组 | 出错 |\n|---|---|---|---|---|---|---|")
    for n, s in specs:
        c = cache[stamp(s)]
        d = {g: np.mean([c["per_inst"][i] - base[i] for i in base if i[0] == g]) for g in "EHM"}
        print(f"| {n} | {c['score']:.4f} | {c['score'] - np.mean(list(base.values())):+.4f} | {d['E']:+.3f} | {d['H']:+.3f} | "
              f"{d['M']:+.3f} | {len(c['errors'])} |")


if __name__ == "__main__":
    main()
