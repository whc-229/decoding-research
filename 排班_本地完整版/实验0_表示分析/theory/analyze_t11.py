"""T11 扫描结果的汇总表（读 t11_A.json / t11_B.json / t11_D.json，输出 markdown 到标准输出）。
口径：每格 20 个种子取平均；"最优 K" = 平均值最小的 K；"近优范围" = 平均值不超过 最优值 + 最优格的标准误 的 K；
"加倍"一栏比较 K = 25 与 K = 50（对应排班里 N ≈ 100、K0.25 ≈ 27 槽与 K0.5 ≈ 54 槽），差值 = f(50) − f(25)，负数表示加倍更好。"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bias_multi as BM  # noqa


def load(mode):
    """读一组扫描的原始行：[(参数元组, 各预算下的值), ...]"""
    p = os.path.join(HERE, f"t11_{mode}.json")
    if not os.path.exists(p):
        return None
    S = json.load(open(p))
    return [(tuple(a), v) for a, v in S["rows"]]


def summarize(vals_by_K):
    """{K: [值...]} → (最优 K, 近优范围字符串, 均值字典, 标准误字典)"""
    mu = {K: float(np.mean(v)) for K, v in vals_by_K.items()}
    se = {K: float(np.std(v, ddof=1) / np.sqrt(len(v))) for K, v in vals_by_K.items()}
    kb = min(mu, key=mu.get)
    near = [K for K in sorted(mu) if mu[K] <= mu[kb] + se[kb]]
    return kb, f"{near[0]}～{near[-1]}" if len(near) > 1 else str(near[0]), mu, se


def diff_25_50(vals_by_K):
    """f(50) − f(25) 的均值与配对标准误（同一种子下目标相同，可配对）"""
    a, b = np.array(vals_by_K[25]), np.array(vals_by_K[50])
    dlt = b - a
    return f"{dlt.mean():+.2f}±{dlt.std(ddof=1) / np.sqrt(len(dlt)):.2f}"


def table_A(rows):
    """检验 A：各 (β, γ) × d × 预算的最优 K、K/d 与 K25→K50 的差"""
    out = []
    for bi, B in enumerate(BM.BUDGETS):
        out += [f"\n**预算 {B}**（格内：最优 K（近优范围）/ f(最优)；末两列为 d = 2、5 时 f(50) − f(25)）\n",
                "| β | γ | p_hit | " + " | ".join(f"d={d}" for d in BM.A_DS) + " | 加倍 d=2 | 加倍 d=5 |",
                "|---|---|---|" + "---|" * (len(BM.A_DS) + 2)]
        for b, g in BM.A_BG:
            cells, dbl = [], []
            for d in BM.A_DS:
                vk = {}
                for a, v in rows:
                    if a[0] == b and a[1] == g and a[2] == d:
                        vk.setdefault(a[3], []).append(v[bi])
                kb, near, mu, _ = summarize(vk)
                cells.append(f"{kb}（{near}）/ {mu[kb]:.1f}")
                if d in (2, 5):
                    dbl.append(diff_25_50(vk))
            p = BM.p_hit(BM.M_VAL, b, 1 / 3 if g is None else g)
            out.append(f"| {b:.2f} | {'—' if g is None else g} | {p:.3f} | " + " | ".join(cells) + " | " + " | ".join(dbl) + " |")
    return out


def table_B(rows):
    """检验 B：各目标集合 × 预算的最优 K（按各目标最小距离的平均），以及最优 K 处各目标的最小距离"""
    out = []
    for bi, B in enumerate(BM.BUDGETS):
        out += [f"\n**预算 {B}**（指标 = 各目标在已评价解中的最小距离的平均；越小越好）\n",
                "| 目标集合 | 结构 | 平均 d | 最优 K（近优范围） | 最优 K / 最小 d | 最优 K / 平均 d | 最优处指标 | 最优处各目标最小距离 | f(50) − f(25) |",
                "|---|---|---|---|---|---|---|---|---|"]
        for name, ds, kind in BM.B_SETS:
            vk, per = {}, {}
            for a, v in rows:
                if a[0] == name:
                    vk.setdefault(a[1], []).append(float(np.mean(v[bi])))
                    per.setdefault(a[1], []).append(v[bi])
            kb, near, mu, _ = summarize(vk)
            pt = np.mean(np.array(per[kb]), axis=0)
            out.append(f"| {name} | {kind if len(ds) > 1 else '单目标'} | {np.mean(ds):.1f} | {kb}（{near}） | {kb / min(ds):.1f} | "
                       f"{kb / np.mean(ds):.2f} | {mu[kb]:.2f} | {' / '.join(f'{x:.1f}' for x in pt)} | {diff_25_50(vk)} |")
    return out


def table_D(rows):
    """额外检验 D：多余偏离代价 λ × d × 预算的最优 K 与 K25→K50 的差"""
    out = []
    for bi, B in enumerate(BM.BUDGETS):
        out += [f"\n**预算 {B}**（格内：最优 K（近优范围）；f = 目标位置错误数 + λ·多余偏离数）\n",
                "| λ | " + " | ".join(f"d={d}" for d in BM.D_DS) + " | 加倍 d=2 | 加倍 d=5 |",
                "|---|" + "---|" * (len(BM.D_DS) + 2)]
        for lam in BM.D_LAM:
            cells, dbl = [], []
            for d in BM.D_DS:
                vk = {}
                for a, v in rows:
                    if a[0] == lam and a[1] == d:
                        vk.setdefault(a[2], []).append(v[bi])
                kb, near, mu, _ = summarize(vk)
                cells.append(f"{kb}（{near}）")
                if d in (2, 5):
                    dbl.append(diff_25_50(vk))
            out.append(f"| {lam} | " + " | ".join(cells) + " | " + " | ".join(dbl) + " |")
    return out


if __name__ == "__main__":
    for mode, fn, title in [("A", table_A, "检验 A：偏离值有偏"), ("B", table_B, "检验 B：多个目标"), ("D", table_D, "额外检验 D：多余偏离的代价 λ")]:
        rows = load(mode)
        if rows is None:
            print(f"\n### {title}：尚无结果"); continue
        print(f"\n### {title}（{len(rows)} 次运行）")
        print("\n".join(fn(rows)))
