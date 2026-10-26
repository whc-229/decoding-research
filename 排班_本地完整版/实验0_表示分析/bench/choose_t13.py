"""T13 第 1 步判定（在看到 pilot 结果之前写好）：pilot 集（Hurink rdata la16～la30，不在 big 集里）上，
每族（db、ps、pls）取指定预算下平均 HV 最高的参数。HV：每个实例内用 CSV 中全部臂统一归一化；先对运行取平均，再对实例取平均。
并列（差 < 1e-9）取写在前面的参数。用法: python choose_t13.py pilot_t13.csv [预算=5000] → 打印并写 choose_t13.json"""
import csv, json, sys, collections
import numpy as np


def hv(P, ref=1.1):
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2


FAM = {"db": ["db0.04", "db0.1", "db0.2", "db0.4", "db0.6"], "ps": ["ps0.05", "ps0.1", "ps0.2", "ps0.4"],
       "pls": ["pls1:sp0.5", "pls2:sp0.5", "pls4:sp0.5", "pls8:sp0.5", "pls16:sp0.5"],
       "spr": ["spr0.1", "spr0.25", "spr0.5", "spr1.0", "spr2.0", "spr3.0", "spr4.0"]}
# 第 5 步（2026-10-26）：spr 选中上端 spr2.0，网格再扩一次（spr3.0、spr4.0）。
# spr（规则组合偏离，2026-10-23 加）：q = 0.4，名义 ρ = 0.04 / 0.1 / 0.2 / 0.4 / 0.8。备选规则常与 ECT 选同一候选，实际偏离步数低于名义值，所以网格一开始就包含 spr2.0。
# 第 1b 步（2026-10-23）：db 与 pls 的选中值落在网格上端，网格往上扩（db0.6；pls8、pls16）。缺的臂自动跳过。
# 多个 CSV 时合并后统一归一化：python choose_t13.py pilot_t13.csv,pilot_t13b.csv 5000

if __name__ == "__main__":
    inp = sys.argv[1]; bud = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    R = collections.defaultdict(list)
    for r in (r for f in inp.split(",") for r in csv.DictReader(open(f))):
        if int(r["evals"]) == bud:
            s = r["front(makespan:workload;...)"]
            R[(r["instance"], r["encoding"])].append([tuple(map(float, p.split(":"))) for p in s.split(";")] if s else [])
    insts = sorted({k[0] for k in R}); encs = sorted({k[1] for k in R})
    M = collections.defaultdict(list)
    for n in insts:
        assert all(R.get((n, e)) for e in encs), f"{n} 缺臂"
        pts = np.array([p for e in encs for fr in R[(n, e)] for p in fr]); lo, hi = pts.min(0), pts.max(0)
        rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        for e in encs:
            M[e].append(np.mean([hv([tuple((np.array(p) - lo) / rg) for p in fr]) for fr in R[(n, e)]]))
    mean = {e: float(np.mean(v)) for e, v in M.items()}
    pick = {}
    for f, arms in FAM.items():
        best = arms[0]
        for e in arms[1:]:
            if mean.get(e, -1) > mean.get(best, -1) + 1e-9:
                best = e
        pick[f] = best
    for e in sorted(mean, key=lambda e: -mean[e]):
        print(f"{e:12s} {mean[e]:.3f}")
    print("选中：", pick)
    json.dump(dict(budget=bud, n_inst=len(insts), mean=mean, pick=pick), open("choose_t13.json", "w"), ensure_ascii=False, indent=1)
