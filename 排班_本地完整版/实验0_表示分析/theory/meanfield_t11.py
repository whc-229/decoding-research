"""T11：平均场模型（meanfield.py）对检验 A 的推广。

原模型里"一个生效偏离落在待修位置上时取值恰好正确"的概率是 1/(m−1)。偏离值有偏（β）、目标取值有偏（γ）时，
这个概率换成 p_hit = γβ + (1−γ)(1−β)/(m−2)（bias_multi.p_hit），其余三条速率方程不变：
  清理（错误槽关掉）与 p_hit 无关；修复、挪动的速率都乘 p_hit；初值 c0 = d·π·p_hit，w0 = (N−d)π + dπ(1−p_hit)。
α、β_mf 仍用 sweep.json 的 465/2000 次数据拟合（meanfield.fit），不为 T11 重新拟合。
用法: python meanfield_t11.py   打印各 p_hit 下预测的最优 K（K 取 1..100 的整数）"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import meanfield as MF  # noqa
import bias_multi as BM  # noqa

Q = MF.Q


def predict_p(N, d, K, B, alpha, beta, p, pop=30):
    """与 meanfield.predict 相同的递推，只把取值正确的概率 1/(m−1) 换成 p"""
    pi = 1 - (1 - Q / N) ** K
    w = (N - d) * pi + d * pi * (1 - p)
    c = d * pi * p
    act = N * pi
    i = max(0.0, K - act)
    f0_sd = np.sqrt(max(w, 1e-9) + max(c * (1 - c / max(d, 1)), 0))
    best_gain = min(w, 1.2 * f0_sd)
    w = max(0.0, w - best_gain)
    for _ in range(int(B - pop)):
        u = max(d - c, 0.0)
        r1 = alpha * w / (2 * K)
        r2 = alpha * i / (2 * K) * u / N * p
        r3 = beta * w / (2 * K) * u / N * p
        w = max(0.0, w - r1 - r3)
        c = min(float(d), c + r2 + r3)
        i = max(0.0, K - w - c)
    return w + (d - c)


def kstar(N, d, B, alpha, beta, p, Ks=range(1, 101)):
    """预测的最优 K 及该处的 f"""
    vals = {K: predict_p(N, d, K, B, alpha, beta, p) for K in Ks}
    k = min(vals, key=vals.get)
    return k, vals[k], vals


def table(alpha, beta, N=100, m=4):
    """各 (β, γ) 组合、各 d、两档预算下的预测最优 K；返回 markdown 行"""
    rows = ["| β | γ | p_hit | 预算 | " + " | ".join(f"d={d}" for d in BM.A_DS) + " |",
            "|---|---|---|---|" + "---|" * len(BM.A_DS)]
    for b, g in BM.A_BG:
        p = BM.p_hit(m, b, 1 / 3 if g is None else g)
        for B in BM.BUDGETS:
            ks = [kstar(N, d, B, alpha, beta, p)[0] for d in BM.A_DS]
            rows.append(f"| {b:.2f} | {'—' if g is None else g} | {p:.3f} | {B} | " + " | ".join(str(k) for k in ks) + " |")
    return rows


if __name__ == "__main__":
    (alpha, beta), mse, *_ = MF.fit()
    print(f"拟合参数（同 meanfield.py）：alpha={alpha} beta={beta} 均方误差={mse:.2f}")
    print("\n".join(table(alpha, beta)))
