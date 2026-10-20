#pragma once
#include "Properties.h"
#include "Entity.h"
#include "workflow.h"
#include <mutex>
#include <unordered_map>
#include <unordered_set>
extern int generation, MAXGEN;
extern Task task;
extern Objects_Properties properties;
extern Workflow_Set Workflows;
// extern bool isFinal;
extern bool is_final_output;
extern std::string objects;
extern std::map<std::string, double> target_objects;
extern std::vector<std::string> target_object_order;
// 整体评估函数
double robot_arrangement(double* var, int num);
void robot_arrangement_moea(float* x, float* obj, int Nvar, int Nobj);
// 编码长度（2026-10-14）：Nvar = 2 × ⌈任务时长 / 最短值岗时长⌉（班次数严格上界），多则截断、少则补足
int estimate_robot_nvar();
int ensure_robot_nvar(int requested);
// 获得类别数量上限
void Get_Res(std::vector<int> &Res_Robot_Num, std::vector<int> &Res_Tool_Num, Objects_Properties & objects_properties);
// 获取可用的机器人列表
void Get_available_Robot(int Empty_Time, std::vector<std::string> &available_robot_list, Entity_Set &Robots, Objects_Properties &objects_properties, Workflow_Set & workflow_set);
// 解码策略选择
std::string robot_select_strategy3(std::vector<std::string> &available_robot_list, Entity_Set &Robots);
// 流程处理
void Workflow_Process(Entity &entity, Workflow_Set &workflow_set, std::map<std::string, Flow> &workflow_temp, Objects_Properties &objects_properties, double start_time, std::string start_flow_No, std::string end_flow_name);
// 利用DFS查询"流程1"到"流程2"的所有通路路径
void dfs(const std::string &current, const std::string &target,
         std::unordered_map<std::string, Flow> &graph,
         std::vector<std::string> &path,
         std::vector<std::vector<std::string>> &all_paths,
         std::unordered_set<std::string> &visited);
std::vector<std::vector<std::string>> findAllPaths(const std::string &start, const std::string &target,
                                                   std::unordered_map<std::string, Flow> &graph);
// 查询实体剩余
void entity_remain(int &select, Task &task, std::vector<int> Res_Num, bool & flag);
// 创建实体
void entity_create(ENTITY &entity, std::string category, int type, std::vector<int> &Res_num, Objects_Properties &objects_properties);
// 时间推算
double Flow2flow(std::map<std::string, Flow> &workflow_temp, std::vector<std::vector<std::string>> &all_path, std::string start_No, std::string end_No, Objects_Properties &objects_properties, Workflow_Set &workflow_set, Entity &entity, int Empty_Time, std::string min_max);
// 可用工具列表选择1
void tool_select_list(std::vector<std::string> &available_tool_list, Entity_Set & Tool, Objects_Properties & objects_properties, Entity & entity, double min_time, Workflow_Set & workflow_set, int Empty_Time, Task &task);
// 不足情况下多增加工具
bool Add_tool(Entity &entity, Objects_Properties &objects_properties, int select_tool, std::vector<int> &Res_Tool_Num, Entity_Set &Tool);
// 处理一次性携带工具
void robot_time_list(Entity &entity, Entity_Set &Tool, Objects_Properties &objects_properties);

// 实体处理流程
bool entity_workflow_process(Entity &entity,
                             Workflow_Set &workflow_set,
                             Objects_Properties &objects_properties,
                             Entity_Set &Tool,
                             double & Empty_Time,
                             std::vector<int> &Res_Tool_Num,
                             std::vector<std::string> &available_tool_list,
                             double *var,
                             int i,
                             int num,
                             Task &task);
// 打印携带的工具
void print_carry_entity(Entity & entity);
// 打印流程时间
void Print_Temp_State(Entity &entity, Workflow_Set &workflow_set);

// 打印消耗实体
void Count_Entity_Types(const Entity_Set &entity_set, Task &task);
void Set_Entity_Timelist(Entity &entity, Objects_Properties &objects_properties);
// 将规划结果存入到json文件中
bool Entity_Set2File(std::vector<Entity_Set> &vector_entity_set, Task &task);

// 测试函数
double Func(double *var, int num);
double ComputePathDuration(
    std::map<std::string, Workflow> &nodes,
    Objects_Properties &props,
    ENTITY &entity,
    const std::string &start,
    const std::string &end,
    std::unordered_set<std::string> visited = {});

// ===== 解码轨迹（研究用插桩，2026-10-14；仅本地研究版）=====
// robot_arrangement_moea 每次评价时填写，供分级惩罚、仿真感知变异使用
struct RosterTrace
{
    std::vector<int> n_avail;        // 每班可用（可复用）机器人数
    std::vector<int> robot_of_shift; // 每班派出的机器人在本次解码中的序号（按首次出现顺序编号）
    std::vector<int> new_shift;      // 新开机器人的班次
    std::unordered_map<std::string, int> idx_of;
    int cur_shift = 0;               // 正在处理的班次（失败时即失败班次）
    double progress = 0.0;           // 已覆盖比例 Empty_Time / 任务时长
    bool feasible = false;
    int cap_override = 0;            // 容量预判把"新开"改成复用的次数（ROBOT_DECODER=3）
    int bt_fixes = 0;                // 回溯修复成功的次数（ROBOT_DECODER=5）
    std::vector<int> act_nav, act_sel; // 实验0：每班实际执行的动作（可用数, 选择：<可用数为复用下标，否则 = 可用数 + 实际新开类型），供写回用（仅解码 5）
    void clear() { act_nav.clear(); act_sel.clear(); n_avail.clear(); robot_of_shift.clear(); new_shift.clear(); idx_of.clear(); cur_shift = 0; progress = 0.0; feasible = false; cap_override = 0; bt_fixes = 0; }
    int index_of(const std::string& id) { auto it = idx_of.find(id); if (it != idx_of.end()) return it->second; int k = (int)idx_of.size(); idx_of[id] = k; return k; }
};
extern RosterTrace g_roster_trace;
