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
