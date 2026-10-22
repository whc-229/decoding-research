"""R0-3 判定与 R0-4 的表（ana 环境；在跑 R0-2 之前写好并用假数据测试过：python r0_choose.py selftest）。
  ~/miniconda3/envs/ana/bin/python r0_choose.py [--kext out/train_Kext.csv] [--q out/train_q.csv] [--dev out/train_q_dev.csv,out/train_q04_dev.csv] [--out out/r0_choose]
判定规则（2026-10-23 事先写死，不看测试集）：
  数据 = train_Kext.csv 的 X0.5、X0.75、X1.0（q = 0.4）+ train_q.csv 的 X1.0q0.6、X1.0q0.8、X0.5q0.8，各 × 8 条规则 × 5 次，15 个训练实例；
  每个实例内这 6 × 8 个臂统一归一化 HV；方法层面 = 每个实例上对 8 条规则 × 5 次取平均。
  最终方法在 κ = 1.0 的 q ∈ {0.4, 0.6, 0.8} 中按合并（8 条规则）的训练平均 HV 选；
  若最高者不是 q = 0.4，且它与 q = 0.4 的实例层面配对 Wilcoxon（15 个实例）p < 0.05，最终方法改为 (κ = 1.0, 该 q)；否则保留 q = 0.4。
另报（不影响判定）：
  - 以 q·κ 为横轴的训练 HV 曲线（全部与 E/H/M，ES16 / GP 两族）；
  - 下降段（事先定义）：κ = 1.0 一线上 q·κ 最大处（q = 0.8）的 HV 低于该线最高点，且两者配对 Wilcoxon p < 0.05；
  - q·κ 不变量：κ = 0.5、q = 0.8 与 κ = 1.0、q = 0.4（q·κ 都是 0.4）的差、好/差实例数、配对 Wilcoxon；
  - 最好解实际用到的偏离数（moea_q.py 的 _dev.csv）：n_dev / 班次数、n_dev / 槽数（对照 FJSP 的 P1：≈ q）。
输出：<out>.md、<out>.json（{"final": {"kappa": 1.0, "q": …}, "changed": …}）
"""
import argparse, csv, json, os, sys, tempfile
import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import analyze_methods as AM  # noqa: E402
import instances as I  # noqa: E402

FAM = {"ES16": [f"ES16(s{s})" for s in range(3)], "GP": [f"GP(run{r})" for r in range(1, 6)]}
ALL = FAM["ES16"] + FAM["GP"]
# (κ, q) → 臂名前缀；q = 0.4 的臂沿用 train_Kext.csv 的名字
SETS = {(0.5, 0.4): "X0.5", (0.75, 0.4): "X0.75", (1.0, 0.4): "X1.0", (1.0, 0.6): "X1.0q0.6", (1.0, 0.8): "X1.0q0.8", (0.5, 0.8): "X0.5q0.8"}
K1 = [(1.0, 0.4), (1.0, 0.6), (1.0, 0.8)]


def wil(d):
    """配对 Wilcoxon 的 p（差全为 0 时记 1）"""
    d = np.asarray(d)
    return float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0


def decide(V, insts):
    """事先写死的判定：V[(κ, q)][实例] = 合并 8 条规则的方法层面 HV → (最终 (κ, q), 是否改变, 最高者, p)"""
    mean = {s: float(np.mean([V[s][i] for i in insts])) for s in K1}
    best = max(K1, key=lambda s: mean[s])
    if best == (1.0, 0.4):
        return (1.0, 0.4), False, best, 1.0
    p = wil([V[best][i] - V[(1.0, 0.4)][i] for i in insts])
    return (best if p < 0.05 else (1.0, 0.4)), p < 0.05, best, p


def analyze(kext, qpath, devpaths, outp):
    """读数据、归一化、判定、写表 → 结果字典"""
    runs = AM.load([kext, qpath])
    need = [f"{SETS[s]}:{r}" for s in SETS for r in ALL]
    arms = {a for _, a in runs}
    miss = [a for a in need if a not in arms]
    assert not miss, f"缺臂：{miss[:5]}…（共 {len(miss)}）"
    insts = sorted({i for i, _ in runs})
    insts = [i for i in insts if all(len(runs.get((i, a), {})) == 5 for a in need)]
    assert len(insts) == 15, f"完整的训练实例只有 {len(insts)} 个"
    H, _ = AM.normalize(runs, insts, need)
    V = {}
    for f, rs in list(FAM.items()) + [("合并", ALL)]:
        for s in SETS:
            V[(f, s)] = {i: float(np.mean([np.mean(H[(i, f"{SETS[s]}:{r}")]) for r in rs])) for i in insts}
    VC = {s: V[("合并", s)] for s in SETS}
    final, changed, best, p = decide(VC, insts)
    mean = lambda f, s, grp=None: float(np.mean([V[(f, s)][i] for i in (grp or insts)]))
    order = sorted(SETS, key=lambda s: (s[0] * s[1], s[0]))
    L = [f"# R0：排班偏离率扫描（{len(insts)} 个训练实例，NSGA-II 465 次，种子 5000+次号，8 条规则 × 5 次）\n",
         "判定规则（事先写死）：κ = 1.0 的 q ∈ {0.4, 0.6, 0.8} 中合并训练平均 HV 最高者；若不是 q = 0.4 且与 q = 0.4 的配对 Wilcoxon p < 0.05 才改，否则保留 q = 0.4。\n",
         f"**结果：κ = 1.0 一线最高的是 q = {best[1]}**" + ("" if best == (1.0, 0.4) else f"（对 q = 0.4 配对 Wilcoxon p = {p:.3g}）")
         + f"；**最终方法 {'改为' if changed else '保留'} κ = {final[0]}、q = {final[1]}**"
         + ("，需要补跑测试集臂（R0-3）。" if changed else "，不跑测试集。") + "\n",
         "## 训练 HV 随 q·κ（合并 8 条规则；每实例内 6 × 8 个臂统一归一化）\n",
         "| q·κ | κ | q | 全部 | E | H | M | ES16 | GP |", "|---|---|---|---|---|---|---|---|---|"]
    grp = {g: [i for i in insts if I.group(i) == g] for g in "EHM"}
    for s in order:
        L.append(f"| {s[0] * s[1]:.2f} | {s[0]} | {s[1]} | {mean('合并', s):.4f} | " + " | ".join(f"{mean('合并', s, grp[g]):.4f}" for g in "EHM")
                 + f" | {mean('ES16', s):.4f} | {mean('GP', s):.4f} |")
    # 下降段
    top = max(K1, key=lambda s: mean("合并", s))
    drop = {}
    for name, gi in [("全部", insts)] + [(g, grp[g]) for g in "EHM"]:
        t = max(K1, key=lambda s: mean("合并", s, gi))
        d = [VC[(1.0, 0.8)][i] - VC[t][i] for i in gi]
        pp = wil(d) if t != (1.0, 0.8) and len(gi) > 1 else 1.0
        drop[name] = {"top_q": t[1], "diff": float(np.mean(d)), "p": pp, "drop": bool(t != (1.0, 0.8) and pp < 0.05)}
    L += ["\n## 下降段（κ = 1.0 一线：q = 0.8 对该线最高点）\n", "| 组 | 该线最高 | q0.8 − 最高 | 配对 Wilcoxon p | 下降段 |", "|---|---|---|---|---|"]
    for name, r in drop.items():
        L.append(f"| {name} | q = {r['top_q']} | {r['diff']:+.4f} | {r['p']:.3g} | {'是' if r['drop'] else '否'} |")
    # 两两比较
    pairs = [((1.0, 0.6), (1.0, 0.4)), ((1.0, 0.8), (1.0, 0.4)), ((1.0, 0.8), (1.0, 0.6)), ((0.5, 0.8), (1.0, 0.4)), ((0.5, 0.8), (0.5, 0.4))]
    L += ["\n## 配对比较（合并，实例层面）\n", "| 比较 | 平均差 | 好/差实例数 | Wilcoxon p |", "|---|---|---|---|"]
    tests = {}
    for a, b in pairs:
        d = np.array([VC[a][i] - VC[b][i] for i in insts])
        tests[f"{a}-{b}"] = (float(d.mean()), int((d > 0).sum()), int((d < 0).sum()), wil(d))
        L.append(f"| κ{a[0]} q{a[1]} − κ{b[0]} q{b[1]} | {d.mean():+.4f} | {(d > 0).sum()}/{(d < 0).sum()} | {wil(d):.3g} |")
    L.append("\nq·κ 不变量看第 4 行（κ0.5 q0.8 与 κ1.0 q0.4，q·κ 都是 0.4）。")
    # 偏离数
    dv = {}
    for pth in devpaths:
        if os.path.exists(pth):
            for r in csv.DictReader(open(pth, encoding="utf-8")):
                dv[(r["scenario"], r["variant"], r["run"], r["res"], r["bal"])] = r     # 按前沿点去重
    if dv:
        L += ["\n## 前沿解实际用到的偏离数（每次运行先对前沿点平均，再对次、规则、实例平均）\n",
              "| κ | q | q·κ | 偏离数 / 班次数 | 偏离数 / 槽数 | 生效槽 / 槽数 | 运行数 |", "|---|---|---|---|---|---|---|"]
        for s in order:
            per = {}
            for (inst, var, run, _, _), r in dv.items():
                if var.split(":", 1)[0] == SETS[s] and inst in insts:
                    per.setdefault((inst, var, run), []).append((int(r["n_dev"]) / int(r["n_shift"]), int(r["n_dev"]) / int(r["n_slot"]), int(r["n_on"]) / int(r["n_slot"])))
            if not per:
                L.append(f"| {s[0]} | {s[1]} | {s[0] * s[1]:.2f} | — | — | — | 0 |"); continue
            m = np.mean([np.mean(v, axis=0) for v in per.values()], axis=0)
            L.append(f"| {s[0]} | {s[1]} | {s[0] * s[1]:.2f} | {m[0]:.3f} | {m[1]:.3f} | {m[2]:.3f} | {len(per)} |")
    res = {"final": {"kappa": final[0], "q": final[1]}, "changed": bool(changed), "best_k1": best[1], "p_best_vs_q04": p,
           "means": {f"{s[0]}|{s[1]}": mean("合并", s) for s in SETS}, "drop": drop, "tests": tests}
    open(outp + ".md", "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(res, open(outp + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return res, L


def selftest():
    """假数据测试：三种情形，判定结果必须与构造一致"""
    insts = I.split()[0]
    assert len(insts) == 15
    HEAD = ["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"]

    def make(effect, d, seed):
        """effect[(κ, q)] = 该组均衡度的平均改善量（越大越好）→ 写两份假 CSV，返回路径"""
        rng = np.random.default_rng(seed)
        pk, pq = os.path.join(d, "kext.csv"), os.path.join(d, "q.csv")
        with open(pk, "w", newline="", encoding="utf-8") as fk, open(pq, "w", newline="", encoding="utf-8") as fq:
            wk, wq = csv.writer(fk), csv.writer(fq); wk.writerow(HEAD); wq.writerow(HEAD)
            for i in insts:
                base = 10 + rng.random() * 5
                for s, pre in SETS.items():
                    for r in ALL:
                        for k in range(5):
                            b1 = base - effect[s] + rng.normal(0, 0.3)
                            row = [i, f"{pre}:{r}", k, 1.0, 465, 100, f"10:{b1 + 2:.3f};11:{b1:.3f}"]
                            (wk if s[1] == 0.4 else wq).writerow(row)
        return pk, pq
    cases = [("q0.8 明显最好 → 改为 q0.8", {(0.5, 0.4): 0, (0.75, 0.4): .3, (1.0, 0.4): .5, (1.0, 0.6): .8, (1.0, 0.8): 1.2, (0.5, 0.8): .5}, (1.0, 0.8), True),
             ("q0.6 略高但不显著 → 保留 q0.4", {(0.5, 0.4): 0, (0.75, 0.4): .3, (1.0, 0.4): .5, (1.0, 0.6): .51, (1.0, 0.8): .2, (0.5, 0.8): .5}, (1.0, 0.4), False),
             ("q0.4 最好、q0.8 下降 → 保留，且有下降段", {(0.5, 0.4): 0, (0.75, 0.4): .3, (1.0, 0.4): .8, (1.0, 0.6): .5, (1.0, 0.8): .1, (0.5, 0.8): .8}, (1.0, 0.4), False)]
    ok = True
    for name, eff, want, ch in cases:
        with tempfile.TemporaryDirectory() as d:
            pk, pq = make(eff, d, 1)
            res, _ = analyze(pk, pq, [], os.path.join(d, "r"))
        got = (res["final"]["kappa"], res["final"]["q"])
        good = got == want and res["changed"] == ch
        if name.startswith("q0.4 最好"):
            good = good and res["drop"]["全部"]["drop"]
            # q·κ 不变量：构造中 κ0.5q0.8 与 κ1.0q0.4 相同 → 差应接近 0
            good = good and abs(res["tests"][f"{(0.5, 0.8)}-{(1.0, 0.4)}"][0]) < 0.02
        ok &= good
        print(f"{'通过' if good else '失败'}：{name}；判定 {got}，changed={res['changed']}，κ1 线最高 q={res['best_k1']}，p={res['p_best_vs_q04']:.3g}，下降段={res['drop']['全部']['drop']}")
    print("假数据测试", "全部通过" if ok else "有失败")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    ap = argparse.ArgumentParser()
    ap.add_argument("--kext", default=os.path.join(OUT, "train_Kext.csv"))
    ap.add_argument("--q", default=os.path.join(OUT, "train_q.csv"))
    ap.add_argument("--dev", default=",".join(os.path.join(OUT, f) for f in ["train_q_dev.csv", "train_q04_dev.csv"]))
    ap.add_argument("--out", default=os.path.join(OUT, "r0_choose"))
    a = ap.parse_args()
    _, L = analyze(a.kext, a.q, a.dev.split(","), a.out)
    print("\n".join(L))
