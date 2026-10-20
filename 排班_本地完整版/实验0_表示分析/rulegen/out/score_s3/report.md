# 规则生成结果（score_s3）

LLM 调用 55 次；候选 54 条，其中出错 0 条。

| 规则 | 来源 | 代 | 得分 | 对默认 | E 组 | H 组 | M 组 |
|---|---|---|---|---|---|---|---|
| r10 | refine r4 | 1 | 0.8206 | +0.0576 | +0.145 | +0.033 | -0.004 |
| r25 | refine r10 | 4 | 0.8206 | +0.0576 | +0.145 | +0.033 | -0.004 |
| r40 | crossover r10,r23 | 8 | 0.8195 | +0.0565 | +0.148 | +0.027 | -0.006 |
| r44 | crossover r10,r28 | 9 | 0.8189 | +0.0558 | +0.146 | +0.030 | -0.009 |
| r32 | crossover r23,r17 | 6 | 0.8180 | +0.0549 | +0.146 | +0.032 | -0.013 |
| r45 | refine r32 | 9 | 0.8180 | +0.0549 | +0.146 | +0.032 | -0.013 |
| r28 | crossover r23,r17 | 5 | 0.8163 | +0.0533 | +0.146 | +0.030 | -0.016 |
| r36 | crossover r10,r28 | 7 | 0.8163 | +0.0533 | +0.146 | +0.030 | -0.016 |
| r17 | refine r10 | 2 | 0.8163 | +0.0532 | +0.146 | +0.030 | -0.017 |
| r33 | refine r24 | 6 | 0.8158 | +0.0528 | +0.146 | +0.033 | -0.021 |
| r23 | explore r7,r10 | 4 | 0.8158 | +0.0528 | +0.142 | +0.031 | -0.014 |
| r15 | explore r13,r10 | 2 | 0.8153 | +0.0523 | +0.146 | +0.037 | -0.025 |
| r24 | crossover r10,r7 | 4 | 0.8152 | +0.0522 | +0.144 | +0.034 | -0.021 |
| r30 | refine r24 | 6 | 0.8152 | +0.0522 | +0.144 | +0.034 | -0.021 |
| r7 | explore r5,r1 | 0 | 0.8148 | +0.0518 | +0.146 | +0.034 | -0.025 |
| r18 | refine r17 | 3 | 0.8144 | +0.0514 | +0.146 | +0.030 | -0.022 |
| r20 | crossover r10,r17 | 3 | 0.8135 | +0.0505 | +0.136 | +0.036 | -0.021 |
| r22 | refine r10 | 4 | 0.8134 | +0.0504 | +0.138 | +0.026 | -0.013 |
| r16 | crossover r10,r7 | 2 | 0.8126 | +0.0496 | +0.148 | +0.020 | -0.019 |
| r52 | crossover r40,r44 | 11 | 0.8112 | +0.0482 | +0.147 | +0.023 | -0.026 |
| r21 | refine r12 | 3 | 0.8091 | +0.0460 | +0.136 | +0.021 | -0.019 |
| r12 | crossover r1,r0 | 1 | 0.8068 | +0.0438 | +0.133 | +0.019 | -0.021 |
| r13 | refine r1 | 1 | 0.8064 | +0.0433 | +0.107 | +0.038 | -0.014 |
| r1 | init r0 | 0 | 0.8057 | +0.0427 | +0.127 | +0.021 | -0.021 |
| r49 | refine r28 | 10 | 0.8019 | +0.0388 | +0.134 | +0.021 | -0.038 |
| r51 | explore r28,r40 | 11 | 0.8012 | +0.0382 | +0.134 | +0.020 | -0.040 |
| r43 | explore r10,r40 | 9 | 0.7980 | +0.0349 | +0.117 | +0.010 | -0.023 |
| r19 | explore r16,r17 | 3 | 0.7963 | +0.0332 | +0.119 | +0.009 | -0.029 |
| r38 | refine r23 | 8 | 0.7935 | +0.0305 | +0.142 | +0.031 | -0.081 |
| r35 | explore r33,r10 | 7 | 0.7691 | +0.0061 | +0.093 | -0.028 | -0.047 |
| r26 | refine r15 | 5 | 0.7633 | +0.0003 | -0.003 | +0.030 | -0.025 |
| r0 | default  | 0 | 0.7630 | +0.0000 | +0.000 | +0.000 | +0.000 |
| r31 | explore r24,r28 | 6 | 0.7596 | -0.0035 | +0.048 | -0.015 | -0.044 |
| r14 | refine r10 | 2 | 0.7536 | -0.0094 | +0.044 | -0.031 | -0.041 |
| r42 | refine r32 | 9 | 0.7512 | -0.0118 | +0.037 | -0.026 | -0.046 |
| r2 | init r0 | 0 | 0.7488 | -0.0142 | +0.000 | -0.011 | -0.032 |
| r37 | refine r17 | 7 | 0.7488 | -0.0142 | +0.000 | -0.011 | -0.032 |
| r8 | crossover r2,r1 | 0 | 0.7488 | -0.0142 | +0.000 | -0.011 | -0.032 |
| r29 | refine r23 | 5 | 0.7488 | -0.0142 | +0.024 | -0.016 | -0.050 |
| r11 | explore r7,r2 | 1 | 0.7487 | -0.0143 | +0.000 | -0.008 | -0.035 |
| r4 | init r0 | 0 | 0.7485 | -0.0145 | +0.000 | -0.012 | -0.032 |
| r27 | explore r15,r10 | 5 | 0.7470 | -0.0160 | -0.002 | -0.010 | -0.037 |
| r3 | init r0 | 0 | 0.7456 | -0.0174 | -0.045 | +0.004 | -0.012 |
| r48 | crossover r32,r10 | 10 | 0.7436 | -0.0194 | -0.017 | -0.005 | -0.037 |
| r9 | refine r1 | 0 | 0.7422 | -0.0208 | -0.017 | -0.011 | -0.035 |
| r41 | refine r32 | 8 | 0.7422 | -0.0208 | -0.017 | -0.011 | -0.035 |
| r39 | explore r32,r33 | 8 | 0.7421 | -0.0209 | +0.029 | -0.035 | -0.057 |
| r53 | refine r10 | 11 | 0.7417 | -0.0213 | -0.017 | -0.012 | -0.035 |
| r46 | refine r32 | 10 | 0.7408 | -0.0223 | -0.017 | -0.013 | -0.037 |
| r34 | refine r10 | 7 | 0.7378 | -0.0253 | -0.017 | -0.013 | -0.046 |
| r6 | refine r1 | 0 | 0.7318 | -0.0313 | -0.047 | -0.002 | -0.044 |
| r50 | refine r10 | 11 | 0.7255 | -0.0375 | -0.078 | -0.001 | -0.034 |
| r47 | explore r32,r40 | 10 | 0.6978 | -0.0652 | +0.119 | -0.129 | -0.186 |
| r5 | init r0 | 0 | 0.5694 | -0.1937 | -0.264 | -0.091 | -0.225 |

## r10（得分 0.8206）

The rule keeps the existing load-balancing score but adds an adaptive maintenance-stagger window: among available robots it permits one robot to run ahead by just enough duties to spread maintenance starts for the current fleet size, while capping count/hours imbalance. Near the horizon it shrinks this window and avoids robots whose next duty would start maintenance that cannot finish; ties then favour fresher budgets and opened balance. New-robot types are ranked by maintenance-amortized throughput and by whether their duty length fits the remaining horizon.

```python
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
```

## r25（得分 0.8206）

The key improvement is to refine the maintenance-slack calculation for mixed robot types: instead of using the candidate robot's own duty length alone, we estimate the average duty length of the *other* opened robots that will cover during its maintenance. This yields a theoretically better permitted load imbalance for the combined count+hours balance metric, without changing behaviour for homogeneous-type instances.

```python
def rule(ctx):
    # Average and total duty length of opened robots (fallback: all types)
    N_robots = len(ctx.robots)
    total_work = 0.0
    if N_robots > 0:
        for r in ctx.robots:
            tp = ctx.types[r.type]
            if tp is not None:
                total_work += tp["work_time"]
            else:
                total_work += 10.0
        avg_work = total_work / N_robots
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
    Ncur = N_robots
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

        # average duty length of the other opened robots
        if N_robots >= 2:
            w_other = (total_work - w) / (N_robots - 1)
        else:
            w_other = w
        if w_other <= 0.0:
            w_other = w

        preserve = (maint > 0.0 and R < maint)
        if preserve:
            K = 0
        else:
            if maint > 0.0 and w > 0.0:
                # refined slack for mixed types
                num = maint * (avg_work + w_other)
                denom = w_other * (avg_work + w) * den
                if denom > 0.0:
                    req = num / denom
                    K = int(req)
                    if K < req - 1e-9:
                        K += 1
                    if K < 1:
                        K = 1
                    if K > M:
                        K = M
                else:
                    K = 0
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
```

## r40（得分 0.8195）

The combined rule keeps Rule 1's maintenance-aware `K` threshold and efficiency-based new-robot preferences, but injects Rule 2's exact variance-balancing score, overlap/danger safeguards, and capacity estimate. Reuse ordering first respects availability/load thresholds, then either preserves fresh robots near the horizon or pushes near-maintenance robots earlier, with exact count/hour variance as a strong tie-breaker; new-robot selection prioritizes feasibility, then capacity/efficiency, while preferring duty lengths close to the current average when remaining work can be covered by one addit

```python
def rule(ctx):
    types = ctx.types
    ntypes = len(types)
    t = ctx.t
    T = ctx.T
    R = ctx.remaining
    robots = ctx.robots

    # Average duty length of opened robots (fallback: all allowed types)
    sumw = 0.0
    nw = 0
    if robots:
        for r in robots:
            tp = types[r.type] if 0 <= r.type < ntypes else None
            if tp is not None:
                w = float(tp.get("work_time", 10.0) or 10.0)
                if w > 0.0:
                    sumw += w
                    nw += 1
    if nw == 0:
        for tp in types:
            if tp is not None:
                w = float(tp.get("work_time", 10.0) or 10.0)
                if w > 0.0:
                    sumw += w
                    nw += 1
    avg_w = sumw / nw if nw else 10.0
    if avg_w <= 0.0:
        avg_w = 10.0

    Nrob = len(robots)
    if Nrob < 1:
        Nrob = 1
    den = Nrob - 1
    if den < 1:
        den = 1

    # Exact variance components for count and hours
    S = 0
    H = 0.0
    Qc = 0.0
    Qh = 0.0
    for r in robots:
        c = r.count
        h = r.hours
        S += c
        H += h
        Qc += c * c
        Qh += h * h

    # Robots currently in maintenance (not ready and budget exhausted)
    maint_now = 0
    for r in robots:
        if r.ready > t + 1e-9:
            if r.duties_left <= 0 or r.budget <= 1e-9:
                maint_now += 1

    items = []
    min_load = None

    for r in ctx.available:
        tp = types[r.type] if 0 <= r.type < ntypes else None
        if tp is None:
            w = 10.0
            single = 10.0
            cont = 10.0
            maint = 0.0
            charge = 0.0
            out = 0.0
            ret = 0.0
        else:
            w = float(tp.get("work_time", 10.0) or 10.0)
            single = float(tp.get("single_work_time", w) or w)
            cont = float(tp.get("continue_max_work", single) or single)
            maint = float(tp.get("maintenance_time", 0.0) or 0.0)
            charge = float(tp.get("charge_time", 0.0) or 0.0)
            out = float(tp.get("out_travel_time", 0.0) or 0.0)
            ret = float(tp.get("return_travel_time", 0.0) or 0.0)

        if w <= 0.0:
            w = 10.0
        if single <= 0.0:
            single = w
        if cont <= 0.0:
            cont = single
        if maint < 0.0:
            maint = 0.0

        M = int(cont / single)
        if M < 1:
            M = 1

        d = int(r.duties_left)
        if d < 0:
            d = 0
        if d > M:
            d = M

        progress = (M - d) / float(M)
        if progress < 0.0:
            progress = 0.0
        if progress > 1.0:
            progress = 1.0

        load = r.count + r.hours / avg_w
        inc_load = 1.0 + w / avg_w

        inc_time = w + out + ret + charge
        if inc_time <= 0.0:
            inc_time = w
        time_to_maint = d * inc_time

        cost_c = Qc + 2.0 * r.count + 1.0 - (S + 1.0) * (S + 1.0) / float(Nrob)
        cost_h = Qh + 2.0 * r.hours * w + w * w - (H + w) * (H + w) / float(Nrob)
        if cost_c < 0.0:
            cost_c = 0.0
        if cost_h < 0.0:
            cost_h = 0.0
        balance = cost_c + cost_h / (avg_w * avg_w + 1e-9)

        preserve = (maint > 0.0 and R < maint)

        maint_flag = 0 if r.first_maint is None else 1

        items.append((r, w, M, d, progress, load, inc_load, balance,
                      preserve, maint, time_to_maint, maint_flag))
        if min_load is None or load < min_load:
            min_load = load

    if min_load is None:
        min_load = 0.0

    healthy_avail = 0
    for it in items:
        if it[3] > 1:
            healthy_avail += 1

    scored = []
    for it in items:
        (r, w, M, d, progress, load, inc_load, balance,
         preserve, maint, time_to_maint, maint_flag) = it

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

        allowed = 0 if load <= min_load + K * inc_load + 1e-9 else 1
        danger = 1 if (maint > 0.0 and R < maint and d <= 1) else 0
        overlap = 1 if (d <= 1 and maint_now > 0 and healthy_avail > 0) else 0

        if preserve:
            key = (allowed, danger, overlap, progress,
                   maint_flag, balance, load, r.idx)
        else:
            key = (allowed, overlap, danger, time_to_maint,
                   maint_flag, balance, load, r.idx)

        scored.append((key, r))

    scored.sort(key=lambda x: x[0])
    actions = [("reuse", r) for _, r in scored]

    # New-robot type preferences
    new_cand = []
    for k, tp in enumerate(types):
        if tp is None or ctx.left[k] <= 0:
            continue

        w = float(tp.get("work_time", 10.0) or 10.0)
        single = float(tp.get("single_work_time", w) or w)
        cont = float(tp.get("continue_max_work", single) or single)
        maint = float(tp.get("maintenance_time", 0.0) or 0.0)
        charge = float(tp.get("charge_time", 0.0) or 0.0)
        out = float(tp.get("out_travel_time", 0.0) or 0.0)
        ret = float(tp.get("return_travel_time", 0.0) or 0.0)

        if w <= 0.0:
            w = 10.0
        if single <= 0.0:
            single = w
        if cont <= 0.0:
            cont = single
        if maint < 0.0:
            maint = 0.0

        M = int(cont / single)
        if M < 1:
            M = 1

        inc_time = w + out + ret + charge
        if inc_time <= 0.0:
            inc_time = w

        exp_duties = R / inc_time if R > 0.0 else 1.0
        if exp_duties < 1.0:
            exp_duties = 1.0
        if exp_duties >= M:
            eff_time = inc_time + maint / float(M)
        else:
            eff_time = inc_time
        efficiency = w / eff_time if eff_time > 0.0 else 0.0

        cycle = M * inc_time + maint
        if cycle <= 0.0:
            cycle = inc_time

        full = int(R / cycle) if R > 0.0 else 0
        cap = full * M * w
        rem = R - full * cycle
        pd = 0
        if rem > 0.0:
            pd = int(rem / inc_time)
            if pd > M:
                pd = M
            if pd < 0:
                pd = 0
            cap += pd * w

        maxd = full * M + pd
        if maxd == 0 and R > 0.0:
            maxd = 1
            cap = w

        cover = 0 if cap >= R - 1e-9 else 1
        overshoot = cap - R if cap > R else 0.0
        if maxd == 1 and full == 0 and R > 0.0:
            overshoot = w - R if w > R else 0.0

        maint_ratio = maint / max(M * w, 1e-6)
        fit_abs = abs(w - avg_w)

        if R <= 0.0:
            score = (0, fit_abs, -efficiency, -w, k)
        elif w > R + 1e-9:
            score = (2, w, -efficiency, fit_abs, k)
        elif cover == 0:
            score = (0, fit_abs, overshoot, -efficiency, maint_ratio, -w, k)
        else:
            score = (1, -cap, -efficiency, fit_abs, maint_ratio, overshoot, -w, k)

        new_cand.append((score, k))

    new_cand.sort()
    for _, k in new_cand:
        actions.append(("new", k))

    if not actions:
        k = ctx.gene_type
        if not (k is not None and 0 <= k < ntypes and types[k] is not None and ctx.left[k] > 0):
            k = None
            for i, tp in enumerate(types):
                if tp is not None and ctx.left[i] > 0:
                    k = i
                    break
        if k is not None:
            actions = [("new", k)]
        else:
            actions = [("new", ctx.gene_type)]

    return actions
```
