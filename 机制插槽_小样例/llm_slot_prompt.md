# 步长插槽的 LLM 提示词（窄接口）

> 用法：把下面整段发给任意 LLM，把返回的函数存成 `llm_rules/<名字>.py`，再运行 `python evaluate_rules.py`。
> 设计要点：LLM **只写 state → F 的一小段规则**，不碰变异公式、选择和 archive；规则冻结后运行时不再调用 LLM。

---

你在为一个多目标进化算法设计"步长控制规则"。算法骨架固定为：DE/rand/1/bin（F 为差分缩放因子）+ 多项式变异 + NSGA-II 环境选择 + 容量 N 的外部非支配 archive。你**只**需要写一个函数：

```python
import numpy as np
def rule(state: dict, n: int, rng: np.random.Generator) -> np.ndarray:
    """返回长度 n 的数组，每个子代一个 F（建议范围 0.05~1.2）"""
```

每代调用一次。`state` 中的字段（都是运行时廉价可得的量）：

| 字段 | 含义 |
|---|---|
| `gen`, `progress` | 当前代数；已用预算比例 ∈ [0,1) |
| `succ` | 上一代子代进入下一代种群的比例（成功率） |
| `rank1_frac` | 当前种群中非支配解（第一前沿）的比例 |
| `stall` | 连续多少代成功率 < 5% |
| `arch_frac` | 外部 archive 的填充比例（=非支配解数/N） |

要求：
1. 只用 numpy 和上面的字段；不要读写全局状态以外的东西；
2. 写出规则背后的一句话假设（作为 docstring）；
3. 给出 3 个彼此思路不同的候选规则，分别以 `rule` 命名、放在不同文件中。

已知参考：固定 F=0.5；JADE 式成功历史均值 + Cauchy；幂律重尾步长（无需调参）。请避免简单复述这三者。
