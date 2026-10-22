"""扩展编码（任务 D1）：基因布局 [2K 个偏离槽基因][1 个默认类型基因][每班 1 个工具基因]，K = ceil(kfrac × 班次上界)（至少 4，与 ruledec.n_slots 相同），
基因长度 2K + 1 + (班次上界 + 1) 随 K 变化。原布局（rulegen/ruledec.py）中前半段只放得下 K ≤ 0.5 的偏离槽，K0.75 的槽会被截断、默认类型基因
落进工具基因区；新布局没有这个限制。不修改 rulegen/。

decode_rule 由 rulegen/ruledec.decode_rule 的源码逐行替换生成，只改了三处取基因的位置：
  偏离槽 x[0:2K]（devmap，不再有"前半段放不下就截断"的判断）、默认类型 x[2K]、第 i 班工具基因 x[2K + 1 + i]；
其余（规则调用、偏离语义、回溯修复）完全相同。check_ext.py 核对：K0.25、K0.5 的旧布局基因映射到新布局后与 ruledec 逐解相同。
"""
import copy
import numpy as np
import common as C

R = C.R


def nvar(sc, kfrac):
    """扩展布局的基因长度 = 2K + 1 + (班次上界 + 1)"""
    K, nmax = R.n_slots(sc, kfrac)
    return 2 * K + 1 + nmax + 1


def devmap(sc, x, kfrac, i0=0):
    """偏离槽 (p, a)：a ≥ DEV_ON 生效，班次 = i0 + min(int(p × 剩余班次), 剩余班次 − 1)，强度 (a − DEV_ON)/(1 − DEV_ON)。
    与 ruledec.devmap 相同，只是去掉了"槽基因超出前半段就停止"的截断（新布局里槽基因总在 x[0:2K]）。"""
    K, nmax = R.n_slots(sc, kfrac)
    nrem = max(1, nmax - i0)
    d = {}
    for k in range(K):
        p, a = x[2 * k], x[2 * k + 1]
        if a >= R.DEV_ON:
            d[i0 + min(int(p * nrem), nrem - 1)] = (a - R.DEV_ON) / (1.0 - R.DEV_ON)
    return d


def from_old(sc, x, kfrac):
    """原布局基因 → 新布局（自检用）：偏离槽与默认类型取原 x[0:2K+1]，工具基因取原后半段 x[h:]"""
    K, nmax = R.n_slots(sc, kfrac)
    h = len(x) // 2
    return np.concatenate([np.asarray(x[:2 * K + 1]), np.asarray(x[h:])])


def decode_rule(sc, x, rule=R.default_rule, kfrac=0.25, W=12, stats=None, start=None):
    """扩展布局的稀疏偏离解码：x = [2K 个偏离槽基因][1 个默认类型基因][每班 1 个工具基因]，长度 = nvar(sc, kfrac)。
    除了这三处取基因的位置，逻辑与 rulegen/ruledec.decode_rule 逐行相同（本函数由那里的源码替换生成）。"""
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x)
    K, nmax = R.n_slots(sc, kfrac)
    h = nmax + 1                                  # 班次数上限（与原布局 len(x) // 2 相同）
    T0 = 2 * K + 1                                # 工具基因起点
    assert n == T0 + h, f"基因长度 {n} 与扩展布局 {T0 + h} 不符"
    nty = len(sc["R"])
    i0 = start[1] if start else 0
    dmap = devmap(sc, x, kfrac, i0)
    tdef = min(int(x[2 * K] * nty), nty - 1)
    rc = R.M.rep_ceil_factory(sc)

    def avail(s):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        return av

    def choose(i, s, av):
        """返回 ('reuse', 机器人) 或 ('new', 类型)"""
        ctx = R.Ctx(sc, s, i, nmax, av, tdef, rc)
        first, reuse, newp = R._normalize(rule(ctx), ctx, nty)
        u = dmap.get(i)
        if u is not None:
            if u < R.REUSE_SHARE:
                alts = [v for v in reuse if not (first[0] == "reuse" and v is first[1])]
                if alts and (first[0] == "new" or len(av) >= 2):
                    return ("reuse", alts[min(int(u / R.REUSE_SHARE * len(alts)), len(alts) - 1)]._r)
            else:
                ty = min(int((u - R.REUSE_SHARE) / (1 - R.REUSE_SHARE) * nty), nty - 1)
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
            return 0 if s.dispatch_reuse(av[forced], x[T0 + i]) else -1
        kind, v = choose(i, s, av)
        if kind == "reuse":
            return 0 if s.dispatch_reuse(v, x[T0 + i]) else -1
        return 1 if s.dispatch_new(v, x[T0 + i]) else -1

    s = copy.deepcopy(start[0]) if start else R.M.Sim(sc, False)
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
            return R.L.Result(None, s, i + 1, 0, fixes, forced)
        i += 1
    if s.E < sc["T"] or s.failed:
        return R.L.Result(None, s, i, 0, fixes, forced)
    o = s.objectives()
    return R.L.Result((float(o[0]), float(o[1])), s, i, 0, fixes, forced)
