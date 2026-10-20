"""在排班问题上批量运行算法库（MOEA_serial_full_cpp）里的算法
用法: python run_lib.py 程序 场景[,场景] 算法清单 每组次数 评价预算 进程数 输出前缀
  程序：paiban_lib_dec3f（排序+容量预判，当前最好的编码）/ paiban_lib_dec2 / paiban_lib_dec3
  算法清单：all = 每种不同实现取一个代表（lib_groups.json，函数体完全相同的算法只跑一个）；或逗号分隔的注册名
输出：<前缀>_runs.csv（与 run_mech.py 同格式，可直接用 analyze_gap.py 分析）
"""
import csv, itertools, json, os, subprocess, sys, tempfile, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
PREP = {"paiban_lib_dec2": "paiban_dec2", "paiban_lib_dec3": "paiban_dec3", "paiban_lib_dec3f": "paiban_dec3f",
        "paiban_lib2_dec3f": "paiban_dec3f"}
LB = {"原请求_paiban": 9, "B_三类型720h": 9, "C_三类型1440h": 9, "D_三类型资源紧": 9}
_fb = os.path.join(HERE, "exact", "family_bounds.json")
if os.path.exists(_fb):
    LB.update({k: v["total_lb"] for k, v in json.load(open(_fb, encoding="utf-8")).items()})


def prepare(exe, scen, root):
    wd = os.path.join(root, scen)
    os.makedirs(wd, exist_ok=True)
    open(os.path.join(wd, "e.json"), "w").write("[]")
    req = os.path.join(HERE, "requests", scen + ".json")
    if not os.path.exists(req):
        req = os.path.join(HERE, "requests_family", scen + ".json")
    subprocess.run([os.path.join(HERE, PREP[exe]), "--request", req, "--workdir", wd, "--templates",
                    os.path.join(HERE, "templates"), "--eval-genes", os.path.join(wd, "e.json"),
                    "--out", os.path.join(wd, "o.json"), "--quiet"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return wd


def nd(P):
    P = [tuple(p) for p in P if p[0] < 29999]
    return sorted({p for p in P if not any(q[0] <= p[0] and q[1] <= p[1] and q != p for q in P)})


def job(a):
    exe, scen, wd, alg, rep, budget = a
    fd, out = tempfile.mkstemp(suffix=".json"); os.close(fd)
    t = time.time()
    try:
        extra = ["--lb", str(LB.get(scen, 0))] if "lib2" in exe else []   # 资源数下界（只有新程序认识该参数）
        subprocess.run([os.path.join(HERE, exe), alg, "--workdir", wd, "--budget", str(budget), "--out", out] + extra,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=max(120, budget * 0.25), check=True)
        r = json.load(open(out))
        res = dict(scen=scen, var=alg, rep=rep, secs=time.time() - t, front=nd(r["pareto_objs"]),
                   evals=r["evaluations"], nvar=r["Nvar"], ok=True)
    except Exception as e:
        res = dict(scen=scen, var=alg, rep=rep, secs=time.time() - t, front=[], evals=0, nvar=0, ok=False, err=str(e)[:80])
    finally:
        if os.path.exists(out):
            os.remove(out)
    return res


if __name__ == "__main__":
    exe, scens, algs, reps, budget, procs, prefix = sys.argv[1], sys.argv[2].split(","), sys.argv[3], \
        int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
    if algs == "all":
        algs = [g[0] for g in json.load(open(os.path.join(HERE, "lib_groups.json"), encoding="utf-8"))["groups"]]
    else:
        algs = algs.split(",")
    root = tempfile.mkdtemp(prefix="paiban_lib_")
    wds = {s: prepare(exe, s, root) for s in scens}
    jobs = [(exe, s, wds[s], a, r, budget) for s, a, r in itertools.product(scens, algs, range(reps))]
    t0 = time.time()
    done = 0
    with Pool(procs) as p, open(prefix + "_runs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "variant", "run", "seconds", "evaluations", "Nvar", "front(资源数:均衡度;...)", "ok"])
        for r in p.imap_unordered(job, jobs, chunksize=1):
            w.writerow([r["scen"], r["var"], r["rep"], round(r["secs"], 1), r["evals"], r["nvar"],
                        ";".join(f"{a:.0f}:{b:.3f}" for a, b in r["front"]), int(r["ok"])])
            fh.flush()
            done += 1
            if done % 50 == 0:
                print(f"{done}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    print(f"完成 {len(jobs)} 次运行，用时 {time.time()-t0:.0f}s")
