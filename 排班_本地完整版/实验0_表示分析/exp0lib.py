"""实验 0 公用库：六种解码（dec0–dec5）的统一接口、表型定义、可达性构造。
依赖排班_本地完整版/exact/mirror.py（与 C++ 逐解核对过的等价模型）。
dec5 的回溯修复从 dls/backtrack_test.py 复制并改为返回状态和改写记录，逻辑不变（W=12，与 C++ paiban_dec5 相同）。
"""
import copy, math, os, sys
import numpy as np

SRC = os.environ.get("PAIBAN_SRC", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # 默认 = 排班_本地完整版/
if not os.path.isdir(os.path.join(SRC, "exact")):
    SRC = os.path.join(SRC, "src")
sys.path.insert(0, os.path.join(SRC, "exact"))
import mirror as M  # noqa: E402

TH = M.THETA
DECODERS = ["dec0", "dec1", "dec2", "dec3f", "dec4", "dec5"]
DEC_NAME = {"dec0": "原解码", "dec1": "阈值", "dec2": "阈值+排序", "dec3f": "排序+容量预判",
            "dec4": "维修相位+容量预判", "dec5": "容量预判+回溯修复"}


def nvar(sc, dec):
    return M.nvar_auto(sc, dec in ("dec3f", "dec4", "dec5", "dec3fr", "dec5r"))


def sel_dec0(x, n_avail, n_types):
    """原解码（ROBOT_DECODER=0）：int((x − 1e-3)·(可用数 + 类型数))，C++ 向零取整"""
    return int((x - 1e-3) * (n_avail + n_types))


def phenotype(sim):
    """表型 = 派班序列（机器人编号）+ 新建工具的类型序列。工具复用是贪心确定的，两者合起来唯一决定排班。"""
    return (tuple(sim.seq), tuple(t.type for t in sim.tools))


class Result:
    __slots__ = ("obj", "sim", "used", "override", "fixes", "choices")

    def __init__(s, obj, sim, used, override=0, fixes=0, choices=None):
        s.obj, s.sim, s.used, s.override, s.fixes, s.choices = obj, sim, used, override, fixes, choices

    @property
    def feasible(s):
        return s.obj is not None

    @property
    def pheno(s):
        return phenotype(s.sim)


def _plain(sc, x, rank, cap, sel=None, fb=False):
    """dec0–dec4：逐班按基因解码。额外记录每班的 (可用数, 实际动作)。逻辑同 mirror.evaluate_genes。"""
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x)
    s = M.Sim(sc, rank)
    nty = len(sc["R"])
    rc = M.rep_ceil_factory(sc) if cap is not None else None
    sel = sel or M.decode_robot_select
    i, over, ch = 0, 0, []
    while s.E < sc["T"] and i < n // 2:
        av = s.available()
        k = sel(x[i], len(av), nty)
        if cap is not None and av and k >= len(av) and not (fb and forced_new(x[i], nty)):
            c = sum(M.robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots)
            if c + 1e-9 >= (1.0 + cap * x[n - 1]) * (sc["T"] - s.E):
                u = (x[i] - TH) / (1.0 - TH)
                k = min(max(int(max(u, 0.0) * len(av)), 0), len(av) - 1)
                over += 1
        ch.append((len(av), k))
        if k < len(av):
            ok = s.dispatch_reuse(av[k], x[i + n // 2])
        else:
            ok = s.dispatch_new(k - len(av), x[i + n // 2])
        i += 1
        if not ok:
            return Result(None, s, i, over, 0, ch)
    if s.E < sc["T"]:
        return Result(None, s, i, over, 0, ch)
    o = s.objectives()
    return Result((float(np.float32(o[0])), float(np.float32(o[1]))), s, i, over, 0, ch)


def _bt(sc, x, W=12, fb=False):
    """dec5：排序（出勤少优先）+ 容量预判 + 回溯修复。与 dls/backtrack_test.decode_bt 相同，另外返回改派记录 forced。"""
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x); h = n // 2
    rc = M.rep_ceil_factory(sc)
    nty = len(sc["R"])
    over = [0]

    def avail(s):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        return av

    def step(s, i, forced=None, count=False):
        av = avail(s)
        if forced is not None:
            return 0 if s.dispatch_reuse(av[forced], x[i + h]) else -1
        k = M.decode_robot_select(x[i], len(av), nty)
        if av and k >= len(av) and not (fb and forced_new(x[i], nty)):
            c = sum(M.robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots)
            if c + 1e-9 >= sc["T"] - s.E:
                u = (x[i] - TH) / (1 - TH); k = min(max(int(max(u, 0) * len(av)), 0), len(av) - 1)
                if count:
                    over[0] += 1
        if k < len(av):
            return 0 if s.dispatch_reuse(av[k], x[i + h]) else -1
        return 1 if s.dispatch_new(k - len(av), x[i + h]) else -1

    s = M.Sim(sc, False)
    snaps, forced = [], {}
    i = fixes = 0
    while s.E < sc["T"] and i < h:
        snaps = snaps[:i] + [copy.deepcopy(s)]
        if not avail(s) and s.robots and W > 0:
            fixed = False
            for t in range(i - 1, max(-1, i - 1 - W), -1):
                base = snaps[t]
                av_t = avail(base)
                cur = forced.get(t)
                for alt in range(len(av_t)):
                    if alt == cur:
                        continue
                    trial = copy.deepcopy(base)
                    ok = True
                    newf = dict(forced); newf[t] = alt
                    for j in range(t, i):
                        if step(trial, j, alt if j == t else None) != 0:
                            ok = False; break
                    if ok and avail(trial):
                        forced = {kk: vv for kk, vv in newf.items() if kk <= t}
                        snaps = snaps[:t + 1]
                        fixed = True; fixes += 1
                        break
                if fixed:
                    break
            if fixed:
                s2 = copy.deepcopy(snaps[t]); snaps = snaps[:t]
                for j in range(t, i):
                    snaps.append(copy.deepcopy(s2)); step(s2, j, forced.get(j))
                s = s2
                snaps.append(copy.deepcopy(s))
        if step(s, i, forced.get(i), count=True) < 0:
            return Result(None, s, i + 1, over[0], fixes, forced)
        i += 1
    if s.E < sc["T"] or s.failed:
        return Result(None, s, i, over[0], fixes, forced)
    o = s.objectives()
    return Result((float(o[0]), float(o[1])), s, i, over[0], fixes, forced)


FB_FRAC = 0.7


def forced_new(x, nty):
    """dec3fr/dec5r：新开区间内每个类型子区间的上 30% 表示"强制新开"，不受容量预判改写（恢复可达性）"""
    if x < TH:
        return False
    u = (x - TH) / (1.0 - TH) * nty
    return (u - min(int(u), nty - 1)) > FB_FRAC


def decode(sc, x, dec):
    if dec == "dec3fr":
        return _plain(sc, x, True, 0.0, fb=True)
    if dec == "dec5r":
        return _bt(sc, x, fb=True)
    if dec == "dec0":
        return _plain(sc, x, False, None, sel_dec0)
    if dec == "dec1":
        return _plain(sc, x, False, None)
    if dec == "dec2":
        return _plain(sc, x, True, None)
    if dec == "dec3f":
        return _plain(sc, x, True, 0.0)
    if dec == "dec4":
        return _plain(sc, x, "phase", 0.0)
    if dec == "dec5":
        return _bt(sc, x)
    raise ValueError(dec)


# ---------- 可达性：给定目标排班（派班序列 + 新建工具类型），构造能解码出它的基因 ----------
GRID = np.concatenate([np.linspace(0.0005, 0.9895, 400)])


def reach_genes(sc, seq, tools, dec):
    """逐班模拟目标排班：在当前状态下，找一个机器人基因值使解码动作等于目标动作、一个工具基因值使新建工具类型一致。
    返回 (基因 或 None, 首个无法表示的班次)。dec5 先按 dec3f 构造，再检查回溯修复是否改动了它。"""
    base = {"dec5": "dec3f", "dec5r": "dec3fr"}.get(dec, dec)
    rank = {"dec0": False, "dec1": False, "dec2": True, "dec3f": True, "dec3fr": True, "dec4": "phase"}[base]
    cap = 0.0 if base in ("dec3f", "dec3fr", "dec4") else None
    fb = base == "dec3fr"
    sel = sel_dec0 if base == "dec0" else M.decode_robot_select
    nv = nvar(sc, dec); h = nv // 2
    x = np.zeros(nv)
    s = M.Sim(sc, rank)
    nty = len(sc["R"])
    rc = M.rep_ceil_factory(sc) if cap is not None else None
    tool_iter = iter(tools)
    for i, rid in enumerate(seq):
        av = s.available()
        ids = [r.id for r in av]
        capok = None
        found = None
        for g in GRID:
            g = float(np.float32(g))
            k = sel(g, len(av), nty)
            if cap is not None and av and k >= len(av) and not (fb and forced_new(g, nty)):
                if capok is None:
                    capok = sum(M.robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots) + 1e-9 >= sc["T"] - s.E
                if capok:
                    u = (g - TH) / (1.0 - TH); k = min(max(int(max(u, 0.0) * len(av)), 0), len(av) - 1)
            if k < len(av):
                if ids[k] == rid:
                    found = (g, k); break
            else:
                ty = s.new_type(k - len(av))
                ser = sc["R"][ty]["limit"] - s.resR[ty] + 1 if ty is not None else None
                if ty is not None and f"Robot_{ty}_{ser}" == rid:
                    found = (g, k); break
        if found is None:
            return None, i
        g, k = found
        x[i] = g
        # 工具基因：试探哪些值让新建工具类型与目标一致
        ntool0 = len(s.tools)
        okt = None
        for tg in np.linspace(0.0005, 0.9895, 60):
            tg = float(np.float32(tg))
            t2 = copy.deepcopy(s)
            if k < len(av):
                ok = t2.dispatch_reuse(t2.available()[k], tg)
            else:
                ok = t2.dispatch_new(k - len(av), tg)
            if not ok:
                continue
            new_types = [t.type for t in t2.tools[ntool0:]]
            exp = list(tools[ntool0:ntool0 + len(new_types)])
            if new_types == exp and t2.seq[-1] == rid:
                okt = (tg, t2); break
        if okt is None:
            return None, i
        x[i + h], s = okt
    if dec in ("dec5", "dec5r"):
        r = decode(sc, x, dec)
        if r.sim.seq != list(seq):
            return None, -1
    return x, None


def write_back(sc, x, r):
    """拉马克式写回：把解码实际执行的动作写回机器人基因，使写回后的基因不经容量预判改写、不经回溯修复就解码出同一排班。
    原基因已表示同一动作（按阈值解码的含义）的位置保持不变；只改被改写/被修复的位置。返回 (新基因, 改动位数)。"""
    if not r.feasible:
        return x, 0
    x = np.asarray(x, np.float32).astype(np.float64).copy()
    n = len(x); h = n // 2
    nty = len(sc["R"])
    s = M.Sim(sc, True)
    changed = 0
    for i, rid in enumerate(r.sim.seq):
        av = s.available()
        ids = [q.id for q in av]
        k0 = M.decode_robot_select(x[i], len(av), nty)
        if rid in ids:
            k = ids.index(rid)
            if k0 != k:
                x[i] = (k + 0.5) / len(av) * TH; changed += 1
            ok = s.dispatch_reuse(av[k], x[i + h])
        else:
            ty = int(rid.split("_")[1])
            # 新开：选一个解码到该类型（考虑顺延）的值
            if not (k0 >= len(av) and s.new_type(k0 - len(av)) == ty):
                x[i] = TH + (ty + 0.5) / nty * (1 - TH) if av else (ty + 0.5) / nty
                if FB_FRAC < 1 and av:
                    x[i] = TH + (ty + 0.85) / nty * (1 - TH)   # 落在强制新开带内，避免再次被容量预判改写
                changed += 1
            ok = s.dispatch_new(M.decode_robot_select(float(np.float32(x[i])), len(av), nty) - len(av), x[i + h])
        if not ok:
            return None, changed
    return x, changed
