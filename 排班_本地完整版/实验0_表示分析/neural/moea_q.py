"""R0：训练实例 MOEA，并记录前沿解实际用到的偏离数（对照 FJSP T3 的 P1）。
NSGA-II 直接调用 moea_any.run_nsga2（与 ga_rule.run 逐行相同），只在解码函数外包一层，记下每个可行目标值第一次出现时的基因，
所以前沿与 moea_any.py 逐位相同；输出 CSV 的格式也与 moea_any.py 相同（可与 train_Kext.csv 合并分析）。
另写 <输出>_dev.csv：每次运行的每个前沿点一行——
  n_dev   = 实际用到的偏离数：生效的偏离槽（a ≥ dev_on）落在已排班次内的不同班次数（同一班多个槽只算 1 个；
            落在实际班次数之外的槽不起作用，不算）；
  n_shift = 该解的班次数；n_slot = 槽数 K；n_on = 生效的槽数（含落在班次外、互相覆盖的）。
用法（neural/ 下）: python moea_q.py 臂[,臂...] 次数 进程数 输出.csv [train|实例,...] [--seed-base 5000]
  臂写法同 arms.py，例如 X1.0q0.6:ES16(s0)=X1.0q0.6:nn:out/es/il_h16/best.npz。可续跑：(实例, 臂, 次号) 已在输出里的跳过。
"""
import argparse, csv, multiprocessing as mp, os, time
import numpy as np
import common as C
import arms as A
import moea_any as MA
import ruledec_ext as X


def job(args):
    """一次运行 → (前沿行, 偏离数行)"""
    inst, name, spec, k, seed_base = args
    sc = C.I.load(inst)
    dec0 = A.decoder(spec)
    kf, q = A.kq_of(spec)
    on = 0.6 if q is None else round(1.0 - q, 10)
    seen = {}

    def dec(sc_, x):
        """包一层：记录每个可行目标值第一次出现时的基因与班次数"""
        r = dec0(sc_, x)
        if r.feasible and r.obj not in seen:
            seen[r.obj] = (np.array(x, dtype=np.float64), r.used)
        return r
    t = time.time()
    nv = A.nvar(spec, sc)
    front = MA.run_nsga2(sc, dec, seed_base + k, [465], nv=nv)[465]
    secs = f"{time.time() - t:.1f}"
    K, _ = C.R.n_slots(sc, kf)
    row = [inst, name, k, secs, 465, nv, ";".join(f"{int(a)}:{b:.3f}" for a, b in front)]
    devs = []
    for a, b in front:
        x, used = seen[(a, b)]
        dm = X.devmap(sc, np.asarray(x, np.float32).astype(np.float64), kf, 0, on)   # 与解码内部相同的取数（float32）
        n_on = int(np.sum(np.asarray(x[1:2 * K:2], np.float32) >= on))
        devs.append([inst, name, k, int(a), f"{b:.3f}", sum(1 for i in dm if i < used), used, K, n_on])
    return row, devs


def main():
    mp.freeze_support()
    ap = argparse.ArgumentParser()
    ap.add_argument("arms"); ap.add_argument("reps", type=int); ap.add_argument("procs"); ap.add_argument("out")
    ap.add_argument("sel", nargs="?", default="train")
    ap.add_argument("--seed-base", type=int, default=5000)
    a = ap.parse_args()
    arms = [A.parse(s) for s in a.arms.split(",")]
    tr, te = C.I.split()
    insts = {"train": tr}.get(a.sel) or a.sel.split(",")
    assert not set(insts) & set(te), "R0 只用训练实例"
    dout = a.out[:-4] + "_dev.csv"
    done = set()
    if os.path.exists(a.out):
        for r in csv.reader(open(a.out, encoding="utf-8")):
            if r and r[0] != "scenario":
                done.add((r[0], r[1], int(r[2])))
    for _, spec in arms:
        A.rule_of(spec)
    jobs = [(i, n, s, k, a.seed_base) for k in range(a.reps) for i in insts for n, s in arms if (i, n, k) not in done]
    jobs.sort(key=lambda j: -A.nvar(j[2], C.I.load(j[0])))
    procs = C.nprocs(a.procs)
    print(f"{len(jobs)} 次运行待做（已有 {len(done)}），{procs} 个进程", flush=True)
    new, newd = not os.path.exists(a.out), not os.path.exists(dout)
    t0 = time.time()
    with open(a.out, "a", newline="", encoding="utf-8") as f, open(dout, "a", newline="", encoding="utf-8") as fd, mp.Pool(procs) as p:
        w, wd = csv.writer(f), csv.writer(fd)
        if new:
            w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        if newd:
            wd.writerow(["scenario", "variant", "run", "res", "bal", "n_dev", "n_shift", "n_slot", "n_on"])
        for n, (row, devs) in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            wd.writerows(devs); fd.flush()        # 先写偏离数，再写前沿行：续跑以前沿行为准，偏离数行最多重复（分析时去重）
            w.writerow(row); f.flush()
            if n % 20 == 0 or n == len(jobs):
                el = time.time() - t0
                print(f"{n}/{len(jobs)}  已用 {el / 60:.0f} 分钟，预计还要 {el / n * (len(jobs) - n) / 60:.0f} 分钟", flush=True)


if __name__ == "__main__":
    main()
