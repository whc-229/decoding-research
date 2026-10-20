"""把规则看到的 ctx 转成"候选动作 × 特征"矩阵，供神经网络 / GP 打分。

候选动作：本班每台可用机器人一个 ("reuse", 机器人)；每种还能新开的类型一个 ("new", 类型)。
每个候选一行特征 = 全局特征 + 类型特征 + 机器人特征（新开候选为 0）+ 新开特征（复用候选为 0）。
所有特征都做了与实例规模无关的归一化，使网络能跨实例（E/H/M、不同时域）使用。
"""
import numpy as np

GLOBAL = ["g_rem_frac", "g_shift_frac", "g_open_frac", "g_cap_ratio", "g_n_avail", "g_no_avail"]
TYPE = ["t_work_rel", "t_cycle_over_work", "t_maint_over_cycle", "t_duties_per_maint", "t_fits_rem",
        "t_maint_before_end", "t_overhead"]
ROBOT = ["r_count_rel", "r_hours_rel", "r_duties_left_frac", "r_last_before_maint", "r_idle",
         "r_maint_done", "r_rank_avail", "r_open_order", "r_maint_finishes"]
NEW = ["n_is_new", "n_left_frac", "n_is_gene_type", "n_gene_offset", "n_type_opened"]
NAMES = GLOBAL + TYPE + ROBOT + NEW
NF = len(NAMES)
I_IS_NEW = NAMES.index("n_is_new")
I_RANK = NAMES.index("r_rank_avail")
I_GENE = NAMES.index("n_is_gene_type")
I_OFF = NAMES.index("n_gene_offset")


def featurize(ctx):
    """→ (动作列表, 特征矩阵 float64[n_cand, NF])"""
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
    zr = [0.0] * len(ROBOT)
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
        rows.append(g + tf[r.type] + rf + [0.0, 0.0, 0.0, 0.0, 0.0])
    gt = ctx.gene_type
    opened = {r.type for r in robots}
    for k in live:
        if ctx.left[k] <= 0:
            continue
        lim = types[k]["limit"] or 1
        nf = [1.0, ctx.left[k] / lim, 1.0 if k == gt else 0.0, ((k - gt) % nty) / nty, 1.0 if k in opened else 0.0]
        acts.append(("new", k))
        rows.append(g + tf[k] + zr + nf)
    X = np.asarray(rows, np.float64) if rows else np.zeros((0, NF))
    return acts, X
