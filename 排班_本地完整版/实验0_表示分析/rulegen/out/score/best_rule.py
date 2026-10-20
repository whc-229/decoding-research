def rule(ctx):
    # Compute average duty length for load balancing
    total_hours = 0.0
    total_count = 0
    for r in ctx.robots:
        total_hours += r.hours
        total_count += r.count
    avg_wt = total_hours / total_count if total_count > 0 else 10.0

    # Capacity slack ratio
    slack = ctx.capacity - ctx.remaining
    if ctx.remaining > 0:
        alpha = slack / ctx.remaining
        if alpha < 0.0:
            alpha = 0.0
        elif alpha > 1.0:
            alpha = 1.0
    else:
        alpha = 1.0

    remaining = ctx.remaining

    # Check if any available robot can fit the remaining horizon without overshooting
    has_fitting = False
    for r in ctx.available:
        if ctx.types[r.type]['work_time'] <= remaining:
            has_fitting = True
            break

    def score(r):
        t = ctx.types[r.type]
        cycle = t['work_time'] + t['out_travel_time'] + t['return_travel_time'] + t['charge_time']
        # Urgency: lower duties_left means more urgent. Adding maintenance_time
        # slightly prioritizes robots with shorter maintenance so they return sooner.
        urgency = r.duties_left * cycle + t['maintenance_time']
        # Load: balance both duty hours and duty counts.
        load = r.hours + r.count * avg_wt
        # Convex combination: tight capacity -> urgency; loose capacity -> balance.
        s = (1.0 - alpha) * urgency + alpha * load
        # Horizon fit penalty if a fitting robot exists.
        if has_fitting and t['work_time'] > remaining:
            s += 10000.0
        return s

    sorted_avail = sorted(ctx.available, key=lambda r: (score(r), r.count, r.hours, r.idx))

    actions = [("reuse", r) for r in sorted_avail]

    # New robot type preference
    valid = []
    for k in range(len(ctx.types)):
        t = ctx.types[k]
        if t is not None and ctx.left[k] > 0:
            valid.append(k)

    if valid:
        opened_types = set()
        for r in ctx.robots:
            opened_types.add(r.type)

        def new_key(k):
            t = ctx.types[k]
            wt = t['work_time']
            swt = t['single_work_time']
            cmw = t['continue_max_work']
            mt = t['maintenance_time']
            out_t = t['out_travel_time']
            ret_t = t['return_travel_time']
            ch_t = t['charge_time']
            cycle = wt + out_t + ret_t + ch_t
            duties = cmw // swt if swt > 0 else 0
            capacity_before_maint = duties * wt
            overshoot = 1 if wt > remaining else 0
            existing = 1 if k in opened_types else 0
            total_cycle_time = duties * cycle + mt
            eff = capacity_before_maint / total_cycle_time if total_cycle_time > 0 else 0.0
            return (overshoot, -existing, -eff, mt, -cmw, k)

        valid.sort(key=new_key)
        if ctx.gene_type in valid:
            valid.remove(ctx.gene_type)
            valid.insert(0, ctx.gene_type)

        actions.extend(("new", k) for k in valid)

    return actions
