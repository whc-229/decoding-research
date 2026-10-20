"""对同一个好解（reroster/plans 的 dec5 最好解），分别计算它相对"默认规则"和"LLM 规则"的偏离数 d：
逐班重放好解，每班看规则在当时状态下的首选动作是否就是好解的动作。输出 rule_distance.json。"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rulegen"))
import exp0lib as L  # noqa
import ruledec as R  # noqa
import instances as I  # noqa
M = L.M
RULES = {"default": R.default_rule,
         "llm_full": R.compile_rule(open(os.path.join(os.path.dirname(HERE), "rulegen/out/full/best_rule.py"), encoding="utf-8").read()),
         "llm_score": R.compile_rule(open(os.path.join(os.path.dirname(HERE), "rulegen/out/score_best_rule.py"), encoding="utf-8").read())}


def dist(sc, seq, rule):
    s = M.Sim(sc, False); rc = M.rep_ceil_factory(sc); nmax = L.nvar(sc, "dec5") // 2 - 1
    d = 0
    for i, rid in enumerate(seq):
        av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
              and r.remain >= sc["R"][r.type]["single_work_time"]]
        av.sort(key=lambda r: (r.count, -r.remain))
        ctx = R.Ctx(sc, s, i, nmax, av, 0, rc)
        first, _, newp = R._normalize(rule(ctx), ctx, len(sc["R"]))
        ty = int(rid.split("_")[1])
        if first[0] == "reuse":
            d += first[1]._r.id != rid
        else:   # 规则想新开：好解也新开同型才算一致（无可用机器人时类型由基因定，不计）
            d += not (rid not in [r.id for r in s.robots] and (ty == first[1] or not av))
        rr = next((q for q in av if q.id == rid), None)
        ok = s.dispatch_reuse(rr, 0.5) if rr else s.dispatch_new(ty, 0.5)
        if not ok:
            return None
    return d


if __name__ == "__main__":
    out = {}
    tr, te = I.split()
    for inst in tr + te:
        p = os.path.join(os.path.dirname(HERE), "reroster", "plans", inst + ".npy")
        sc = I.load(inst); r = L.decode(sc, np.load(p), "dec5"); seq = list(r.pheno[0])
        out[inst] = {k: dist(sc, seq, f) for k, f in RULES.items()}
        out[inst]["N"] = len(seq); out[inst]["split"] = "train" if inst in tr else "test"
        print(inst, out[inst], flush=True)
    json.dump(out, open(os.path.join(HERE, "rule_distance.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
