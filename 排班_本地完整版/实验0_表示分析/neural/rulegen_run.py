"""rulegen.py 的外壳：只把候选规则的评价超时改为固定的 600 秒，其余（提示词、算子、种群、评价器、日志、续跑）完全不变。

为什么：evalrule.score 的默认超时 = 60 + 8 × 默认规则总耗时 / 进程数。原来的 full / score 运行在 Windows 上用 15 个进程，
默认规则评价 3 秒、超时约 71 秒，规则可以比默认慢约 24 倍而不被判失败（两次运行都没有超时）。服务器上消融重复用 2 个进程、
又和测试集验证等任务共用 CPU，默认规则评价要 80～100 秒、超时只有约 141 秒，慢 1.5 倍就会被误判。
固定 600 秒（与 eoh.py 相同）后，允许的倍数回到与原运行相当的量级，只防死循环。不修改 rulegen/ 里的任何文件。

用法（参数与 rulegen.py 相同）: python rulegen_run.py --feedback full --tag full_s2 --seed 2 --procs 2
"""
import sys
import common as C  # noqa: F401  （把 rulegen/ 加入 sys.path）
import evalrule as E

TIMEOUT = 600.0
_score = E.score


def score(src, insts, base, procs, n=E.N_SAMPLES, kfrac=E.KFRAC, timeout=None):
    """与 evalrule.score 相同，只是没给超时时用固定的 TIMEOUT"""
    return _score(src, insts, base, procs, n, kfrac, timeout=TIMEOUT if timeout is None else timeout)


E.score = score
import rulegen as RG  # noqa: E402

if __name__ == "__main__":
    C.mp.freeze_support()
    sys.argv[0] = RG.__file__
    RG.main()
