"""重排班模拟器自检：
1. 原计划完整重放 = 原计划目标值；
2. 无事件时，"照原计划"规则的不偏离解码 = 原计划（改动 0、目标相同）；
3. 无事件时，dec5_from 用原计划基因从中间继续 = 原计划；encode_dec5 编出的基因也 = 原计划；
4. 各类事件下三种解码随机基因的可行率、改动数。"""
import glob, os, sys, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C  # noqa: E402

insts = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(HERE, "plans", "*.npy")))
n_inst = int(sys.argv[1]) if len(sys.argv) > 1 else len(insts)
bad = collections.Counter(); tot = collections.Counter()
stat = collections.defaultdict(list)
rng = np.random.default_rng(0)
for inst in insts[:n_inst]:
    x = np.load(os.path.join(HERE, "plans", inst + ".npy"))
    sc = C.I.load(inst)
    pl = C.Plan(sc, x)
    s = pl.replay(len(pl.duties)); o = s.objectives()
    tot["replay"] += 1; bad["replay"] += not (o and abs(o[0] - pl.obj[0]) < 1e-6 and abs(o[1] - pl.obj[1]) < 1e-6)
    for frac in (0.3, 0.6):
        k = int(frac * len(pl.duties))
        scn = C.Scenario(inst, x, k, {"type": "none"})
        K, _ = C.R.n_slots(sc, 0.25)
        x0 = pl.x.copy(); x0[1:2 * K:2] = 0.0
        e = scn.evaluate(C.decoder(scn, "plan")(x0))
        tot["plan_rule_only"] += 1; bad["plan_rule_only"] += not (e and e[1] == 0 and e[0] == pl.obj[0] and abs(e[2] - pl.obj[1]) < 1e-6)
        e = scn.evaluate(C.decoder(scn, "dec5")(pl.x))
        tot["dec5_from"] += 1; bad["dec5_from"] += not (e and e[1] == 0 and e[0] == pl.obj[0])
        xe, r = C.encode_dec5(scn); e = scn.evaluate(r)
        tot["encode"] += 1; bad["encode"] += not (e and e[1] == 0 and e[0] == pl.obj[0])
        for typ, ev in [("breakdown", {"type": "breakdown", "D": 48}), ("early_maint", {"type": "early_maint"}), ("delay", {"type": "delay", "d": 6}),
                        ("overrun", {"type": "overrun", "d": 4}), ("tool_loss", {"type": "tool_loss"})]:
            scn = C.Scenario(inst, x, k, ev)
            if not scn.valid:
                continue
            e = scn.evaluate(C.decoder(scn, "plan")(x0))
            stat[(typ, "plan_rule_only")].append(e)
            xe, r = C.encode_dec5(scn); stat[(typ, "seed")].append(scn.evaluate(r))
            for dname in ("plan", "sparse", "dec5"):
                d = C.decoder(scn, dname)
                for _ in range(4):
                    stat[(typ, dname)].append(scn.evaluate(d(rng.random(scn.nv))))
for k in tot:
    print(f"{k}: {tot[k] - bad[k]}/{tot[k]} 一致")
print("\n事件 / 解码：可行率，平均改动数，平均资源数（相对原计划）")
for (typ, dn), v in sorted(stat.items()):
    f = [e for e in v if e]
    print(f"{typ:12s} {dn:15s} 可行 {len(f)}/{len(v)}  改动 {np.mean([e[1] for e in f]) if f else float('nan'):5.1f}  资源 {np.mean([e[0] for e in f]) if f else float('nan'):5.1f}")
