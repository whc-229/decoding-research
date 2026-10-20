"""实验3：每个实例的便宜特征（不需要先找到好解），用于预测最合适的偏离密度 d。
用法: python features8.py 实例名 [每档样本数] [输出目录]
特征：
  基本参数：时域、班次上界、机器人/工具类型数、资源下界
  纯规则解（所有班次不偏离）：资源数、比下界多几个、均衡度、回溯修复次数
  各档 d 的初始供给：N 个均匀随机基因中 资源 = 下界 / ≤ 下界+1 的比例、资源最少层的最好均衡度
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L, ddec, sde
M = L.M
DEC9 = os.environ.get("FEAT_DEC") == "dec9"   # dec9：各档为偏离槽数比例 K/Nmax（dec6b 语义）
if DEC9:
    sde.NEW_CAP, sde.REUSE_SHARE = False, 0.7
inst = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
outdir = sys.argv[3] if len(sys.argv) > 3 else "out8"
DS = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else ([0.1, 0.25, 0.5, 1.0] if DEC9 else [0.05, 0.1, 0.2, 0.4])   # 只算这几档，结果并入已有文件
os.makedirs(outdir, exist_ok=True)
path = f"{L.SRC}/requests/{inst}.json"
for sub in ("requests_family", "requests_family2"):
    if not os.path.exists(path):
        path = f"{L.SRC}/{sub}/{inst}.json"
sc = M.load_scenario(path)
fb = json.load(open(f"{L.SRC}/exact/family_bounds.json", encoding="utf-8"))
if os.path.exists(f"{L.SRC}/exact/family_bounds2.json"):
    fb.update(json.load(open(f"{L.SRC}/exact/family_bounds2.json", encoding="utf-8")))
LB = fb[inst]["total_lb"] if inst in fb else 9
nv = L.nvar(sc, "dec5")
t0 = time.time()
r = ddec.rule_solution(sc)
old = os.path.join(outdir, f"{inst}.json")
prev = json.load(open(old, encoding="utf-8")).get("supply", {}) if os.path.exists(old) else {}
f = dict(instance=inst, T=sc["T"], nmax=nv // 2 - 1, n_robot_types=sum(1 for x in sc["R"] if x), n_tool_types=sum(1 for x in sc["Tl"] if x),
         LB=LB, rule_res=r.obj[0] if r.feasible else None, rule_gap=(r.obj[0] - LB) if r.feasible else None,
         rule_bal=r.obj[1] if r.feasible else None, rule_fixes=r.fixes, supply=prev)
for d in DS:
    rng = np.random.default_rng(5)
    R, B = [], []
    for _ in range(N):
        if DEC9 and d >= 1.0:          # 1.0 表示 dec5（每班都由基因决定，即"偏离密度最大"的一端）
            q = L.decode(sc, rng.uniform(0, 0.99, nv), "dec5")
        elif DEC9:
            sde.K_FRAC = d
            q = sde.decode6(sc, rng.uniform(0, 0.99, nv))
        else:
            q = ddec.decode8(sc, rng.uniform(0, 0.99, nv), d)
        if q.feasible:
            R.append(q.obj[0]); B.append(q.obj[1])
    R, B = np.array(R), np.array(B)
    if len(R) == 0:      # 全部不可行
        f["supply"][str(d)] = dict(p_lb=0.0, p_lb1=0.0, res_min=999.0, bal_at_min=999.0, res_mean=999.0, feasible=0.0)
        continue
    mn = R.min()
    f["supply"][str(d)] = dict(p_lb=float(np.mean(R == LB)), p_lb1=float(np.mean(R <= LB + 1)), res_min=float(mn),
                               bal_at_min=float(B[R == mn].min()), res_mean=float(R.mean()), feasible=len(R) / N)
f["secs"] = time.time() - t0
json.dump(f, open(os.path.join(outdir, f"{inst}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(f, ensure_ascii=False))
