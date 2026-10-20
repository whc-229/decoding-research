def rule(ctx):
    def val(t, name, default):
        if t is None:
            return default
        v = t.get(name, default)
        return default if v is None else v

    remaining = ctx.remaining
    capacity = ctx.capacity
    if capacity is None:
        capacity = 0.0
    slack = capacity - remaining
    afford_maint = slack > max(24.0, 0.18 * remaining)

    def robot_key(r):
        t = ctx.types[r.type] if 0 <= r.type < len(ctx.types) else None
        work = val(t, 'work_time', 10.0)
        if work <= 0:
            work = 1.0
        single = val(t, 'single_work_time', 1.0)
        if single <= 0:
            single = 1.0
        dl = r.duties_left
        if dl is None:
            dl = int(r.budget / single)
        idle = 0.0
        if r.last_end is not None:
            idle = ctx.t - r.last_end
            if idle < 0:
                idle = 0.0
        if afford_maint:
            return (dl, r.count, r.hours, -idle, r.idx)
        return (r.count, r.hours, -dl, -idle, r.idx)

    actions = []
    for r in sorted(ctx.available, key=robot_key):
        actions.append(("reuse", r))

    def type_key(k):
        t = ctx.types[k]
        work = val(t, 'work_time', 10.0)
        if work <= 0:
            work = 1.0
        out = val(t, 'out_travel_time', 0.0)
        ret = val(t, 'return_travel_time', 0.0)
        charge = val(t, 'charge_time', 0.0)
        maint = val(t, 'maintenance_time', 0.0)
        single = val(t, 'single_work_time', 1.0)
        if single <= 0:
            single = 1.0
        maxw = val(t, 'continue_max_work', 1.0)
        if maxw <= 0:
            maxw = 1.0
        cycle = work + out + ret + charge
        if cycle <= 0:
            cycle = 1.0
        duties = maxw / single
        if duties < 1.0:
            duties = 1.0
        time_to_maint = duties * cycle
        overshoot = 0.0
        if work > remaining:
            overshoot = work - remaining
        denom = time_to_maint + maint
        burden = maint / denom if denom > 0 else 0.0
        can_cover = 0 if time_to_maint >= remaining else 1
        return (can_cover, burden, -duties, overshoot, k)

    candidates = []
    for k in range(len(ctx.types)):
        if ctx.types[k] is not None and k < len(ctx.left) and ctx.left[k] > 0:
            candidates.append(k)

    ordered_types = []
    gt = ctx.gene_type
    if gt is not None and 0 <= gt < len(ctx.types) and ctx.types[gt] is not None and gt < len(ctx.left) and ctx.left[gt] > 0:
        ordered_types.append(gt)
    for k in sorted(candidates, key=type_key):
        if k not in ordered_types:
            ordered_types.append(k)

    for k in ordered_types:
        actions.append(("new", k))

    if not actions:
        fallback = ctx.gene_type
        if fallback is None or fallback < 0 or fallback >= len(ctx.types) or ctx.types[fallback] is None:
            fallback = 0
        actions.append(("new", fallback))

    return actions
