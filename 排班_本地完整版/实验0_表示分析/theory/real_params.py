"""真实实例上的模型参数：N（班数）、d（好解相对规则的偏离数，规则 = 有可用就派出勤最少的，无回溯修复）、
m（决策时可选动作数的均值：可用机器人数 + 可新开类型数）、K（0.25/0.5 两档槽数）。
好解 = reroster/plans/ 里的 dec5 GA 最好解（资源最少、其次均衡）。"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import exp0lib as L, sde  # noqa
import instances as I  # noqa
M = L.M
out = {}
for p in sorted(glob.glob(os.path.join(os.path.dirname(HERE), "reroster", "plans", "*.npy"))):
    inst = os.path.basename(p)[:-4]
    sc = I.load(inst); x = np.load(p)
    r = L.decode(sc, x, "dec5")
    seq, tools = r.pheno
    # m：沿好解的轨迹，每个决策时刻的可用机器人数 + 可新开类型数
    s = M.Sim(sc, True); ms = []
    for rid in seq:
        av = s.available(); ms.append(len(av) + sum(1 for t in range(len(sc["R"])) if s.resR[t] > 0))
        rr = next((q for q in av if q.id == rid), None)
        ok = s.dispatch_reuse(rr, 0.5) if rr else s.dispatch_new(int(rid.split("_")[1]), 0.5)
    res = {}
    for kf in (0.25, 0.5):
        sde.K_FRAC = kf
        _, d, K = sde.encode_schedule(sc, list(seq), list(tools))
        res[kf] = K
    out[inst] = dict(N=len(seq), nmax=L.nvar(sc, "dec5") // 2 - 1, d=d, K25=res[0.25], K50=res[0.5], m=float(np.mean(ms)), obj=r.obj, group=I.group(inst))
    print(inst, out[inst], flush=True)
json.dump(out, open(os.path.join(HERE, "real_params.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
