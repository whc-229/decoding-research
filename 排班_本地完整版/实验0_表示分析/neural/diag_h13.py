"""诊断（只诊断，不改规则）：几条 LLM 规则在测试实例 H13_720h 上 MOEA 几乎找不到可行解的原因。
对每条规则，在 H13 上用 evalrule.genomes 同样方式生成的 3 个不偏离基因 + 64 个随机基因解码，统计可行率；
对不可行的解码记录失败原因（机器人用完 / 工具用完 / 班次上界用完而时域没覆盖完）、发生在第几班、当时各类型已开机器人数与工具余量，
以及规则在不偏离解码中每班的选择（复用 / 新开、类型）。H13 是测试实例，这里只用于事后诊断，不参与任何训练或选择。

做法：在本进程里给模拟器 mirror.Sim 的 dispatch_new / dispatch_reuse 套一层记录（不改文件），失败时把原因写到 sim 对象上。
用法: python diag_h13.py [实例名]   输出: out/diag_h13.md、out/diag_h13.json
"""
import collections, json, os, sys
import numpy as np
import common as C
import evalrule as E
import score_rules as SR

INST = sys.argv[1] if len(sys.argv) > 1 else "H13_720h"
RULES = ["LLM-full(s2)=K0.25:out/full_s2/best_rule.py", "LLM-full(s3)=K0.25:out/full_s3/best_rule.py",
         "LLM-score(s2)=K0.25:out/score_s2/best_rule.py", "LLM-score(s3)=K0.25:out/score_s3/best_rule.py",
         "EoH(run1)=K0.25:../neural/out/eoh/run1/best_rule.py",
         "LLM(r47)=K0.25:out/full/best_rule.py", "LLM(r35)=K0.25:out/score/best_rule.py",
         "GP(run4)=K0.25:../neural/out/gp/run4/best_rule.py", "ES16(s0)=K0.25:nn:out/es/il_h16/best.npz",
         "默认=K0.25:default"]
M = C.M
_new, _reuse = M.Sim.dispatch_new, M.Sim.dispatch_reuse


def snapshot(s):
    """失败时刻的状态摘要"""
    sc = s.sc
    return {"shift": s.shift, "t": s.E, "remaining": sc["T"] - s.E,
            "opened": [sum(1 for r in s.robots if r.type == k) for k in range(len(sc["R"]))],
            "robot_left": list(s.resR), "tool_left": list(s.resT),
            "tools_opened": [sum(1 for t in s.tools if t.type == k) for k in range(len(sc["Tl"]))]}


def dispatch_new(s, ty, g):
    """记录：要开的类型、是否因机器人用完失败、是否因工具不足失败"""
    t2 = s.new_type(ty)
    snap = snapshot(s)
    ok = _new(s, ty, g)
    if not ok and not hasattr(s, "fail"):
        s.fail = dict(snap, reason="机器人用完" if t2 is None else "工具用完", action=f"新开类型{ty}" + ("" if t2 in (None, ty) else f"（顺延到{t2}）"))
    return ok


def dispatch_reuse(s, r, g):
    snap = snapshot(s)
    ok = _reuse(s, r, g)
    if not ok and not hasattr(s, "fail"):
        s.fail = dict(snap, reason="工具用完", action=f"复用类型{r.type}")
    return ok


M.Sim.dispatch_new, M.Sim.dispatch_reuse = dispatch_new, dispatch_reuse


def genomes(inst):
    """与 evalrule.genomes 相同的生成方式（3 个不偏离 + 64 个随机）"""
    return E.genomes(inst)


def trace(sc, x, rule):
    """不偏离解码中规则每班的首选（复用 / 新开、类型），用于对照规则代码"""
    seq = []

    def wrapped(ctx):
        out = rule(ctx)
        first = out[0] if out else None
        seq.append((ctx.shift, len(ctx.available), first[0] if first else None,
                    (first[1].type if first and first[0] == "reuse" else first[1]) if first else None))
        return out
    r = C.R.decode_rule(sc, x, wrapped)
    return r, seq


def main():
    sc = C.I.load(INST)
    X = genomes(INST)
    res, out = {}, []
    for spec in RULES:
        name, s = SR.A.parse(spec)
        rule = SR.picklable(s)
        rows = []
        for k, x in enumerate(X):
            r = C.R.decode_rule(sc, x, rule)
            sim = r.sim
            if r.obj:
                rows.append({"k": k, "ok": True, "obj": r.obj})
            else:
                f = getattr(sim, "fail", None)
                if f is None:      # 没有派班失败：班次上界用完、时域没覆盖完
                    f = dict(snapshot(sim), reason="班次上界用完（时域放不下）", action="—")
                rows.append({"k": k, "ok": False, **f})
        pure = rows[:3]; rnd = rows[3:]
        _, tr = trace(sc, X[1], rule)          # 不偏离基因（默认类型基因 0.5）上规则每班的首选
        res[name] = {"pure_feasible": sum(r["ok"] for r in pure), "rand_feasible": sum(r["ok"] for r in rnd),
                     "reasons": collections.Counter(r["reason"] for r in rows if not r["ok"]),
                     "fail_shift": [r["shift"] for r in rows if not r["ok"]], "rows": rows, "trace": tr}
    lb = C.I.lb(INST)
    out += [f"# {INST} 不可行诊断（只诊断，不改规则）\n",
            f"实例：时域 {sc['T']} h，资源数下界 {lb}，班次上界 {C.L.nvar(sc, 'dec5') // 2}。"
            "基因 = evalrule.genomes 同样方式生成的 3 个不偏离 + 64 个随机。\n",
            "| 规则 | 不偏离可行 | 随机基因可行 | 失败原因（次数） | 失败班次（中位，范围） |", "|---|---|---|---|---|"]
    for n, v in res.items():
        fs = v["fail_shift"]
        rs = "、".join(f"{k} {c}" for k, c in v["reasons"].most_common()) or "—"
        out.append(f"| {n} | {v['pure_feasible']}/3 | {v['rand_feasible']}/64 | {rs} | "
                   + (f"{int(np.median(fs))}（{min(fs)}～{max(fs)}）" if fs else "—") + " |")
    out.append("\n## 失败时刻的状态（每条失败规则取不偏离基因 0.5 的那次；没有失败就取第一个失败的随机基因）\n")
    for n, v in res.items():
        bad = [r for r in v["rows"] if not r["ok"]]
        if not bad:
            continue
        r = next((b for b in bad if b["k"] == 1), bad[0])
        out.append(f"- **{n}**（基因 {r['k']}）：第 {r['shift']} 班（t = {r['t']:.0f} h，还剩 {r['remaining']:.0f} h）{r['action']} → {r['reason']}；"
                   f"已开机器人（按类型）{r['opened']}、还能开 {r['robot_left']}；已开工具 {r['tools_opened']}、工具余量 {r['tool_left']}")
    out.append("\n## 不偏离解码（默认类型基因 0.5）中规则每班的首选：按类型统计复用 / 新开次数\n")
    out += ["| 规则 | 规则调用次数 | 复用（类型 0/1/2） | 新开（类型 0/1/2） | 有可用机器人时仍新开 |", "|---|---|---|---|---|"]
    for n, v in res.items():
        ru = collections.Counter(t for _, _, a, t in v["trace"] if a == "reuse")
        nw = collections.Counter(t for _, _, a, t in v["trace"] if a == "new")
        busy = sum(1 for _, na, a, _ in v["trace"] if a == "new" and na > 0)
        out.append(f"| {n} | {len(v['trace'])} | {'/'.join(str(ru[k]) for k in range(3))} | {'/'.join(str(nw[k]) for k in range(3))} | {busy} |")
    open(os.path.join(C.OUT, "diag_h13.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    json.dump({n: {k: v for k, v in d.items() if k != "trace"} | {"reasons": dict(d["reasons"])} for n, d in res.items()},
              open(os.path.join(C.OUT, "diag_h13.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("\n".join(out))


if __name__ == "__main__":
    main()
