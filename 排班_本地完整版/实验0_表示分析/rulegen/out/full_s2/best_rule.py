def rule(ctx):
    types = ctx.types
    n = len(types)

    def params(k):
        ti = types[k] if 0 <= k < n else None
        if ti is None:
            return 10.0, 0.0, 0.0, 0.0, 0.0, 10.0, 1.0
        wt = ti.get("work_time", 10)
        if wt is None:
            wt = 10
        wt = float(wt)
        out = ti.get("out_travel_time", 0)
        out = float(out) if out is not None else 0.0
        ret = ti.get("return_travel_time", 0)
        ret = float(ret) if ret is not None else 0.0
        ch = ti.get("charge_time", 0)
        ch = float(ch) if ch is not None else 0.0
        mt = ti.get("maintenance_time", 0)
        mt = float(mt) if mt is not None else 0.0
        single = ti.get("single_work_time", wt)
        if single is None or single <= 0:
            single = wt if wt > 0 else 1.0
        else:
            single = float(single)
        cont = ti.get("continue_max_work", 0)
        if cont is None:
            cont = 0.0
        cont = float(cont)
        if cont <= 0:
            cont = single
        return wt, out, ret, ch, mt, single, cont

    active = []
    work_times = []
    max_maint = 0.0
    max_cyc = 0.0
    max_w = 0.0

    for k in range(n):
        if types[k] is not None:
            active.append(k)
            wt, out, ret, ch, mt, single, cont = params(k)
            work_times.append(wt)
            if mt > max_maint:
                max_maint = mt
            cyc = out + wt + ret + ch
            if cyc > max_cyc:
                max_cyc = cyc
            if wt > max_w:
                max_w = wt

    mixed = False
    if work_times:
        if max(work_times) - min(work_times) > 0.1:
            mixed = True
    n_active = len(active)

    total_count = 0
    total_hours = 0.0
    for r in ctx.robots:
        total_count += r.count
        total_hours += r.hours

    if total_count > 0:
        avg_work = total_hours / total_count
    elif work_times:
        avg_work = sum(work_times) / len(work_times)
    else:
        avg_work = 10.0
    if avg_work <= 0.0:
        avg_work = 10.0

    opened = [False] * n
    for r in ctx.robots:
        if 0 <= r.type < n:
            opened[r.type] = True

    memo = {}

    def can_make(x):
        x = int(round(x))
        if x in memo:
            return memo[x]
        if x <= 0:
            memo[x] = (x == 0)
            return memo[x]

        ws = []
        for k in active:
            if types[k] is not None and (opened[k] or ctx.left[k] > 0):
                wt, out, ret, ch, mt, single, cont = params(k)
                w = int(round(wt))
                if w > 0:
                    ws.append(w)

        if not ws:
            memo[x] = False
            return False

        g = 0
        for w in ws:
            g = math.gcd(g, w)

        if g == 0 or x % g != 0:
            memo[x] = False
            return False

        if x > 200:
            memo[x] = True
            return True

        dp = [False] * (x + 1)
        dp[0] = True
        for s in range(1, x + 1):
            for w in ws:
                if w <= s and dp[s - w]:
                    dp[s] = True
                    break
        memo[x] = dp[x]
        return dp[x]

    def fallback_new():
        gt = ctx.gene_type
        if isinstance(gt, int) and 0 <= gt < n and types[gt] is not None and ctx.left[gt] > 0:
            return gt
        for k in active:
            if ctx.left[k] > 0:
                return k
        if active:
            return active[0]
        return gt

    def new_candidates(rem):
        cand = []
        for k in active:
            if ctx.left[k] <= 0:
                continue
            wt, out, ret, ch, mt, single, cont = params(k)
            if mixed:
                if wt > rem + 1e-9:
                    fit_bad = 1
                    fit_val = wt - rem
                else:
                    r = rem - wt
                    if r > 0 and not can_make(r):
                        fit_bad = 1
                        fit_val = r
                    else:
                        fit_bad = 0
                        fit_val = -wt

                gene_pen = 0 if k == ctx.gene_type else 1
                cap = cont * wt / single if single > 0 else cont
                if cap <= 0:
                    cap = max(1.0, cont)
                eff = (mt / max(1.0, cap)
                       + ch / max(1.0, wt)
                       + (out + ret) / max(1.0, wt)
                       - wt / 10.0)
                cand.append((fit_bad, fit_val, gene_pen, -cont, mt, ch,
                             out + ret, -wt, eff, k))
            else:
                cap = cont * wt / max(1e-6, single)
                score = (mt / max(1.0, cap)
                         + ch / max(1.0, wt)
                         - wt / 10.0)
                cand.append((0, score, k))

        cand.sort()
        if not cand:
            return [("new", fallback_new())]
        return [("new", item[-1]) for item in cand]

    def rule1_order(avail_list):
        if not avail_list:
            return []

        if not mixed:
            info = []
            for r in avail_list:
                wt, out, ret, ch, mt, single, cont = params(r.type)
                max_duties = cont / single if single > 0 else 1.0
                if max_duties < 1.0:
                    max_duties = 1.0
                dl = r.duties_left if r.duties_left is not None else 1.0
                rem_frac = dl / max_duties
                load = 0.5 * (r.count + r.hours / avg_work)
                info.append((rem_frac, load, r.idx, r))

            window = 0.5
            in_window = [x for x in info if x[0] <= window]
            if in_window:
                in_window.sort(key=lambda x: (x[0], x[1], x[2]))
                rest = [x for x in info if x[0] > window]
                rest.sort(key=lambda x: (x[1], x[2]))
                ordered = in_window + rest
            else:
                info.sort(key=lambda x: (x[1], x[2]))
                ordered = info
            return [x[3] for x in ordered]

        endgame = ctx.remaining <= max_maint + max_w + 1e-9
        infos = []
        for r in avail_list:
            wt, out, ret, ch, mt, single, cont = params(r.type)
            max_duties = cont / single if single > 0 else 1.0
            if max_duties < 1.0:
                max_duties = 1.0
            dl = r.duties_left if r.duties_left is not None else 1.0
            rem_frac = dl / max_duties
            load = 0.5 * (r.count + r.hours / avg_work)

            rrem = ctx.remaining - wt
            if wt > ctx.remaining + 1e-9:
                fit_bad = 1
                fit_val = wt - ctx.remaining
            elif rrem > 0 and not can_make(rrem):
                fit_bad = 1
                fit_val = rrem
            else:
                fit_bad = 0
                fit_val = -wt

            maint_bad = 1 if (dl <= 1.0 and (wt + ret + mt > ctx.remaining + 1e-9)) else 0
            infos.append((fit_bad, maint_bad, rem_frac, load, fit_val, r.idx, r))

        if endgame:
            infos.sort(key=lambda x: (x[0], x[1], x[3], x[2], x[4], x[5]))
        else:
            infos.sort(key=lambda x: (
                x[0],
                0 if x[2] <= 0.5 else 1,
                x[2] if x[2] <= 0.5 else x[3],
                x[3] if x[2] <= 0.5 else x[2],
                x[4],
                x[5]
            ))
        return [x[6] for x in infos]

    def rule2_nonlate_order(avail_list):
        if not avail_list:
            return []

        info = []
        for r in avail_list:
            wt, out, ret, ch, mt, single, cont = params(r.type)
            max_duties = cont / single if single > 0 else 1.0
            if max_duties < 1.0:
                max_duties = 1.0
            dl = r.duties_left if r.duties_left is not None else 1.0
            rem_frac = dl / max_duties
            load = 0.5 * (r.count + r.hours / avg_work)
            info.append((rem_frac, load, r.idx, r))

        in_window = [x for x in info if x[0] <= 0.5]
        if in_window:
            in_window.sort(key=lambda x: (x[0], x[1], x[2]))
            default = in_window[0]
        else:
            info.sort(key=lambda x: (x[1], x[2]))
            default = info[0]

        default_idx = default[3].idx
        rest = [x for x in info if x[3].idx != default_idx]
        rest.sort(key=lambda x: (x[1], x[3].count, x[3].hours, x[0], x[2]))
        ordered = [default] + rest
        return [x[3] for x in ordered]

    def late_key(r):
        wt, out, ret, ch, mt, single, cont = params(r.type)
        dl = r.duties_left if r.duties_left is not None else 1.0
        load = 0.5 * (r.count + r.hours / avg_work)

        fit_bad = 0
        fit_val = 0.0
        if mixed:
            rrem = ctx.remaining - wt
            if wt > ctx.remaining + 1e-9:
                fit_bad = 1
                fit_val = wt - ctx.remaining
            elif rrem > 0 and not can_make(rrem):
                fit_bad = 1
                fit_val = rrem
            else:
                fit_bad = 0
                fit_val = -wt

        if dl <= 1.0:
            useful = (out + wt + ret + mt + out + wt + ret <= ctx.remaining + 1e-9)
            urg = 0 if useful else 2
        else:
            urg = 1

        away = out + wt + ret + (mt if dl <= 1.0 else ch)
        return (fit_bad, urg, load, r.count, r.hours, -dl, -r.budget,
                away, fit_val, r.ready, r.idx)

    avail = list(ctx.available)
    if not avail:
        return new_candidates(ctx.remaining)

    if n_active == 1:
        ordered = rule1_order(avail)
        actions = [("reuse", r) for r in ordered]
        actions.extend(new_candidates(ctx.remaining))
        return actions

    late = ctx.remaining <= max_maint + 2.0 * max_cyc + 1e-9
    if late:
        ordered = sorted(avail, key=late_key)
        primary = ordered[0]
        rest = ordered[1:]
    else:
        r1 = rule1_order(avail)
        primary = r1[0]
        r2 = rule2_nonlate_order(avail)
        rest = [r for r in r2 if r.idx != primary.idx]

    actions = [("reuse", primary)]
    for r in rest:
        actions.append(("reuse", r))
    actions.extend(new_candidates(ctx.remaining))
    return actions
