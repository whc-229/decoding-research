"""资源数 = 9 层级（5 台机器人 + 4 个工具）上均衡度的精确求解：分支定界（前缀）+ 记忆化动态规划（后缀）
关键的结构性观察（使状态可以合并）：
  1. 均衡度对"出勤次数整体平移"不变：std(c + k) = std(c)，所以状态里只需记 c_i − min(c)
  2. 时间只以"相对当前时刻"的形式进入后续决策：机器人/工具的就绪时间记成 ready − E，
     且早于"可用门槛"的值彼此等价（机器人截到 −去程，工具截到 −最大去程）
  3. 可选机器人类型的值岗时长相同（10 h），剩余班次数 = ⌈(T − E)/10⌉ 由 E 唯一确定，std(时长) = 10·std(次数)，
     于是 均衡度 = 4.3·std(次数) + 0.3·std(首次维修间隔)
两阶段：
  · 阶段二（5 台机器人都已创建且都已发生首次维修）：首次维修间隔已全部确定，剩余只需最小化 std(次数)，
    它只依赖归一化状态（相对时间 + 次数差），用记忆化动态规划精确求出
  · 阶段一（之前的前缀）：分支定界枚举前缀，下界 = 0.3·间隔下界 + 4.3·次数下界（带容量上限的整数注水，见 balance_bb.py），
    到达阶段二时用动态规划给出精确的剩余最优值
只要阶段一在时限内搜完，结果就是精确最优值。转移规则与 mirror.py（≡ C++ 原目标函数）一致。
用法: python exact/balance_dp.py 场景名 [阶段一时限秒]
"""
import json, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_R, MAX_T = 5, 4


def std(v):
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / len(v))


def solve(scen, tlimit=3600.0, ub=float("inf"), verbose=True):
    sc = M.load_scenario(os.path.join(HERE, "requests", scen + ".json"))
    R, Tl, T = sc["R"], sc["Tl"], sc["T"]
    types = [k for k, P in enumerate(R) if P and int(P["carry_num"]) == 2]
    D = {R[k]["work_time"] for k in types}
    assert len(D) == 1
    d = D.pop()
    W = 0.3 + 0.4 * d                      # 均衡度中 std(次数) 的系数（= 4.3）
    cyc = {k: Q["install_time"] + Q["tool_out_time"] + Q["tool_work_time"] + Q["tool_return_time"] + Q["removal_time"]
           + Q["tool_rest_time"] for k, Q in enumerate(Tl) if Q}
    maxout = max(R[k]["out_travel_time"] for k in types)
    remmin = {k: min(Tl[int(t)]["removal_time"] for t in R[k]["cargo_type_list"]) for k in types}

    def step(E, robots, tools, resT, ri, ty_new, sel):
        robots = [list(r) for r in robots]
        tools = [list(t) for t in tools]
        resT = list(resT)
        rb = robots[ri] if ri is not None else [ty_new, 0.0, R[ty_new]["continue_max_work"], 0, -1]
        P = R[rb[0]]
        target = max(0.0, E - P["out_travel_time"])
        lst = [int(v) for v in P["cargo_type_list"]]
        cand = sorted([t for t in tools if t[0] in lst and t[1] <= target + 1e-9], key=lambda t: t[1])
        use = cand[:2]
        ctn = len(lst)
        while len(use) < 2:
            picked, indd = None, sel
            for _ in range(ctn):
                if indd >= ctn or indd < 0:
                    indd = 0
                if resT[lst[indd]] > 0:
                    picked = lst[indd]; break
                indd += 1
            if picked is None or len(tools) >= MAX_T:
                return None
            resT[picked] -= 1
            t = [picked, 0.0]
            tools.append(t); use.append(t)
        ins = max(Tl[t[0]]["install_time"] for t in use)
        rem = max(Tl[t[0]]["removal_time"] for t in use)
        if E == 0:
            ib, db = 0.0, ins + P["out_travel_time"]
        else:
            ib, db = E - ins - P["out_travel_time"], E
        de = db + P["work_time"]
        back = de + P["return_travel_time"] + rem
        rb[2] -= P["single_work_time"]
        if rb[2] >= P["single_work_time"]:
            rb[1] = back + P["charge_time"]
        else:
            if rb[4] < 0:
                rb[4] = back
            rb[1] = back + P["maintenance_time"]; rb[2] = P["continue_max_work"]
        rb[3] += 1
        for t in use:
            t[1] = ib + cyc[t[0]]
        if ri is None:
            robots.append(rb)
        return de, robots, tools, resT

    def choices(E, robots, tools, resR, resT):
        """所有可由基因实现的决策（同签名机器人去重；新建工具的类型选择去重）→ [(决策, 新状态, 新resR)]"""
        out, sigs = [], set()
        cands = []
        for i, r in enumerate(robots):
            P = R[r[0]]
            ok = (r[1] <= 0.0) if E == 0 else (r[1] <= E - P["out_travel_time"] + 1e-9)
            if ok and r[2] >= P["single_work_time"] and tuple(r) not in sigs:
                sigs.add(tuple(r)); cands.append((r[3], 0, i, None))
        if len(robots) < MAX_R:
            cands += [(-1, 1, None, ty) for ty in types if resR[ty] > 0]
        cands.sort(key=lambda c: (c[0], c[1]))
        for _, _, ri, tyn in cands:
            ty = robots[ri][0] if ri is not None else tyn
            seen = set()
            for sel in range(max(len(R[ty]["cargo_type_list"]) - 1, 1)):
                st = step(E, robots, tools, resT, ri, tyn, sel)
                if st is None:
                    continue
                sig = (tuple(tuple(t) for t in st[2]), tuple(st[3]),
                       tuple(sorted(tuple(r) for r in st[1])))
                if sig in seen:
                    continue
                seen.add(sig)
                nresR = list(resR)
                if tyn is not None:
                    nresR[tyn] -= 1
                dec = (("reuse", tuple(robots[ri])) if ri is not None else ("new", tyn), sel)
                out.append((dec, st, nresR))
        return out

    # ---------- 阶段二：记忆化动态规划，求最小 std(次数) ----------
    # 记忆表只存数值（键压成定长整数串以省内存）；若某状态已达到它自己的次数下界，后续分支不必再试（仍是精确的）
    import struct
    memo2 = {}
    outR = {k: R[k]["out_travel_time"] for k in types}

    def key2(E, robots, tools, resT):
        mc = min(r[3] for r in robots)
        rob = sorted((r[0], int(max(r[1] - E, -outR[r[0]])), int(r[2]), r[3] - mc) for r in robots)
        flat = [math.ceil((T - E) / d - 1e-9), len(tools)] + [x for rr in rob for x in rr] + \
               [x for t in tools for x in (t[0], int(max(t[1] - E, -maxout)))] + list(resT)
        return struct.pack(f"{len(flat)}h", *flat)

    def V2(E, robots, tools, resR, resT):
        if E >= T:
            return std([r[3] for r in robots])
        k = key2(E, robots, tools, resT)
        v = memo2.get(k)
        if v is not None:
            return v
        nrem = math.ceil((T - E) / d - 1e-9)
        cur = [r[3] for r in robots]
        lbv = count_lb(cur, [cap(r[0], r[1] - E, r[2], nrem) for r in robots], sum(cur) + nrem)
        best = float("inf")
        if lbv is not None:
            for dec, st, nresR in choices(E, robots, tools, resR, resT):
                v = V2(st[0], st[1], st[2], nresR, st[3])
                if v < best:
                    best = v
                if best <= lbv + 1e-12:
                    break
        memo2[k] = best
        return best

    # ---------- 阶段一：分支定界 ----------
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def cap(ty, rel, rm, nrem):
        P = R[ty]
        c, t, rr = 0, 0, rel
        while t < nrem:
            if rr <= d * t - P["out_travel_time"] + 1e-9:
                back = d * (t + 1) + P["return_travel_time"] + remmin[ty]
                rm -= P["single_work_time"]
                if rm >= P["single_work_time"]:
                    rr = back + P["charge_time"]
                else:
                    rr = back + P["maintenance_time"]; rm = P["continue_max_work"]
                c += 1
            t += 1
        return c

    def count_lb(cur, caps, ntot):
        c = list(cur)
        hi = [a + b for a, b in zip(cur, caps)]
        need = ntot - sum(c)
        if need < 0 or sum(hi) < ntot:
            return None
        for _ in range(need):
            j = min((i for i in range(len(c)) if c[i] < hi[i]), key=lambda i: c[i])
            c[j] += 1
        return std(c)

    def rep_lb(reps):
        if len(reps) < 2:
            return 0.0
        iv = [b - a for a, b in zip(reps, reps[1:])]
        n, k = MAX_R - 1, len(iv)
        m = sum(iv) / k
        return math.sqrt(sum((x - m) ** 2 for x in iv) / (k if k >= n else n))

    def lower_bound(E, robots, reps):
        if E == 0:
            return 0.0
        nrem = math.ceil((T - E) / d - 1e-9)
        cur = [r[3] for r in robots] + [0] * (MAX_R - len(robots))
        caps = [cap(r[0], r[1] - E, r[2], nrem) for r in robots]
        if len(robots) < MAX_R:
            caps += [max(cap(ty, -1e9, R[ty]["continue_max_work"], nrem) for ty in types)] * (MAX_R - len(robots))
        s = count_lb(cur, caps, sum(cur) + nrem)
        if s is None:
            return None
        return W * s + 0.3 * rep_lb(reps)

    best = [ub, None]
    seen1 = set()
    st_ = dict(nodes=0, phase2=0, timed_out=False, last=time.time())
    t0 = time.time()

    def dfs(E, robots, tools, resR, resT, path):
        if time.time() - t0 > tlimit:
            st_["timed_out"] = True; return
        reps = sorted(r[4] for r in robots if r[4] >= 0)
        if E >= T or (len(robots) == MAX_R and len(reps) == MAX_R):
            st_["phase2"] += 1
            v = V2(E, robots, tools, resR, resT)
            if v == float("inf"):
                return
            iv = [b - a for a, b in zip(reps, reps[1:])]
            tot = W * v + 0.3 * (std(iv) if len(iv) > 0 else 0.0)
            if tot < best[0] - 1e-9:
                best[0], best[1] = tot, (list(path), (E, [list(r) for r in robots], [list(t) for t in tools], list(resR), list(resT)))
                if verbose:
                    print(f"   新上界 {tot:.4f}（{time.time()-t0:.0f}s，前缀 {st_['nodes']}，阶段二状态 {len(memo2)}）", flush=True)
            return
        k = (E, tuple(sorted(tuple(r) for r in robots)), tuple(tuple(t) for t in tools), tuple(resR), tuple(resT))
        if k in seen1:
            return
        seen1.add(k)
        st_["nodes"] += 1
        if verbose and time.time() - st_["last"] > 120:
            st_["last"] = time.time()
            print(f"   ...{time.time()-t0:.0f}s 前缀 {st_['nodes']} 阶段二状态 {len(memo2)} 当前上界 {best[0]:.4f}", flush=True)
        lb = lower_bound(E, robots, reps)
        if lb is None or lb >= best[0] - 1e-9:
            return
        for dec, st, nresR in choices(E, robots, tools, resR, resT):
            path.append(dec)
            dfs(st[0], st[1], st[2], nresR, st[3], path)
            path.pop()
            if st_["timed_out"]:
                return

    sys.setrecursionlimit(200000)
    resR0 = [P["limit"] if P else 0 for P in R]
    resT0 = [Q["limit"] if Q else 0 for Q in Tl]
    root = min(v for v in (lower_bound(st[0], st[1], sorted(r[4] for r in st[1] if r[4] >= 0))
                           for _, st, _ in choices(0.0, [], [], resR0, resT0)) if v is not None)
    dfs(0.0, [], [], resR0, resT0, [])
    secs = time.time() - t0
    path = None
    if best[1] is not None:
        path, (E, robots, tools, resR, resT) = best[1]
        path = list(path)
        while E < T:
            target = V2(E, robots, tools, resR, resT)
            for dec, st, nresR in choices(E, robots, tools, resR, resT):
                if abs(V2(st[0], st[1], st[2], nresR, st[3]) - target) < 1e-12:
                    break
            path.append(dec)
            E, robots, tools, resR, resT = st[0], st[1], st[2], nresR, st[3]
    return dict(scen=scen, best=best[0], path=path, root_lb=root, complete=not st_["timed_out"],
                prefixes=st_["nodes"], phase2_states=len(memo2), secs=secs, sc=sc)


if __name__ == "__main__":
    import balance_bb as B
    scen = sys.argv[1]
    tl = float(sys.argv[2]) if len(sys.argv) > 2 else 3600
    r = solve(scen, tl)
    msg = f"{scen}: 根下界 {r['root_lb']:.4f}，最好 {r['best']:.4f}，{'已证最优' if r['complete'] else '超时（未证）'}；" \
          f"前缀 {r['prefixes']}，阶段二状态 {r['phase2_states']}，{r['secs']:.0f}s"
    out = dict(scen=scen, best=r["best"], root_lb=r["root_lb"], complete=r["complete"], secs=r["secs"],
               prefixes=r["prefixes"], phase2_states=r["phase2_states"])
    if r["path"]:
        g = B.path_to_genes(r["sc"], r["path"])
        o, sim = M.evaluate_genes(r["sc"], g)
        msg += f"；基因复核 {o}"
        out.update(genes=g, seq=sim.seq, check=[float(o[0]), float(o[1])], counts=[x.count for x in sim.robots],
                   first_rep=[x.first_rep for x in sim.robots], tools=[(t.type, t.uses) for t in sim.tools])
    print(msg, flush=True)
    json.dump(out, open(os.path.join(HERE, "exact", f"dp_{scen}.json"), "w", encoding="utf-8"), ensure_ascii=False)
