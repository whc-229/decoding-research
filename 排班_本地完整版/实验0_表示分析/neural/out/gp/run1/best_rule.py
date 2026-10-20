# GP 规则：运行 1，第 5 代，代理分（15 个训练实例 × 67 个基因）0.8221
# 复用树 9 个节点、深度 3；新开树 15 个节点、深度 5（导出时已折叠常数子树）

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


def pr_reuse(g_rem_frac, g_shift_frac, g_open_frac, g_cap_ratio, g_n_avail, g_no_avail, t_work_rel, t_cycle_over_work, t_maint_over_cycle, t_duties_per_maint, t_fits_rem, t_maint_before_end, t_overhead, r_count_rel, r_hours_rel, r_duties_left_frac, r_last_before_maint, r_idle, r_maint_done, r_rank_avail, r_open_order, r_maint_finishes):
    return ((max(g_cap_ratio, g_open_frac) + (r_maint_finishes - g_cap_ratio)) + g_open_frac)


def pr_new(g_rem_frac, g_shift_frac, g_open_frac, g_cap_ratio, g_n_avail, g_no_avail, t_work_rel, t_cycle_over_work, t_maint_over_cycle, t_duties_per_maint, t_fits_rem, t_maint_before_end, t_overhead, n_left_frac, n_is_gene_type, n_gene_offset, n_type_opened):
    return (min((((g_shift_frac - t_cycle_over_work) * min(g_no_avail, n_gene_offset)) - t_work_rel), (n_type_opened - t_work_rel)) * g_no_avail)


def pdiv(a, b):
    # 保护除法：分母接近 0 时取 1
    return a / b if abs(b) > 1e-6 else 1.0


def rule(ctx):
    # 复用候选用 pr_reuse 打分、新开候选用 pr_new 打分，全部按分数从高到低排序（并列保持原顺序）
    acts, rows = feats(ctx)
    if len(acts) <= 1:
        return acts if acts else [("new", ctx.gene_type)]
    sc = []
    for a, x in zip(acts, rows):
        s = pr_reuse(*x) if a[0] == "reuse" else pr_new(*x)
        if not (s == s and abs(s) < 1e300):
            s = -1e300
        sc.append(s)
    order = sorted(range(len(acts)), key=lambda i: -sc[i])
    return [acts[i] for i in order]
