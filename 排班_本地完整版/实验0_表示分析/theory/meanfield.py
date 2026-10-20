"""稀疏偏离编码的固定预算平均场模型（半解析）。

把 K 个槽分成三类：错误生效 w（落在不该偏离的位置或取值错）、正确生效 c、未生效 i = K − w − c。f = w + (d − c)。
每个后代平均变异 1 个基因，每个槽被碰到的概率约 1/K（位置基因、开关基因各一半）。只有使 f 下降的变化被保留（精英选择）：
  清理：错误槽的开关基因跌破阈值               w → w−1        速率 α·w/(2K)
  修复：未生效槽被打开且恰好落在待修位置、取值对   c → c+1        速率 α·i/(2K)·(d−c)/N·1/(m−1)
  挪动：错误槽的位置基因挪到待修位置且取值对       w−1, c+1       速率 β·w/(2K)·(d−c)/N·1/(m−1)
初值：w0 = qK(1−d/N)（扣除碰撞），c0 = qK·(d/N)/(m−1)。α、β 为算子相关常数，用模拟数据拟合（共 2 个参数）。
由此得到 f(B) 的预测，以及最优槽数 K*(B, d)。"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model as Mo  # noqa

Q = Mo.Q


def predict(N, d, m, K, B, alpha, beta, pop=30):
    pi = 1 - (1 - Q / N) ** K                      # 每个位置被偏离的概率（含碰撞）
    w = (N - d) * pi + d * pi * (m - 2) / (m - 1)   # 错误偏离的位置数
    c = d * pi / (m - 1)
    act = N * pi
    i = max(0.0, K - act)
    # 初始种群取最好者：近似为期望值减去种群内的标准差带来的选择差（简单修正）
    f0_sd = np.sqrt(max(w, 1e-9) + max(c * (1 - c / max(d, 1)), 0))
    best_gain = min(w, 1.2 * f0_sd)                # 30 个个体中的最好者大约好 1.2 个标准差
    w = max(0.0, w - best_gain)
    steps = B - pop
    for _ in range(int(steps)):
        u = max(d - c, 0.0)
        r1 = alpha * w / (2 * K)
        r2 = alpha * i / (2 * K) * u / N / (m - 1)
        r3 = beta * w / (2 * K) * u / N / (m - 1)
        w = max(0.0, w - r1 - r3)
        c = min(float(d), c + r2 + r3)
        i = max(0.0, K - w - c)
    return w + (d - c)


def fit(path=os.path.join(HERE, "sweep.json")):
    S = json.load(open(path))
    N, m = S["N"], S["m"]
    data = [(int(d), int(K), int(b), v) for b, bd in S["mean"].items() for d, row in bd.items() for K, v in row.items() if K != "PS"]
    best, bp = None, None
    for alpha in [0.01, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1]:
        for beta in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
            err = np.mean([(predict(N, d, m, K, b, alpha, beta) - v) ** 2 for d, K, b, v in data if b <= 2000])
            if best is None or err < best:
                best, bp = err, (alpha, beta)
    return bp, best, data, N, m


if __name__ == "__main__":
    (alpha, beta), mse, data, N, m = fit()
    print(f"拟合（只用 465 与 2000 次预算的数据）：alpha={alpha} beta={beta}  均方误差={mse:.2f}")
    # 用 10000 次的数据检验外推
    test = [(d, K, b, v) for d, K, b, v in data if b == 10000]
    pred = [predict(N, d, m, K, b, alpha, beta) for d, K, b, v in test]
    obs = [v for *_, v in test]
    print(f"外推到 10000 次：均方误差 {np.mean((np.array(pred) - np.array(obs)) ** 2):.2f}，相关 {np.corrcoef(pred, obs)[0, 1]:.3f}")
    Ks = sorted({K for _, K, _, _ in data})
    for b in [465, 2000, 10000]:
        line = []
        for d in [5, 10, 20, 30, 40]:
            ko = min(Ks, key=lambda K: dict(((dd, KK), v) for dd, KK, bb, v in data if bb == b)[(d, K)])
            kp = min(Ks, key=lambda K: predict(N, d, m, K, b, alpha, beta))
            line.append(f"d={d}: 实测最优K={ko} 预测={kp}")
        print(f"预算 {b}: " + "；".join(line))
