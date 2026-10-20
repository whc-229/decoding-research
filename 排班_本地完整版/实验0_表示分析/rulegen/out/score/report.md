# 规则生成结果（score）

LLM 调用 58 次；候选 54 条，其中出错 0 条。

| 规则 | 来源 | 代 | 得分 | 对默认 | E 组 | H 组 | M 组 |
|---|---|---|---|---|---|---|---|
| r35 | explore r27,r28 | 7 | 0.8191 | +0.0561 | +0.140 | +0.028 | -0.000 |
| r43 | explore r40,r35 | 9 | 0.8191 | +0.0561 | +0.140 | +0.028 | -0.000 |
| r44 | crossover r35,r27 | 9 | 0.8191 | +0.0561 | +0.140 | +0.028 | -0.000 |
| r19 | explore r15,r8 | 3 | 0.8153 | +0.0523 | +0.123 | +0.029 | +0.005 |
| r24 | crossover r19,r8 | 4 | 0.8153 | +0.0523 | +0.123 | +0.029 | +0.005 |
| r32 | crossover r24,r15 | 6 | 0.8153 | +0.0523 | +0.123 | +0.029 | +0.005 |
| r45 | refine r24 | 9 | 0.8153 | +0.0523 | +0.123 | +0.029 | +0.005 |
| r49 | refine r24 | 10 | 0.8153 | +0.0523 | +0.123 | +0.029 | +0.005 |
| r40 | crossover r27,r36 | 8 | 0.8153 | +0.0523 | +0.122 | +0.030 | +0.004 |
| r52 | crossover r24,r40 | 11 | 0.8153 | +0.0523 | +0.122 | +0.030 | +0.004 |
| r48 | crossover r40,r24 | 10 | 0.8153 | +0.0522 | +0.122 | +0.030 | +0.004 |
| r27 | explore r24,r23 | 5 | 0.8152 | +0.0522 | +0.122 | +0.030 | +0.004 |
| r23 | explore r15,r19 | 4 | 0.8152 | +0.0521 | +0.123 | +0.029 | +0.005 |
| r36 | crossover r23,r31 | 7 | 0.8151 | +0.0521 | +0.123 | +0.029 | +0.004 |
| r28 | crossover r23,r24 | 5 | 0.8150 | +0.0520 | +0.123 | +0.029 | +0.004 |
| r31 | explore r23,r27 | 6 | 0.8149 | +0.0518 | +0.123 | +0.028 | +0.004 |
| r42 | refine r24 | 9 | 0.8139 | +0.0509 | +0.117 | +0.030 | +0.006 |
| r50 | refine r24 | 11 | 0.8128 | +0.0498 | +0.118 | +0.028 | +0.003 |
| r47 | explore r40,r27 | 10 | 0.8106 | +0.0476 | +0.121 | +0.020 | +0.002 |
| r39 | explore r27,r35 | 8 | 0.8096 | +0.0466 | +0.116 | +0.023 | +0.001 |
| r25 | refine r15 | 4 | 0.8091 | +0.0460 | +0.111 | +0.026 | +0.001 |
| r33 | refine r25 | 6 | 0.8091 | +0.0460 | +0.111 | +0.026 | +0.001 |
| r15 | explore r8,r1 | 2 | 0.8089 | +0.0458 | +0.111 | +0.026 | -0.000 |
| r8 | crossover r1,r0 | 0 | 0.8084 | +0.0454 | +0.111 | +0.025 | -0.000 |
| r12 | crossover r8,r0 | 1 | 0.8083 | +0.0453 | +0.111 | +0.025 | -0.000 |
| r21 | refine r8 | 3 | 0.8082 | +0.0452 | +0.111 | +0.025 | -0.001 |
| r20 | crossover r12,r6 | 3 | 0.8082 | +0.0451 | +0.111 | +0.025 | -0.001 |
| r1 | init r0 | 0 | 0.8081 | +0.0450 | +0.111 | +0.025 | -0.001 |
| r11 | explore r4,r8 | 1 | 0.8081 | +0.0450 | +0.111 | +0.025 | -0.001 |
| r16 | crossover r6,r8 | 2 | 0.8081 | +0.0450 | +0.111 | +0.025 | -0.001 |
| r46 | refine r44 | 10 | 0.8080 | +0.0449 | +0.121 | +0.017 | -0.004 |
| r6 | refine r1 | 0 | 0.8079 | +0.0449 | +0.111 | +0.025 | -0.001 |
| r34 | refine r24 | 7 | 0.8048 | +0.0418 | +0.094 | +0.030 | +0.001 |
| r51 | explore r48,r24 | 11 | 0.8023 | +0.0393 | +0.102 | +0.017 | -0.001 |
| r22 | refine r19 | 4 | 0.8016 | +0.0385 | +0.112 | +0.027 | -0.024 |
| r29 | refine r24 | 5 | 0.7910 | +0.0280 | +0.093 | -0.014 | +0.004 |
| r37 | refine r27 | 7 | 0.7770 | +0.0139 | +0.050 | -0.006 | -0.003 |
| r4 | init r0 | 0 | 0.7631 | +0.0001 | +0.000 | +0.000 | +0.000 |
| r26 | refine r24 | 5 | 0.7630 | +0.0000 | +0.000 | -0.001 | +0.001 |
| r0 | default  | 0 | 0.7630 | +0.0000 | +0.000 | +0.000 | +0.000 |
| r38 | refine r23 | 8 | 0.7629 | -0.0001 | -0.025 | +0.022 | +0.002 |
| r3 | init r0 | 0 | 0.7628 | -0.0002 | +0.000 | -0.001 | +0.000 |
| r14 | refine r6 | 2 | 0.7628 | -0.0002 | +0.000 | -0.001 | +0.000 |
| r18 | refine r6 | 3 | 0.7628 | -0.0002 | +0.000 | -0.001 | +0.000 |
| r53 | refine r44 | 11 | 0.7628 | -0.0002 | +0.000 | -0.001 | +0.000 |
| r10 | refine r6 | 1 | 0.7620 | -0.0011 | +0.000 | +0.000 | -0.004 |
| r30 | refine r28 | 6 | 0.7617 | -0.0014 | +0.000 | -0.001 | -0.003 |
| r41 | refine r23 | 8 | 0.7615 | -0.0015 | +0.000 | -0.001 | -0.004 |
| r9 | refine r4 | 0 | 0.7581 | -0.0050 | -0.027 | +0.011 | +0.001 |
| r17 | refine r4 | 2 | 0.7579 | -0.0052 | -0.003 | +0.003 | -0.016 |
| r2 | init r0 | 0 | 0.7364 | -0.0267 | +0.000 | -0.037 | -0.043 |
| r13 | refine r1 | 1 | 0.7328 | -0.0302 | -0.052 | -0.018 | -0.020 |
| r5 | init r0 | 0 | 0.6727 | -0.0903 | +0.000 | -0.102 | -0.169 |
| r7 | explore r3,r0 | 0 | 0.6125 | -0.1505 | -0.208 | -0.100 | -0.143 |

## r35（得分 0.8191）

The rule introduces a horizon-fit filter: before applying any load-balancing or urgency logic, it checks whether any available robot's duty length fits within the remaining horizon. If so, robots that would overshoot are heavily penalized, which is crucial for mixed duty lengths (group M). It then uses a convex combination of urgency (based on duties left and maintenance time) and load (hours plus scaled duty counts), with the weight controlled by capacity slack. This differs from previous rules by explicitly preventing overshoot on reuse and by incorporating maintenance time into the urgency 

```python
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
```

## r43（得分 0.8191）

I propose a lookahead-aware capacity-adaptive rule: it still blends maintenance urgency and load balancing based on capacity slack, but adds a one-shift lookahead to keep a non-empty ready pool. For each reuse candidate, it checks whether using that robot would leave zero robots ready at the next shift start (`t + work_time`), and heavily penalizes such choices. When a new robot must be opened, it prefers a type whose work_time both fits the remaining horizon and leaves at least one existing robot ready by the next shift start, effectively bridging maintenance/charging gaps and reducing unnece

```python
def rule(ctx):
    R = ctx.remaining
    if R <= 0:
        return []

    # Average duty length for load balancing
    total_hours = 0.0
    total_count = 0
    for r in ctx.robots:
        total_hours += r.hours
        total_count += r.count
    avg_wt = total_hours / total_count if total_count > 0 else 10.0

    # Capacity slack -> blend urgency and load
    capacity = ctx.capacity
    slack = capacity - R
    if R > 0:
        alpha = slack / R
        if alpha < 0.0:
            alpha = 0.0
        elif alpha > 1.0:
            alpha = 1.0
    else:
        alpha = 1.0

    avail = ctx.available

    # Precompute ready counts for possible next shift starts
    ready_at = {}
    for r in avail:
        wt = ctx.types[r.type]['work_time']
        if wt not in ready_at:
            t_next = ctx.t + wt
            cnt = 0
            for rb in ctx.robots:
                if rb.ready <= t_next:
                    cnt += 1
            ready_at[wt] = cnt

    def score(r):
        t_info = ctx.types[r.type]
        wt = t_info['work_time']
        cycle = wt + t_info['out_travel_time'] + t_info['return_travel_time'] + t_info['charge_time']
        urgency = r.duties_left * cycle + t_info['maintenance_time']
        load = r.hours + r.count * avg_wt
        s = (1.0 - alpha) * urgency + alpha * load
        avail_next = ready_at.get(wt, 0) - 1
        if avail_next <= 0:
            s += 10000.0
        return (s, r.count, r.hours, r.idx)

    sorted_avail = sorted(avail, key=score)
    actions = [("reuse", r) for r in sorted_avail]

    # New robot type selection
    valid = []
    for k in range(len(ctx.types)):
        if ctx.types[k] is not None and ctx.left[k] > 0:
            valid.append(k)

    if valid:
        opened_types = set(r.type for r in ctx.robots)

        # Representability of remainders
        work_times = []
        for k in range(len(ctx.types)):
            if ctx.types[k] is not None:
                work_times.append(ctx.types[k]['work_time'])
        work_times = list(set(work_times))
        g = 0
        for wt in work_times:
            g = math.gcd(g, wt)
        max_check = 200
        dp = [False] * (max_check + 1)
        dp[0] = True
        for i in range(max_check + 1):
            if dp[i]:
                for wt in work_times:
                    j = i + wt
                    if j <= max_check:
                        dp[j] = True
        def is_rep(x):
            if x < 0:
                return False
            if g > 0 and x % g != 0:
                return False
            if x > max_check:
                return True
            return dp[x]

        def new_key(k):
            t_info = ctx.types[k]
            wt = t_info['work_time']
            swt = t_info['single_work_time']
            cmw = t_info['continue_max_work']
            mt = t_info['maintenance_time']
            out_t = t_info['out_travel_time']
            ret_t = t_info['return_travel_time']
            ch_t = t_info['charge_time']

            # 1) Fit to remaining horizon
            if wt > R:
                fit = 2000
            else:
                rem = R - wt
                if rem == 0:
                    fit = -1000
                elif not is_rep(rem):
                    fit = 1000
                else:
                    fit = 0

            # 2) Lookahead: will any existing robot be ready at t + wt?
            t_next = ctx.t + wt
            ready_cnt = 0
            for rb in ctx.robots:
                if rb.ready <= t_next:
                    ready_cnt += 1
            gap_penalty = 0 if ready_cnt > 0 else 1

            # 3) Efficiency and preferences
            duties = cmw // swt if swt > 0 else 0
            cycle = wt + out_t + ret_t + ch_t
            total_cycle = duties * cycle + mt if duties > 0 else 1e9
            eff = (duties * wt) / total_cycle if total_cycle > 0 else 0.0
            existing = 1 if k in opened_types else 0

            return (fit, gap_penalty, -existing, -eff, mt, -cmw, -wt, k)

        valid.sort(key=new_key)
        if ctx.gene_type in valid:
            valid.remove(ctx.gene_type)
            valid.insert(0, ctx.gene_type)

        actions.extend(("new", k) for k in valid)

    return actions
```

## r44（得分 0.8191）

This rule merges Rule 1’s adaptive reuse scoring—blending maintenance urgency with load balance according to capacity slack, and penalising robots that cannot fit the remaining horizon—with Rule 2’s stronger new‑robot type ordering. The latter first prefers types that can cover the entire remaining horizon before needing maintenance (`fits`), then avoids horizon overshoot, reuses already‑opened types, and finally compares efficiency, maintenance duration and work budget. The gene‑specified type is still promoted when valid, preserving the evolutionary bias.

```python
def rule(ctx):
    # Average duty length for load balancing
    total_hours = 0.0
    total_count = 0
    for r in ctx.robots:
        total_hours += r.hours
        total_count += r.count
    if total_count > 0:
        avg_wt = total_hours / total_count
    else:
        avg_wt = 10.0

    # Adaptive balance weight from capacity slack
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

    # Check if any available robot can fit the remaining horizon
    has_fitting = False
    for r in ctx.available:
        if ctx.types[r.type]['work_time'] <= remaining:
            has_fitting = True
            break

    def score(r):
        t = ctx.types[r.type]
        cycle = t['work_time'] + t['out_travel_time'] + t['return_travel_time'] + t['charge_time']
        urgency = r.duties_left * cycle + t['maintenance_time']
        load = r.hours + r.count * avg_wt
        s = (1.0 - alpha) * urgency + alpha * load
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
            fits = 0 if capacity_before_maint >= remaining else 1
            overshoot = 1 if wt > remaining else 0
            existing = 1 if k in opened_types else 0
            eff = capacity_before_maint / (duties * cycle + mt) if duties > 0 else 0.0
            return (fits, overshoot, -existing, -eff, mt, -cmw, k)

        valid.sort(key=new_key)
        if ctx.gene_type in valid:
            valid.remove(ctx.gene_type)
            valid.insert(0, ctx.gene_type)

        actions.extend(("new", k) for k in valid)

    return actions
```
