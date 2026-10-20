"""假设：平时用中等步长足够；一旦连续多代几乎没有子代存活（停滞），
说明陷入局部前沿，此时给一部分个体重尾的大步"踢出去"，且停滞越久踢得越多。
（由 Claude 按 llm_slot_prompt.md 一次生成，未经外层迭代）"""
import numpy as np


def rule(state, n, rng):
    F = rng.uniform(0.4, 0.6, n)
    if state["stall"] >= 2:
        k = min(0.8, 0.2 * state["stall"])
        kick = rng.random(n) < k
        F[kick] = np.clip(0.5 * (1 - rng.random(kick.sum())) ** (-1 / 1.2), 0.5, 1.2)
    return F
