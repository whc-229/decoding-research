"""任务 B2：按实例选编码 + 好规则（沿用实验 3b 的"按随机样本最好解选"）。

候选档 = dec5、K0.25+R、K0.5+R，R 为一条 ES16（s0～s2）或 GP（run1～5）规则，每条规则算一个设计运行。
每个测试实例：用固定的 100 个均匀随机基因（种子 = sum(ord(实例名)) × 7919 + 31337，三档共用同一组基因，与 MOEA 种子无关），
各档解码，取最好的解（先比资源数，再比均衡度）；选最好的档，平局按 dec5、K0.25、K0.5 的顺序取。只用随机解码，不看任何 MOEA 结果。
方法的值 = 选中档那个臂（val_server.csv）的 5 次 MOEA 平均 HV（实例内所有臂统一归一化）。选档成本 = 300 次解码 / 实例，
同总预算对照 = dec5-765（465 + 300 次评价）。

两步：
  python select_enc.py sample [进程数]      （实验环境）→ out/select_samples.json，可续跑
  ~/miniconda3/envs/ana/bin/python select_enc.py report   （ana 环境，需 val_server.csv 里 B1 的臂跑完）→ ../../报告/实验5_B_按实例选编码.md 的表格部分 out/select_enc.md
"""
import json, multiprocessing as mp, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SAMPLES = os.path.join(OUT, "select_samples.json")
N_GENES = 100
RULES = {**{f"ES16(s{s})": f"nn:out/es/il_h16{'' if s == 0 else f'_s{s}'}/best.npz" for s in range(3)},
         **{f"GP(run{r})": f"../neural/out/gp/run{r}/best_rule.py" for r in range(1, 6)}}
TIERS = ["dec5", "K0.25", "K0.5"]


def arm_name(tier, rule):
    """档 + 规则 → val_server.csv 里的臂名"""
    return "dec5" if tier == "dec5" else f"{tier}:{rule}"


def sample_job(args):
    """一个实例、一个档（dec5 或 K+规则）：100 个随机基因里最好的解 → (实例, 键, 最好 (资源数, 均衡度) 或 None, 可行数)"""
    import common as C
    import arms as A
    inst, key, spec = args
    sc = C.I.load(inst)
    rng = np.random.default_rng(sum(map(ord, inst)) * 7919 + 31337)
    nv = C.L.nvar(sc, "dec5")
    X = [rng.uniform(0, 0.99, nv) for _ in range(N_GENES)]
    dec = A.decoder(spec)
    objs = [r.obj for r in (dec(sc, x) for x in X) if r.feasible]
    return inst, key, (min(objs) if objs else None), len(objs)


def sample(procs):
    import common as C
    te = C.I.split()[1]
    res = json.load(open(SAMPLES, encoding="utf-8")) if os.path.exists(SAMPLES) else {}
    jobs = []
    for i in te:
        if "dec5" not in res.get(i, {}):
            jobs.append((i, "dec5", "dec5"))
        for k in ("K0.25", "K0.5"):
            for rn, src in RULES.items():
                key = f"{k}:{rn}"
                if key not in res.get(i, {}):
                    jobs.append((i, key, f"{k}:{src}"))
    jobs.sort(key=lambda j: -C.L.nvar(C.I.load(j[0]), "dec5"))
    print(f"{len(jobs)} 个（实例, 档）待采样，{procs} 个进程", flush=True)
    with mp.Pool(procs) as p:
        for n, (i, key, best, nf) in enumerate(p.imap_unordered(sample_job, jobs, chunksize=1), 1):
            res.setdefault(i, {})[key] = {"best": best, "feasible": nf}
            if n % 50 == 0 or n == len(jobs):
                json.dump(res, open(SAMPLES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print(f"{n}/{len(jobs)}", flush=True)


def choose(s, rule):
    """按随机样本最好解选档：先比资源数、再比均衡度；无可行解视为最差；平局按 dec5、K0.25、K0.5"""
    cand = []
    for t, tier in enumerate(TIERS):
        b = s["dec5"]["best"] if tier == "dec5" else s[f"{tier}:{rule}"]["best"]
        cand.append(((float("inf"), float("inf")) if b is None else tuple(b), t, tier))
    return min(cand)[2]


def report():
    from scipy.stats import wilcoxon
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
    import analyze_methods as AM
    import instances as I
    S = json.load(open(SAMPLES, encoding="utf-8"))
    runs = AM.load([os.path.join(OUT, "val_server.csv")])
    arms = sorted({x for _, x in runs})
    need = ["dec5", "dec5-765"] + [arm_name(t, r) for t in ("K0.25", "K0.5") for r in RULES]
    miss = [a for a in need if a not in arms]
    assert not miss, f"val_server.csv 缺臂：{miss}"
    insts = sorted(S)
    insts = [i for i in insts if all(len(runs.get((i, a), {})) == 5 for a in arms)]
    H, _ = AM.normalize(runs, insts, arms)
    hv = lambda i, a: float(np.mean(H[(i, a)]))
    fam = {"ES16": [r for r in RULES if r.startswith("ES16")], "GP": [r for r in RULES if r.startswith("GP")]}
    # 每个实例、每条规则：选中的档与它的值
    pick = {(i, r): choose(S[i], r) for i in insts for r in RULES}
    V = {}
    for f, rs in fam.items():
        V[f"选档+{f}"] = {i: np.mean([hv(i, arm_name(pick[(i, r)], r)) for r in rs]) for i in insts}
        V[f"K0.25+{f}"] = {i: np.mean([hv(i, arm_name("K0.25", r)) for r in rs]) for i in insts}
        V[f"K0.5+{f}"] = {i: np.mean([hv(i, arm_name("K0.5", r)) for r in rs]) for i in insts}
        V[f"事后最好档+{f}"] = {i: np.mean([max(hv(i, arm_name(t, r)) for t in TIERS) for r in rs]) for i in insts}
    V["dec5"] = {i: hv(i, "dec5") for i in insts}
    V["dec5-765"] = {i: hv(i, "dec5-765") for i in insts}
    L = ["# 任务 B：按实例选编码 + 好规则（测试集）\n",
         f"{len(insts)} 个测试实例；HV 在每个实例内用 val_server.csv 的全部 {len(arms)} 个臂统一归一化。"
         "选档：每档 100 个固定随机基因的最好解（先资源数后均衡度），平局按 dec5、K0.25、K0.5。"
         "方法的值 = 选中档臂的 5 次 MOEA 平均 HV，再对同一族的规则（ES16 3 条、GP 5 条）取平均。"
         "p = 实例层面配对 Wilcoxon；Holm 校正在每个分组内对下表的全部比较（每族 4 个对照 × 2 族 = 8 个）一起做。"
         "\"事后最好档\"按 MOEA 结果挑，只作上限，不参与检验。\n"]
    for gname, grp in [("全部", insts)] + [(g + " 组", [i for i in insts if I.group(i) == g]) for g in ["原", "E", "H", "M"]]:
        if not grp:
            continue
        tests = []
        for f in fam:
            for ref in ("dec5", "dec5-765", f"K0.25+{f}", f"K0.5+{f}"):
                d = np.array([V[f"选档+{f}"][i] - V[ref][i] for i in grp])
                p = wilcoxon(d).pvalue if len(grp) > 1 and np.any(d != 0) else 1.0
                tests.append((f, ref, d.mean(), p))
        adj = AM.holm([t[3] for t in tests])
        L += [f"\n## {gname}（{len(grp)} 个实例）\n", "| 方法 | 平均 HV |", "|---|---|"]
        for m in ["dec5", "dec5-765"] + [f"{p}+{f}" for f in fam for p in ("K0.25", "K0.5", "选档", "事后最好档")]:
            L.append(f"| {m} | {np.mean([V[m][i] for i in grp]):.3f} |")
        L += ["\n| 选档方法 | 对照 | 平均差 | p | Holm p |", "|---|---|---|---|---|"]
        for (f, ref, dm, p), pa in zip(tests, adj):
            L.append(f"| 选档+{f} | {ref} | {dm:+.3f} | {p:.3g} | {pa:.3g}{'*' if pa < 0.05 else ''} |")
        L += ["\n各档被选中的比例（该组实例 × 该族规则）：\n", "| 族 | dec5 | K0.25 | K0.5 |", "|---|---|---|---|"]
        for f, rs in fam.items():
            c = [pick[(i, r)] for i in grp for r in rs]
            L.append(f"| {f} | " + " | ".join(f"{c.count(t) / len(c):.2f}" for t in TIERS) + " |")
    # 选对了吗：选中档与事后最好档一致的比例
    L += ["\n## 选中档与事后最好档（按 MOEA 平均 HV）一致的比例\n", "| 族 | 全部 | 原 | E | H | M |", "|---|---|---|---|---|---|"]
    for f, rs in fam.items():
        row = []
        for g in [None, "原", "E", "H", "M"]:
            grp = [i for i in insts if g is None or I.group(i) == g]
            ok = [pick[(i, r)] == max(TIERS, key=lambda t: (hv(i, arm_name(t, r)), -TIERS.index(t))) for i in grp for r in rs]
            row.append(f"{np.mean(ok):.2f}")
        L.append(f"| {f} | " + " | ".join(row) + " |")
    open(os.path.join(OUT, "select_enc.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({f"{i}|{r}": t for (i, r), t in pick.items()}, open(os.path.join(OUT, "select_pick.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    mp.freeze_support()
    if sys.argv[1] == "sample":
        sample(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    else:
        report()
