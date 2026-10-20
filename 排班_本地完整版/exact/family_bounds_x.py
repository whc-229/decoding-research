"""实例族的资源数下界：机器人（有限时域精确可行性搜索，对工具放宽）+ 工具（相邻两班工具是否必不相同）
用法: python exact/family_bounds.py [实例目录] [每个 k 的时限秒]
输出: <实例目录>/../exact/family_bounds.json
"""
import itertools, json, os, signal, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror as M
import robot_lb as RL

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TO(Exception):
    pass


def tool_lb(sc):
    R, Tl = sc["R"], sc["Tl"]
    types = [k for k, P in enumerate(R) if P and P["limit"] > 0]
    best_slack = -1e9
    for a, b in itertools.product(types, repeat=2):
        A, B = R[a], R[b]
        for t in set(map(int, A["cargo_type_list"])) & set(map(int, B["cargo_type_list"])):
            Q = Tl[t]
            if not Q or Q["limit"] <= 0:
                continue
            cyc = Q["install_time"] + Q["tool_out_time"] + Q["tool_work_time"] + Q["tool_return_time"] + Q["removal_time"] + Q["tool_rest_time"]
            insmax = max(Tl[int(u)]["install_time"] for u in A["cargo_type_list"] if Tl[int(u)])
            best_slack = max(best_slack, A["work_time"] - (cyc - A["out_travel_time"] - insmax + B["out_travel_time"]))
    carries = [int(R[k]["carry_num"]) for k in types]
    disjoint = best_slack < 0
    return (2 * min(carries) if disjoint else min(carries)), disjoint, best_slack


def robot_lb(sc, tlim):
    def handler(sig, frm):
        raise TO()
    signal.signal(signal.SIGALRM, handler)
    total = sum(P["limit"] for P in sc["R"] if P)
    for k in range(1, total + 1):
        signal.alarm(int(tlim))
        try:
            ok, n, _ = RL.feasible_with(sc, k)
        except TO:
            return k, False, "超时（≥该值）"
        finally:
            signal.alarm(0)
        if ok:
            return k, True, f"{k} 可行"
    return None, True, "上限内都不可行"


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "requests_family")
    tl = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    res = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        sc = M.load_scenario(os.path.join(d, f))
        t0 = time.time()
        rk, exact, note = robot_lb(sc, tl)
        tk, disj, slack = tool_lb(sc)
        res[f[:-5]] = dict(robot_lb=rk, robot_exact=exact, robot_note=note, tool_lb=tk, tool_adjacent_disjoint=disj,
                           tool_slack=slack, total_lb=(rk + tk) if rk else None, secs=round(time.time() - t0, 1))
        print(f[:-5], res[f[:-5]], flush=True)
    json.dump(res, open(os.path.join(HERE, "exact", os.environ.get("BOUNDS_OUT", "family_bounds.json")), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
