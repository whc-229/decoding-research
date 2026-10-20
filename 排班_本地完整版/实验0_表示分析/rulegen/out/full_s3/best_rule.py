def rule(ctx):
    def get_info(k):
        if k is None or k < 0 or k >= len(ctx.types):
            return None
        return ctx.types[k]

    max_maint = 0.0
    max_duty = 0.0
    max_work = 0.0
    min_duty = None
    max_duty_val = 0.0
    n_types = 0
    sum_type_w = 0.0

    for info in ctx.types:
        if info is not None:
            n_types += 1
            if info["maintenance_time"] > max_maint:
                max_maint = info["maintenance_time"]
            w = info["work_time"]
            if w > max_duty:
                max_duty = w
            if info["continue_max_work"] > max_work:
                max_work = info["continue_max_work"]
            sum_type_w += w
            if min_duty is None:
                min_duty = w
                max_duty_val = w
            else:
                if w < min_duty:
                    min_duty = w
                if w > max_duty_val:
                    max_duty_val = w

    if min_duty is None:
        min_duty = 0.0

    mixed_duty = n_types > 1 and (max_duty_val - min_duty > 1e-9)

    if mixed_duty:
        active = False
        for r in ctx.robots:
            if r.ready > ctx.t:
                info = get_info(r.type)
                if info is not None:
                    thresh = (info["charge_time"] + info["work_time"] +
                              info["out_travel_time"] + info["return_travel_time"] + 1.0)
                    if r.ready - ctx.t > thresh:
                        active = True
                        break

        def new_actions_mixed():
            cand = []
            for k, info in enumerate(ctx.types):
                if info is not None and ctx.left[k] > 0:
                    work = info["work_time"]
                    fit = 0 if ctx.remaining <= 0 or work <= ctx.remaining + 1e-9 else 1
                    gene = 0 if k == ctx.gene_type else 1
                    single = info["single_work_time"]
                    if single <= 0:
                        single = 1.0
                    dpm = info["continue_max_work"] / single
                    cand.append((fit, gene, -dpm, info["maintenance_time"], -work, k))
            if not cand:
                return [("new", ctx.gene_type)]
            cand.sort()
            return [("new", item[-1]) for item in cand]

        new_list = new_actions_mixed()
        if not ctx.available:
            return new_list

        end_mode = ctx.remaining < max(max_maint, max_work) + 2.0 * max_duty
        single_mode = n_types <= 1

        def sort_key_mixed(r):
            info = get_info(r.type)
            if info is None:
                return (9, r.count, r.idx)

            duty = info["work_time"]
            maint = info["maintenance_time"]
            due = r.budget
            will = r.duties_left <= 1
            safe_will = will and ctx.remaining <= duty + 1e-9

            if end_mode:
                if will and not safe_will:
                    if active:
                        return (2, -r.count, r.hours, maint, r.idx)
                    return (1, -r.count, r.hours, maint, r.idx)

                if safe_will:
                    safe_rank = 0
                else:
                    if ctx.remaining <= duty + 1e-9:
                        safe_rank = 0
                    else:
                        safe_rank = 0 if r.duties_left > 2 else 1
                return (0, safe_rank, r.count, -r.duties_left, r.hours, r.idx)

            if active:
                if will:
                    return (1, -r.count, maint, -due, r.idx)
                safe_rank = 0 if r.duties_left > 2 else 1
                return (0, safe_rank, r.count, -r.duties_left, -due, r.hours, r.idx)

            if will:
                return (0, -r.count, r.hours, maint, due, r.idx)

            if single_mode:
                return (1, r.count, -r.duties_left, r.hours, due, r.idx)

            return (1, r.budget, r.count, r.hours, r.idx)

        ordered = sorted(ctx.available, key=sort_key_mixed)
        actions = [("reuse", r) for r in ordered]
        actions.extend(new_list)
        return actions

    avg_type_w = sum_type_w / n_types if n_types > 0 else 10.0
    if avg_type_w <= 1e-9:
        avg_type_w = 10.0

    opened_of_type = [0] * len(ctx.types)
    sum_opened_w = 0.0
    n_opened = 0

    for r in ctx.robots:
        info = get_info(r.type)
        if info is not None:
            if 0 <= r.type < len(opened_of_type):
                opened_of_type[r.type] += 1
            sum_opened_w += info["work_time"]
            n_opened += 1

    avg_duty = sum_opened_w / n_opened if n_opened > 0 else avg_type_w
    if avg_duty <= 1e-9:
        avg_duty = 10.0

    active_maint = 0
    for r in ctx.robots:
        info = get_info(r.type)
        if info is not None and r.ready > ctx.t:
            thr = (info["charge_time"] + info["work_time"] +
                   info["out_travel_time"] + info["return_travel_time"] + 1.0)
            if r.ready - ctx.t > thr:
                active_maint += 1

    cap_ok = ctx.capacity >= ctx.remaining - 1e-9
    congested = active_maint > 0 and ((not cap_ok) or
                                      active_maint >= max(1, len(ctx.robots) - 2))
    near_end = ctx.remaining < max_maint + 2.0 * max_duty

    def new_actions_uniform():
        cand = []
        for k, info in enumerate(ctx.types):
            if info is not None and ctx.left[k] > 0:
                w = info["work_time"]
                if w <= 0:
                    w = 1e-9
                single = info["single_work_time"]
                if single <= 0:
                    single = w
                dpm = info["continue_max_work"] / single
                if dpm < 1e-9:
                    dpm = 1e-9
                cycle = (w + info["out_travel_time"] +
                         info["return_travel_time"] + info["charge_time"])
                if cycle <= 1e-9:
                    cycle = w + 1.0
                cost_rate = (cycle + info["maintenance_time"] / dpm) / w
                opened_pen = 0.0 if opened_of_type[k] > 0 else 0.45

                if near_end:
                    if w <= ctx.remaining + 1e-9:
                        fit = 0
                        n = int(-((-ctx.remaining) // w))
                        if n < 1:
                            n = 1
                        extra = n * w - ctx.remaining
                    else:
                        fit = 1
                        n = 1
                        extra = w - ctx.remaining
                    key = (fit, n, extra, opened_pen, cost_rate,
                           info["maintenance_time"], -dpm, k)
                else:
                    fit = 0 if ctx.remaining <= 0 or w <= ctx.remaining + 1e-9 else 1
                    overshoot = 0.0 if fit == 0 else w - ctx.remaining
                    score = cost_rate + opened_pen
                    key = (fit, overshoot, score, info["maintenance_time"],
                           -dpm, -w, k)
                cand.append((key, k))

        if not cand:
            return [("new", ctx.gene_type)]
        cand.sort()
        return [("new", item[1]) for item in cand]

    if not ctx.available:
        return new_actions_uniform()

    items = []
    for r in ctx.available:
        info = get_info(r.type)
        if info is None:
            w = 10.0
            mt = 0.0
            charge = 0.0
            out = 0.0
            ret = 0.0
            single = 10.0
            dpm = 1.0
        else:
            w = info["work_time"]
            if w <= 0:
                w = 1e-9
            mt = info["maintenance_time"]
            charge = info["charge_time"]
            out = info["out_travel_time"]
            ret = info["return_travel_time"]
            single = info["single_work_time"]
            if single <= 0:
                single = w
            dpm = info["continue_max_work"] / single
            if dpm < 1e-9:
                dpm = 1e-9

        load = r.count + r.hours / avg_duty
        will = r.duties_left <= 1
        return_gap = w + out + ret + mt + charge
        maint_comp = ctx.remaining > return_gap + 1e-9
        safe_fin = ctx.remaining <= w + 1e-9
        can_fin = r.duties_left * w >= ctx.remaining - 1e-9
        overshoot = (w - ctx.remaining) if safe_fin else 0.0
        if overshoot < 0.0:
            overshoot = 0.0

        items.append((r, (load, will, maint_comp, safe_fin, can_fin,
                          w, mt, r.duties_left, r.budget,
                          r.first_maint, r.idx, overshoot)))

    def default_key(item):
        r, m = item
        load, will, maint_comp, safe_fin, can_fin, w, mt, dl, budget, first_maint, idx, overshoot = m

        if safe_fin:
            return (0, overshoot, load, -dl, idx)

        if near_end:
            if (not will) and can_fin:
                return (1, load, -dl, budget, idx)
            if not will:
                return (2, load, -dl, budget, idx)
            if maint_comp:
                return (3, -load, dl, mt, idx)
            return (4, -load, dl, mt, idx)

        if will:
            if maint_comp and not congested:
                return (0, -load, dl, mt, idx)
            return (3, -load, dl, mt, idx)

        return (1, load, -dl, -budget, idx)

    default_sorted = sorted(items, key=default_key)
    first_item = default_sorted[0]
    first_r = first_item[0]
    first_will = first_item[1][1]
    rest = [item for item in items if item[0] is not first_r]

    def explore_key(item):
        r, m = item
        load, will, maint_comp, safe_fin, can_fin, w, mt, dl, budget, first_maint, idx, overshoot = m

        if safe_fin:
            return (0, overshoot, -load, idx)

        if first_will:
            if not will:
                return (1, load, -dl, budget, idx)
            return (2, 0 if maint_comp else 1, -load, dl, mt, idx)

        if will:
            return (1, 0 if maint_comp else 1, -load, dl, mt, idx)
        return (2, load, -dl, budget, idx)

    explore_sorted = sorted(rest, key=explore_key)
    actions = [("reuse", first_r)]
    for item in explore_sorted:
        actions.append(("reuse", item[0]))
    actions.extend(new_actions_uniform())
    return actions
