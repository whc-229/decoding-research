def rule(ctx):
    def work_hours(r):
        th = ctx.types[r.type]
        if th is None:
            return 0.0
        return float(th.get("work_time", 0))

    robots = ctx.robots
    n_robots = len(robots)

    if n_robots:
        min_count = min(r.count for r in robots)
        min_hours = min(r.hours for r in robots)
        avg_work = sum(work_hours(r) for r in robots) / float(n_robots)
    else:
        min_count = 0
        min_hours = 0.0
        avg_work = 10.0

    if avg_work < 1.0:
        avg_work = 1.0

    remaining = ctx.remaining
    if remaining < 1.0:
        remaining = 1.0

    if remaining > 20.0 * avg_work:
        fair_count_gap = 2
        fair_hour_gap = 2.2 * avg_work
        phase_strength = 0.45
    elif remaining > 8.0 * avg_work:
        fair_count_gap = 1
        fair_hour_gap = 1.3 * avg_work
        phase_strength = 0.30
    else:
        fair_count_gap = 0
        fair_hour_gap = 0.6 * avg_work
        phase_strength = 0.15

    t = ctx.t

    def avail_key(r):
        th = ctx.types[r.type]
        work = float(th.get("work_time", 0)) if th is not None else 0.0
        if work < 1.0:
            work = 1.0

        over_count = r.count - min_count - fair_count_gap
        if over_count < 0:
            over_count = 0

        over_hours = r.hours - min_hours - fair_hour_gap
        if over_hours < 0:
            over_hours = 0.0

        phase = (r.idx % 4) * (phase_strength * work)
        pressure = float(r.budget) + phase

        if r.last_end is None:
            idle = 1000000.0 + float(ctx.shift)
        else:
            idle = t - r.last_end

        return (over_count, over_hours, pressure, -idle, r.ready, r.idx)

    avail = sorted(ctx.available, key=avail_key)
    actions = [("reuse", r) for r in avail]

    type_count = len(ctx.types)

    def type_key(k):
        th = ctx.types[k]
        if th is None or ctx.left[k] <= 0:
            return (1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, k)

        work = float(th.get("work_time", 0))
        out = float(th.get("out_travel_time", 0))
        ret = float(th.get("return_travel_time", 0))
        charge = float(th.get("charge_time", 0))
        maint = float(th.get("maintenance_time", 0))
        sw = float(th.get("single_work_time", 0))
        cmw = float(th.get("continue_max_work", 0))

        if work < 0.1:
            work = 0.1

        if sw > 0.0 and cmw > 0.0:
            cycle_duties = cmw / sw
        else:
            cycle_duties = 1.0

        if cycle_duties < 1.0:
            cycle_duties = 1.0

        busy = work + out + ret + charge
        denom = busy + maint / cycle_duties
        if denom > 0.0:
            eff = work / denom
        else:
            eff = 0.0

        if work > remaining:
            overshoot = (work - remaining) / remaining
        else:
            overshoot = 0.0

        rem_mod = remaining % work
        alt = work - rem_mod
        waste = rem_mod if rem_mod < alt else alt
        fit = waste / work

        already = 0
        for r in robots:
            if r.type == k:
                already = 1
                break
        type_penalty = 0 if already else 1
        gene_penalty = 0 if k == ctx.gene_type else 1

        return (
            0,
            overshoot,
            type_penalty,
            -eff,
            fit,
            gene_penalty,
            maint / (remaining + 1.0),
            -float(ctx.left[k]),
            k
        )

    valid_new = []
    for k in range(type_count):
        if ctx.types[k] is not None and ctx.left[k] > 0:
            valid_new.append(k)

    valid_new.sort(key=type_key)
    actions.extend(("new", k) for k in valid_new)
    return actions
