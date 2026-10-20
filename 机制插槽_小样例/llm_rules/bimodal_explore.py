"""假设：多目标搜索同时需要"沿前沿铺开"的大步和"向前沿收敛"的小步；
种群越多处于第一前沿，收敛压力越弱，越该分配更多大步去开拓。
（由 Claude 按 llm_slot_prompt.md 一次生成，未经外层迭代）"""
import numpy as np


def rule(state, n, rng):
    p_big = 0.15 + 0.6 * state["rank1_frac"]
    big = rng.random(n) < p_big
    F = np.where(big, rng.uniform(0.7, 1.0, n), rng.uniform(0.15, 0.4, n))
    return F
