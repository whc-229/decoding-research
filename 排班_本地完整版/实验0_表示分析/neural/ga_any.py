"""测试集 MOEA 验证（与 rulegen/ga_rule.py 完全相同的 NSGA-II、种子 1000+次号、输出格式），另外支持神经网络规则和显示名。
用法: python ga_any.py 臂[,臂...] 次数 进程数|auto 输出.csv [test|train|实例,...]
臂的写法见 arms.py。可续跑：已有的 (实例, 臂名, 次号) 跳过。新结果建议写 out/val_more.csv，分析时与 rulegen/out/val_full.csv 合并统一归一化。
"""
import csv, multiprocessing as mp, os, sys, time
import common as C
import arms as A
import ga_rule as GR   # 只用其 run()
import ga as G


def job(args):
    inst, name, spec, k = args
    sc = C.I.load(inst)
    t = time.time()
    fr = GR.run(sc, A.decoder(spec), 1000 + k)
    return [inst, name, k, f"{time.time() - t:.1f}", G.EVALS, C.L.nvar(sc, "dec5"), ";".join(f"{int(a)}:{b:.3f}" for a, b in fr)]


def main():
    mp.freeze_support()
    arms = [A.parse(s) for s in sys.argv[1].split(",")]
    reps, procs, outp = int(sys.argv[2]), C.nprocs(sys.argv[3]), sys.argv[4]
    sel = sys.argv[5] if len(sys.argv) > 5 else "test"
    tr, te = C.I.split()
    insts = {"test": te, "train": tr}.get(sel) or sel.split(",")
    done = set()
    if os.path.exists(outp):
        for r in csv.reader(open(outp, encoding="utf-8")):
            if r and r[0] != "scenario":
                done.add((r[0], r[1], int(r[2])))
    for _, spec in arms:          # 先在主进程里检查规则能否加载，出错立即停
        if spec != "dec5":
            A.rule_of(spec)
    jobs = [(i, n, s, k) for k in range(reps) for i in insts for n, s in arms if (i, n, k) not in done]
    # 大实例先跑，减少最后的长尾
    jobs.sort(key=lambda j: -C.L.nvar(C.I.load(j[0]), "dec5"))
    print(f"{len(jobs)} 次运行待做（已有 {len(done)}），{procs} 个进程", flush=True)
    new = not os.path.exists(outp)
    t0 = time.time()
    with open(outp, "a", newline="", encoding="utf-8") as f, mp.Pool(procs) as p:
        w = csv.writer(f)
        if new:
            w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        for n, row in enumerate(p.imap_unordered(job, jobs, chunksize=1), 1):
            w.writerow(row); f.flush()
            if n % 20 == 0 or n == len(jobs):
                el = time.time() - t0
                print(f"{n}/{len(jobs)}  已用 {el / 60:.0f} 分钟，预计还要 {el / n * (len(jobs) - n) / 60:.0f} 分钟", flush=True)


if __name__ == "__main__":
    main()
