def rule(ctx):
    avail = ctx.available
    types = ctx.types

    if not avail:
        valid = []
        for k in range(len(types)):
            if types[k] is not None and ctx.left[k] > 0:
                valid.append(k)
        if not valid:
            return [("new", ctx.gene_type)]

        existing_types = set()
        for r in ctx.robots:
            existing_types.add(r.type)

        def tkey(k):
            typ = types[k]
            cm = typ.get('continue_max_work', 0) or 0
            sw = typ.get('single_work_time', 1) or 1
            if sw <= 0:
                sw = 1
            wt = typ.get('work_time', 1) or 1
            out = typ.get('out_travel_time', 0) or 0
            ret = typ.get('return_travel_time', 0) or 0
            ct = typ.get('charge_time', 0) or 0
            mt = typ.get('maintenance_time', 0) or 0

            duties = cm / sw
            cycle = out + wt + ret + ct
            denom = duties * cycle + mt
            frac = (duties * wt) / denom if denom > 0 else 0.0

            fit = 0 if wt <= ctx.remaining + 1e-9 else 1
            existing_bonus = 0.25 if k in existing_types else 0.0
            gene_bonus = 0.05 if k == ctx.gene_type else 0.0
            score = frac + existing_bonus + gene_bonus
            return (fit, -score, -ctx.left[k], k)

        return [("new", k) for k in sorted(valid, key=tkey)]

    n_avail = len(avail)
    n_opened = len(ctx.robots)

    total_wt = 0.0
    num = 0
    max_maint = 0.0
    for r in ctx.robots:
        typ = types[r.type] if r.type < len(types) else None
        if typ is not None:
            wt = typ.get('work_time', 10) or 10
            total_wt += wt
            num += 1
            mt = typ.get('maintenance_time', 0) or 0
            if mt > max_maint:
                max_maint = mt

    avg_wt = total_wt / num if num > 0 else 10.0
    if avg_wt <= 0:
        avg_wt = 10.0

    min_count = min(r.count for r in avail)

    def bal_key(r):
        typ = types[r.type] if r.type < len(types) else None
        wt = (typ.get('work_time', 10) or 10) if typ is not None else 10.0

        projected_count = r.count + 1
        projected_hours = r.hours + wt
        balance = projected_count + projected_hours / avg_wt

        urgent = (r.duties_left <= 1 and n_avail >= 2 and r.count <= min_count + 2)
        tier = 0 if urgent else 1

        return (tier, balance, r.count, r.hours,
                -r.duties_left, -r.budget, r.idx)

    wave_candidate = min(
        avail,
        key=lambda r: (r.budget, -r.count, -r.hours, r.idx)
    )
    early_enough = (max_maint <= 0) or (ctx.remaining > max_maint + 20.0)

    if n_opened <= 2 and early_enough:
        default = wave_candidate
    else:
        default = min(avail, key=bal_key)

    ordered = sorted(avail, key=bal_key)
    rest = [r for r in ordered if r is not default]

    return [("reuse", default)] + [("reuse", r) for r in rest]
