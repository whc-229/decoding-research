"""按前端请求的格式生成多类型排班场景请求（与 requests/原请求_paiban.json 同一结构，走同一条服务端解析路径）。
机器人/工具的工作流程直接取自原请求（Evaluate_Update 节点里的 workflow），参数取自毕设 view.md 的参数表（一级维修版本）：
  single_work_time = 每班消耗的连续可用工时 = 去程 + 值岗 + 返程（原请求 G1：1+10+1=12）
  remain_work_time = continue_max_work；cargo_type_num = 可适配工具类型数
注意：C++ 按 (类别, 类型, 序号) 定位实体，序号来自 exampleName 中的数字，必须在每个类型内从 1 开始编号。
用法：python tools/gen_request.py   →  requests/B_三类型720h.json 等
"""
import copy, json, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = json.load(open(os.path.join(HERE, "requests", "原请求_paiban.json"), encoding="utf-8"))
node = [n for n in base["workflow"]["nodeList"]
        if n.get("algorithmMetadata", {}).get("algorithmEnglishName") == "Evaluate_Update"][0]
ents = {e.get("englishName"): e for e in node["entityDataList"]}
ROBOT_WF = ents["Robot"]["exampleList"][0]["workflow"]
TOOL_WF = ents["Tool"]["exampleList"][0]["workflow"]
TASK_ENT = [e for e in node["entityDataList"] if e.get("englishName") not in ("Robot", "Tool")][0]

ROBOTS = [  # view.md 机器人参数表
    dict(type=0, out_travel_time=1, return_travel_time=1, work_time=10, continue_max_work=36, maintenance_time=72,
         charge_time=3, carry_num=2, cargo_type_list=[1, 2, 3]),
    dict(type=1, out_travel_time=2, return_travel_time=2, work_time=6, continue_max_work=50, maintenance_time=100,
         charge_time=4, carry_num=3, cargo_type_list=[0, 1]),
    dict(type=2, out_travel_time=2, return_travel_time=2, work_time=10, continue_max_work=60, maintenance_time=120,
         charge_time=3, carry_num=2, cargo_type_list=[2, 3]),
]
TOOLS = [(1, 1, 8), (2, 2, 6), (1, 1, 4), (2, 2, 3)]   # (安装, 卸载, 保养)


def p(name, val):
    return {"paramEnglishName": name, "inputValue": val}


def make(duration, per_type, pop=100, gen=100):
    robot_ex, tool_ex = [], []
    for r in ROBOTS:
        q = dict(r, single_work_time=r["out_travel_time"] + r["work_time"] + r["return_travel_time"],
                 remain_work_time=r["continue_max_work"], cargo_type_num=len(r["cargo_type_list"]), limit_num=per_type)
        for k in range(1, per_type + 1):
            robot_ex.append({"exampleName": f"实例{k}", "paramList": [p(n, v) for n, v in q.items()],
                             "workflow": copy.deepcopy(ROBOT_WF)})
    for ty, (ins, rem, rest) in enumerate(TOOLS):
        q = dict(install_time=ins, removal_time=rem, tool_work_time=10, type=ty, limit_num=per_type,
                 tool_rest_time=rest, tool_out_time=1, tool_return_time=1)
        for k in range(1, per_type + 1):
            tool_ex.append({"exampleName": f"实例{k}", "paramList": [p(n, v) for n, v in q.items()],
                            "workflow": copy.deepcopy(TOOL_WF)})
    task = copy.deepcopy(TASK_ENT)
    task["exampleList"] = [{"exampleName": "实例1", "paramList": [p("task_duration", duration)]}]
    rob = {k: v for k, v in ents["Robot"].items() if k != "exampleList"}; rob["exampleList"] = robot_ex
    tol = {k: v for k, v in ents["Tool"].items() if k != "exampleList"}; tol["exampleList"] = tool_ex
    return {
        "questName": base.get("questName", "robot"),
        "entityDataList": [rob, tol, task],
        "globalParamList": [{"paramName": "POPSIZE", "paramValue": str(pop)},
                            {"paramName": "max_iterations", "paramValue": str(gen)},
                            {"paramName": "Nvar", "paramValue": "240"},
                            {"paramName": "Lbound", "paramValue": "0"},
                            {"paramName": "Ubound", "paramValue": "0.99"}],
        "parameterList": node["algorithmMetadata"]["parameterList"],
    }


if __name__ == "__main__":
    for name, kw in [("B_三类型720h", dict(duration=720, per_type=10)),
                     ("C_三类型1440h", dict(duration=1440, per_type=10)),
                     ("D_三类型资源紧", dict(duration=720, per_type=6))]:
        path = os.path.join(HERE, "requests", name + ".json")
        json.dump(make(**kw), open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("写入", path, f"{os.path.getsize(path)/1024:.0f} KB")
