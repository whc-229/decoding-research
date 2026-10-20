"""实验3 扩充：在指定实例目录上批量运行一个"臂"（解码 + 参数）。
用法: python run_arm.py 臂名 每实例次数 进程数 输出.csv 实例目录
臂名：dec5 | K=0.1 | K=0.25 | K=0.5
"""
import csv, json, os, subprocess, sys, tempfile, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = {"dec5": ("paiban_dec5", []), "dec5_gen20": ("paiban_dec5", ["--gen", "20"]), "K=0.1": ("paiban_dec9", ["--slot-frac", "0.1"]),
        "K=0.25": ("paiban_dec9", ["--slot-frac", "0.25"]), "K=0.5": ("paiban_dec9", ["--slot-frac", "0.5"])}


def job(a):
    arm, req, rep = a
    exe, flags = ARMS[arm]
    with tempfile.TemporaryDirectory() as wd:
        out = os.path.join(wd, "r.json")
        t = time.time()
        subprocess.run([os.path.join(HERE, exe), "--request", req, "--workdir", wd, "--templates", os.path.join(HERE, "templates"),
                        "--pop", "30", "--quiet", "--out", out] + (flags if "--gen" in flags else ["--gen", "10"] + flags), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        r = json.load(open(out))
    P = [tuple(o) for o in r["pareto_objs"] if o[0] < 29999]
    nd = sorted({p for p in P if not any(q[0] <= p[0] and q[1] <= p[1] and q != p for q in P)})
    return [os.path.basename(req)[:-5], arm, rep, round(time.time() - t, 1), r["evaluations"], r["Nvar"], ";".join(f"{x:.0f}:{y:.3f}" for x, y in nd)]


if __name__ == "__main__":
    arm, reps, procs, outp, d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    reqs = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".json"))
    with Pool(procs) as p:
        res = p.map(job, [(arm, q, k) for q in reqs for k in range(reps)], chunksize=1)
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)"])
        w.writerows(res)
    print("done", len(res))
