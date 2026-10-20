"""neural/ 公用：路径、导入 rulegen 的解码与实例划分（只读使用，不修改 rulegen/）。"""
import os, sys, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
EXP0 = os.path.dirname(HERE)
RULEGEN = os.path.join(EXP0, "rulegen")
for p in (HERE, RULEGEN, EXP0):
    if p not in sys.path:
        sys.path.insert(0, p)
import ruledec as R      # noqa: E402
import instances as I    # noqa: E402
L = R.L
M = R.M
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def nprocs(arg):
    """'auto' → CPU 核数 − 1；否则按整数"""
    if arg in (None, "", "auto"):
        return max(1, mp.cpu_count() - 1)
    return max(1, int(arg))
