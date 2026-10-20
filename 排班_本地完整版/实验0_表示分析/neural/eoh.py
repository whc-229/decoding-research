"""LLM 基线（第 3 步）：EoH 原版流程（Liu 等 ICML 2024；按官方实现 github.com/FeiLiu36/EoH 当前版本 eoh/src/eoh/eoh/ 复现）。

与官方实现一致的部分：
  - 个体 = 一句话思路（花括号内）+ 代码；提示词模板 i1 / e1 / e2 / m1 / m2 逐字照抄 evolution.py 的 _build_prompt；
    提示词里只给父代的思路和代码，**不给分数**（这是 EoH 与 rulegen 的 score 反馈的区别）；
  - 稳态进化：种群 5；初始化 2 × 5 = 10 个 i1 样本；之后每个样本从 e1、e2、m1、m2 中均匀随机选一个算子；
    父代按名次加权 1/(名次 + 1 + 种群大小)（e1/e2 抽 2 个、m1/m2 抽 1 个，有放回）；
    新个体评价后并入种群，按目标值去重、保留最好的 5 个；
  - 抽不出思路或代码时同一提示词最多重问 4 次；代码与种群中已有个体重复时最多重新生成 2 次；
  - 不给种子规则（use_seed = False），不给领域思路提示。
与 rulegen 相同的部分（保证可比）：问题描述（rulegen.PROBLEM，只去掉其中"回复格式"那一行，换成 EoH 自己的格式要求）、
  规则接口与模板（默认规则源码作 template_program）、受限执行沙箱（compile_rule）、代理打分（evalrule.score，同 15 个实例、67 个基因、
  同一归一化）、LLM 接口与温度（../llm_config.json）。
预算对齐：候选（= 代理评价）54 个 = rulegen 的 1 条默认 + 5 条初始化 + 12 代 × 4；LLM 调用次数和 token 用量照实记录。

用法（在 neural/ 下）: python eoh.py 运行号 [--procs 2] [--samples 54] [--mock]
输出: out/eoh/run<运行号>/ 下 state.json（每个样本后保存，可续跑）、llm_log.jsonl、best_rule.py、report.md
"""
import argparse, json, os, random, re, sys, time, urllib.error, urllib.request
import common as C
import evalrule as E
import rulegen as RG

POP, INIT_FACTOR, N_PARENTS = 5, 2, 2
OPERATORS = ["e1", "e2", "m1", "m2"]
TEMPLATE = C.R.DEFAULT_RULE_SRC
FORMAT_LINE = '- Reply with one short paragraph explaining the idea, then exactly one ```python code block.'
assert FORMAT_LINE in RG.PROBLEM
TASK = RG.PROBLEM.replace("\n" + FORMAT_LINE, "")


# ---------------- 提示词：逐字照抄 EoH evolution.py ----------------
def func_spec():
    return ("implement the following Python function:\n"
            f"```python\n{TEMPLATE.strip()}\n```\n"
            "Do not give additional explanations.")


def parent_block(parents):
    return "\n".join(f"No.{i + 1} algorithm and the corresponding code are:\n{p['algorithm']}\n{p['code']}"
                     for i, p in enumerate(parents))


def build_prompt(op, parents=None):
    spec = func_spec()
    if op == "i1":
        return (f"{TASK}\n"
                "First, describe your new algorithm and main steps in one sentence. "
                f"The description must be inside a brace. Next, {spec}")
    if op == "e1":
        return (f"{TASK}\n"
                f"I have {len(parents)} existing algorithms with their codes as follows:\n{parent_block(parents)}\n"
                "Please help me create a new algorithm that has a totally different form from the given ones.\n"
                "First, describe your new algorithm and main steps in one sentence. "
                f"The description must be inside a brace. Next, {spec}")
    if op == "e2":
        return (f"{TASK}\n"
                f"I have {len(parents)} existing algorithms with their codes as follows:\n{parent_block(parents)}\n"
                "Please help me create a new algorithm that has a totally different form from the given ones "
                "but can be motivated from them.\n"
                "Firstly, identify the common backbone idea in the provided algorithms. "
                "Secondly, based on the backbone idea describe your new algorithm in one sentence. "
                f"The description must be inside a brace. Thirdly, {spec}")
    p = parents[0]
    if op == "m1":
        return (f"{TASK}\n"
                f"I have one algorithm with its code as follows.\n"
                f"Algorithm description: {p['algorithm']}\nCode:\n{p['code']}\n"
                "Please assist me in creating a new algorithm that has a different form but can be a "
                "modified version of the algorithm provided.\n"
                "First, describe your new algorithm and main steps in one sentence. "
                f"The description must be inside a brace. Next, {spec}")
    if op == "m2":
        return (f"{TASK}\n"
                f"I have one algorithm with its code as follows.\n"
                f"Algorithm description: {p['algorithm']}\nCode:\n{p['code']}\n"
                "Please identify the main algorithm parameters and assist me in creating a new algorithm "
                "that has different parameter settings.\n"
                "First, describe your new algorithm and main steps in one sentence. "
                f"The description must be inside a brace. Next, {spec}")
    raise ValueError(op)


def extract(response):
    """与 EoH evolution._extract 相同：代码取 ``` 代码块（没有就找第一句 def 并裁到能解析），思路取代码前花括号内的文字"""
    import ast
    if not response:
        return None, None
    code = re.findall(r'```(?:python)?\n(.*?)```', response, re.DOTALL)
    if not code:
        start = re.search(r'^(?:import |from |def |class |@)', response, re.MULTILINE)
        if start:
            lines = response[start.start():].strip().splitlines()
            for trim in range(len(lines)):
                snippet = '\n'.join(lines[:len(lines) - trim]).strip()
                if not snippet:
                    break
                try:
                    ast.parse(snippet); code = [snippet]; break
                except SyntaxError:
                    continue
    code = [re.sub(r'^\s*\{[^}]*\}\s*\n+', '', c, flags=re.DOTALL).strip() for c in code]
    code = [c for c in code if c]
    if '```' in response:
        pre = response[:response.find('```')].strip()
    elif code:
        idx = response.find(code[0][:60])
        pre = response[:idx].strip() if idx > 0 else response.strip()
    else:
        pre = response.strip()
    alg = re.findall(r'\{([^{}]{8,})\}', pre)
    if not alg and pre:
        alg = [pre]
    if not alg or not code:
        return None, None
    return code[0] + "\n", alg[0]


def parent_selection(pop, m, rnd):
    """EoH：按名次加权 1/(名次 + 1 + 种群大小)，有放回"""
    w = [1 / (r + 1 + len(pop)) for r in range(len(pop))]
    return rnd.choices(pop, weights=w, k=m)


def manage(pop, size):
    """EoH population_management：丢掉无效个体，按目标值去重，保留目标值最小（= 代理分最高）的 size 个"""
    seen, out = set(), []
    for ind in sorted([p for p in pop if p["objective"] is not None], key=lambda x: x["objective"]):
        if ind["objective"] not in seen:
            seen.add(ind["objective"]); out.append(ind)
    return out[:size]


# ---------------- LLM 接口（与 rulegen.call 相同的请求，另外返回 token 用量） ----------------
def call(cfg, prompt):
    """→ (回复文本, usage dict)。EoH 只发一条 user 消息，不带 system。不可恢复的错误抛 RG.Fatal。"""
    req = urllib.request.Request(cfg["api_base"].rstrip("/") + "/chat/completions",
                                 data=json.dumps(dict(model=cfg["model"], messages=[{"role": "user", "content": prompt}],
                                                      temperature=cfg.get("temperature", 0.7))).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["api_key"]})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 120) * 2) as r:
                d = json.load(r)
                return d["choices"][0]["message"]["content"], d.get("usage", {})
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 402, 403, 404):
                raise RG.Fatal(f"接口返回 {e.code}（{e.reason}）：请检查余额、密钥或模型名，处理后重新运行同一条命令即可继续")
            print("接口出错，稍后重试：", e, flush=True)
        except Exception as e:
            print("接口出错，稍后重试：", type(e).__name__, flush=True)
        time.sleep(min(60, 5 * 2 ** attempt))
    raise RG.Fatal("接口连续 8 次失败，已停止；重新运行同一条命令即可继续")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=int)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--samples", type=int, default=54, help="候选总数（含初始化的 10 个）")
    ap.add_argument("--timeout", type=float, default=600.0,
                    help="单个候选评价的超时（秒）；rulegen 默认约 140 秒（2 进程），机器满载时会误判，这里放宽，只防死循环")
    ap.add_argument("--mock", action="store_true", help="不调接口，用 rulegen 的内置规则走一遍流程（自检）")
    a = ap.parse_args()
    tag = f"run{a.run}" + ("_mock" if a.mock else "")
    out = os.path.join(C.OUT, "eoh", tag)
    os.makedirs(out, exist_ok=True)
    train = C.I.split()[0]
    base = E.baseline(train, a.procs, os.path.join(C.RULEGEN, "out", "baseline_train.json"))
    cfg = None if a.mock else RG.load_cfg()
    sp = os.path.join(out, "state.json")
    st = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else \
        {"samples": [], "pop": [], "calls": 0, "tokens": {"prompt": 0, "completion": 0}, "secs_llm": 0.0, "secs_eval": 0.0}
    rnd = random.Random(1000 * a.run + len(st["samples"]))     # 续跑时按已完成样本数重新播种

    def save():
        json.dump(st, open(sp + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(sp + ".tmp", sp)

    def ask(op, prompt):
        """一次 LLM 调用并记日志 → (代码, 思路) 或 (None, None)"""
        t = time.time()
        if a.mock:
            text, usage = "{mock idea: sort available robots differently}\n```python\n" + rnd.choice(RG.MOCK) + "\n```", {}
        else:
            text, usage = call(cfg, prompt)
        st["secs_llm"] += time.time() - t
        st["calls"] += 1
        st["tokens"]["prompt"] += usage.get("prompt_tokens", 0); st["tokens"]["completion"] += usage.get("completion_tokens", 0)
        with open(os.path.join(out, "llm_log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"op": op, "prompt": prompt, "response": text, "usage": usage}, ensure_ascii=False) + "\n")
        return extract(text)

    def generate(op, pop):
        """EoH generate_code：抽不出时重问（最多 4 次），与种群重复时重新生成（最多 2 次）"""
        parents = None if op == "i1" else parent_selection(pop, N_PARENTS if op in ("e1", "e2") else 1, rnd)
        prompt = build_prompt(op, parents)

        def once():
            for _ in range(4):
                code, alg = ask(op, prompt)
                if code:
                    return code, alg
            return None, None
        code, alg = once()
        n = 0
        while code and any(p["code"] == code for p in pop) and n < 2:
            code, alg = once(); n += 1
        return parents, code, alg

    n_init = INIT_FACTOR * POP
    try:
        while len(st["samples"]) < a.samples:
            k = len(st["samples"])
            op = "i1" if k < n_init else rnd.choice(OPERATORS)
            parents, code, alg = generate(op, st["pop"] if k >= n_init else [])
            ind = {"id": f"e{k}", "op": op, "parents": [p["id"] for p in parents] if parents else [], "algorithm": alg,
                   "code": code, "objective": None, "score": None, "error": "没有抽出代码" if code is None else None}
            if code is not None:
                t = time.time()
                sc, res, err = E.score(code, train, base, a.procs, timeout=a.timeout)
                st["secs_eval"] += time.time() - t
                ind["error"] = err
                if err is None:
                    ind["score"] = sc; ind["objective"] = -round(sc, 5)       # EoH 求最小，目标值保留 5 位小数
                    ind["diag"] = E.diagnose(res, base)
            st["samples"].append(ind)
            if k + 1 == n_init:           # 初始化的 10 个样本全部评价后组成种群
                st["pop"] = manage(st["samples"], POP)
            elif k >= n_init:             # 之后稳态更新：新个体并入、去重、保留最好的 5 个
                st["pop"] = manage(st["pop"] + [ind], POP)
            save()
            best = st["pop"][0]["score"] if st["pop"] else None
            msg = f"得分 {ind['score']:.4f}" if ind["score"] is not None else f"无效：{(ind['error'] or '')[:100]}"
            print(f"[{ind['id']}] {op}  {msg}  | 种群最好 {best if best is None else round(best, 4)}  调用 {st['calls']} 次", flush=True)
    except RG.Fatal as e:
        save(); print("停止：", e); E.reset_pool(); sys.exit(1)
    E.reset_pool()
    report(st, out)


def report(st, out):
    """report.md + best_rule.py（全部样本中代理分最高的一条）"""
    ok = sorted([s for s in st["samples"] if s["score"] is not None], key=lambda s: -s["score"])
    nbad = len(st["samples"]) - len(ok)
    d0 = json.load(open(os.path.join(C.RULEGEN, "out", "baseline_train.json"), encoding="utf-8"))
    dflt = sum(v["hv"] for k, v in d0.items() if not k.startswith("_")) / 15
    L = [f"# EoH 规则生成结果（{os.path.basename(out)}）\n",
         f"候选 {len(st['samples'])} 个（有效 {len(ok)}，无效 {nbad}）；LLM 调用 {st['calls']} 次；"
         f"token：输入 {st['tokens']['prompt']}、输出 {st['tokens']['completion']}；"
         f"LLM 耗时 {st['secs_llm'] / 60:.1f} 分钟，评价耗时 {st['secs_eval'] / 60:.1f} 分钟。默认规则代理分 {dflt:.4f}。\n",
         "| 个体 | 算子 | 父代 | 得分 | 对默认 | E 组 | H 组 | M 组 |", "|---|---|---|---|---|---|---|---|"]
    for s in ok:
        L.append(f"| {s['id']} | {s['op']} | {','.join(s['parents'])} | {s['score']:.4f} | {s['score'] - dflt:+.4f} | " +
                 " | ".join(f"{s['diag'][g]['vs_default']:+.3f}" if g in s["diag"] else "—" for g in "EHM") + " |")
    for s in ok[:3]:
        L += [f"\n## {s['id']}（得分 {s['score']:.4f}）\n", s["algorithm"] or "", "\n```python\n" + s["code"] + "```"]
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    if ok:
        open(os.path.join(out, "best_rule.py"), "w", encoding="utf-8").write(ok[0]["code"])
    print("已写出", os.path.join(out, "report.md"), "和 best_rule.py")


if __name__ == "__main__":
    C.mp.freeze_support()
    main()
