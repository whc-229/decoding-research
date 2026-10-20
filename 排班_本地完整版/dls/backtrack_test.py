"""回溯修复解码（等价模型上的原型）：
按基因解码（排序 = 出勤少优先，即 dec3f 的排序），一旦某班出现"没有可用机器人"（只能新开），
就回到前 W 班，依次尝试把某一班改派成另一台可用机器人、其余基因不变地重新推进到该班；
若能让该班有可用机器人，就采用这个修改（相当于在必要处自动"偏离规则"）；都不行才新开。
用法: python dls/backtrack_test.py
"""
import copy, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exact"))
import mirror as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TH = M.THETA


def decode_bt(sc, x, W=6, cap=True, key="count"):
    x = np.asarray(x, np.float32).astype(np.float64)
    n = len(x); h = n // 2
    rc = M.rep_ceil_factory(sc)
    nty = len(sc["R"])

    def avail(s):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=(lambda r: (r.count, -r.remain)) if key == "count" else (lambda r: (r.remain, r.count)))
        return av

    def step(s, i, forced=None):
        """执行第 i 班；forced = 指定复用的可用列表下标。返回 0 = 复用，1 = 新开，-1 = 不可行（与 C++ bt_step 相同）"""
        av = avail(s)
        if forced is not None:
            return 0 if s.dispatch_reuse(av[forced], x[i + h]) else -1
        k = M.decode_robot_select(x[i], len(av), nty)
        if cap and av and k >= len(av):
            c = sum(M.robot_capacity_hours(sc, r, s.E, sc["T"], rc) for r in s.robots)
            if c + 1e-9 >= sc["T"] - s.E:
                u = (x[i] - TH) / (1 - TH); k = min(max(int(max(u, 0) * len(av)), 0), len(av) - 1)
        if k < len(av):
            return 0 if s.dispatch_reuse(av[k], x[i + h]) else -1
        return 1 if s.dispatch_new(k - len(av), x[i + h]) else -1

    s = M.Sim(sc, False)
    snaps = []           # 每班开始前的状态快照
    forced = {}          # 回溯改派：班次 -> 可用列表下标
    i = 0
    fixes = 0
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
                        s = trial; forced = {kk: vv for kk, vv in newf.items() if kk <= t}
                        snaps = snaps[:t + 1]
                        for j in range(t + 1, i + 1):
                            pass
                        fixed = True; fixes += 1
                        break
                if fixed:
                    break
            if fixed:
                # 重建 t+1..i 的快照：简单起见从 t 重新推进一次记录
                s2 = copy.deepcopy(snaps[t]); snaps = snaps[:t]
                for j in range(t, i):
                    snaps.append(copy.deepcopy(s2)); step(s2, j, forced.get(j))
                s = s2
                snaps.append(copy.deepcopy(s))
        if step(s, i, forced.get(i)) < 0:
            return None, fixes
        i += 1
    if s.E < sc["T"] or s.failed:
        return None, fixes
    o = s.objectives()
    decode_bt.last_seq = list(s.seq)
    return (o[0], o[1]), fixes


if __name__ == "__main__":
    rng = np.random.default_rng(3)
    for scen in ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]:
        sc = M.load_scenario(os.path.join(HERE, "requests", scen + ".json"))
        nv = M.nvar_auto(sc, True); h = nv // 2
        z = np.zeros(nv)
        base, _ = M.evaluate_genes(sc, z, True, 0.0)
        bt, fx = decode_bt(sc, z)
        res = []
        for t in range(60):
            x = rng.uniform(0, 0.99, nv)
            m = rng.random(h) < [0.05, 0.15, 0.3][t % 3]
            x[:h] = np.where(m, rng.uniform(0, 0.85, h), 0.0)
            o, _ = decode_bt(sc, x)
            if o: res.append(o)
        at = [b for a, b in res if a == 9]
        print(f"{scen}: 全0 普通解码 {tuple(round(float(v),2) for v in base)} | 全0+回溯 {tuple(round(v,2) for v in bt) if bt else None}（修复 {fx} 次）"
              f" | 稀疏偏离+回溯：资源9比例 {len(at)/max(1,len(res)):.0%}，最好均衡 {min(at) if at else float('nan'):.2f}，中位 {np.median(at) if at else float('nan'):.2f}", flush=True)
