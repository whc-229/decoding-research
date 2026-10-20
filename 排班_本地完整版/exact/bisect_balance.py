"""用"带阈值的分支定界"夹逼资源数 = 9 层级上的最优均衡度：
  先无阈值跑一段得到上界 hi；再取 τ ∈ (lo, hi)，以 τ 为初始上界完整搜索：
    · 搜完且没找到解 → 证明最优值 ≥ τ（lo = τ）
    · 找到更好的解 → hi 更新；若搜完 → hi 即为最优
    · 超时且没找到 → 这一 τ 不确定，缩小步长再试
用法: python exact/bisect_balance.py 场景 每次时限秒 轮数
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import balance_bb as B
import mirror as M

scen, tl, rounds = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
HERE = B.HERE
log = []
r = B.solve(scen, tl, verbose=False)
hi, hi_path, lo = r["best"], r["path"], r["root_lb"]
if r["complete"]:
    lo = hi
log.append(dict(tau=None, complete=r["complete"], best=r["best"], secs=round(r["secs"])))
print(f"[{scen}] 无阈值: 上界 {hi:.4f} 根下界 {lo:.4f} {'已证最优' if r['complete'] else ''}", flush=True)
for _ in range(rounds):
    if hi - lo < 0.05:
        break
    tau = lo + (hi - lo) / 2
    r = B.solve(scen, tl, ub=tau, verbose=False)
    found = r["path"] is not None
    if found:
        hi, hi_path = r["best"], r["path"]
        if r["complete"]:
            lo = hi
    elif r["complete"]:
        lo = tau
    else:
        # 不确定：向下收一点再试（更紧的阈值剪枝更强）
        tau2 = lo + (hi - lo) / 4
        r2 = B.solve(scen, tl, ub=tau2, verbose=False)
        if r2["path"] is not None:
            hi, hi_path = r2["best"], r2["path"]
            if r2["complete"]:
                lo = hi
        elif r2["complete"]:
            lo = tau2
        log.append(dict(tau=round(tau2, 4), complete=r2["complete"], best=(r2["best"] if r2["path"] else None),
                        secs=round(r2["secs"])))
    log.append(dict(tau=round(tau, 4), complete=r["complete"], best=(r["best"] if found else None), secs=round(r["secs"])))
    print(f"[{scen}] τ={tau:.4f}: {'找到 '+format(r['best'],'.4f') if found else '无解'}，"
          f"{'搜完' if r['complete'] else '超时'} → 区间 [{lo:.4f}, {hi:.4f}]", flush=True)
sc = M.load_scenario(os.path.join(HERE, "requests", scen + ".json"))
genes = B.path_to_genes(sc, hi_path)
o, sim = M.evaluate_genes(sc, genes)
json.dump(dict(scen=scen, lb=lo, ub=hi, genes=genes, check=[float(o[0]), float(o[1])], seq=sim.seq,
               counts=[r.count for r in sim.robots], first_rep=[r.first_rep for r in sim.robots],
               tools=[(t.type, t.uses) for t in sim.tools], log=log),
          open(os.path.join(HERE, "exact", f"bisect_{scen}.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(f"[{scen}] 结果: 最优均衡度 ∈ [{lo:.4f}, {hi:.4f}]，最好解复核 {o}", flush=True)
