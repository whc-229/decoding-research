"""规则生成实验：让 LLM 改写解码器的默认规则（稀疏偏离编码 K=0.25 中"不偏离时做什么"），用进化方式迭代。

用法（在 实验0_表示分析/rulegen/ 下运行）：
  python rulegen.py                          # 默认：理论诊断反馈（full），种群 6，每代 4 个后代，12 代，输出 out/full/
  python rulegen.py --feedback score         # 消融：只反馈总分，不给诊断，输出 out/score/
  python rulegen.py --mock --gens 1          # 不调用接口，用内置的几条规则走一遍流程（自检）
  python rulegen.py --dry-run                # 只打印第一个提示词
  python rulegen.py --eval-only 我的规则.py   # 只给一个规则文件打分
中途断了重跑同一条命令会从上次的进度继续（out/<tag>/state.json）。
接口配置读 ../llm_config.json。余额不足、密钥错误等不可恢复的错误会直接停止；网络超时、限流会等待后重试。

安全：LLM 写的代码只在受限环境中执行（只允许 math，禁止 import、文件、反射、私有属性和 while 循环），见 ruledec.compile_rule。
"""
import argparse, json, multiprocessing as mp, os, random, re, sys, time, urllib.error, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))

SYSTEM = "You are an expert in scheduling heuristics and evolutionary computation. You write small, fast, correct Python functions."

PROBLEM = """## Problem
Bi-objective robot duty rostering. One duty post must be covered continuously for the whole horizon (480-1080 h). Each shift exactly one
robot goes out with tools and works one duty period. A robot's cycle: install tools -> travel out -> duty -> travel back -> remove tools ->
charge. Each robot type has a work budget: after `continue_max_work` hours of work (i.e. after a fixed number of duties) it must go to
maintenance, which takes much longer (48-120 h) than charging (2-5 h). Tools must rest after each use. Robots and tools are opened as needed,
up to a per-type limit. Objectives (both minimized): (1) number of resources = robots + tools opened; (2) imbalance = weighted std of
per-robot duty counts, duty hours and first-maintenance times.
Instance groups: E = one robot type, duty 10 h; H = 2-3 robot types, all duty 10 h; M = 2-3 robot types with mixed duty lengths (6/8/10/12 h).

## Decoder (what your rule plugs into)
NSGA-II (population 30, ~465 evaluations) searches a genome that does NOT encode every decision. The roster is built shift by shift:
  - a DEFAULT RULE decides each shift;
  - the genome holds a few sparse "deviation slots" (about 25% of the shifts). A deviation slot picks one shift and overrides the rule there:
    either send another available robot (chosen among the rule's other "reuse" options, in the rule's order), or open a new robot of a
    gene-chosen type (only allowed when existing robots cannot cover the remaining horizon);
  - when no robot is available, the decoder tries to repair by changing one of the previous 12 shifts; otherwise it opens a new robot of the
    type your rule prefers;
  - tools are handled by the decoder, not by your rule.
So the rule is the search BIAS: the roster produced with no deviations should already be good (few resources, balanced), and the order
of alternatives should make random deviations useful. You write that rule.

## Interface
def rule(ctx):
    return [...]   # actions in order of preference; each is ("reuse", robot) with robot from ctx.available, or ("new", type_index)
The FIRST action is what happens when the genome does not deviate. Available robots you omit are appended in default order.
ctx fields:
  ctx.t            current shift start time (h);  ctx.T horizon (h);  ctx.remaining = T - t
  ctx.shift        shift index (0-based);  ctx.n_shifts_max  upper bound on the number of shifts
  ctx.available    robots that can go now, pre-sorted by (count asc, budget desc)
  ctx.robots       all opened robots
  ctx.types[k]     dict of robot type k params or None: work_time (duty h), out_travel_time, return_travel_time, single_work_time
                   (budget used per duty), continue_max_work (budget per maintenance cycle), charge_time, maintenance_time, limit
  ctx.left[k]      how many more robots of type k can be opened
  ctx.gene_type    default new-robot type chosen by the genome
  ctx.capacity     (property, costs a little) estimated duty hours the opened robots can still supply before T; >= ctx.remaining
                   means no new robot is needed
robot fields: type, count (duties so far), hours (duty hours so far), budget (work budget left before maintenance),
  duties_left (duties left before maintenance, including this one), ready (time it became ready), first_maint (time of first
  maintenance or None), last_end (end time of its last duty or None), idx (opening order)

## Rules for your code
- Define only `def rule(ctx):` (helper functions inside it are fine). Plain Python; `math` is available; no imports, no while loops,
  no attributes starting with "_". It runs thousands of times per evaluation, so keep it O(number of robots).
- Must be deterministic and must not modify ctx or robots.
- Reply with one short paragraph explaining the idea, then exactly one ```python code block."""

DIAG_HELP = """Diagnostics are per instance group, averaged over training instances (each scored on the same 64 random genomes + 3 no-deviation genomes):
  score: normalized hypervolume of all those rosters (higher is better); vs_default: difference to the default rule
  rule_only_extra_resources: resources above the instance lower bound when the genome makes NO deviation ("rule distance"; 0 is ideal)
  rule_only_imbalance: imbalance of that no-deviation roster
  best_sample_extra_resources: best roster among the random genomes, resources above the lower bound
  random_genome_feasible_rate: share of random genomes giving a feasible roster
  rule_opens_new_while_robots_available_per_decode: how often your rule itself opens robots although some are available"""

INIT_HINTS = [
    "Think about maintenance cycles: robots that hit maintenance at the same time cause gaps that force new robots. Consider staggering them.",
    "Think about heterogeneous robot types (groups H and M): which type is the cheapest way to cover hours, and which type to open when a new robot is needed.",
    "Think about timing: a robot that has been ready for longest vs one that just finished charging; who should go so that the others stay available.",
    "Think about balance: the second objective penalizes uneven duty counts, duty hours and first-maintenance times. Use hours, not only counts.",
    "Think about look-ahead: use ctx.capacity and ctx.remaining to decide when opening a robot early is better than repairing later.",
]


def load_cfg():
    return json.load(open(os.path.join(os.path.dirname(HERE), "llm_config.json"), encoding="utf-8"))


class Fatal(Exception):
    pass


def call(cfg, messages):
    req = urllib.request.Request(cfg["api_base"].rstrip("/") + "/chat/completions",
                                 data=json.dumps(dict(model=cfg["model"], messages=messages, temperature=cfg.get("temperature", 0.7))).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["api_key"]})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 120) * 2) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 402, 403, 404):
                raise Fatal(f"接口返回 {e.code}（{e.reason}）：请检查余额、密钥或模型名，处理后重新运行同一条命令即可继续")
            print("接口出错，稍后重试：", e, flush=True)
        except Exception as e:
            print("接口出错，稍后重试：", e, flush=True)
        time.sleep(min(60, 5 * 2 ** attempt))
    raise Fatal("接口连续 8 次失败，已停止；重新运行同一条命令即可继续")


MOCK = [
    '''def rule(ctx):
    av = sorted(ctx.available, key=lambda r: (r.hours, -r.budget))
    return [("reuse", r) for r in av] + [("new", ctx.gene_type)]''',
    '''def rule(ctx):
    av = sorted(ctx.available, key=lambda r: (r.count, r.ready))
    best = max(range(len(ctx.types)), key=lambda k: (ctx.left[k] > 0 and ctx.types[k] is not None,
               (ctx.types[k]["continue_max_work"] / ctx.types[k]["single_work_time"]) if ctx.types[k] else 0))
    return [("reuse", r) for r in av] + [("new", best)]''',
    '''def rule(ctx):
    av = sorted(ctx.available, key=lambda r: (-r.duties_left, r.count))
    return [("reuse", r) for r in av] + [("new", ctx.gene_type)]''',
    '''def rule(ctx):
    return [("reuse", r) for r in ctx.available[::-1]] + [("new", ctx.gene_type)]''',
]


def extract(text):
    m = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    code = m[-1] if m else text
    idea = text.split("```")[0].strip()
    return code.strip() + "\n", idea[:600]


def fmt_diag(c, mode):
    if c.get("error"):
        return f"ERROR: {c['error']}"
    if mode == "score":
        return f"score {c['score']:.4f} (default rule {DEFAULT_SCORE[0]:.4f})"
    return f"overall score {c['score']:.4f} (default rule {DEFAULT_SCORE[0]:.4f})\n" + json.dumps(c["diag"], ensure_ascii=False, indent=1)


DEFAULT_SCORE = [0.0]


def prompt(op, parents, mode, hint=None):
    s = PROBLEM + "\n\n"
    if mode == "full":
        s += DIAG_HELP + "\n\n"
    if op == "init":
        p = parents[0]
        s += f"## The current default rule\n```python\n{p['src']}```\nIts results:\n{fmt_diag(p, mode)}\n\n## Task\nWrite a better rule. {hint}"
    elif op == "refine":
        p = parents[0]
        s += f"## A rule to improve\n```python\n{p['src']}```\nIts results:\n{fmt_diag(p, mode)}\n\n## Task\n"
        if mode == "full":
            weak = min(p["diag"].items(), key=lambda kv: kv[1]["vs_default"])[0]
            s += f"Improve this rule. Its weakest group is {weak}. Use the diagnostics to decide what to change (e.g. too many resources in the no-deviation roster vs. too little room for useful deviations)."
        else:
            s += "Improve this rule."
    elif op in ("explore", "crossover"):
        for k, p in enumerate(parents):
            s += f"## Rule {k + 1}\n```python\n{p['src']}```\nIts results:\n{fmt_diag(p, mode)}\n\n"
        s += "## Task\n" + ("Write a rule based on a clearly DIFFERENT idea from all rules above, likely to score higher."
                            if op == "explore" else "Combine the strengths of these rules into one better rule.")
    elif op == "fix":
        p = parents[0]
        s += f"## This rule failed\n```python\n{p['src']}```\nError: {p['error']}\n\n## Task\nFix it, keeping the idea."
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feedback", default="full", choices=["full", "score"])
    ap.add_argument("--pop", type=int, default=6)
    ap.add_argument("--offspring", type=int, default=4)
    ap.add_argument("--gens", type=int, default=12)
    ap.add_argument("--procs", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--tag", default=None)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--eval-only", default=None)
    a = ap.parse_args()
    import evalrule as E
    import instances as I
    import ruledec as R
    tag = a.tag or (a.feedback + ("_mock" if a.mock else ""))
    out = os.path.join(HERE, "out", tag)
    os.makedirs(out, exist_ok=True)
    train, _ = I.split()
    t = time.time()
    base = E.baseline(train, a.procs, os.path.join(HERE, "out", "baseline_train.json"))
    print(f"训练集 {len(train)} 个实例，默认规则基准就绪（{time.time() - t:.0f}s）", flush=True)

    def evaluate(src):
        t = time.time()
        sc, res, err = E.score(src, train, base, a.procs)
        c = {"src": src, "score": sc, "error": err, "secs": round(time.time() - t, 1)}
        if err is None:
            c["diag"] = E.diagnose(res, base)
        return c

    if a.eval_only:
        c = evaluate(open(a.eval_only, encoding="utf-8").read())
        print(json.dumps({k: v for k, v in c.items() if k != "src"}, ensure_ascii=False, indent=1))
        E.reset_pool(); return

    sp = os.path.join(out, "state.json")
    st = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {"cands": {}, "pop": [], "gen": 0, "calls": 0, "init_done": 0}
    rnd = random.Random(a.seed + len(st["cands"]))
    cfg = None if a.mock else load_cfg()

    def save():
        json.dump(st, open(sp + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(sp + ".tmp", sp)

    if "r0" not in st["cands"]:
        c = evaluate(R.DEFAULT_RULE_SRC); c.update(op="default", parents=[], gen=0, idea="dec9 default rule")
        st["cands"]["r0"] = c; st["pop"] = ["r0"]; save()
    DEFAULT_SCORE[0] = st["cands"]["r0"]["score"]
    print(f"默认规则得分 {DEFAULT_SCORE[0]:.4f}", flush=True)

    def ask(op, parents, hint=None):
        msg = prompt(op, parents, a.feedback, hint)
        if a.dry_run:
            print(msg); sys.exit(0)
        if a.mock:
            text = "mock idea\n```python\n" + rnd.choice(MOCK) + "\n```"
        else:
            text = call(cfg, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": msg}])
        st["calls"] += 1
        with open(os.path.join(out, "llm_log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"op": op, "parents": [p.get("id") for p in parents], "prompt": msg, "response": text}, ensure_ascii=False) + "\n")
        return extract(text)

    def new_cand(op, parents, hint=None):
        src, idea = ask(op, parents, hint)
        c = evaluate(src)
        if c["error"] and op != "fix":
            print("  出错，让 LLM 修一次：", c["error"][:150], flush=True)
            src2, idea2 = ask("fix", [dict(c, id=None)])
            c2 = evaluate(src2)
            if not c2["error"]:
                c, idea = c2, idea2
        cid = f"r{len(st['cands'])}"
        c.update(op=op, parents=[p["id"] for p in parents], gen=st["gen"], idea=idea, id=cid)
        st["cands"][cid] = c
        d0 = st["cands"]["r0"]
        if c["error"]:
            print(f"[{cid}] {op:9s} 失败：{c['error'][:150]}", flush=True)
        else:
            per = " ".join(f"{g}{v['vs_default']:+.3f}" for g, v in c["diag"].items())
            print(f"[{cid}] {op:9s} 得分 {c['score']:.4f}（对默认 {c['score'] - d0['score']:+.4f}；{per}） {c['secs']}s", flush=True)
        return cid

    def cand(cid):
        return dict(st["cands"][cid], id=cid)

    def update_pop():
        ok = [k for k, c in st["cands"].items() if not c["error"]]
        ok.sort(key=lambda k: (-st["cands"][k]["score"], len(st["cands"][k]["src"])))
        pop, seen = [], []
        for k in ok:
            sig = (round(st["cands"][k]["score"], 9), json.dumps(st["cands"][k]["diag"], sort_keys=True))
            if sig in seen:
                continue
            seen.append(sig); pop.append(k)
            if len(pop) == a.pop:
                break
        st["pop"] = pop

    def pick(n):
        pop = st["pop"]
        w = [len(pop) - i for i in range(len(pop))]
        ch = []
        for _ in range(min(n, len(pop))):
            k = rnd.choices([p for p in pop if p not in ch], weights=[w[i] for i, p in enumerate(pop) if p not in ch])[0]
            ch.append(k)
        return [cand(k) for k in ch]

    try:
        # 初始种群：每次给一个不同的思路提示
        while st["init_done"] < a.pop - 1:
            hint = INIT_HINTS[st["init_done"] % len(INIT_HINTS)]
            new_cand("init", [cand("r0")], hint)
            st["init_done"] += 1; update_pop(); save()
        ops = ["refine", "explore", "crossover", "refine"]
        while st["gen"] < a.gens:
            st.setdefault("gen_done", 0)
            while st["gen_done"] < a.offspring:
                op = ops[st["gen_done"] % len(ops)]
                parents = pick(1 if op == "refine" else 2)
                new_cand(op, parents)
                st["gen_done"] += 1; save()
            update_pop()
            st["gen"] += 1; st["gen_done"] = 0; save()
            best = st["cands"][st["pop"][0]]
            print(f"== 第 {st['gen']} 代结束：最好 {st['pop'][0]} 得分 {best['score']:.4f}（对默认 {best['score'] - DEFAULT_SCORE[0]:+.4f}），已调用 {st['calls']} 次", flush=True)
    except Fatal as e:
        save(); print("停止：", e); E.reset_pool(); sys.exit(1)
    E.reset_pool()
    write_report(st, out)


def write_report(st, out):
    cs = sorted([(k, c) for k, c in st["cands"].items() if not c["error"]], key=lambda kc: -kc[1]["score"])
    d0 = st["cands"]["r0"]["score"]
    lines = [f"# 规则生成结果（{os.path.basename(out)}）\n", f"LLM 调用 {st['calls']} 次；候选 {len(st['cands'])} 条，其中出错 {sum(1 for c in st['cands'].values() if c['error'])} 条。\n",
             "| 规则 | 来源 | 代 | 得分 | 对默认 | " + " | ".join(f"{g} 组" for g in "EHM") + " |", "|---|---|---|---|---|---|---|---|"]
    for k, c in cs:
        lines.append(f"| {k} | {c['op']} {','.join(c['parents'])} | {c['gen']} | {c['score']:.4f} | {c['score'] - d0:+.4f} | " +
                     " | ".join(f"{c['diag'][g]['vs_default']:+.3f}" if g in c["diag"] else "—" for g in "EHM") + " |")
    for k, c in cs[:3]:
        lines += [f"\n## {k}（得分 {c['score']:.4f}）\n", c.get("idea", ""), "\n```python\n" + c["src"] + "```"]
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    open(os.path.join(out, "best_rule.py"), "w", encoding="utf-8").write(cs[0][1]["src"])
    print("已写出", os.path.join(out, "report.md"), "和 best_rule.py")


if __name__ == "__main__":
    mp.freeze_support()
    main()
