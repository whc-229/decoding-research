// 排班模型 ↔ 算法库（MOEA_serial_full_cpp/Multi_serial_v3）的桥接层
// 只包含 model-crow 模型一侧的头文件，与算法库的头文件（同名的 MOEA_solver/Population）分开编译，避免冲突。
#include "problem.h"
#include <cstdio>
#include <fstream>
#include <iostream>
#include <streambuf>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

#ifndef ROBOT_DECODER
#define ROBOT_DECODER 0
#endif

// ---- 服务端在 algorithm_routes.cpp 定义的全局对象 ----
int generation = 0;
int MAXGEN = -1;   // problem.cpp 中 generation==MAXGEN 才打印调试信息，保持 -1
Task task;
Objects_Properties properties;
Workflow_Set Workflows;
std::string work_path = "./";
extern std::map<std::string, double> target_objects;

namespace {
struct NullBuf : std::streambuf { int overflow(int c) override { return c; } };
NullBuf g_null;
long long g_evals = 0, g_feasible = 0;
std::vector<std::pair<float, float>> g_arch;   // 所有已评价解的非支配集（只存目标值）
}

int paiban_bridge_setup(const char* workdir)
{
    std::streambuf* cb = std::cout.rdbuf(&g_null);
    work_path = std::string(workdir) + "/";
    task.Set_Task(work_path + "config/scenario.json");
    properties.Set_Objects_Properties(work_path + "config/");
    Workflows.Set_Workflow_Set(work_path + "config/scenario.json");
    target_objects.clear();
    target_objects["min_num"] = 1.0;
    target_objects["max_balance"] = 1.0;
    target_object_order = {"min_num", "max_balance"};
    int nv = estimate_robot_nvar();
    if (nv % 2) nv++;
#if ROBOT_DECODER >= 3
    nv += 2;
#endif
    std::cout.rdbuf(cb);
    return nv;
}

void paiban_bridge_eval(float* x, float* obj, int nvar)
{
    std::streambuf* cb = std::cout.rdbuf(&g_null);
    robot_arrangement_moea(x, obj, nvar, 2);
    std::cout.rdbuf(cb);
    ++g_evals;
    if (obj[0] >= 29999.0f) return;
    ++g_feasible;
    std::pair<float, float> p(obj[0], obj[1]);
    for (auto& q : g_arch)
        if (q.first <= p.first && q.second <= p.second) return;   // 被支配或重复
    std::vector<std::pair<float, float>> nxt;
    for (auto& q : g_arch)
        if (!(p.first <= q.first && p.second <= q.second)) nxt.push_back(q);
    nxt.push_back(p);
    g_arch.swap(nxt);
}

long long paiban_bridge_evals() { return g_evals; }

void paiban_bridge_dump(const char* path, const char* alg, double secs, int popsize, int nvar)
{
    nlohmann::json out;
    out["algorithm"] = alg;
    out["evaluations"] = g_evals;
    out["feasible_evaluations"] = g_feasible;
    out["seconds"] = secs;
    out["popsize"] = popsize;
    out["Nvar"] = nvar;
    out["decoder"] = ROBOT_DECODER;
    nlohmann::json f = nlohmann::json::array();
    std::sort(g_arch.begin(), g_arch.end());
    for (auto& q : g_arch) f.push_back({q.first, q.second});
    out["pareto_objs"] = f;
    std::ofstream o(path);
    o << out.dump(1) << std::endl;
}
