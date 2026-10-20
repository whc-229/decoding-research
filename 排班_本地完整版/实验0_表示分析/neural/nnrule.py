"""神经网络规则：共享 MLP 给每个候选动作打分，按分数从高到低排成偏好顺序，接到 ruledec 的 rule(ctx) 接口上。
偏离照旧作用在这个顺序上（第一个 = 不偏离时的动作，其余 reuse 的顺序 = 改派偏离的候选顺序）。

参数存为 .npz：mu, sd（特征标准化）, W0, b0, W1, b1, ..., 最后一层输出 1 维；隐藏层激活 tanh。
"""
import numpy as np
import features as F


def init_params(hidden=(32, 16), seed=0, nf=F.NF):
    rng = np.random.default_rng(seed)
    p, d = {"mu": np.zeros(nf), "sd": np.ones(nf)}, nf
    sizes = list(hidden) + [1]
    for li, h in enumerate(sizes):
        p[f"W{li}"] = rng.normal(0, 1.0 / np.sqrt(d), (d, h))
        p[f"b{li}"] = np.zeros(h)
        d = h
    p["nl"] = np.array(len(sizes))
    return p


def forward(p, X):
    """X: [n, NF] → 分数 [n]"""
    h = (X - p["mu"]) / p["sd"]
    nl = int(p["nl"])
    for li in range(nl):
        h = h @ p[f"W{li}"] + p[f"b{li}"]
        if li < nl - 1:
            h = np.tanh(h)
    return h[:, 0]


def n_weights(p):
    return sum(p[f"W{i}"].size + p[f"b{i}"].size for i in range(int(p["nl"])))


def flatten(p):
    return np.concatenate([np.concatenate([p[f"W{i}"].ravel(), p[f"b{i}"].ravel()]) for i in range(int(p["nl"]))])


def unflatten(p, v):
    q = dict(p); o = 0
    for i in range(int(p["nl"])):
        for k in (f"W{i}", f"b{i}"):
            n = p[k].size
            q[k] = v[o:o + n].reshape(p[k].shape); o += n
    return q


class NNRule:
    """可 pickle 的规则对象（多进程评价用）"""

    def __init__(self, params):
        self.p = {k: np.asarray(v) for k, v in params.items()}

    def __call__(self, ctx):
        acts, X = F.featurize(ctx)
        if len(acts) <= 1:
            return acts if acts else [("new", ctx.gene_type)]
        s = forward(self.p, X)
        order = np.argsort(-s, kind="stable")
        return [acts[i] for i in order]

    def save(self, path):
        np.savez(path, **self.p)


def load(path):
    d = np.load(path)
    return NNRule({k: d[k] for k in d.files})


def default_equiv_params():
    """一组线性权重，使网络规则与默认规则（dec9）逐解相同：复用优先、按可用列表顺序；新开时基因类型优先，用完则顺延。"""
    p = {"mu": np.zeros(F.NF), "sd": np.ones(F.NF), "nl": np.array(1)}
    w = np.zeros((F.NF, 1))
    w[F.I_IS_NEW, 0] = -100.0
    w[F.I_RANK, 0] = -1.0
    w[F.I_GENE, 0] = 0.5
    w[F.I_OFF, 0] = -0.1
    p["W0"], p["b0"] = w, np.zeros(1)
    return p
