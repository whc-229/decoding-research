"""实验3：偏离密度编码（paiban_dec8）的 MOEA 运行。
用法: python run_dd.py 密度(数字或 adapt) 每组次数 进程数 输出.csv 场景[,场景...]|all|family|both
输出列与 *_runs.csv 相同，另加 d_mean_front：最终非支配解所用的密度均值（自适应时有意义）。
"""
import csv, itertools, json, os, subprocess, sys, tempfile, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]
FAM = sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "requests_family")))
DENS = None


def job(a):
    scen, rep, dens = a
    req = os.path.join(HERE, "requests", scen + ".json")
    if not os.path.exists(req):
        req = os.path.join(HERE, "requests_family", scen + ".json")
    with tempfile.TemporaryDirectory() as wd:
        out = os.path.join(wd, "r.json")
        cmd = [os.path.join(HERE, "paiban_dec8"), "--request", req, "--workdir", wd, "--templates", os.path.join(HERE, "templates"),
               "--pop", "30", "--gen", "10", "--quiet", "--out", out]
        if dens != "adapt":
            cmd += ["--dev-density", dens]
        t = time.time()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        r = json.load(open(out))
    secs = time.time() - t
    E = [(tuple(o), x[-1]) for o, x in zip(r["pareto_objs"], r["pareto_vars"]) if o[0] < 29999]
    P = [o for o, _ in E]
    nd = sorted({p for p in P if not any(q[0] <= p[0] and q[1] <= p[1] and q != p for q in P)})
    ndset = set(nd)
    if dens == "adapt":
        ds = [0.02 * 30.0 ** g for o, g in E if o in ndset]
        dm = sum(ds) / max(1, len(ds))
    else:
        dm = float(dens)
    return [scen, f"偏离密度 d={dens}", rep, round(secs, 1), r["evaluations"], r["Nvar"],
            ";".join(f"{a:.0f}:{b:.3f}" for a, b in nd), round(dm, 4)]


if __name__ == "__main__":
    dens, reps, procs, outp, sc = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    scens = {"all": SCEN, "family": FAM, "both": SCEN + FAM}.get(sc, sc.split(","))
    with Pool(procs) as p:
        res = p.map(job, [(s, k, dens) for s in scens for k in range(reps if s in SCEN else max(1, reps // 2))], chunksize=1)
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)", "d_mean_front"])
        w.writerows(res)
    print("done", len(res))
