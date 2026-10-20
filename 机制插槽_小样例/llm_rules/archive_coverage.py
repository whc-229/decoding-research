"""假设：archive 没填满说明前沿覆盖还不够，应该用大步扩张；
archive 填满后转入精修，步长随预算消耗退火，但保留少量随机性以防早熟。
（由 Claude 按 llm_slot_prompt.md 一次生成，未经外层迭代）"""
import numpy as np


def rule(state, n, rng):
    if state["arch_frac"] < 0.95:
        center = 0.8
    else:
        center = 0.6 - 0.35 * state["progress"]
    return np.clip(center + 0.1 * rng.standard_normal(n), 0.05, 1.2)
