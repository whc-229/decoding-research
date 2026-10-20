"""测试集方法对比（第 7 步的主表）。用 ana 环境运行（需要 scipy）：
    ~/miniconda3/envs/ana/bin/python analyze_methods.py out/val_server.csv [更多.csv ...] [--out out/val_methods.md]

口径（与 rulegen/analyze_val.py 相同的归一化和 HV）：
  - 每个实例内，用所有臂、所有运行的解统一求最小 / 最大值做归一化，再算每次运行的 HV（参考点 1.1）；
  - 臂 = 一条具体规则（一个设计运行），名字写成 "方法(运行)"，例如 K0.25:IL16(s0)、K0.25:GP(run3)；
    方法 = 括号前的部分；ALIAS 里给出例外（r47 → LLM-full，r35 → LLM-score）；
  - 方法层面：每个实例上对该方法的所有设计运行 × 5 次 MOEA 取平均，再在实例层面做配对 Wilcoxon（双侧）；
    逐实例 Mann-Whitney（p < 0.05 计好 / 差）比较的是两种方法在该实例上的全部运行（设计运行 × MOEA 次数）；
  - 另附逐个设计运行的表：每条规则的平均 HV，以及每种方法各设计运行的均值、最小～最大、"最好一次"
    （"最好一次"按测试集挑出，只作报告，不能当作方法的成绩）；
  - 分 全部 / 原 / E / H / M 组报告。只用所有臂都有结果的实例（不全时会提示缺多少）。
  - 多重比较：每个分组内做 Holm 校正，两个检验族分开——两两表（除 dec5、默认规则外的方法两两，7 种方法时 21 对）；
    主表的"对 dec5 / 对默认规则"（每种方法对两个参照，dec5 对默认规则只算一次）。表中同时给原始 p 和 Holm p。
多个 CSV 合并时按 (实例, 臂, 次) 去重（先出现的为准）。
"""
import argparse, collections, csv, os, re, sys
import numpy as np
from scipy.stats import wilcoxon, mannwhitneyu

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import instances as I  # noqa: E402

ALIAS = {"K0.25:LLM(r47)": ("LLM-full", "r47"), "K0.25:LLM(r35)": ("LLM-score", "r35"),
         "K0.25:default": ("默认规则", "—"), "dec5": ("dec5", "—")}
ORDER = ["dec5", "默认规则", "LLM-full", "LLM-score", "EoH", "GP", "IL16", "ES16", "IL32-16"]
REFS = ["dec5", "默认规则"]


def method_of(arm):
    """臂名 → (方法, 设计运行)"""
    if arm in ALIAS:
        return ALIAS[arm]
    m = re.match(r"^(?:K[\d.]+:)?(.+?)\((.+)\)$", arm)
    return (m.group(1), m.group(2)) if m else (arm, "—")


def hv(P, ref=1.1):
    """二维最小化 HV（与 analyze_val.py 相同）"""
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2


def load(paths):
    """→ {(实例, 臂): {次号: 前沿点列表}}，按 (实例, 臂, 次) 去重"""
    runs = collections.defaultdict(dict)
    for pth in paths:
        for r in csv.DictReader(open(pth, encoding="utf-8")):
            key, k = (r["scenario"], r["variant"]), int(r["run"])
            if k in runs[key]:
                continue
            f = r["front(资源数:均衡度;...)"]
            runs[key][k] = [tuple(map(float, p.split(":"))) for p in f.split(";")] if f else []
    return runs


def normalize(runs, insts, arms):
    """每个实例内所有臂统一归一化 → H[(实例, 臂)] = 各次 HV 列表，R[(实例, 臂)] = 各次最少资源数 − 下界"""
    H, R = {}, {}
    for i in insts:
        pts = [p for a in arms for fr in runs[(i, a)].values() for p in fr]
        if not pts:
            continue
        A = np.array(pts); lo, hi = A.min(0), A.max(0); rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        for a in arms:
            frs = [runs[(i, a)][k] for k in sorted(runs[(i, a)])]
            H[(i, a)] = [hv([tuple((np.array(p) - lo) / rg) for p in fr]) if fr else 0.0 for fr in frs]
            R[(i, a)] = [min(p[0] for p in fr) - I.lb(i) if fr else np.nan for fr in frs]
    return H, R


def holm(ps):
    """Holm 逐步校正：ps 为原始 p 列表 → 校正后 p 列表（顺序不变）"""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m - k) * ps[i]))
        adj[i] = run
    return adj


def compare(Hm, a, b, grp):
    """方法 a 对 b：实例层面平均差、配对 Wilcoxon p、逐实例 Mann-Whitney 好/差数"""
    d = np.array([np.mean(Hm[(i, a)]) - np.mean(Hm[(i, b)]) for i in grp])
    p = wilcoxon(d).pvalue if len(grp) > 1 and np.any(d != 0) else 1.0
    up = dn = 0
    for i in grp:
        x, y = Hm[(i, a)], Hm[(i, b)]
        try:
            pp = mannwhitneyu(x, y).pvalue
        except ValueError:
            pp = 1.0
        if pp < 0.05:
            up += np.mean(x) > np.mean(y); dn += np.mean(x) < np.mean(y)
    return d.mean(), p, up, dn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "val_methods.md"))
    a = ap.parse_args()
    runs = load(a.csv)
    arms = sorted({x for _, x in runs})
    meth = collections.OrderedDict()
    for x in sorted(arms, key=lambda x: (ORDER.index(method_of(x)[0]) if method_of(x)[0] in ORDER else 99, x)):
        meth.setdefault(method_of(x)[0], []).append(x)
    all_insts = sorted({i for i, _ in runs})
    nrun = {x: collections.Counter(len(runs[(i, x)]) for i in all_insts) for x in arms}
    insts = [i for i in all_insts if all(runs.get((i, x)) for x in arms)]
    H, R = normalize(runs, insts, arms)
    # 方法层面：把该方法所有设计运行的所有 MOEA 运行合在一起
    Hm = {(i, m): [h for x in xs for h in H[(i, x)]] for i in insts for m, xs in meth.items()}
    Rm = {(i, m): [r for x in xs for r in R[(i, x)]] for i in insts for m, xs in meth.items()}
    out = [f"# 测试集方法对比：{len(insts)} 个实例（Python NSGA-II，465 次评价）\n",
           f"输入：{', '.join(os.path.relpath(p, HERE) for p in a.csv)}。HV 在每个实例内用全部 {len(arms)} 个臂统一归一化。"
           "方法层面：每个实例上对所有设计运行 × MOEA 次数取平均；p = 实例层面配对 Wilcoxon（双侧）原始 p，"
           "Holm p = 分组内按检验族做 Holm 校正（主表一族、两两表一族）；"
           "好/差 = 逐实例 Mann-Whitney p<0.05 的实例数；资源差 = 最少资源数 − 下界（实例平均）。\n"]
    miss = [i for i in all_insts if i not in insts]
    if miss:
        out.append(f"**注意：{len(miss)} 个实例缺部分臂的结果，未计入**：{', '.join(miss[:10])}{' …' if len(miss) > 10 else ''}\n")
    out += ["| 方法 | 设计运行数 | 每臂 MOEA 次数 | 臂 |", "|---|---|---|---|"]
    for m, xs in meth.items():
        ks = sorted({k for x in xs for k in nrun[x]})
        out.append(f"| {m} | {len(xs)} | {'/'.join(map(str, ks))} | {', '.join(method_of(x)[1] for x in xs)} |")
    mlist = list(meth)
    for gname, grp in [("全部", insts)] + [(g + " 组", [i for i in insts if I.group(i) == g]) for g in ["原", "E", "H", "M"]]:
        if not grp:
            continue
        refs = [b for b in REFS if b in meth]
        lm = [m for m in mlist if m not in REFS]
        # 主表检验族：每种方法对每个参照（dec5 对默认规则只算一次）
        cmp_main = {}
        for m in mlist:
            for b in refs:
                if m != b and (b, m) not in cmp_main:
                    cmp_main[(m, b)] = compare(Hm, m, b, grp)
        keys = list(cmp_main)
        hadj = dict(zip(keys, holm([cmp_main[k][1] for k in keys])))

        def main_cell(m, b):
            if m == b:
                return ["—", "—", "—", "—"]
            k = (m, b) if (m, b) in cmp_main else (b, m)
            dm, p, up, dn = cmp_main[k]
            if k != (m, b):
                dm, up, dn = -dm, dn, up
            return [f"{dm:+.3f}", f"{p:.3g}", f"{hadj[k]:.3g}", f"{up}/{dn}"]
        out += [f"\n## {gname}（{len(grp)} 个实例）\n",
                "| 方法 | 平均 HV | " + " | ".join(f"对 {b} | p | Holm p | 好/差" for b in refs) + " | 资源差 |",
                "|---|---|" + "---|---|---|---|" * len(refs) + "---|"]
        for m in mlist:
            row = [m, f"{np.mean([np.mean(Hm[(i, m)]) for i in grp]):.3f}"]
            for b in refs:
                row += main_cell(m, b)
            row.append(f"{np.nanmean([np.nanmean(Rm[(i, m)]) for i in grp]):.2f}")
            out.append("| " + " | ".join(row) + " |")
        # 方法两两对比（行 − 列），Holm 校正的检验族 = 这些方法的全部无序对
        if len(lm) > 1:
            pairs = [(m, n) for k, m in enumerate(lm) for n in lm[k + 1:]]
            pc = {pr: compare(Hm, pr[0], pr[1], grp) for pr in pairs}
            pa = dict(zip(pairs, holm([pc[pr][1] for pr in pairs])))
            out += [f"\n方法两两对比（行 − 列的平均 HV 差；括号内为配对 Wilcoxon 原始 p；Holm p，{len(pairs)} 对一起校正；"
                    "* 表示 Holm p < 0.05）：\n",
                    "| | " + " | ".join(lm) + " |", "|---|" + "---|" * len(lm)]
            for m in lm:
                cells = []
                for n in lm:
                    if m == n:
                        cells.append("—"); continue
                    k = (m, n) if (m, n) in pc else (n, m)
                    dm = pc[k][0] if k == (m, n) else -pc[k][0]
                    cells.append(f"{dm:+.3f}（{pc[k][1]:.2g}；Holm {pa[k]:.2g}{'*' if pa[k] < 0.05 else ''}）")
                out.append(f"| {m} | " + " | ".join(cells) + " |")
    # 逐个设计运行
    out += ["\n## 逐个设计运行（全部实例）\n",
            "每条规则（臂）在测试集上的平均 HV（每个实例先对 5 次 MOEA 取平均）、对 dec5 / 对默认规则的配对 Wilcoxon。\n",
            "| 方法 | 设计运行 | 平均 HV | 对 dec5 | p | 对默认规则 | p | 资源差 |", "|---|---|---|---|---|---|---|---|"]
    per = {}
    for m, xs in meth.items():
        for x in xs:
            v = np.array([np.mean(H[(i, x)]) for i in insts]); per[x] = v.mean()
            row = [m, method_of(x)[1], f"{v.mean():.3f}"]
            for b in REFS:
                if b not in meth or m == b:
                    row += ["—", "—"]; continue
                d = v - np.array([np.mean(Hm[(i, b)]) for i in insts])
                row += [f"{d.mean():+.3f}", f"{wilcoxon(d).pvalue if np.any(d != 0) else 1.0:.3g}"]
            row.append(f"{np.nanmean([np.nanmean(R[(i, x)]) for i in insts]):.2f}")
            out.append("| " + " | ".join(row) + " |")
    out += ["\n## 各方法设计运行的离散程度（全部实例）\n",
            "\"最好一次\"是按测试集挑出的，只说明上限，不能当作方法成绩。\n",
            "| 方法 | 设计运行数 | 各次平均 | 最小～最大 | 最好一次 |", "|---|---|---|---|---|"]
    for m, xs in meth.items():
        v = [per[x] for x in xs]
        best = max(xs, key=lambda x: per[x])
        out.append(f"| {m} | {len(xs)} | {np.mean(v):.3f} | {min(v):.3f}～{max(v):.3f} | {method_of(best)[1]}（{per[best]:.3f}） |")
    open(a.out, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
