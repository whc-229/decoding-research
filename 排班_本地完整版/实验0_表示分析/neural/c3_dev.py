"""任务 C3：规则到好解的距离（实验 2 的做法），训练实例上。
对每个训练实例、每条规则 R：把 dec5 老师运行（out/teacher/<实例>__dec5__<k>.pkl）里第 1 层非支配好解逐个重放（replay.py 的做法），
每班比较"好解实际做的动作"与"规则的首选"（R._normalize 后的第一个动作），不一致的班次数 = dev。
  - 规则的新开类型受基因类型影响，而稀疏编码里基因类型可自由设定，所以对每种基因类型各算一次 dev，取最小；
  - 一个实例有多个好解，按"到最近好解"取最小 dev（实验 6：规则距离应按到最近好解计），另报中位数。
比值 = dev / 偏离槽数 K_slots（K_slots = ruledec.n_slots(实例, K) 的第一个值，K = 0.25 / 0.5 / 0.75）。
比值 > 1 表示好解与规则的差别多于偏离槽数，搜索在离好解 dev − K_slots 处到底。
用法: python c3_dev.py [进程数]   输出: out/c3_dev.json（C2 报告再算与"K0.5 对 K0.25 增益"的相关）
"""
import glob, json, multiprocessing as mp, os, pickle, sys
import numpy as np
import common as C
import score_rules as SR
import replay as RP

R, M = C.R, C.M
RULES = {**{f"ES16(s{s})": f"K0.25:nn:out/es/il_h16{'' if s == 0 else f'_s{s}'}/best.npz" for s in range(3)},
         **{f"GP(run{r})": f"K0.25:../neural/out/gp/run{r}/best_rule.py" for r in range(1, 6)},
         "默认": "K0.25:default"}
KS = (0.25, 0.5, 0.75)


def dev_of(sc, x, seq, rule, gene_type):
    """沿好解的派班序列前推，统计规则首选与好解动作不同的班次数（重放失败返回 None）"""
    _, nmax = R.n_slots(sc, 0.25)
    rc = M.rep_ceil_factory(sc)
    s = M.Sim(sc, False)
    nty = len(sc["R"])
    dev = 0
    x = np.asarray(x, np.float32).astype(np.float64)   # 与 replay.py 相同：第 i 班用好解自己的工具基因 x[i + h]
    h = len(x) // 2
    for i, rid in enumerate(seq):
        _, ty, ser = rid.split("_"); ty, ser = int(ty), int(ser)
        av = RP._avail(sc, s)
        ctx = R.Ctx(sc, s, i, nmax, av, gene_type, rc)
        first, _, _ = R._normalize(rule(ctx), ctx, nty)
        hit = [r for r in s.robots if r.type == ty and r.serial == ser]
        if hit:
            same = first[0] == "reuse" and first[1]._r is hit[0]
            ok = s.dispatch_reuse(hit[0], x[i + h])
        else:
            same = first[0] == "new" and first[1] == ty
            ok = s.dispatch_new(ty, x[i + h])
        if not ok:
            return None
        dev += 0 if same else 1
    return dev


def job(args):
    """一个训练实例：各规则到各好解的 dev"""
    inst = args
    sc = C.I.load(inst)
    sols = []
    for f in sorted(glob.glob(os.path.join(C.OUT, "teacher", f"{inst}__dec5__*.pkl"))):
        d = pickle.load(open(f, "rb"))
        sols += [s for s in d["sols"] if s["rank"] == 0]
    # 同一排班只算一次
    uniq = list({tuple(s["seq"]): s for s in sols}.values())
    K = {k: R.n_slots(sc, k)[0] for k in KS}
    _, nmax = R.n_slots(sc, 0.25)
    out = {"inst": inst, "n_sols": len(uniq), "nmax": nmax, "slots": K, "rules": {}}
    for name, spec in RULES.items():
        rule = SR.picklable(spec)
        devs = []
        for s in uniq:
            ds = [dev_of(sc, s["x"], s["seq"], rule, g) for g in range(len(sc["R"])) if sc["R"][g] is not None]
            ds = [d for d in ds if d is not None]
            if ds:
                devs.append(min(ds))
        out["rules"][name] = {"min": min(devs) if devs else None, "median": float(np.median(devs)) if devs else None,
                              "n": len(devs), "shifts_median": float(np.median([len(s["seq"]) for s in uniq]))}
    return out


def main():
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    tr = C.I.split()[0]
    with mp.Pool(procs) as p:
        res = p.map(job, tr, chunksize=1)
    json.dump(res, open(os.path.join(C.OUT, "c3_dev.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("| 实例 | 好解数 | 班次上界 | K0.25 槽数 | " + " | ".join(f"{n} dev（最近 / 中位）" for n in RULES) + " |")
    for r in res:
        print(f"| {r['inst']} | {r['n_sols']} | {r['nmax']} | {r['slots'][0.25]} | " +
              " | ".join(f"{v['min']} / {v['median']}" for v in r["rules"].values()) + " |")


if __name__ == "__main__":
    main()
