"""资源数取最优值（9 = 5 台机器人 + 4 个工具）时，均衡度的分支定界搜索
语义与 mirror.py（已与 C++ 逐解一致）相同；决策 = 每班派哪台机器人（复用 / 新建哪一类型）+ 新建工具时选哪一类型。
限定：机器人 ≤ 5、工具 ≤ 4（即资源数 = 9 的层级）；只允许携带数为 2 的机器人类型
      （相邻两班的工具必不相同，带 3 个工具的机器人一出现工具就 ≥ 5，总数 ≥ 10，不属于这一层）。
下界（用于剪枝，也给出根节点下界）：
  · 出勤次数：各机器人最终次数 ∈ [当前次数, 当前次数 + 剩余班次内最多还能出勤的次数]，总和 = 总班次，
    取方差最小的连续松弛（带上限的注水），值岗时长均为 10 h 时 std(时长) = 10·std(次数)
    若上限之和 < 剩余班次 → 覆盖不了任务，直接剪掉（"容量剪枝"）
  · 首次维修间隔：已发生的首次维修间隔固定不变（之后的首次维修都更晚），据此给出 std 的下界
状态完全相同的节点只展开一次（状态里含出勤次数和首次维修时间，子树结果相同）。
用法: python exact/balance_bb.py 场景名 [时间上限秒] [初始上界]
"""
import json, math, os, sys, time
from functools import lru_cache
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_R, MAX_T = 5, 4


def solve(scen, tlimit=600.0, ub=float("inf"), verbose=True, selftest=0):
    sc = M.load_scenario(os.path.join(HERE, "requests", scen + ".json"))
    R, Tl, T = sc["R"], sc["Tl"], sc["T"]
    types = [k for k, P in enumerate(R) if P and int(P["carry_num"]) == 2]
    D = {R[k]["work_time"] for k in types}
    assert len(D) == 1, "当前下界假设可选类型值岗时长相同"
    d = D.pop()
    cyc = {k: Q["install_time"] + Q["tool_out_time"] + Q["tool_work_time"] + Q["tool_return_time"] + Q["removal_time"]
           + Q["tool_rest_time"] for k, Q in enumerate(Tl) if Q}
    remmin = {k: min(Tl[int(t)]["removal_time"] for t in R[k]["cargo_type_list"]) for k in types}

    @lru_cache(maxsize=None)
    def cap(ty, rel, rm, nrem):
        """从当前时刻起剩余 nrem 个班次内，该机器人最多还能出勤几次（贪心最早出勤即最多；拆卸取最小值→上界）"""
        P = R[ty]
        c, t = 0, 0              # t: 当前考察的班次下标（班次 t 开始于 E + d·t）
        rel_ready = rel
        while t < nrem:
            if rel_ready <= d * t - P["out_travel_time"] + 1e-9:
                end = d * (t + 1)
                back = end + P["return_travel_time"] + remmin[ty]
                rm -= P["single_work_time"]
                if rm >= P["single_work_time"]:
                    rel_ready = back + P["charge_time"]
                else:
                    rel_ready = back + P["maintenance_time"]; rm = P["continue_max_work"]
                c += 1
                t += 1
            else:
                t += 1
        return c

    def count_lb(cur, caps, ntot):
        """带上下限的注水：min Σ(c_i − mean)^2，c_i ∈ [cur_i, cur_i+caps_i]，Σc_i = ntot（连续松弛）。返回 std 下界或 None（不可行）"""
        c = list(cur)
        hi = [a + b for a, b in zip(cur, caps)]
        need = ntot - sum(c)
        if need < 0 or sum(hi) < ntot:
            return None
        # 整数注水：每次给当前最小且未到上限者 +1（可分凸目标下贪心即最优）
        for _ in range(need):
            j = min((i for i in range(len(c)) if c[i] < hi[i]), key=lambda i: c[i])
            c[j] += 1
        m = sum(c) / len(c)
        return math.sqrt(sum((v - m) ** 2 for v in c) / len(c))

    def rep_lb(reps):
        reps = sorted(reps)
        if len(reps) < 2:
            return 0.0
        iv = np.diff(reps)
        n = MAX_R - 1
        k = len(iv)
        if k >= n:
            return M.std(iv)
        return float(np.sqrt(((iv - iv.mean()) ** 2).sum() / n))

    best = [ub, None]
    seen = set()
    nodes = [0]
    t0 = time.time()
    timed_out = [False]
    root_lb = [None]

    # 状态：E, robots(list of [ty, ready, remain, count, first_rep]), tools(list of [ty, ready]), resR, resT
    def lower_bound(E, robots):
        if E == 0:
            return 0.0
        nrem = math.ceil((T - E) / d - 1e-9)
        cur = [r[3] for r in robots] + [0] * (MAX_R - len(robots))
        caps = [cap(r[0], r[1] - E, r[2], nrem) for r in robots]
        if len(robots) < MAX_R:
            capnew = max(cap(ty, -1e9, R[ty]["continue_max_work"], nrem) for ty in types)
            caps += [capnew] * (MAX_R - len(robots))
        s = count_lb(cur, caps, sum(cur) + nrem)
        if s is None:
            return None
        return 0.3 * s + 0.4 * d * s + 0.3 * rep_lb([r[4] for r in robots if r[4] >= 0])

    def step(E, robots, tools, resT, ri, ty_new, sel):
        """执行一个班次，返回新状态或 None。ri: 复用的机器人下标；ty_new: 新建类型；sel: 新建工具的类型下标"""
        robots = [list(r) for r in robots]
        tools = [list(t) for t in tools]
        resT = list(resT)
        if ri is not None:
            rb = robots[ri]
        else:
            rb = [ty_new, 0.0, R[ty_new]["continue_max_work"], 0, -1]
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

    def key_of(E, robots, tools, resT, resR):
        return (E, tuple(sorted(tuple(r) for r in robots)), tuple(tuple(t) for t in tools), tuple(resT), tuple(resR))

    def dfs(E, robots, tools, resR, resT, path):
        if time.time() - t0 > tlimit:
            timed_out[0] = True
            return
        if E >= T:
            o = M.objectives_of_simple([r[3] for r in robots], [r[3] * d for r in robots],
                                       [r[4] for r in robots if r[4] >= 0])
            if o < best[0] - 1e-9:
                best[0], best[1] = o, list(path)
                if verbose:
                    print(f"   新上界 {o:.4f}  （{time.time()-t0:.1f}s，{nodes[0]} 节点）", flush=True)
            return
        k = key_of(E, robots, tools, resT, resR)
        if k in seen:
            return
        seen.add(k)
        nodes[0] += 1
        lb = lower_bound(E, robots)
        if lb is None or lb >= best[0] - 1e-9:
            return
        # 候选：可用机器人（按出勤次数升序，同签名去重）+ 新建
        cands = []
        sigs = set()
        for i, r in enumerate(robots):
            P = R[r[0]]
            ok = (r[1] <= 0.0) if E == 0 else (r[1] <= E - P["out_travel_time"] + 1e-9)
            if ok and r[2] >= P["single_work_time"]:
                sg = tuple(r)
                if sg in sigs:
                    continue
                sigs.add(sg)
                cands.append((r[3], 0, i, None))
        if len(robots) < MAX_R:
            for ty in types:
                if resR[ty] > 0:
                    cands.append((-1, 1, None, ty))
        cands.sort(key=lambda c: (c[0], c[1]))
        for _, _, ri, tyn in cands:
            ty = robots[ri][0] if ri is not None else tyn
            ctn = len(R[ty]["cargo_type_list"])
            outs = {}
            for sel in range(max(ctn - 1, 1)):
                st = step(E, robots, tools, resT, ri, tyn, sel)
                if st is None:
                    continue
                kk = key_of(st[0], st[1], st[2], st[3], resR)
                if kk not in outs:
                    outs[kk] = (sel, st)
            for sel, st in outs.values():
                nresR = list(resR)
                if tyn is not None:
                    nresR[tyn] -= 1
                path.append((("reuse", tuple(robots[ri])) if ri is not None else ("new", tyn), sel))
                dfs(st[0], st[1], st[2], nresR, st[3], path)
                path.pop()
                if timed_out[0]:
                    return

    sys.setrecursionlimit(100000)
    resR0 = [P["limit"] if P else 0 for P in R]
    resT0 = [Q["limit"] if Q else 0 for Q in Tl]

    if selftest:
        # 随机走完整条决策序列（同样受 5 机器人 / 4 工具限制），比较本文件的状态转移与 mirror（≡C++）的结果
        rng = np.random.default_rng(7)
        bad = done = 0
        for _ in range(selftest):
            E, robots, tools, resR, resT, path = 0.0, [], [], list(resR0), list(resT0), []
            while E < T:
                opts = []
                for i, r in enumerate(robots):
                    P = R[r[0]]
                    ok = (r[1] <= 0.0) if E == 0 else (r[1] <= E - P["out_travel_time"] + 1e-9)
                    if ok and r[2] >= P["single_work_time"]:
                        opts.append((i, None))
                if len(robots) < MAX_R:
                    opts += [(None, ty) for ty in types if resR[ty] > 0]
                if not opts:
                    break
                ri, tyn = opts[rng.integers(len(opts))]
                ty = robots[ri][0] if ri is not None else tyn
                sel = int(rng.integers(max(len(R[ty]["cargo_type_list"]) - 1, 1)))
                st = step(E, robots, tools, resT, ri, tyn, sel)
                if st is None:
                    break
                path.append((("reuse", tuple(robots[ri])) if ri is not None else ("new", tyn), sel))
                if tyn is not None:
                    resR[tyn] -= 1
                E, robots, tools, resT = st
            if E < T:
                continue
            done += 1
            mine = M.objectives_of_simple([r[3] for r in robots], [r[3] * d for r in robots],
                                          [r[4] for r in robots if r[4] >= 0])
            o, _ = M.evaluate_genes(sc, path_to_genes(sc, path))
            if o is None or abs(float(o[1]) - mine) > 1e-3 or float(o[0]) != len(robots) + len(tools):
                bad += 1
        return dict(selftest_done=done, selftest_bad=bad)
    # 根节点下界：首班结束后的最小可能下界（对首班的各种选择取最小）
    lbs = []
    for ty in types:
        for sel in range(max(len(R[ty]["cargo_type_list"]) - 1, 1)):
            st = step(0.0, [], [], resT0, None, ty, sel)
            if st:
                v = lower_bound(st[0], st[1])
                if v is not None:
                    lbs.append(v)
    root_lb[0] = min(lbs)
    dfs(0.0, [], [], resR0, resT0, [])
    return dict(scen=scen, best=best[0], path=best[1], root_lb=root_lb[0], nodes=nodes[0],
                complete=not timed_out[0], secs=time.time() - t0, sc=sc)


def path_to_genes(sc, path, rank=False):
    """把决策序列转成基因（阈值解码 / 排序解码），以便交给 C++ 原目标函数复核"""
    nv = M.nvar_auto(sc)
    x = np.zeros(nv)
    s = M.Sim(sc, rank)
    nty = len(sc["R"])
    th = M.THETA
    for i, (dec, sel) in enumerate(path):
        av = s.available()
        if dec[0] == "reuse":
            sig = dec[1]
            idx = next(j for j, r in enumerate(av)
                       if (r.type, r.ready, r.remain, r.count, (r.first_rep if r.first_rep is not None else -1)) == sig)
            x[i] = (idx + 0.5) / len(av) * th
        else:
            t = dec[1]
            x[i] = th + (t + 0.5) / nty * (1 - th) if av else (t + 0.5) / nty
        ty = av[idx].type if dec[0] == "reuse" else dec[1]
        ctn = int(sc["R"][ty]["cargo_type_num"])
        x[i + nv // 2] = (sel + 0.5) / (ctn - 1) if ctn > 1 else 0.5
        if dec[0] == "reuse":
            s.dispatch_reuse(av[idx], x[i + nv // 2])
        else:
            s.dispatch_new(dec[1], x[i + nv // 2])
    for j in range(len(path), nv // 2):
        x[j] = 0.0
    return [float(np.float32(v)) for v in x]


if __name__ == "__main__":
    scen = sys.argv[1]
    tl = float(sys.argv[2]) if len(sys.argv) > 2 else 600
    ub = float(sys.argv[3]) if len(sys.argv) > 3 else float("inf")
    r = solve(scen, tl, ub)
    print(f"{scen}: 根下界 {r['root_lb']:.4f}  最好 {r['best']:.4f}  {'已证最优' if r['complete'] else '超时未证'}  "
          f"{r['nodes']} 节点 {r['secs']:.0f}s")
    if r["path"]:
        g = path_to_genes(r["sc"], r["path"])
        o, sim = M.evaluate_genes(r["sc"], g)
        print("   基因复核（Python 等价模型）:", o)
        json.dump(dict(scen=scen, best=r["best"], root_lb=r["root_lb"], complete=r["complete"], genes=g,
                       seq=sim.seq, nodes=r["nodes"], secs=r["secs"]),
                  open(os.path.join(HERE, "exact", f"bb_{scen}.json"), "w", encoding="utf-8"), ensure_ascii=False)
