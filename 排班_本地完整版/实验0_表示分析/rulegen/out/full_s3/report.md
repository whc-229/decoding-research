# 规则生成结果（full_s3）

LLM 调用 53 次；候选 54 条，其中出错 0 条。

| 规则 | 来源 | 代 | 得分 | 对默认 | E 组 | H 组 | M 组 |
|---|---|---|---|---|---|---|---|
| r36 | crossover r27,r8 | 7 | 0.8170 | +0.0540 | +0.138 | +0.024 | +0.000 |
| r40 | crossover r34,r27 | 8 | 0.8170 | +0.0540 | +0.138 | +0.024 | +0.000 |
| r44 | crossover r40,r27 | 9 | 0.8170 | +0.0540 | +0.138 | +0.024 | +0.000 |
| r48 | crossover r38,r40 | 10 | 0.8170 | +0.0540 | +0.138 | +0.024 | +0.000 |
| r47 | explore r39,r34 | 10 | 0.8147 | +0.0517 | +0.140 | +0.017 | -0.001 |
| r52 | crossover r40,r47 | 11 | 0.8140 | +0.0510 | +0.136 | +0.017 | +0.000 |
| r51 | explore r40,r27 | 11 | 0.8132 | +0.0502 | +0.140 | +0.034 | -0.023 |
| r27 | explore r22,r19 | 5 | 0.8077 | +0.0446 | +0.138 | +0.024 | -0.028 |
| r45 | refine r39 | 9 | 0.8052 | +0.0421 | +0.140 | +0.018 | -0.031 |
| r39 | explore r27,r36 | 8 | 0.8046 | +0.0416 | +0.140 | +0.017 | -0.032 |
| r50 | refine r39 | 11 | 0.8028 | +0.0397 | +0.140 | +0.017 | -0.037 |
| r46 | refine r39 | 10 | 0.8005 | +0.0375 | +0.142 | -0.006 | -0.024 |
| r53 | refine r47 | 11 | 0.8003 | +0.0372 | +0.140 | +0.017 | -0.045 |
| r49 | refine r39 | 10 | 0.8000 | +0.0369 | +0.140 | +0.017 | -0.046 |
| r38 | refine r36 | 8 | 0.7995 | +0.0365 | +0.138 | +0.024 | -0.052 |
| r34 | refine r28 | 7 | 0.7947 | +0.0317 | +0.098 | -0.003 | +0.000 |
| r28 | crossover r19,r10 | 5 | 0.7946 | +0.0316 | +0.098 | -0.003 | +0.000 |
| r22 | refine r18 | 4 | 0.7946 | +0.0316 | +0.098 | -0.003 | +0.000 |
| r33 | refine r8 | 6 | 0.7946 | +0.0316 | +0.098 | -0.003 | +0.000 |
| r8 | crossover r1,r0 | 0 | 0.7941 | +0.0311 | +0.098 | -0.004 | +0.000 |
| r16 | crossover r8,r7 | 2 | 0.7941 | +0.0311 | +0.098 | -0.004 | +0.000 |
| r32 | crossover r28,r19 | 6 | 0.7936 | +0.0305 | +0.094 | -0.003 | +0.000 |
| r42 | refine r34 | 9 | 0.7935 | +0.0304 | +0.098 | -0.006 | +0.000 |
| r10 | refine r8 | 1 | 0.7926 | +0.0296 | +0.098 | -0.009 | +0.000 |
| r19 | explore r10,r11 | 3 | 0.7926 | +0.0296 | +0.095 | -0.003 | -0.004 |
| r18 | refine r14 | 3 | 0.7925 | +0.0295 | +0.098 | -0.009 | +0.000 |
| r20 | crossover r8,r7 | 3 | 0.7925 | +0.0295 | +0.098 | -0.009 | +0.000 |
| r21 | refine r14 | 3 | 0.7925 | +0.0295 | +0.098 | -0.009 | +0.000 |
| r30 | refine r10 | 6 | 0.7919 | +0.0289 | +0.098 | -0.011 | +0.000 |
| r14 | refine r10 | 2 | 0.7882 | +0.0252 | +0.098 | -0.022 | +0.000 |
| r1 | init r0 | 0 | 0.7868 | +0.0238 | +0.076 | -0.005 | +0.000 |
| r7 | explore r1,r4 | 0 | 0.7857 | +0.0227 | +0.076 | -0.008 | +0.000 |
| r23 | explore r8,r1 | 4 | 0.7810 | +0.0180 | +0.076 | -0.006 | -0.015 |
| r11 | explore r1,r8 | 1 | 0.7767 | +0.0137 | +0.098 | -0.009 | -0.048 |
| r25 | refine r8 | 4 | 0.7767 | +0.0136 | +0.098 | -0.009 | -0.048 |
| r9 | refine r3 | 0 | 0.7764 | +0.0134 | +0.019 | +0.021 | +0.000 |
| r13 | refine r8 | 1 | 0.7753 | +0.0123 | +0.098 | -0.013 | -0.048 |
| r37 | refine r8 | 7 | 0.7746 | +0.0115 | +0.098 | -0.015 | -0.048 |
| r15 | explore r7,r8 | 2 | 0.7729 | +0.0098 | +0.089 | -0.020 | -0.040 |
| r41 | refine r33 | 8 | 0.7673 | +0.0042 | +0.098 | -0.085 | +0.000 |
| r6 | refine r3 | 0 | 0.7660 | +0.0030 | +0.019 | +0.022 | -0.032 |
| r3 | init r0 | 0 | 0.7642 | +0.0012 | +0.019 | +0.021 | -0.037 |
| r0 | default  | 0 | 0.7630 | +0.0000 | +0.000 | +0.000 | +0.000 |
| r4 | init r0 | 0 | 0.7622 | -0.0008 | +0.000 | +0.001 | -0.003 |
| r29 | refine r8 | 5 | 0.7620 | -0.0011 | +0.098 | -0.101 | +0.000 |
| r17 | refine r11 | 2 | 0.7606 | -0.0024 | +0.094 | -0.016 | -0.085 |
| r35 | explore r28,r10 | 7 | 0.7591 | -0.0039 | +0.036 | -0.009 | -0.039 |
| r26 | refine r19 | 5 | 0.7561 | -0.0070 | +0.027 | -0.008 | -0.040 |
| r31 | explore r19,r27 | 6 | 0.7521 | -0.0109 | -0.002 | +0.002 | -0.033 |
| r2 | init r0 | 0 | 0.7488 | -0.0142 | +0.000 | -0.011 | -0.032 |
| r24 | crossover r8,r18 | 4 | 0.7446 | -0.0184 | +0.096 | -0.108 | -0.044 |
| r5 | init r0 | 0 | 0.6975 | -0.0655 | -0.077 | -0.015 | -0.105 |
| r43 | explore r27,r34 | 9 | 0.6936 | -0.0694 | -0.020 | -0.026 | -0.162 |
| r12 | crossover r1,r8 | 1 | 0.6865 | -0.0766 | +0.098 | -0.092 | -0.235 |

## r36（得分 0.8170）

Idea: use the strongly balanced, maintenance-aware Rule 1 for uniform-duty instances (E/H), where it clearly wins, and switch to Rule 2’s simpler maintenance/budget ordering for mixed-duty-length instances (M), where its default choice and alternative ordering perform better. The new-robot ordering is also taken from the corresponding winning rule so resource decisions stay consistent with the selected mode.

```python
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
```

## r40（得分 0.8170）

The hybrid detects whether all robot types have the same duty length. Same-duty cases (groups E/H, including single-type instances) use the stronger Rule 2-style selection, maintenance-completion logic, and resource-cost ordering. Mixed-duty cases (group M) use Rule 1’s more conservative ordering and new-robot choice, which was more robust for varying duty lengths. This preserves each rule’s strongest regime while keeping a single deterministic decoder rule.

```python
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
            mt = info["maintenance_time"]
            if mt > max_maint:
                max_maint = mt
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

    same_duty = (min_duty is not None and max_duty_val - min_duty <= 1e-9)
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

    active = active_maint > 0
    cap_ok = ctx.capacity >= ctx.remaining - 1e-9
    avail_n = len(ctx.available)
    risky = (active_maint > 0 and
             (not cap_ok or active_maint >= max(1, avail_n - 1)))
    end_mode = ctx.remaining < max(max_maint, max_work) + 2.0 * max_duty
    single_mode = n_types <= 1
    congested = active_maint > 0 and ((not cap_ok) or
                                      active_maint >= max(1, len(ctx.robots) - 2))
    near_end = ctx.remaining < max_maint + 2.0 * max_duty

    if not same_duty:
        def new_actions_mixed():
            cand = []
            for k, info in enumerate(ctx.types):
                if info is not None and ctx.left[k] > 0:
                    w = info["work_time"]
                    fit = 0 if (ctx.remaining <= 0 or w <= ctx.remaining + 1e-9) else 1
                    gene = 0 if k == ctx.gene_type else 1
                    single = info["single_work_time"]
                    if single <= 0:
                        single = 1.0
                    dpm = info["continue_max_work"] / single
                    cand.append((fit, gene, -dpm,
                                 info["maintenance_time"], -w, k))
            if not cand:
                return [("new", ctx.gene_type)]
            cand.sort()
            return [("new", item[-1]) for item in cand]

        def key_mixed(r):
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

        ordered = sorted(ctx.available, key=key_mixed)
        actions = [("reuse", r) for r in ordered]
        actions.extend(new_actions_mixed())
        return actions

    def new_actions_same():
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
        return new_actions_same()

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
        (load, will, maint_comp, safe_fin, can_fin, w, mt,
         dl, budget, first_maint, idx, overshoot) = m

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
        (load, will, maint_comp, safe_fin, can_fin, w, mt,
         dl, budget, first_maint, idx, overshoot) = m

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
    actions.extend(new_actions_same())
    return actions
```

## r44（得分 0.8170）

The combined rule keeps Rule 1’s specialised mixed-duty reuse ordering (budget and maintenance-aware) while folding in Rule 2’s more robust new-robot selection: it considers fit, near-end minimum robot count, cost rate, and opened-type penalty, with the genome’s preferred type used as a tie-breaker. A load-based tie-breaker is added to the mixed-duty reuse order to improve balance without sacrificing the budget-first strategy that worked well for M instances.

```python
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
            mt = info["maintenance_time"]
            if mt > max_maint:
                max_maint = mt
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

    same_duty = (min_duty is not None and max_duty_val - min_duty <= 1e-9)
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

    active = active_maint > 0
    cap_ok = ctx.capacity >= ctx.remaining - 1e-9
    avail_n = len(ctx.available)
    end_mode = ctx.remaining < max(max_maint, max_work) + 2.0 * max_duty
    single_mode = n_types <= 1
    congested = active_maint > 0 and ((not cap_ok) or
                                      active_maint >= max(1, len(ctx.robots) - 2))
    near_end = ctx.remaining < max_maint + 2.0 * max_duty

    if not same_duty:
        def new_actions_mixed():
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
                    gene = 0 if k == ctx.gene_type else 1

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
                        key = (fit, n, extra, gene, cost_rate + opened_pen,
                               info["maintenance_time"], -dpm, -w, k)
                    else:
                        fit = 0 if ctx.remaining <= 0 or w <= ctx.remaining + 1e-9 else 1
                        overshoot = 0.0 if fit == 0 else w - ctx.remaining
                        key = (fit, gene, cost_rate + opened_pen, overshoot,
                               info["maintenance_time"], -dpm, -w, k)
                    cand.append((key, k))

            if not cand:
                return [("new", ctx.gene_type)]
            cand.sort()
            return [("new", item[1]) for item in cand]

        def key_mixed(r):
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
            load = r.count + r.hours / avg_duty
            return (1, r.budget, load, r.count, r.hours, r.idx)

        ordered = sorted(ctx.available, key=key_mixed)
        actions = [("reuse", r) for r in ordered]
        actions.extend(new_actions_mixed())
        return actions

    def new_actions_same():
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
        return new_actions_same()

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
        (load, will, maint_comp, safe_fin, can_fin, w, mt,
         dl, budget, first_maint, idx, overshoot) = m

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
        (load, will, maint_comp, safe_fin, can_fin, w, mt,
         dl, budget, first_maint, idx, overshoot) = m

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
    actions.extend(new_actions_same())
    return actions
```
