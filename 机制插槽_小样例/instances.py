"""扩充的问题实例（注册进 slot_moea.PROBLEMS）：DTLZ1-4/7 的 2、3 目标版本，ZDT4 的 20 维版本。
导入本模块即完成注册；同时扩展 slot_moea.true_front。
"""
import numpy as np
import slot_moea as s


def dtlz_g(name, M, k):
    n = M - 1 + k

    def f(X):
        xm = X[:, M - 1:]
        xp = X[:, :M - 1]
        if name in ("DTLZ1", "DTLZ3"):
            g = 100 * (k + ((xm - .5) ** 2 - np.cos(20 * np.pi * (xm - .5))).sum(1))
        elif name in ("DTLZ2", "DTLZ4"):
            g = ((xm - .5) ** 2).sum(1)
        elif name == "DTLZ7":
            g = 1 + 9 / k * xm.sum(1)
        if name == "DTLZ1":
            F = np.ones((len(X), M)) * 0.5 * (1 + g)[:, None]
            for i in range(M):
                F[:, i] *= np.prod(xp[:, :M - 1 - i], 1)
                if i > 0:
                    F[:, i] *= 1 - xp[:, M - 1 - i]
            return F
        if name == "DTLZ7":
            F = np.empty((len(X), M))
            F[:, :M - 1] = xp
            h = M - (xp / (1 + g)[:, None] * (1 + np.sin(3 * np.pi * xp))).sum(1)
            F[:, M - 1] = (1 + g) * h
            return F
        th = xp ** 100 if name == "DTLZ4" else xp
        F = np.ones((len(X), M)) * (1 + g)[:, None]
        for i in range(M):
            F[:, i] *= np.prod(np.cos(th[:, :M - 1 - i] * np.pi / 2), 1)
            if i > 0:
                F[:, i] *= np.sin(th[:, M - 1 - i] * np.pi / 2)
        return F
    return f, np.zeros(n), np.ones(n)


def front(name, M):
    if M == 2:
        t = np.linspace(0, 1, 2000)
        W = np.stack([t, 1 - t], 1)
    else:
        H = 40
        W = np.array([[i, j, H - i - j] for i in range(H + 1) for j in range(H + 1 - i)]) / H
    if name == "DTLZ1":
        return 0.5 * W
    if name in ("DTLZ2", "DTLZ3", "DTLZ4"):
        if M == 2:
            a = np.linspace(0, np.pi / 2, 2000)
            return np.stack([np.cos(a), np.sin(a)], 1)
        return W / np.linalg.norm(W, axis=1, keepdims=True)
    if name == "DTLZ7":
        if M == 2:
            x = np.linspace(0, 1, 4000)[:, None]
        else:
            g1 = np.linspace(0, 1, 80)
            x = np.array(np.meshgrid(g1, g1)).reshape(2, -1).T
        h = M - (x / 2 * (1 + np.sin(3 * np.pi * x))).sum(1)
        P = np.hstack([x, (2 * h)[:, None]])
        return P[s.nondominated_mask(P)]


FRONTS = {}
for nm, M, k in [("DTLZ1", 2, 5), ("DTLZ3", 2, 10), ("DTLZ3", 3, 10), ("DTLZ2", 2, 10),
                 ("DTLZ4", 2, 10), ("DTLZ4", 3, 10), ("DTLZ7", 2, 20), ("DTLZ7", 3, 20)]:
    key = f"{nm}_M{M}"
    s.PROBLEMS[key] = (lambda nm=nm, M=M, k=k: dtlz_g(nm, M, k))
    FRONTS[key] = (lambda nm=nm, M=M: front(nm, M))
s.PROBLEMS["ZDT4_n20"] = lambda: s.zdt("ZDT4", 20)
FRONTS["ZDT4_n20"] = lambda: s.true_front("ZDT4")

_old = s.true_front
_cache = {}


def true_front(name, npts=2000):
    if name not in _cache:
        _cache[name] = FRONTS[name]() if name in FRONTS else _old(name, npts)
    return _cache[name]


s.true_front = true_front

# 问题族（留一族交叉验证时整族留出，避免同族泄漏）
FAMILY = {k: k.split("_")[0] for k in s.PROBLEMS}
FAMILY.update({"DTLZ1": "DTLZ1", "DTLZ2": "DTLZ2"})
