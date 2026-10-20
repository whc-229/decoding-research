"""实验3：让 LLM 为每个实例选择解码的偏离密度：稀疏偏离（偏离槽数 K = 0.25 / 0.5 × 班次上界）或逐班基因（dec5，记为 1.0）。
用法:
  python llm_choose_d.py --mode params            # 只给实例参数
  python llm_choose_d.py --mode params+features   # 再给便宜特征（纯规则解、各档的初始供给，来自 out9/<实例>.json）
  python llm_choose_d.py --mode params --dry-run  # 只打印提示词，不调用接口
配置读 llm_config.json（同目录）。输出 out8/llm_choice_<mode>.json：每个实例每次采样的 d 和理由。
LLM 看不到任何 MOEA 结果；选择的好坏由 eval_policies.py 对照扫描结果离线评价。
"""
import argparse, json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp0lib as L
M = L.M
HERE = os.path.dirname(os.path.abspath(__file__))
GRID = [0.25, 0.5, 1.0]
INSTS = ["原请求_paiban", "B_三类型720h", "C_三类型1440h", "D_三类型资源紧"] + \
        sorted(f[:-5] for f in os.listdir(os.path.join(L.SRC, "requests_family"))) + \
        (sorted(f[:-5] for f in os.listdir(os.path.join(L.SRC, "requests_family2"))) if os.path.isdir(os.path.join(L.SRC, "requests_family2")) else [])

SYSTEM = """You are an expert in evolutionary computation and scheduling. You design solution encodings (decoders) for genetic algorithms."""

TASK = """We solve a bi-objective robot duty-rostering problem with NSGA-II (population 30, about 465 evaluations).
A single duty post must be covered continuously for the whole horizon. Each shift one robot goes out, carrying tools, and works one duty period.
Robots follow a cycle: install tools -> travel out -> duty -> travel back -> remove tools -> charge; after a number of consecutive duties
(continue_max_work / single_work_time of them) the robot must go to maintenance, which takes much longer than charging.
Tools must rest after each use, so consecutive shifts cannot reuse the same tool.
Objectives (both minimized): (1) number of resources = robots + tools used; (2) imbalance = weighted std of per-robot duty counts,
duty hours and first-maintenance intervals.

The decoder builds the roster shift by shift. Default rule: send the available robot with the fewest duties so far; if none is
available, try to repair by re-assigning one of the previous 12 shifts, otherwise open a new robot.
We can choose how much freedom the genome has to deviate from this rule:
  0.25, 0.5 = "sparse deviation" encodings: the genome holds K = 0.25 / 0.5 x (number of shifts) deviation slots; each slot
      picks one shift and overrides the rule there (send a different available robot, or open a new robot). All other shifts follow the rule.
  1.0 = "per-shift" encoding: every shift has its own gene that chooses which available robot to send or whether to open a new one
      (with capacity look-ahead and the same repair).
Sparse encodings help when good rosters are close to the rule (the search starts near good solutions); per-shift encoding is better
when good rosters need many deviations from the rule or when the rule itself is a poor starting point.

Choose one value for the instance below from exactly: 0.25, 0.5, 1.0.
Answer with JSON only: {"d": <value>, "reason": "<one or two sentences>"}"""


def describe(inst):
    path = f"{L.SRC}/requests/{inst}.json"
    if not os.path.exists(path):
        path = f"{L.SRC}/requests_family/{inst}.json"
    if not os.path.exists(path):
        path = f"{L.SRC}/requests_family2/{inst}.json"
    sc = M.load_scenario(path)
    lines = [f"Horizon: {sc['T']} hours."]
    for k, r in enumerate(sc["R"]):
        if r:
            lines.append(f"Robot type {k}: up to {r['limit']} units; duty {r['work_time']} h; travel out {r['out_travel_time']} h, back {r['return_travel_time']} h; "
                         f"one shift uses {r['single_work_time']} h of its work budget; maintenance needed when the budget of {r['continue_max_work']} h is used up; "
                         f"charge {r['charge_time']} h; maintenance {r['maintenance_time']} h; carries {int(r['carry_num'])} tools of types {list(map(int, r['cargo_type_list']))}.")
    for k, t in enumerate(sc["Tl"]):
        if t:
            lines.append(f"Tool type {k}: up to {t['limit']} units; install {t['install_time']} h; remove {t['removal_time']} h; rest after use {t['tool_rest_time']} h.")
    return "\n".join(lines)


def features_text(inst):
    f = json.load(open(os.path.join(HERE, "out9", f"{inst}.json"), encoding="utf-8"))
    s = [f"Proven lower bound on resources: {f['LB']}.",
         (f"Pure-rule roster (no deviations): {f['rule_res']:.0f} resources ({f['rule_gap']:+.0f} vs. lower bound), imbalance {f['rule_bal']:.2f}, repairs used {f['rule_fixes']}."
          if f.get("rule_res") is not None else "Pure-rule roster (no deviations): infeasible (the rule alone cannot cover the horizon with the available robots/tools)."),
         "Random initial population quality for each choice (100 random genomes): "]
    for d, v in sorted(f["supply"].items(), key=lambda kv: float(kv[0])):
        if float(d) not in GRID:
            continue
        if v.get("feasible", 1.0) == 0.0:
            s.append(f"  {d}: no feasible roster among the 100 random genomes."); continue
        s.append(f"  {d}: share at lower bound {v['p_lb']:.2f}, share within lower bound +1 {v['p_lb1']:.2f}, best resources {v['res_min']:.0f} (imbalance {v['bal_at_min']:.2f}).")
    return "\n".join(s)


def call(cfg, messages):
    req = urllib.request.Request(cfg["api_base"].rstrip("/") + "/chat/completions",
                                 data=json.dumps(dict(model=cfg["model"], messages=messages, temperature=cfg.get("temperature", 0.7))).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["api_key"]})
    with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 120)) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        j = json.loads(m.group(0))
        d = float(j["d"])
        return min(GRID, key=lambda g: abs(g - d)), j.get("reason", "")
    except Exception:
        return None, text[:200]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="params", choices=["params", "params+features"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    cfg = json.load(open(os.path.join(HERE, "llm_config.json"), encoding="utf-8"))
    insts = a.only.split(",") if a.only else INSTS
    os.makedirs(os.path.join(HERE, "out9"), exist_ok=True)
    outp = os.path.join(HERE, "out9", f"llm_choice_{a.mode}.json")
    res = json.load(open(outp, encoding="utf-8")) if os.path.exists(outp) else {}
    for inst in insts:
        user = TASK + "\n\nInstance:\n" + describe(inst)
        if a.mode == "params+features":
            user += "\n\nCheap diagnostics (computed without running the GA):\n" + features_text(inst)
        if a.dry_run:
            print("=" * 30, inst, "\n" + user); continue
        res.setdefault(inst, [])
        while len(res[inst]) < cfg.get("samples_per_instance", 5):
            try:
                text = call(cfg, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
            except Exception as e:
                print(inst, "接口出错：", e); time.sleep(5); continue
            d, why = parse(text)
            res[inst].append(dict(d=d, reason=why))
            print(inst, d, why[:120], flush=True)
            json.dump(res, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not a.dry_run:
        print("已保存", outp)
