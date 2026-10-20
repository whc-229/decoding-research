def rule(ctx):
    # Average duty length of opened robots (fallback: all types)
    if ctx.robots:
        total_w = 0.0
        for r in ctx.robots:
            tp = ctx.types[r.type]
            if tp is not None:
                total_w += tp["work_time"]
            else:
                total_w += 10.0
        avg_work = total_w / len(ctx.robots)
    else:
        total_w = 0.0
        n = 0
        for k in range(len(ctx.types)):
            tp = ctx.types[k]
            if tp is not None:
                total_w += tp["work_time"]
                n += 1
        avg_work = total_w / n if n > 0 else 10.0
    if avg_work <= 0.0:
        avg_work = 10.0

    R = ctx.remaining
    Ncur = len(ctx.robots)
    if Ncur < 2:
        Ncur = 2
    den = Ncur - 1
    if den < 1:
        den = 1

    items = []
    min_load = None

    for r in ctx.available:
        tp = ctx.types[r.type]
        if tp is not None:
            w = tp["work_time"]
            single = tp["single_work_time"]
            cont = tp["continue_max_work"]
            maint = tp["maintenance_time"]
        else:
            w = 10.0
            single = 10.0
            cont = 10.0
            maint = 0.0

        if w is None or w <= 0.0:
            w = 10.0
        if single is None or single <= 0.0:
            single = w
        if cont is None or cont <= 0.0:
            cont = single
        if maint is None or maint < 0.0:
            maint = 0.0

        M = int(cont / single)
        if M < 1:
            M = 1

        preserve = (maint > 0.0 and R < maint)
        if preserve:
            K = 0
        else:
            if maint > 0.0 and w > 0.0:
                req = maint / (w * den)
                K = int(req)
                if K < req - 1e-9:
                    K += 1
                if K < 1:
                    K = 1
                if K > M:
                    K = M
            else:
                K = 0

        load = r.count + r.hours / avg_work
        inc = 1.0 + w / avg_work
        progress = (M - r.duties_left) / float(M)
        if progress < 0.0:
            progress = 0.0
        if progress > 1.0:
            progress = 1.0

        danger = 0
        if maint > 0.0 and R < maint and r.duties_left <= 1:
            danger = 1

        items.append((r, w, M, K, load, inc, progress, preserve, maint, danger))
        if min_load is None or load < min_load:
            min_load = load

    if min_load is None:
        min_load = 0.0

    scored = []
    for it in items:
        r, w, M, K, load, inc, progress, preserve, maint, danger = it
        allowed = 0 if load <= min_load + K * inc + 1e-9 else 1
        maint_flag = 0 if r.first_maint is None else 1

        # Before the horizon, push one maintenance cycle forward.
        # Near the horizon, preserve robots with fresh budgets instead.
        if preserve:
            prog_key = progress
        else:
            prog_key = -progress

        if allowed == 0:
            key = (0, danger, prog_key, maint_flag, load, -r.duties_left, r.idx, r)
        else:
            key = (1, danger, load, prog_key, maint_flag, -r.duties_left, r.idx, r)
        scored.append((key, r))

    scored.sort(key=lambda x: x[0])
    actions = [("reuse", r) for _, r in scored]

    # New-robot type preferences
    new_prefs = []
    for k in range(len(ctx.types)):
        tp = ctx.types[k]
        if tp is None:
            continue
        if ctx.left[k] <= 0:
            continue

        w = tp["work_time"]
        out = tp["out_travel_time"]
        ret = tp["return_travel_time"]
        charge = tp["charge_time"]
        maint = tp["maintenance_time"]
        single = tp["single_work_time"]
        cont = tp["continue_max_work"]

        if w is None or w <= 0.0:
            w = 10.0
        if single is None or single <= 0.0:
            single = w
        if cont is None or cont <= 0.0:
            cont = single
        if out is None:
            out = 0.0
        if ret is None:
            ret = 0.0
        if charge is None:
            charge = 0.0
        if maint is None or maint < 0.0:
            maint = 0.0

        duties_per_cycle = int(cont / single)
        if duties_per_cycle < 1:
            duties_per_cycle = 1

        ct = out + w + ret + charge
        if ct <= 0.0:
            ct = w

        if R > 0.0:
            exp_duties = R / ct
        else:
            exp_duties = 1.0
        if exp_duties < 1.0:
            exp_duties = 1.0

        if exp_duties >= duties_per_cycle:
            eff_time = ct + maint / duties_per_cycle
        else:
            eff_time = ct

        efficiency = w / eff_time if eff_time > 0.0 else 0.0
        fit = 0 if (R <= 0.0 or w <= R + 1e-9) else 1

        if fit == 0:
            new_prefs.append((0, -efficiency, -w, k))
        else:
            new_prefs.append((1, w, -efficiency, k))

    new_prefs.sort()
    for entry in new_prefs:
        actions.append(("new", entry[-1]))

    if not actions:
        actions.append(("new", ctx.gene_type))
    return actions
