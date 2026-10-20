# 规则生成结果（full）

LLM 调用 53 次；候选 54 条，其中出错 0 条。

| 规则 | 来源 | 代 | 得分 | 对默认 | E 组 | H 组 | M 组 |
|---|---|---|---|---|---|---|---|
| r47 | explore r14,r37 | 10 | 0.8234 | +0.0604 | +0.151 | +0.029 | +0.001 |
| r37 | refine r33 | 7 | 0.8227 | +0.0597 | +0.148 | +0.031 | +0.001 |
| r49 | refine r37 | 10 | 0.8215 | +0.0585 | +0.144 | +0.031 | +0.000 |
| r14 | refine r13 | 2 | 0.8210 | +0.0580 | +0.142 | +0.028 | +0.004 |
| r40 | crossover r33,r14 | 8 | 0.8210 | +0.0580 | +0.142 | +0.028 | +0.004 |
| r11 | explore r8,r4 | 1 | 0.8199 | +0.0569 | +0.137 | +0.030 | +0.004 |
| r48 | crossover r14,r39 | 10 | 0.8197 | +0.0567 | +0.136 | +0.030 | +0.004 |
| r39 | explore r11,r14 | 8 | 0.8197 | +0.0567 | +0.137 | +0.030 | +0.003 |
| r50 | refine r11 | 11 | 0.8196 | +0.0566 | +0.137 | +0.030 | +0.003 |
| r45 | refine r32 | 9 | 0.8196 | +0.0566 | +0.142 | +0.028 | +0.000 |
| r28 | crossover r16,r13 | 5 | 0.8195 | +0.0565 | +0.142 | +0.028 | -0.000 |
| r32 | crossover r15,r28 | 6 | 0.8195 | +0.0565 | +0.142 | +0.028 | -0.000 |
| r13 | refine r7 | 1 | 0.8195 | +0.0565 | +0.142 | +0.028 | -0.000 |
| r33 | refine r13 | 6 | 0.8195 | +0.0565 | +0.142 | +0.028 | -0.000 |
| r15 | explore r13,r12 | 2 | 0.8193 | +0.0562 | +0.142 | +0.028 | -0.001 |
| r30 | refine r15 | 6 | 0.8187 | +0.0557 | +0.142 | +0.029 | -0.004 |
| r31 | explore r13,r28 | 6 | 0.8185 | +0.0554 | +0.137 | +0.027 | +0.002 |
| r41 | refine r32 | 8 | 0.8184 | +0.0554 | +0.142 | +0.028 | -0.004 |
| r7 | explore r0,r4 | 0 | 0.8173 | +0.0542 | +0.142 | +0.021 | -0.000 |
| r53 | refine r49 | 11 | 0.8168 | +0.0538 | +0.130 | +0.030 | +0.002 |
| r16 | crossover r10,r8 | 2 | 0.8165 | +0.0535 | +0.131 | +0.027 | +0.002 |
| r44 | crossover r14,r11 | 9 | 0.8161 | +0.0531 | +0.130 | +0.027 | +0.002 |
| r12 | crossover r4,r8 | 1 | 0.8147 | +0.0517 | +0.131 | +0.026 | -0.002 |
| r8 | crossover r4,r0 | 0 | 0.8142 | +0.0511 | +0.131 | +0.026 | -0.004 |
| r20 | crossover r14,r13 | 3 | 0.8137 | +0.0507 | +0.133 | +0.018 | +0.001 |
| r10 | refine r4 | 1 | 0.8135 | +0.0505 | +0.122 | +0.027 | +0.002 |
| r4 | init r0 | 0 | 0.8117 | +0.0487 | +0.122 | +0.026 | -0.002 |
| r27 | explore r14,r13 | 5 | 0.8102 | +0.0472 | +0.123 | +0.020 | -0.001 |
| r21 | refine r11 | 3 | 0.8093 | +0.0463 | +0.137 | +0.020 | -0.018 |
| r24 | crossover r13,r14 | 4 | 0.8064 | +0.0434 | +0.142 | +0.009 | -0.021 |
| r2 | init r0 | 0 | 0.8006 | +0.0376 | +0.111 | +0.027 | -0.026 |
| r42 | refine r14 | 9 | 0.7990 | +0.0360 | +0.142 | +0.014 | -0.048 |
| r3 | init r0 | 0 | 0.7971 | +0.0341 | +0.082 | +0.019 | +0.001 |
| r36 | crossover r14,r33 | 7 | 0.7958 | +0.0328 | +0.142 | +0.011 | -0.054 |
| r51 | explore r47,r11 | 11 | 0.7938 | +0.0308 | +0.077 | +0.024 | -0.009 |
| r25 | refine r14 | 4 | 0.7809 | +0.0179 | +0.142 | +0.014 | -0.102 |
| r9 | refine r1 | 0 | 0.7805 | +0.0175 | +0.065 | +0.020 | -0.033 |
| r1 | init r0 | 0 | 0.7802 | +0.0172 | +0.065 | +0.020 | -0.033 |
| r29 | refine r14 | 5 | 0.7745 | +0.0115 | +0.131 | +0.021 | -0.117 |
| r23 | explore r7,r11 | 4 | 0.7727 | +0.0097 | +0.001 | +0.025 | +0.004 |
| r43 | explore r32,r39 | 9 | 0.7695 | +0.0064 | +0.026 | +0.008 | -0.015 |
| r52 | crossover r37,r48 | 11 | 0.7646 | +0.0016 | -0.027 | +0.030 | +0.002 |
| r22 | refine r11 | 4 | 0.7643 | +0.0013 | -0.027 | +0.029 | +0.002 |
| r0 | default  | 0 | 0.7630 | +0.0000 | +0.000 | +0.000 | +0.000 |
| r17 | refine r7 | 2 | 0.7626 | -0.0005 | +0.000 | +0.002 | -0.003 |
| r26 | refine r11 | 5 | 0.7618 | -0.0012 | +0.000 | -0.000 | -0.004 |
| r35 | explore r30,r15 | 7 | 0.7557 | -0.0074 | +0.000 | -0.018 | -0.004 |
| r6 | refine r5 | 0 | 0.7496 | -0.0134 | +0.000 | -0.005 | -0.035 |
| r46 | refine r39 | 10 | 0.7481 | -0.0149 | -0.049 | +0.006 | -0.003 |
| r19 | explore r14,r11 | 3 | 0.7431 | -0.0200 | +0.137 | +0.035 | -0.231 |
| r18 | refine r11 | 3 | 0.7421 | -0.0209 | +0.035 | -0.040 | -0.057 |
| r38 | refine r14 | 8 | 0.7307 | -0.0323 | +0.023 | -0.018 | -0.102 |
| r5 | init r0 | 0 | 0.7200 | -0.0430 | -0.033 | -0.089 | -0.007 |
| r34 | refine r11 | 7 | 0.6599 | -0.1031 | -0.273 | -0.025 | -0.011 |

## r47（得分 0.8234）

The rule uses projected post-shift load (count + projected hours / average work time) as the balancing metric, and a maintenance-aware lead threshold that adapts to fleet size:  
`threshold = avg_maintenance_time / max(1, n_robots - 1)`.  
When few robots exist, this allows a large lead so robots are exhausted one-by-one, staggering maintenance and avoiding simultaneous downtime. As more robots are opened, the threshold shrinks, shifting toward balanced workloads to reduce count/hours/first-maintenance imbalance. Urgency (budget) is still used as a tie-breaker: when there is time to recover, r

```python
def rule(ctx):
    total_w = 0.0
    n_types = 0
    min_w = float('inf')
    total_m = 0.0
    n_m = 0
    for k in range(len(ctx.types)):
        t = ctx.types[k]
        if t is not None:
            w = t['work_time']
            total_w += w
            n_types += 1
            if w < min_w:
                min_w = w
            total_m += t['maintenance_time']
            n_m += 1
    avg_w = total_w / n_types if n_types else 1.0
    if min_w == float('inf'):
        min_w = 1.0
    avg_m = total_m / n_m if n_m else 100.0

    n_robots = len(ctx.robots)
    if n_robots <= 1:
        threshold_hours = avg_m
    else:
        threshold_hours = avg_m / (n_robots - 1)
    if threshold_hours < min_w:
        threshold_hours = min_w

    actions = []
    available = list(ctx.available)
    if available:
        proj_items = []
        for r in available:
            t = ctx.types[r.type]
            w = t['work_time']
            if w > ctx.remaining:
                proj_hours = 1e9
                load = 1e9
            else:
                proj_hours = r.hours + w
                proj_count = r.count + 1
                load = proj_count + proj_hours / avg_w
            proj_items.append((r, proj_hours, load))
        min_proj_hours = min(ph for _, ph, _ in proj_items)
        def key(item):
            r, proj_hours, load = item
            t = ctx.types[r.type]
            w = t['work_time']
            if w > ctx.remaining:
                return (2, 0, 0, 0, 0, 0)
            over = 1 if proj_hours > min_proj_hours + threshold_hours else 0
            if ctx.remaining > t['maintenance_time']:
                urgency = r.budget
            else:
                urgency = -r.budget
            return (over, urgency, load, r.count, -w, r.idx)
        proj_items.sort(key=key)
        actions = [("reuse", r) for r, _, _ in proj_items]

    left_types = [k for k in range(len(ctx.types)) if ctx.types[k] is not None and ctx.left[k] > 0]
    def type_score(k):
        t = ctx.types[k]
        w = t['work_time']
        if w > ctx.remaining:
            return 1000.0 + (w - ctx.remaining)
        overhead = t['out_travel_time'] + t['return_travel_time'] + t['charge_time']
        score = overhead / w
        if ctx.remaining > t['maintenance_time']:
            score += t['maintenance_time'] / t['continue_max_work']
        rem = ctx.remaining - w
        if rem > 0:
            if rem < min_w:
                score += 10.0
            if rem % w == 0:
                score -= 2.0
        else:
            score -= 5.0
        return score
    left_types.sort(key=type_score)

    new_actions = []
    gt = ctx.gene_type
    if 0 <= gt < len(ctx.types) and ctx.types[gt] is not None and ctx.left[gt] > 0:
        new_actions.append(("new", gt))
    for k in left_types:
        if k != gt:
            new_actions.append(("new", k))

    return actions + new_actions
```

## r37（得分 0.8227）

The key insight for improving group M (mixed duty lengths) is to balance a composite load of duty count and duty hours rather than just hours, and to use `duties_left` directly for maintenance urgency. This prevents short-duty robots from accumulating too many duties while long-duty robots lag in count, while still staggering maintenance to keep resource usage near optimal. The new-robot type score also rewards exact horizon fit and penalizes impossible small tails.

```python
def rule(ctx):
    # Compute average and minimum work time over all types
    total_w = 0.0
    n_types = 0
    min_w = float('inf')
    for k in range(len(ctx.types)):
        t = ctx.types[k]
        if t is not None:
            w = t['work_time']
            total_w += w
            n_types += 1
            if w < min_w:
                min_w = w
    avg_w = total_w / n_types if n_types else 1.0
    if min_w == float('inf'):
        min_w = 1.0

    actions = []
    if ctx.available:
        # Precompute composite loads: count + hours / avg_w
        items = []
        for r in ctx.available:
            load = r.count + r.hours / avg_w
            items.append((r, load))
        min_load = min(load for _, load in items)

        def key(item):
            r, load = item
            t = ctx.types[r.type]
            w = t['work_time']
            if w > ctx.remaining:
                return (2, 0, 0, 0, 0, 0)
            # Allow up to 5 load units of imbalance before deprioritizing
            over = 1 if load > min_load + 5.0 else 0
            maint_time = t['maintenance_time']
            if ctx.remaining > maint_time:
                urgency = r.duties_left          # exhaust closer-to-maintenance first
            else:
                urgency = -r.duties_left         # avoid triggering maintenance near end
            return (over, urgency, load, r.count, -w, r.idx)

        for r, _ in sorted(items, key=key):
            actions.append(("reuse", r))

    left_types = [k for k in range(len(ctx.types)) if ctx.types[k] is not None and ctx.left[k] > 0]

    def type_score(k):
        t = ctx.types[k]
        w = t['work_time']
        if w > ctx.remaining:
            return 1000.0 + (w - ctx.remaining)
        overhead = t['out_travel_time'] + t['return_travel_time'] + t['charge_time']
        score = overhead / w
        if ctx.remaining > t['maintenance_time']:
            score += t['maintenance_time'] / t['continue_max_work']
        rem = ctx.remaining - w
        if rem > 0 and rem < min_w:
            score += 10.0
        if rem == 0:
            score -= 5.0
        return score

    left_types.sort(key=type_score)

    new_actions = []
    gt = ctx.gene_type
    if 0 <= gt < len(ctx.types) and ctx.types[gt] is not None and ctx.left[gt] > 0:
        new_actions.append(("new", gt))
    for k in left_types:
        if k != gt:
            new_actions.append(("new", k))

    return actions + new_actions
```

## r49（得分 0.8215）

The key insight is to keep the original rule's first action (which is tuned for resource-optimal maintenance staggering) but reorder the remaining "reuse" alternatives by current load instead of by maintenance urgency. This makes deviations much more useful for balancing: when a random genome overrides a shift, it will now likely pick the least‑loaded available robot, reducing the imbalance objective without increasing the number of opened resources. The new‑robot ordering and type scoring are left unchanged, as the diagnostics show resource usage is already optimal for group M.

```python
def rule(ctx):
    total_w = 0.0
    n_types = 0
    min_w = float('inf')
    for k in range(len(ctx.types)):
        t = ctx.types[k]
        if t is not None:
            w = t['work_time']
            total_w += w
            n_types += 1
            if w < min_w:
                min_w = w
    avg_w = total_w / n_types if n_types else 1.0
    if min_w == float('inf'):
        min_w = 1.0

    actions = []
    if ctx.available:
        items = []
        for r in ctx.available:
            load = r.count + r.hours / avg_w
            items.append((r, load))
        min_load = min(load for _, load in items)

        def urgency_key(item):
            r, load = item
            t = ctx.types[r.type]
            w = t['work_time']
            if w > ctx.remaining:
                return (2, 0, 0, 0, 0, 0)
            over = 1 if load > min_load + 5.0 else 0
            maint_time = t['maintenance_time']
            if ctx.remaining > maint_time:
                urgency = r.duties_left
            else:
                urgency = -r.duties_left
            return (over, urgency, load, r.count, -w, r.idx)

        # First action: the original urgency-based choice (keeps resource usage optimal).
        best_item = min(items, key=urgency_key)
        best_r = best_item[0]

        # Remaining actions: sort by load ascending so deviations favour balance.
        rest = [it for it in items if it[0].idx != best_r.idx]
        rest.sort(key=lambda it: (it[1], it[0].idx))

        actions.append(("reuse", best_r))
        for r, _ in rest:
            actions.append(("reuse", r))

    left_types = [k for k in range(len(ctx.types)) if ctx.types[k] is not None and ctx.left[k] > 0]

    def type_score(k):
        t = ctx.types[k]
        w = t['work_time']
        if w > ctx.remaining:
            return 1000.0 + (w - ctx.remaining)
        overhead = t['out_travel_time'] + t['return_travel_time'] + t['charge_time']
        score = overhead / w
        if ctx.remaining > t['maintenance_time']:
            score += t['maintenance_time'] / t['continue_max_work']
        rem = ctx.remaining - w
        if rem > 0 and rem < min_w:
            score += 10.0
        if rem == 0:
            score -= 5.0
        return score

    left_types.sort(key=type_score)

    new_actions = []
    gt = ctx.gene_type
    if 0 <= gt < len(ctx.types) and ctx.types[gt] is not None and ctx.left[gt] > 0:
        new_actions.append(("new", gt))
    for k in left_types:
        if k != gt:
            new_actions.append(("new", k))

    return actions + new_actions
```
