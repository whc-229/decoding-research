def rule(ctx):
    available = ctx.available
    if available:
        min_count = min(r.count for r in available)
    else:
        min_count = 0

    def reuse_key(r):
        p = ctx.types[r.type]
        if p is not None:
            wt = p["work_time"]
        else:
            wt = 10.0
        over = wt - ctx.remaining
        if over < 0:
            over = 0.0
        band = r.count - min_count
        if band < 0:
            band = 0
        if band <= 1:
            band_pen = 0
        else:
            band_pen = band
        return (band_pen, over, r.duties_left, r.hours, -r.budget, r.idx)

    reuses = sorted(available, key=reuse_key)

    remaining = ctx.remaining
    if remaining < 0:
        remaining = 0.0

    def type_key(k):
        p = ctx.types[k]
        if p is None or ctx.left[k] <= 0:
            return (1, 0, 0, 0, 0, 0, 0, 0, k)
        wt = p["work_time"]
        if wt <= 0:
            wt = 1.0
        over = wt - remaining
        if over < 0:
            over = 0.0
        if remaining > 0:
            waste = (remaining % wt) / wt
        else:
            waste = 0.0
        single = p["single_work_time"]
        cmw = p["continue_max_work"]
        mt = p["maintenance_time"]
        ct = p["charge_time"]
        out = p["out_travel_time"]
        ret = p["return_travel_time"]
        if single > 0:
            dpm = cmw / single
        else:
            dpm = 1.0
        if dpm < 1.0:
            dpm = 1.0
        denom = out + wt + ret + ct + mt / dpm
        if denom <= 0:
            denom = 1.0
        eff = wt / denom
        gene_pen = 0 if k == ctx.gene_type else 1
        return (1 if over > 0 else 0, over, gene_pen, waste, -eff, mt / dpm, -dpm, -wt, k)

    new_order = []
    for k in sorted(range(len(ctx.types)), key=type_key):
        p = ctx.types[k]
        if p is not None and ctx.left[k] > 0:
            new_order.append(k)

    actions = [("reuse", r) for r in reuses]
    for k in new_order:
        actions.append(("new", k))

    if not new_order:
        gt = ctx.gene_type
        if 0 <= gt < len(ctx.types):
            actions.append(("new", gt))

    return actions
