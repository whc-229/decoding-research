"""T13 第 4 步分析（排班测试集）：稠密有偏 D 与偏离空间 Pareto 局部搜索 P，对最终方法 X1.0（ρ = 0.4）与 dec5。
数据：out/val_t13.csv（D、P 各 8 条规则 × 5 次）+ out/val_Kext.csv 中的 X1.0 臂（8 条规则 × 5 次）+ out/val_server.csv 中的 dec5（5 次）；
三者都是 47 个测试实例、NSGA-II 465 次评价、种子 1000 + 次号、同一台机器。
HV：每个实例内用四种方法的全部解统一归一化（资源数, 均衡度），参考点 1.1；不可行运行 HV = 0。
方法层面：每个实例先对 8 条规则 × 5 次取平均（dec5 对 5 次取平均），再做实例层面配对 Wilcoxon；
Holm 族 = 全部 47 个实例上的 4 个检验（D、P 各对 X1.0、对 dec5）；分组（原/E/H/M）只报未校正 p。
逐实例 Mann-Whitney：用各次运行的 HV（规则臂 40 个值、dec5 5 个值），双侧 p < 0.05，按均值方向计"好/差"。
用法（neural/ 下）: python stats_t13_roster.py [输出.md=out/stats_t13_val.md]"""
import csv, collections, os, sys
import numpy as np
from scipy.stats import mannwhitneyu, wilcoxon
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import instances as I  # noqa: E402

COL = "front(资源数:均衡度;...)"


def hv(P, ref=1.1):
    """二维 HV（最小化，归一化后参考点 ref），与 choose_t13.hv 相同。"""
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2


def load():
    """读三个 CSV，返回 {(实例, 方法): [每次运行的前沿]}；方法 = 臂名冒号前的部分（D0.2 / P4 / X1.0）或 dec5。"""
    R = collections.defaultdict(list)
    src = [("out/val_t13.csv", lambda v: True), ("out/val_Kext.csv", lambda v: v.startswith("X1.0:")), ("out/val_server.csv", lambda v: v == "dec5")]
    for f, keep in src:
        for r in csv.DictReader(open(os.path.join(HERE, f), encoding="utf-8")):
            if keep(r["variant"]):
                s = r[COL]
                R[(r["scenario"], r["variant"].split(":")[0])].append([tuple(map(float, p.split(":"))) for p in s.split(";")] if s else [])
    return R


def run_hv(R):
    """每个实例内用四种方法的全部解统一归一化，返回 {(实例, 方法): 各次运行 HV 数组}、实例列表、方法列表。"""
    insts = sorted({k[0] for k in R}); meths = sorted({k[1] for k in R})
    H = {}
    for n in insts:
        pts = np.array([p for m in meths for fr in R[(n, m)] for p in fr]); lo, hi = pts.min(0), pts.max(0)
        rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        for m in meths:
            H[(n, m)] = np.array([hv([tuple((np.array(p) - lo) / rg) for p in fr]) if fr else 0.0 for fr in R[(n, m)]])
    return H, insts, meths


def holm(ps):
    """Holm 逐步校正，返回与输入同序的校正后 p 值。"""
    m = len(ps); order = np.argsort(ps); adj = np.empty(m); run = 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (m - i) * ps[j])); adj[j] = run
    return adj


def compare(H, ok, a, c):
    """方法 a 对 c 在实例集 ok 上：平均 HV、差、配对 Wilcoxon p、赢/输、逐实例 Mann-Whitney 好/差。"""
    va = np.array([H[(n, a)].mean() for n in ok]); vc = np.array([H[(n, c)].mean() for n in ok]); d = va - vc
    p = wilcoxon(d).pvalue if len(ok) > 1 and np.any(d) else float("nan")
    good = bad = 0
    for n in ok:
        x, y = H[(n, a)], H[(n, c)]
        if np.ptp(np.concatenate([x, y])) > 0 and mannwhitneyu(x, y, alternative="two-sided").pvalue < 0.05:
            good += x.mean() > y.mean(); bad += x.mean() < y.mean()
    return dict(n=len(ok), ma=va.mean(), mc=vc.mean(), d=d.mean(), p=p, win=int(np.sum(d > 0)), lose=int(np.sum(d < 0)), good=good, bad=bad)


def main():
    """计算全部实例（含 Holm）与各组的对比表，并写出 Markdown。"""
    outp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out/stats_t13_val.md")
    H, insts, meths = run_hv(load())
    cnt = collections.Counter(k[1] for k in H)
    runs = {m: len(H[(insts[0], m)]) for m in meths}
    pairs = [(a, c) for a in ("D0.2", "P4") for c in ("X1.0", "dec5")]
    out = [f"# T13 第 4 步：排班测试集（{len(insts)} 个实例），方法 {', '.join(meths)}\n",
           f"每个实例的运行数：{runs}（规则臂为 8 条规则 × 5 次）。HV 每个实例内四种方法统一归一化，不可行 HV = 0。"
           "p：实例层面配对 Wilcoxon（方法层面先对规则 × 次取平均）；Holm 族 = 全部实例上的 4 个检验；分组只报未校正 p。"
           "MW 好/差：逐实例 Mann-Whitney（各次运行 HV，双侧 p < 0.05）。\n"]
    groups = [("全部", insts)] + [(g + " 组", [i for i in insts if I.group(i) == g]) for g in ["原", "E", "H", "M"]]
    for gname, ok in groups:
        if not ok:
            continue
        rows = [dict(arm=a, ref=c, **compare(H, ok, a, c)) for a, c in pairs]
        if gname == "全部":
            for r, q in zip(rows, holm(np.array([r["p"] for r in rows]))):
                r["holm"] = f"{q:.2g}"
        mean = {m: np.mean([H[(n, m)].mean() for n in ok]) for m in meths}
        out += [f"\n## {gname}（{len(ok)}）\n", "平均 HV：" + "，".join(f"{m} {mean[m]:.3f}" for m in meths) + "\n",
                "| 方法 | 对照 | 方法平均 HV | 对照平均 HV | 差 | p | Holm p | 赢/输 | MW 好/差 |", "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            out.append(f"| {r['arm']} | {r['ref']} | {r['ma']:.3f} | {r['mc']:.3f} | {r['d']:+.3f} | {r['p']:.2g} | {r.get('holm', '—')} | {r['win']}/{r['lose']} | {r['good']}/{r['bad']} |")
    open(outp, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
