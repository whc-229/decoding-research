"""随机生成排班实例族（与 requests/原请求_paiban.json 同一结构，走同一条服务端解析路径）
目的：检验解码/算子机制是否对这一类排班问题普遍有效，而不是只对 4 个手工场景有效。
三组，每组若干个实例（固定随机种子，可复现）：
  E 组 —— 同构：1 种机器人、1～2 种工具
  H 组 —— 异构、值岗时长相同：2～3 种机器人，值岗都是 10 h
  M 组 —— 异构、值岗时长混合：2～3 种机器人，值岗从 {6, 8, 10, 12} 中取（班次不再对齐成等长槽）
每种机器人的参数：去程/返程 1～2 h，充电 2～5 h，维修 48～120 h，每个维修周期出勤 2～5 次
（最大连续工作时间 = 单次工时 × 次数），携带 2～3 个工具，可带工具类型 1～3 种；数量上限 6～10。
工具：安装/拆卸 1～2 h，去程/返程 1 h，工作 10 h，休息 3～8 h；数量上限 6～10。
任务时长从 {480, 720, 1080, 1440} 中取。
用法: python tools/gen_family.py [输出目录，默认 requests_family]
"""
import copy, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_request as G

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def p(name, val):
    return {"paramEnglishName": name, "inputValue": val}


def make(robots, tools, duration):
    robot_ex, tool_ex = [], []
    for r in robots:
        q = dict(r)
        q["single_work_time"] = q["out_travel_time"] + q["work_time"] + q["return_travel_time"]
        q["continue_max_work"] = q["single_work_time"] * q.pop("m")
        q["remain_work_time"] = q["continue_max_work"]
        q["cargo_type_num"] = len(q["cargo_type_list"])
        for k in range(1, q["limit_num"] + 1):
            robot_ex.append({"exampleName": f"实例{k}", "paramList": [p(n, v) for n, v in q.items()],
                             "workflow": copy.deepcopy(G.ROBOT_WF)})
    for q in tools:
        for k in range(1, q["limit_num"] + 1):
            tool_ex.append({"exampleName": f"实例{k}", "paramList": [p(n, v) for n, v in q.items()],
                            "workflow": copy.deepcopy(G.TOOL_WF)})
    task = copy.deepcopy(G.TASK_ENT)
    task["exampleList"] = [{"exampleName": "实例1", "paramList": [p("task_duration", duration)]}]
    rob = {k: v for k, v in G.ents["Robot"].items() if k != "exampleList"}; rob["exampleList"] = robot_ex
    tol = {k: v for k, v in G.ents["Tool"].items() if k != "exampleList"}; tol["exampleList"] = tool_ex
    return {"questName": G.base.get("questName", "robot"), "entityDataList": [rob, tol, task],
            "globalParamList": [{"paramName": "POPSIZE", "paramValue": "30"},
                                {"paramName": "max_iterations", "paramValue": "10"},
                                {"paramName": "Nvar", "paramValue": "240"},
                                {"paramName": "Lbound", "paramValue": "0"},
                                {"paramName": "Ubound", "paramValue": "0.99"}],
            "parameterList": G.node["algorithmMetadata"]["parameterList"]}


def gen(rng, group):
    n_tool = 1 if group == "E" and rng.random() < 0.5 else rng.randint(2, 3)
    tools = [dict(install_time=rng.randint(1, 2), removal_time=rng.randint(1, 2), tool_work_time=10, type=t,
                  limit_num=rng.randint(6, 10), tool_rest_time=rng.randint(3, 8), tool_out_time=1, tool_return_time=1)
             for t in range(n_tool)]
    n_rob = 1 if group == "E" else rng.randint(2, 3)
    robots = []
    for ty in range(n_rob):
        duty = 10 if group in ("E", "H") else rng.choice([6, 8, 10, 12])
        k = rng.randint(1, n_tool)
        robots.append(dict(type=ty, out_travel_time=rng.randint(1, 2), return_travel_time=rng.randint(1, 2),
                           work_time=duty, m=rng.randint(2, 5), maintenance_time=rng.randint(48, 120),
                           charge_time=rng.randint(2, 5), carry_num=rng.choice([2, 2, 3]),
                           cargo_type_list=sorted(rng.sample(range(n_tool), k)), limit_num=rng.randint(6, 10)))
    if group == "M" and len({r["work_time"] for r in robots}) == 1:      # 保证确实混合
        robots[-1]["work_time"] = 6 if robots[0]["work_time"] != 6 else 12
    return robots, tools, rng.choice([480, 720, 1080, 1440])


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "requests_family")
    os.makedirs(out, exist_ok=True)
    rng = random.Random(20261014)
    meta = {}
    for group, cnt in [("E", 3), ("H", 4), ("M", 5)]:
        for j in range(1, cnt + 1):
            robots, tools, T = gen(rng, group)
            name = f"{group}{j:02d}_{T}h"
            json.dump(make(robots, tools, T), open(os.path.join(out, name + ".json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            meta[name] = dict(T=T, robots=robots, tools=tools)
            print(name, "机器人", [(r["work_time"], r["m"], r["carry_num"], r["cargo_type_list"]) for r in robots],
                  "工具类型", len(tools))
    json.dump(meta, open(os.path.join(HERE, "tools", "family_参数.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
