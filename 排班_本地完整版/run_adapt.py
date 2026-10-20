"""实验2：自适应解码（paiban_dec7，末位基因选 dec5 / dec6b）的 MOEA 运行，另记录解码方式的占比。
用法: python run_adapt.py 每组次数 进程数 输出.csv 场景[,场景...]|all|family
输出列与 *_runs.csv 相同，另加：dec6_share_ep（最终档案中选 dec6b 的比例）、dec6_share_front（非支配解中选 dec6b 的比例）
"""
import csv, itertools, json, os, subprocess, sys, tempfile, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"]


def job(a):
    scen, rep = a
    req = os.path.join(HERE, "requests", scen + ".json")
    if not os.path.exists(req):
        req = os.path.join(HERE, "requests_family", scen + ".json")
    with tempfile.TemporaryDirectory() as wd:
        out = os.path.join(wd, "r.json")
        t = time.time()
        subprocess.run([os.path.join(HERE, "paiban_dec7"), "--request", req, "--workdir", wd, "--templates", os.path.join(HERE, "templates"),
                        "--pop", "30", "--gen", "10", "--quiet", "--out", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        r = json.load(open(out))
    secs = time.time() - t
    E = [(tuple(o), x[-1] >= 0.5) for o, x in zip(r["pareto_objs"], r["pareto_vars"]) if o[0] < 29999]
    P = [o for o, _ in E]
    nd = sorted({p for p in P if not any(q[0] <= p[0] and q[1] <= p[1] and q != p for q in P)})
    ndset = set(nd)
    front_flags = [f for o, f in E if o in ndset]
    return [scen, "自适应(dec5/dec6b)", rep, round(secs, 1), r["evaluations"], r["Nvar"],
            ";".join(f"{a:.0f}:{b:.3f}" for a, b in nd),
            round(sum(f for _, f in E) / max(1, len(E)), 3), round(sum(front_flags) / max(1, len(front_flags)), 3)]


if __name__ == "__main__":
    reps, procs, outp, sc = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
    if sc == "all":
        scens = SCEN
    elif sc == "family":
        scens = sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "requests_family")))
    else:
        scens = sc.split(",")
    with Pool(procs) as p:
        res = p.map(job, list(itertools.product(scens, range(reps))), chunksize=1)
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)", "dec6_share_ep", "dec6_share_front"])
        w.writerows(res)
    print("done", len(res))
