"""特征计算的纯 Python 源码（只用内置函数，能通过 rulegen 的 compile_rule 受限执行），供 GP 规则导出时内嵌。
与 features.featurize 逐位相同（features.py 本身就是用 Python float 逐个算的，这里只是去掉 numpy 并按复用 / 新开拆成两段）。
check_featsrc.py 核对两者一致。

FEAT_SRC 定义 feats(ctx) → (动作列表, 每个动作的特征列表)：
  复用候选的特征 = 全局 6 + 类型 7 + 机器人 9（共 22，顺序 = REUSE_TERMS）
  新开候选的特征 = 全局 6 + 类型 7 + 新开 4（共 17，顺序 = NEW_TERMS；n_is_new 对新开恒为 1，去掉）
"""
import features as F

REUSE_TERMS = F.GLOBAL + F.TYPE + F.ROBOT
NEW_TERMS = F.GLOBAL + F.TYPE + F.NEW[1:]

FEAT_SRC = '''
def feats(ctx):
    # 返回 (动作列表, 特征列表)；复用候选 22 维、新开候选 17 维，全部做了与实例规模无关的归一化
    T, rem = ctx.T, ctx.remaining
    types = ctx.types
    nty = len(types)
    live = [k for k in range(nty) if types[k] is not None]
    wmax = max(types[k]["work_time"] for k in live)
    robots = ctx.robots
    nR = len(robots)
    limR = sum(types[k]["limit"] for k in live) or 1
    mc = sum(r.count for r in robots) / nR if nR else 0.0
    mh = sum(r.hours for r in robots) / nR if nR else 0.0
    av = ctx.available
    na = len(av)
    if rem > 0:
        capr = min(ctx.capacity / rem, 3.0) if nR else 0.0
    else:
        capr = 3.0
    g = [rem / T, ctx.shift / max(1, ctx.n_shifts_max), nR / limR, capr, min(na, 8) / 8.0, 1.0 if na == 0 else 0.0]
    tf = {}
    for k in live:
        t = types[k]
        w = t["work_time"]
        cyc = w + t["out_travel_time"] + t["return_travel_time"] + t["charge_time"]
        nd = t["continue_max_work"] / t["single_work_time"]
        tf[k] = [w / wmax, cyc / w, t["maintenance_time"] / (nd * cyc), nd / 20.0, 1.0 if w <= rem + 1e-9 else 0.0,
                 1.0 if rem - w > t["maintenance_time"] else 0.0,
                 (t["out_travel_time"] + t["return_travel_time"] + t["charge_time"]) / w]
    acts, rows = [], []
    for i, r in enumerate(av):
        t = types[r.type]
        w = t["work_time"]
        cyc = w + t["out_travel_time"] + t["return_travel_time"] + t["charge_time"]
        nd = t["continue_max_work"] / t["single_work_time"]
        idle = (ctx.t - r.last_end) / cyc if r.last_end is not None else 0.0
        rf = [(r.count - mc) / 5.0, (r.hours - mh) / (5.0 * wmax), r.duties_left / nd, 1.0 if r.duties_left <= 1 else 0.0,
              min(idle, 5.0) / 5.0, 1.0 if r.first_maint is not None else 0.0, i / max(1, na - 1), r.idx / max(1, nR - 1),
              1.0 if (r.duties_left <= 1 and rem - w > t["maintenance_time"]) else 0.0]
        acts.append(("reuse", r))
        rows.append(g + tf[r.type] + rf)
    gt = ctx.gene_type
    opened = {r.type for r in robots}
    for k in live:
        if ctx.left[k] <= 0:
            continue
        lim = types[k]["limit"] or 1
        acts.append(("new", k))
        rows.append(g + tf[k] + [ctx.left[k] / lim, 1.0 if k == gt else 0.0, ((k - gt) % nty) / nty, 1.0 if k in opened else 0.0])
    return acts, rows
'''


def full_row(act, row):
    """把 FEAT_SRC 的一行拆分特征还原成 features.featurize 的 27 维（核对用）"""
    nG, nT, nR = len(F.GLOBAL), len(F.TYPE), len(F.ROBOT)
    if act[0] == "reuse":
        return row + [0.0] * len(F.NEW)
    return row[:nG + nT] + [0.0] * nR + [1.0] + row[nG + nT:]
