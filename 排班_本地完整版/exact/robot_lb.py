"""机器人数量下界：有限时域上的精确可行性搜索（对工具做松弛）
问题：只用 k 台机器人（类型任意组合，受各类型数量上限约束），能否让值岗覆盖到任务时长 T？
松弛（只会让可行性变容易，因此"不可行"的结论对原模型成立）：
  · 工具数量不限，且每班的拆卸时间取该机器人可带工具类型中的最小值（就绪更早）
  · 首班安装时间取可带工具类型中的最大值（首班覆盖更长）
其余规则与原模型完全一致（可用判定 Next_Ready ≤ E − 去程；值岗首尾相接；剩余工时不足即维修）。
搜索：深度优先 + 记忆化（状态 = 当前 E、各机器人的(类型, 相对就绪时间, 剩余工时)、各类型剩余可新建数）。
用法: python exact/robot_lb.py
"""
import os, sys, time
from functools import lru_cache
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mirror as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCEN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]


def robot_params(sc):
    out = []
    for ty, P in enumerate(sc["R"]):
        comp = [sc["Tl"][int(t)] for t in P["cargo_type_list"]]
        out.append(dict(d=P["work_time"], out=P["out_travel_time"], ret=P["return_travel_time"],
                        rem=min(c["removal_time"] for c in comp), ins=max(c["install_time"] for c in comp),
                        ch=P["charge_time"], mt=P["maintenance_time"], single=P["single_work_time"],
                        cmax=P["continue_max_work"], limit=P["limit"]))
    return out


def feasible_with(sc, k, types=None):
    """k 台机器人能否覆盖 T；types 限定可用类型（None 为全部）。返回 (可行, 访问状态数, 一条可行序列或 None)"""
    RP = robot_params(sc)
    T = sc["T"]
    types = list(range(len(RP))) if types is None else types
    seen = {}
    nodes = [0]

    def rec(E, robots, left, made):
        # robots: tuple of (type, rel_ready, remain) 排序后作为状态；rel_ready 截到 −out（再小等价）
        if E >= T:
            return ()
        key = (E, robots, left, made)
        if key in seen:
            return seen[key]
        nodes[0] += 1
        res = None
        tried = set()
        # 复用
        for idx, (ty, rel, rm) in enumerate(robots):
            P = RP[ty]
            if (rel <= -P["out"] + 1e-9) and rm >= P["single"] and (ty, rel, rm) not in tried:
                tried.add((ty, rel, rm))
                rest = robots[:idx] + robots[idx + 1:]
                r = go(E, rest, ty, rm, left, made)
                if r is not None:
                    res = (ty,) + r; break
        # 新建
        if res is None and made < k:
            for ty in types:
                if left[ty] > 0:
                    nl = left[:ty] + (left[ty] - 1,) + left[ty + 1:]
                    r = go(E, robots, ty, RP[ty]["cmax"], nl, made + 1)
                    if r is not None:
                        res = (ty + 100,) + r; break
        seen[key] = res
        return res

    def go(E, rest, ty, rm, left, made):
        P = RP[ty]
        if E == 0:
            dend = P["ins"] + P["out"] + P["d"]
        else:
            dend = E + P["d"]
        back = dend + P["ret"] + P["rem"]
        rm2 = rm - P["single"]
        if rm2 >= P["single"]:
            ready = back + P["ch"]
        else:
            ready = back + P["mt"]; rm2 = P["cmax"]
        nr = []
        for (t2, rel, r2) in rest:
            nr.append((t2, max(rel - (dend - E), -RP[t2]["out"]), r2))
        nr.append((ty, max(ready - dend, -P["out"]), rm2))
        return rec(dend, tuple(sorted(nr)), left, made)

    sys.setrecursionlimit(100000)
    left0 = tuple(p["limit"] for p in RP)
    r = rec(0, (), left0, 0)
    return r is not None, nodes[0], r


if __name__ == "__main__":
    for s in SCEN:
        sc = M.load_scenario(os.path.join(HERE, "requests", s + ".json"))
        t0 = time.time()
        line = [s, f"T={sc['T']}"]
        for k in range(1, 7):
            ok, n, seq = feasible_with(sc, k)
            line.append(f"k={k}:{'可行' if ok else '不可行'}({n}状态)")
            if ok:
                break
        print("  ".join(line), f"{time.time()-t0:.1f}s", flush=True)
