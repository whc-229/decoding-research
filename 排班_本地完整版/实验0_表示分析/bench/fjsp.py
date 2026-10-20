"""公开基准：柔性作业车间（FJSP，Brandimarte / Hurink / Kacem 等实例，SchedulingLab/fjsp-instances）。
把排班问题里的"规则 + 稀疏偏离"框架原样搬过来，检验偏置–自由度的结论能否推广。

调度构造：逐步决策。每步的候选 = 各工件的下一道工序 × 它可用的机器；开始时刻 = max(工件就绪, 机器就绪)（不插空）。
规则（偏置）：最早完工优先（ECT），并列时剩余工作量大的工件优先（MWKR），再按加工时间短。
四种编码（基因都在 [0,1)）：
  rule   纯规则（无基因，参照）
  pd     逐步基因（dec5 的对应）：每步一个基因，在按规则排好序的候选里选第 floor(g·|C|) 个
  sp{K}  稀疏偏离（dec9 的对应）：K 个槽 (p, a)，a ≥ 0.6 时在第 floor(p·N) 步偏离，选规则排序中第 1+floor(u·(|C|−1)) 个
  rk     经典双段随机键（工序序列 OS + 机器分配 MS），文献中最常见的基线
目标（双目标，最小化）：完工时间 makespan、总负荷 total workload。
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fjsp-instances")
DEV_ON, Q = 0.6, 0.4


def load(path):
    with open(path if os.path.isabs(path) else os.path.join(ROOT, path)) as f:
        tok = f.read().split()
    it = iter(tok)
    nj, nm = int(next(it)), int(float(next(it)))
    jobs = []
    for _ in range(nj):
        no = int(next(it)); ops = []
        for _ in range(no):
            k = int(next(it)); ops.append([(int(next(it)), int(next(it))) for _ in range(k)])
        jobs.append(ops)
    return dict(nj=nj, nm=nm, jobs=jobs, nops=sum(len(j) for j in jobs))


def meta():
    return {d["name"]: d for d in json.load(open(os.path.join(ROOT, "instances.json")))}


def _candidates(inst, nxt, jr, mr, rem):
    C = []
    for j, ops in enumerate(inst["jobs"]):
        o = nxt[j]
        if o < len(ops):
            for (k, p) in ops[o]:
                st = max(jr[j], mr[k])
                C.append((st + p, -rem[j], p, j, k))
    C.sort()
    return C


def build(inst, chooser):
    """chooser(step, 候选列表[已按规则排序]) → 选中的下标。返回 (makespan, total_workload, 选择序列)"""
    nj, nm = inst["nj"], inst["nm"]
    nxt = [0] * nj; jr = [0] * nj; mr = [0] * nm
    rem = [sum(min(p for _, p in op) for op in ops) for ops in inst["jobs"]]
    tw = 0; picks = []
    for step in range(inst["nops"]):
        C = _candidates(inst, nxt, jr, mr, rem)
        i = chooser(step, C)
        c, _, p, j, k = C[i]
        jr[j] = mr[k] = c; tw += p
        rem[j] -= min(pp for _, pp in inst["jobs"][j][nxt[j]])
        nxt[j] += 1; picks.append(i)
    return (max(jr), tw, picks)


def decode(inst, enc, g=None):
    N = inst["nops"]
    if enc == "rule":
        return build(inst, lambda s, C: 0)[:2]
    if enc == "pd":
        return build(inst, lambda s, C: min(int(g[s] * len(C)), len(C) - 1))[:2]
    if enc.startswith("sp"):
        K = int(enc[2:])
        dev = {}
        for k in range(K):
            p, a = g[2 * k], g[2 * k + 1]
            if a >= DEV_ON:
                dev[min(int(p * N), N - 1)] = (a - DEV_ON) / (1 - DEV_ON)

        def ch(s, C):
            u = dev.get(s)
            if u is None or len(C) < 2:
                return 0
            return 1 + min(int(u * (len(C) - 1)), len(C) - 2)
        return build(inst, ch)[:2]
    if enc == "rk":
        return decode_rk(inst, g)
    raise ValueError(enc)


def nvar(inst, enc):
    N = inst["nops"]
    return {"pd": N, "rk": 2 * N}.get(enc, 2 * int(enc[2:]) if enc.startswith("sp") else 0)


def decode_rk(inst, g):
    N = inst["nops"]
    owner = [j for j, ops in enumerate(inst["jobs"]) for _ in ops]
    seq = [owner[i] for i in np.argsort(g[:N], kind="stable")]
    nj, nm = inst["nj"], inst["nm"]
    nxt = [0] * nj; jr = [0] * nj; mr = [0] * nm; tw = 0
    base = np.cumsum([0] + [len(o) for o in inst["jobs"]])
    for j in seq:
        o = nxt[j]; opts = inst["jobs"][j][o]
        k, p = opts[min(int(g[N + base[j] + o] * len(opts)), len(opts) - 1)]
        c = max(jr[j], mr[k]) + p
        jr[j] = mr[k] = c; tw += p; nxt[j] += 1
    return (max(jr), tw)


def rule_distance(inst, picks):
    """一个选择序列相对规则的偏离步数（选的不是规则首选的步数）"""
    return sum(1 for i in picks if i != 0)


def k_slots(inst, frac):
    return max(4, math.ceil(frac * inst["nops"]))
