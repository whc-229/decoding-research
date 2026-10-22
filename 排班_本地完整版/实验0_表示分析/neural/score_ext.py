"""任务 D2（代理分部分）：扩展布局下每个 K 的代理分（15 个训练实例 × 67 个基因，归一化范围仍用 rulegen/out/baseline_train.json）。
基因生成方式与 evalrule.genomes 相同（种子 sum(ord(实例名)) × 7919；3 个不偏离基因：偏离槽的 a 全为 0、默认类型基因取 0.1 / 0.5 / 0.9；
再加 64 个均匀随机基因），只是长度换成扩展布局 ruledec_ext.nvar(实例, K)。
用法: python score_ext.py [进程数]   输出: out/score_ext.json、out/score_ext.md
"""
import json, multiprocessing as mp, os, sys
import numpy as np
import common as C
import evalrule as E
import proxy as PX
import score_rules as SR
import ruledec_ext as X

KS = [0.25, 0.5, 0.75, 1.0]
RULES = {**{f"ES16(s{s})": f"K0.25:nn:out/es/il_h16{'' if s == 0 else f'_s{s}'}/best.npz" for s in range(3)},
         **{f"GP(run{r})": f"K0.25:../neural/out/gp/run{r}/best_rule.py" for r in range(1, 6)}}
OUTJ = os.path.join(C.OUT, "score_ext.json")


def genomes(inst, kf, n=E.N_SAMPLES):
    """扩展布局的代理分基因（见文件说明）"""
    sc = C.I.load(inst)
    nv = X.nvar(sc, kf)
    K, _ = C.R.n_slots(sc, kf)
    rng = np.random.default_rng(sum(map(ord, inst)) * 7919)
    out = []
    for g in (0.1, 0.5, 0.9):
        x = rng.random(nv); x[1:2 * K:2] = 0.0; x[2 * K] = g
        out.append(x)
    return out + [rng.random(nv) for _ in range(n)]


def job(args):
    """一条规则、一个 K、一个实例 → HV"""
    name, spec, kf, inst = args
    rule = SR.picklable(spec)
    sc = C.I.load(inst)
    b = PX.BASE[inst]
    objs = [r.obj for r in (X.decode_rule(sc, x, rule, kf) for x in genomes(inst, kf)) if r.obj]
    hv = E.hv(objs, (b["LB"], 0.0), (b["res_span"], b["bal_max"])) if objs else 0.0
    return name, kf, inst, hv


def main():
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    tr = C.I.split()[0]
    res = json.load(open(OUTJ, encoding="utf-8")) if os.path.exists(OUTJ) else {}
    jobs = [(n, s, k, i) for k in KS for n, s in RULES.items() for i in sorted(tr, key=lambda i: -PX.BASE[i]["secs"])
            if i not in res.get(f"{n}|{k}", {})]
    print(f"{len(jobs)} 个（规则, K, 实例）待算，{procs} 个进程", flush=True)
    with mp.Pool(procs) as p:
        for t, (n, k, i, hv) in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            res.setdefault(f"{n}|{k}", {})[i] = hv
            if t % 30 == 0 or t == len(jobs):
                json.dump(res, open(OUTJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    L = ["# 扩展布局下各 K 的代理分（15 个训练实例 × 67 个基因）\n", "| 规则 | " + " | ".join(f"X{k}" for k in KS) + " |", "|---|" + "---|" * len(KS)]
    for n in RULES:
        L.append(f"| {n} | " + " | ".join(f"{np.mean(list(res[f'{n}|{k}'].values())):.4f}" for k in KS) + " |")
    for fam, ns in [("ES16 平均", [n for n in RULES if n.startswith("ES16")]), ("GP 平均", [n for n in RULES if n.startswith("GP")]), ("8 条合并", list(RULES))]:
        L.append(f"| **{fam}** | " + " | ".join(f"{np.mean([np.mean(list(res[f'{n}|{k}'].values())) for n in ns]):.4f}" for k in KS) + " |")
    open(os.path.join(C.OUT, "score_ext.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
