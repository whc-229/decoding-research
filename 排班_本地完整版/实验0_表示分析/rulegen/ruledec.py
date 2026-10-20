"""规则生成实验：可插拔"默认规则"的稀疏偏离解码（dec9 的结构，规则可替换）。

基因结构与 sde.decode6（= C++ paiban_dec9）完全相同：K 个偏离槽 (p, a)，默认类型基因 x[2K]，后半段为工具基因。
唯一的区别：每班"不偏离时做什么"、"改派偏离在哪些机器人里选"、"新开偏离/无可用机器人时新开哪种类型"由规则决定。

规则接口（LLM 生成的代码只需定义这一个函数）：
    def rule(ctx) -> list
返回按偏好排序的动作列表，每个动作是 ("reuse", 机器人视图) 或 ("new", 类型编号)。
  - 列表第一个动作 = 该班不偏离时的默认动作；
  - 改派偏离在列表中其余的 "reuse" 动作里按顺序选；
  - 新开类型优先用列表里出现的 "new" 动作的类型；
  - 没列出的可用机器人按 (出勤少, 剩余工时多) 补到末尾；非法或重复项忽略。
默认规则 default_rule 与 dec9 逐解相同（check_ruledec.py 核对）。
"""
import copy, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import exp0lib as L  # noqa: E402

M = L.M
DEV_ON = 0.6
REUSE_SHARE = 0.85


class RobotView:
    """只读视图，给规则看的机器人状态。"""
    __slots__ = ("type", "serial", "count", "hours", "budget", "duties_left", "ready", "first_maint", "last_end", "idx", "_r")

    def __init__(s, r, sc, idx):
        P = sc["R"][r.type]
        s._r = r
        s.type = r.type
        s.serial = r.serial                    # 该类型的第几台（1 起），(type, serial) 唯一标识一台机器人
        s.count = r.count                      # 已出勤班次数
        s.hours = r.dur                        # 已出勤时长（h）
        s.budget = r.remain                    # 距下次维修还剩的工作预算（h）
        s.duties_left = int(r.remain // P["single_work_time"] + 1e-9)   # 下次维修前还能出勤几班（含本班）
        s.ready = r.ready                      # 最早可再次出发的时刻
        s.first_maint = r.first_rep            # 第一次进维修的时刻（尚未维修为 None）
        s.last_end = r.duties[-1][1] if r.duties else None   # 上一班结束时刻
        s.idx = idx                            # 开启顺序（0 起）


class Ctx:
    """规则看到的决策时刻信息。"""

    def __init__(s, sc, sim, shift, nmax, avail, gene_type, rc):
        s._sc, s._sim, s._rc = sc, sim, rc
        s.t = sim.E                            # 当前班开始时刻（h）
        s.T = sc["T"]                          # 总时域（h）
        s.remaining = sc["T"] - sim.E          # 剩余需要覆盖的时长（h）
        s.shift = shift                        # 当前是第几班（0 起）
        s.n_shifts_max = nmax                  # 班次数上界
        idx = {id(r): k for k, r in enumerate(sim.robots)}
        s.robots = [RobotView(r, sc, idx[id(r)]) for r in sim.robots]       # 已开启的全部机器人
        byid = {id(v._r): v for v in s.robots}
        s.available = [byid[id(r)] for r in avail]                           # 本班可出发的机器人，已按 (出勤少, 剩余工时多) 排好
        s.types = [dict(t) if t else None for t in sc["R"]]                  # 各机器人类型参数（None 表示没有该类型）
        s.left = list(sim.resR)                                              # 各类型还能新开几台
        s.gene_type = gene_type                                              # 基因给出的默认新开类型
        s._cap = None

    @property
    def capacity(s):
        """已开启机器人在剩余时域内还能提供的出勤时长估计（h），与 dec5 容量预判相同。≥ remaining 表示现有机器人理论上够用。"""
        if s._cap is None:
            s._cap = sum(M.robot_capacity_hours(s._sc, r, s._sim.E, s._sc["T"], s._rc) for r in s._sim.robots)
        return s._cap


def default_rule(ctx):
    """dec9 的规则：派出勤最少的可用机器人；没有可用的就新开基因指定类型。"""
    return [("reuse", r) for r in ctx.available] + [("new", ctx.gene_type)]


DEFAULT_RULE_SRC = '''def rule(ctx):
    # 派出勤最少（并列时剩余工时多）的可用机器人；没有可用的就新开基因指定的类型
    return [("reuse", r) for r in ctx.available] + [("new", ctx.gene_type)]
'''


def n_slots(sc, kfrac):
    nmax = L.nvar(sc, "dec5") // 2 - 1
    return max(4, math.ceil(kfrac * nmax - 1e-9)), nmax


def devmap(sc, x, kfrac, i0=0):
    """i0 > 0（重排班）时，偏离位置映射到剩余的班次 i0 … nmax−1 上"""
    K, nmax = n_slots(sc, kfrac)
    nrem = max(1, nmax - i0)
    d = {}
    h = L.nvar(sc, "dec5") // 2
    for k in range(K):
        if 2 * k + 1 >= h:
            break
        p, a = x[2 * k], x[2 * k + 1]
        if a >= DEV_ON:
            d[i0 + min(int(p * nrem), nrem - 1)] = (a - DEV_ON) / (1.0 - DEV_ON)
    return d


class RuleError(Exception):
    pass


def _normalize(opts, ctx, nty):
    """→ (默认动作, 改派候选机器人列表[按规则顺序], 新开类型偏好列表)"""
    av_ids = {id(v): v for v in ctx.available}
    reuse, seen, newp, first = [], set(), [], None
    if not isinstance(opts, (list, tuple)):
        raise RuleError("rule must return a list")
    for o in opts:
        if not isinstance(o, (list, tuple)) or len(o) != 2:
            continue
        kind, v = o
        if kind == "reuse" and id(v) in av_ids and id(v) not in seen:
            seen.add(id(v)); reuse.append(v)
            if first is None:
                first = ("reuse", v)
        elif kind == "new":
            try:
                ty = int(v)
            except Exception:
                continue
            if 0 <= ty < nty and ctx.types[ty] is not None and ty not in newp:
                newp.append(ty)
                if first is None:
                    first = ("new", ty)
    for v in ctx.available:
        if id(v) not in seen:
            reuse.append(v)
    if ctx.gene_type not in newp:
        newp.append(ctx.gene_type)
    if first is None:
        first = ("reuse", reuse[0]) if reuse else ("new", newp[0])
    return first, reuse, newp


def decode_rule(sc, x, rule=default_rule, kfrac=0.25, W=12, stats=None, start=None):
    """稀疏偏离解码，默认规则可替换。返回 exp0lib.Result。stats（dict）可收集：规则选新开的次数等。
    start=(状态, i0)：从中间状态继续解码（重排班）：前 i0 班已执行、不可改动，回溯修复也不会越过 i0。"""
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x); h = n // 2
    K, nmax = n_slots(sc, kfrac)
    nty = len(sc["R"])
    i0 = start[1] if start else 0
    dmap = devmap(sc, x, kfrac, i0)
    tdef = min(int(x[2 * K] * nty), nty - 1)
    rc = M.rep_ceil_factory(sc)

    def avail(s):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        return av

    def choose(i, s, av):
        """返回 ('reuse', 机器人) 或 ('new', 类型)"""
        ctx = Ctx(sc, s, i, nmax, av, tdef, rc)
        first, reuse, newp = _normalize(rule(ctx), ctx, nty)
        u = dmap.get(i)
        if u is not None:
            if u < REUSE_SHARE:
                alts = [v for v in reuse if not (first[0] == "reuse" and v is first[1])]
                if alts and (first[0] == "new" or len(av) >= 2):
                    return ("reuse", alts[min(int(u / REUSE_SHARE * len(alts)), len(alts) - 1)]._r)
            else:
                ty = min(int((u - REUSE_SHARE) / (1 - REUSE_SHARE) * nty), nty - 1)
                if not av:
                    return ("new", ty)
                if ctx.capacity + 1e-9 < sc["T"] - s.E:
                    return ("new", ty)
        if first[0] == "reuse":
            return ("reuse", first[1]._r)
        if stats is not None and av:
            stats["rule_new"] = stats.get("rule_new", 0) + 1
        return ("new", newp[0])

    def step(s, i, forced=None):
        av = avail(s)
        if forced is not None:
            return 0 if s.dispatch_reuse(av[forced], x[i + h]) else -1
        kind, v = choose(i, s, av)
        if kind == "reuse":
            return 0 if s.dispatch_reuse(v, x[i + h]) else -1
        return 1 if s.dispatch_new(v, x[i + h]) else -1

    s = copy.deepcopy(start[0]) if start else M.Sim(sc, False)
    snaps, forced = {}, {}
    i, fixes = i0, 0
    while s.E < sc["T"] and i < h:
        for kk in [kk for kk in snaps if kk > i]:
            del snaps[kk]
        snaps[i] = copy.deepcopy(s)
        if not avail(s) and s.robots and W > 0 and i not in dmap:
            fixed = False
            for t in range(i - 1, max(i0 - 1, i - 1 - W), -1):
                base = snaps[t]
                av_t = avail(base)
                cur = forced.get(t)
                for alt in range(len(av_t)):
                    if alt == cur:
                        continue
                    trial = copy.deepcopy(base)
                    ok = True
                    for j in range(t, i):
                        if step(trial, j, alt if j == t else forced.get(j) if j < t else None) != 0:
                            ok = False; break
                    if ok and avail(trial):
                        forced = {kk: vv for kk, vv in forced.items() if kk < t}
                        forced[t] = alt
                        fixed = True; fixes += 1
                        break
                if fixed:
                    break
            if fixed:
                s2 = copy.deepcopy(snaps[t])
                for j in range(t, i):
                    snaps[j] = copy.deepcopy(s2); step(s2, j, forced.get(j))
                s = s2
                snaps[i] = copy.deepcopy(s)
        if step(s, i, forced.get(i)) < 0:
            return L.Result(None, s, i + 1, 0, fixes, forced)
        i += 1
    if s.E < sc["T"] or s.failed:
        return L.Result(None, s, i, 0, fixes, forced)
    o = s.objectives()
    return L.Result((float(o[0]), float(o[1])), s, i, 0, fixes, forced)


# ---------------- 编译 LLM 代码（受限执行） ----------------
import ast  # noqa: E402

SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k) for k in
                 ["min", "max", "sorted", "len", "range", "abs", "sum", "enumerate", "zip", "list", "dict", "set", "tuple",
                  "float", "int", "bool", "any", "all", "round", "reversed", "isinstance", "map", "filter", "str"]}
BANNED_NAMES = {"open", "exec", "eval", "compile", "globals", "locals", "getattr", "setattr", "delattr", "input",
                "vars", "dir", "type", "object", "breakpoint", "help", "memoryview", "bytearray"}


def compile_rule(src):
    """检查并编译规则代码，返回 rule 函数。只允许 math，禁止 import、双下划线属性、文件与反射操作、访问 _ 开头的私有字段。"""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.With, ast.AsyncFunctionDef,
                             ast.Await, ast.Yield, ast.YieldFrom, ast.ClassDef, ast.Try, ast.Raise, ast.Delete)):
            raise RuleError(f"不允许的语法：{type(node).__name__}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise RuleError(f"不允许访问私有属性：{node.attr}")
        if isinstance(node, ast.Name) and (node.id in BANNED_NAMES or node.id.startswith("__")):
            raise RuleError(f"不允许的名称：{node.id}")
        if isinstance(node, ast.While):
            raise RuleError("不允许 while 循环（防止死循环），请用 for")
    ns = {"__builtins__": SAFE_BUILTINS, "math": math}
    exec(compile(tree, "<rule>", "exec"), ns)
    f = ns.get("rule")
    if not callable(f):
        raise RuleError("代码里没有定义 rule(ctx)")
    return f
