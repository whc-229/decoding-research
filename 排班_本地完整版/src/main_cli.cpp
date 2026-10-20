// 机器人—工具排班多目标求解：本地命令行入口
// 与服务端 algorithm_routes.cpp 中 run_robot_moea_solver() 走同一条路径：
//   前端请求 JSON → normalizeRobotSolverParam → 目标/全局参数/MOEA 参数解析
//   → para_set_robot_solver（按模板生成 config/1.json…N.json 与 scenario.json）
//   → task / properties / Workflows 读入 → MOEA_solver(robot_arrangement_moea) 迭代 → 输出外部档案 EP
// 请求处理函数全部逐字抽取自 algorithm_routes.cpp（见 request_adapter.inc），不依赖 httplib / SQLite / curl。
//
// 用法：
//   ./paiban --request requests/原请求_paiban.json [--workdir work] [--templates templates]
//            [--pop N] [--gen N] [--nvar N|auto] [--alg NSGA2|MOEAD|IBEA|GREA|HYPE|MOEADD]
//            [--objs min_num,max_balance] [--no-auto-types] [--detail] [--out result.json] [--quiet] [--show-model-log]
//            [--graded] [--sim-mutate] [--seed-rule]   （研究用机制，见下方说明）
//   未给的参数一律按请求里的值（与服务端一致）；Nvar 默认 auto = 2×⌈任务时长/最短值岗时长⌉（班次数严格上界）。
#include "problem.h"
#include "MOEA_solver.h"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <random>
#include <cstdint>

using namespace std;
using json = nlohmann::json;

// ---- 服务端里定义在 algorithm_routes.cpp 的全局对象，这里重新定义 ----
int generation = 0;
int MAXGEN = -1;            // 保持 -1：problem.cpp 中 generation==MAXGEN 才打印调试信息
Task task;
Objects_Properties properties;
Workflow_Set Workflows;
string work_path = "./";    // para_set_robot_solver 用 work_path + "config/"

#include "request_adapter.inc"

#ifndef ROBOT_DECODER
#define ROBOT_DECODER 0
#endif
#ifndef ROBOT_DECODER_THETA
#define ROBOT_DECODER_THETA 0.85
#endif
#ifndef CAP_RHO_SPAN
#define CAP_RHO_SPAN 1.0
#endif
#define CAP_RHO_SPAN_VALUE (ROBOT_DECODER >= 3 ? (double)(CAP_RHO_SPAN) : 0.0)

namespace fs = std::filesystem;

// ======================= 研究用机制（2026-10-14，仅本地研究版） =======================
// --graded      分级惩罚：不可行解目标 = 30000 + 1000 × (1 − 已覆盖比例)，推进越远越好（原做法一律 30000）
// --sim-mutate  仿真感知变异：算子序列中的 mutate 换成 SIM_MUTATE——按父代的解码轨迹定点改机器人基因
//               · 父代不可行：把失败班次及之前 5 班的机器人基因（各以 1/2 概率）改到"复用已有机器人"区间
//               · 父代可行：1/2 概率"减资源"（随机挑一次新开机器人的班次改成复用），
//                           1/2 概率"均衡"（出勤最多的机器人随机让出一个班次给其他可用机器人）
//               改完再做一次多项式变异
// --seed-rule   规则播种：初始种群放入全 0 个体（=每班都复用第一个可用机器人；排序解码下即"最闲优先"）及 9 个小扰动版本
static bool g_graded = false, g_cache_on = false;
static long long g_evals = 0, g_sim_calls = 0, g_sim_hits = 0;
struct TraceRec { std::vector<int> n_avail, robot_of_shift, new_shift; int fail_shift; bool feasible; };
static std::unordered_map<uint64_t, TraceRec> g_trace_cache;
static uint64_t hash_x(const float* x, int n)
{
    uint64_t h = 1469598103934665603ULL;
    const unsigned char* p = reinterpret_cast<const unsigned char*>(x);
    for (size_t i = 0; i < sizeof(float) * (size_t)n; ++i) { h ^= p[i]; h *= 1099511628211ULL; }
    return h;
}
// --write-back  实验0：拉马克式写回（仅解码 5）。评价后把解码实际执行的动作（容量预判改写、回溯修复改派后的选择）写回机器人基因，
//               原基因已表示同一动作的位置不动；写回后重新评价核对目标值，不一致则恢复原基因（核对用的评价不计入评价次数）
static bool g_write_back = false;
extern double g_dev_density;
extern double g_slot_frac;
extern int g_slot_adapt;   // 实验3：解码 8 的偏离密度（problem.cpp）
static long long g_wb_genes = 0, g_wb_inds = 0, g_wb_reverts = 0;
static int wb_select(double x, int n, int nT)   // 与 problem.cpp 的 decode_robot_select（阈值解码）相同
{
    const double th = ROBOT_DECODER_THETA;
    if (n > 0 && x < th) { int s = (int)(x / th * n); return std::min(std::max(s, 0), n - 1); }
    double u = (n > 0) ? (x - th) / (1.0 - th) : x;
    int t = (int)(std::max(u, 0.0) * nT);
    return n + std::min(std::max(t, 0), nT - 1);
}
static void write_back(float* x, float* obj, int Nvar, int Nobj)
{
    const RosterTrace& t = g_roster_trace;
    if (!t.feasible || t.act_sel.empty()) return;
    const int nT = task.objects_type["Robot"];
    const double th = ROBOT_DECODER_THETA;
    std::vector<float> old(x, x + Nvar);
    std::vector<int> nav = t.act_nav, act = t.act_sel;
    int changed = 0;
    for (size_t i = 0; i < act.size() && (int)i < Nvar / 2; ++i)
    {
        const int n = nav[i], a = act[i];
        const int s0 = wb_select((double)x[i], n, nT);
        if (a < n) { if (s0 != a) { x[i] = (float)((a + 0.5) / n * th); ++changed; } }
        else
        {
            const int ty = a - n;
            if (!(s0 >= n && s0 - n == ty)) { x[i] = (float)(n > 0 ? th + (ty + 0.85) / nT * (1.0 - th) : (ty + 0.5) / nT); ++changed; }
        }
    }
    if (!changed) return;
    std::vector<float> o2(Nobj);
    robot_arrangement_moea(x, o2.data(), Nvar, Nobj);
    bool same = true;
    for (int k = 0; k < Nobj; ++k) same = same && (o2[k] == obj[k]);
    if (!same) { std::copy(old.begin(), old.end(), x); ++g_wb_reverts; return; }
    g_wb_genes += changed; ++g_wb_inds;
}
static void eval_wrapper(float* x, float* obj, int Nvar, int Nobj)
{
    robot_arrangement_moea(x, obj, Nvar, Nobj);
    ++g_evals;
    if (g_write_back) write_back(x, obj, Nvar, Nobj);
    const RosterTrace& t = g_roster_trace;
    if (g_graded && !t.feasible)
        for (int k = 0; k < Nobj; ++k) obj[k] = static_cast<float>(30000.0 + 1000.0 * (1.0 - std::min(1.0, t.progress)));
    if (g_cache_on)
    {
        if (g_trace_cache.size() > 60000) g_trace_cache.clear();
        g_trace_cache[hash_x(x, Nvar)] = TraceRec{t.n_avail, t.robot_of_shift, t.new_shift, t.cur_shift, t.feasible};
    }
}
static std::mt19937 g_rng{std::random_device{}()};
static double urand() { return std::uniform_real_distribution<double>(0.0, 1.0)(g_rng); }
// "复用已有机器人"区间内的随机基因值（与解码方式一致）
static float reuse_gene(int n_avail, int n_types)
{
#if ROBOT_DECODER >= 1
    (void)n_avail; (void)n_types;
    return static_cast<float>(urand() * ROBOT_DECODER_THETA);
#else
    return static_cast<float>(urand() * n_avail / double(n_avail + n_types) * 0.999);
#endif
}
static void sim_mutate(individual* ind, int Nvar, int n_types)
{
    ++g_sim_calls;
    auto it = g_trace_cache.find(hash_x(ind->x, Nvar));
    if (it == g_trace_cache.end()) return;
    ++g_sim_hits;
    const TraceRec& t = it->second;
    const auto& na = t.n_avail;
    if (na.empty()) return;
    if (!t.feasible)
    {
        int k = std::min(t.fail_shift, (int)na.size() - 1);
        for (int s = std::max(0, k - 5); s <= k; ++s)
            if (na[s] > 0 && urand() < 0.5) ind->x[s] = reuse_gene(na[s], n_types);
        return;
    }
    if (urand() < 0.5 && !t.new_shift.empty())
    {
        std::vector<int> c;
        for (int s : t.new_shift) if (s < (int)na.size() && na[s] > 0) c.push_back(s);
        if (!c.empty()) { int s = c[g_rng() % c.size()]; ind->x[s] = reuse_gene(na[s], n_types); }
        return;
    }
    std::map<int, int> cnt;
    for (int r : t.robot_of_shift) cnt[r]++;
    int busiest = -1, best = -1;
    for (auto& kv : cnt) if (kv.second > best) { best = kv.second; busiest = kv.first; }
    std::vector<int> c;
    for (int s = 0; s < (int)t.robot_of_shift.size() && s < (int)na.size(); ++s)
        if (t.robot_of_shift[s] == busiest && na[s] > 1) c.push_back(s);
    if (!c.empty()) { int s = c[g_rng() % c.size()]; ind->x[s] = reuse_gene(na[s], n_types); }
}
// ==================================================================================

// 丢弃一切输出的流缓冲（不依赖 /dev/null，Windows 下同样可用）
struct NullBuf : std::streambuf { int overflow(int c) override { return c; } };
static NullBuf g_nullbuf;

static void set_env(const char* k, const char* v)
{
#ifdef _WIN32
    _putenv_s(k, v);
#else
    setenv(k, v, 1);
#endif
}

static void usage()
{
    cerr << "用法: paiban --request 请求.json [--workdir work] [--templates templates] [--pop N] [--gen N]\n"
            "              [--nvar N|auto] [--alg NSGA2] [--objs min_num,max_balance] [--no-auto-types]\n"
            "              [--detail] [--out result.json] [--quiet]\n";
}

int main(int argc, char** argv)
{
    string request_path, workdir = "work", templates = "templates", out_path, alg_override, objs_override, nvar_arg = "auto";
    string eval_genes_path;
    int pop_override = -1, gen_override = -1;
    bool auto_types = true, detail = false, quiet = false, show_model_log = false, allow_short_nvar = false;
    bool sim_mut = false, seed_rule = false;
    for (int i = 1; i < argc; ++i) {
        string a = argv[i];
        auto next = [&]() -> string { if (i + 1 >= argc) { usage(); exit(2); } return argv[++i]; };
        if (a == "--request") request_path = next();
        else if (a == "--workdir") workdir = next();
        else if (a == "--templates") templates = next();
        else if (a == "--pop") pop_override = stoi(next());
        else if (a == "--gen") gen_override = stoi(next());
        else if (a == "--nvar") nvar_arg = next();
        else if (a == "--alg") alg_override = next();
        else if (a == "--objs") objs_override = next();
        else if (a == "--no-auto-types") auto_types = false;
        else if (a == "--detail") detail = true;
        else if (a == "--quiet") quiet = true;
        else if (a == "--show-model-log") show_model_log = true;
        else if (a == "--allow-short-nvar") allow_short_nvar = true;   // 仅用于测试覆盖检查
        else if (a == "--graded") g_graded = true;
        else if (a == "--sim-mutate") sim_mut = true;
        else if (a == "--seed-rule") seed_rule = true;
        else if (a == "--write-back") g_write_back = true;
        else if (a == "--dev-density") g_dev_density = stod(next());
        else if (a == "--slot-frac") g_slot_frac = stod(next());
        else if (a == "--slot-adapt") g_slot_adapt = 1;
        else if (a == "--out") out_path = next();
        else if (a == "--eval-genes") eval_genes_path = next();
        else { usage(); return 2; }
    }
    if (request_path.empty()) { usage(); return 2; }
    if (out_path.empty()) out_path = workdir + "/result.json";

    auto t0 = chrono::high_resolution_clock::now();
    json param;
    {
        ifstream f(request_path);
        if (!f.is_open()) { cerr << "无法打开请求文件: " << request_path << endl; return 1; }
        f >> param;
    }

    // ===== 1. 与 run_robot_moea_solver 相同的参数解析 =====
    json normalized_param = normalizeRobotSolverParam(param);
    if (!normalized_param.contains("entityDataList") || !normalized_param["entityDataList"].is_array()) {
        cerr << "请求缺少 entityDataList" << endl; return 1;
    }

    target_objects.clear();
    target_object_order.clear();
    if (!objs_override.empty()) {
        stringstream ss(objs_override); string name;
        while (getline(ss, name, ',')) {
            if (name == "min_num" || name == "max_balance") { target_objects[name] = 1.0; target_object_order.push_back(name); }
        }
    } else if (normalized_param.contains("objects") && normalized_param["objects"].is_array()) {
        for (const auto& obj : normalized_param["objects"]) {
            if (!obj.contains("name") || !obj["name"].is_string()) continue;
            const string name = obj["name"].get<string>();
            if (name != "min_num" && name != "max_balance") continue;
            double weight = 1.0;
            if (obj.contains("weight")) {
                if (obj["weight"].is_string()) { try { weight = stod(obj["weight"].get<string>()); } catch (...) {} }
                else if (obj["weight"].is_number()) weight = obj["weight"].get<double>();
            }
            target_objects[name] = weight;
            target_object_order.push_back(name);
        }
    }
    if (target_object_order.empty()) {
        target_objects["min_num"] = 1.0;
        target_objects["max_balance"] = 1.0;
        target_object_order = {"min_num", "max_balance"};
    }

    int Popsize = 20, maxgen = 200, Nvar = 100, dummy_gen = 0;
    double Lbound_value = 0.0, Ubound_value = 0.9999;
    if (normalized_param.contains("globalParamList")) {
        extractGlobalParams(normalized_param["globalParamList"], Popsize, Nvar, Lbound_value, Ubound_value, maxgen, dummy_gen);
    }
    if (pop_override > 0) Popsize = pop_override;
    if (gen_override > 0) maxgen = gen_override;

    int Nobj = 0;
    if (normalized_param.contains("targetNum") && normalized_param["targetNum"].is_number_integer())
        Nobj = normalized_param["targetNum"].get<int>();
    else if (normalized_param.contains("Nobj") && normalized_param["Nobj"].is_number_integer())
        Nobj = normalized_param["Nobj"].get<int>();
    if (Nobj <= 0 || !objs_override.empty()) Nobj = static_cast<int>(target_object_order.size());
    if (Nobj <= 0) Nobj = 2;

    moea_opeset moea_set;
    string algorithm = "NSGA2";
    if (normalized_param.contains("algorithmName") && normalized_param["algorithmName"].is_string())
        algorithm = normalized_param["algorithmName"].get<string>();
    else if (normalized_param.contains("moeaAlgorithm") && normalized_param["moeaAlgorithm"].is_string())
        algorithm = normalized_param["moeaAlgorithm"].get<string>();
    vector<string> opeList = {"crossover", "mutate"};
    apply_moea_params(normalized_param, moea_set, algorithm, opeList);
    if (!alg_override.empty()) algorithm = alg_override;
    transform(algorithm.begin(), algorithm.end(), algorithm.begin(), [](unsigned char c) { return (char)toupper(c); });
    if (algorithm == "EVALUATE_UPDATE") algorithm = "NSGA2";

    // ===== 2. 生成运行时配置（与服务端相同：模板 → config/N.json + scenario.json）=====
    fs::create_directories(workdir + "/config");
    work_path = workdir + "/";
    for (const char* f : {"robot_template.json", "tool_template.json", "scenario.json"})
        fs::copy_file(templates + "/" + f, work_path + "config/" + f, fs::copy_options::overwrite_existing);
    para_set_robot_solver(normalized_param);

    // 本地版补充：scenario.json 的 objects_type 按实际出现的类型更新（服务端沿用模板值，多类型场景需要这一步）
    double min_work_time = 1e9;
    {
        map<string, int> max_type;
        for (const auto& e : fs::directory_iterator(work_path + "config")) {
            string n = e.path().filename().string();
            if (!regex_match(n, regex(R"(\d+\.json)"))) continue;
            ifstream g(e.path()); json ej; g >> ej;
            string cat = ej.value("category", "");
            max_type[cat] = max(max_type[cat], ej.value("type", 0));
            if (cat == "Robot" && ej.contains("normal_property") && ej["normal_property"].contains("work_time"))
                min_work_time = min(min_work_time, ej["normal_property"]["work_time"].get<double>());
        }
        if (auto_types) {
            ifstream g(work_path + "config/scenario.json"); json sc; g >> sc; g.close();
            for (auto& kv : max_type) sc["objects_type"][kv.first] = kv.second + 1;
            ofstream o(work_path + "config/scenario.json"); o << setw(4) << sc << endl;
        }
    }

    task.Set_Task(work_path + "config/scenario.json");
    properties.Set_Objects_Properties(work_path + "config/");
    Workflows.Set_Workflow_Set(work_path + "config/scenario.json");

    // 编码长度：默认 auto = 2×⌈任务时长/最短值岗时长⌉；手动给定时与服务端一样多则截断、少则补足（--allow-short-nvar 可跳过，仅测试用）
    if (nvar_arg == "auto") {
        Nvar = estimate_robot_nvar();
    } else if (!nvar_arg.empty()) {
        Nvar = stoi(nvar_arg);
        if (!allow_short_nvar) Nvar = ensure_robot_nvar(Nvar);
    }
    if (Nvar % 2) Nvar++;
#if ROBOT_DECODER >= 3
    Nvar += 2;   // 容量预判解码：末位作为裕度基因（多出的一个班次槽不会被用到，因为班次上界 ⌈T/最短值岗⌉ 是严格上界）
#endif

    if (!quiet) {
        cout << "[配置] 请求=" << request_path << " 任务时长=" << task.task_duration
             << " 机器人类型数=" << task.objects_type["Robot"] << " 工具类型数=" << task.objects_type["Tool"]
             << " 实体文件数=" << properties.Properties_Set.size() << endl;
        cout << "[参数] 算法=" << algorithm << " 种群=" << Popsize << " 代数=" << maxgen << " Nvar=" << Nvar
             << " Nobj=" << Nobj << " 解码=" << (ROBOT_DECODER == 8 ? "偏离密度" : ROBOT_DECODER == 7 ? "自适应(dec5/dec6)" : ROBOT_DECODER == 6 ? "规则+稀疏偏离" : ROBOT_DECODER == 5 ? "排序+容量预判+回溯修复" : ROBOT_DECODER == 4 ? "维修相位排序+容量预判" : ROBOT_DECODER == 3 ? "排序+容量预判" : ROBOT_DECODER == 2 ? "排序" : (ROBOT_DECODER ? "阈值" : "原")) << " pc=" << moea_set.pc
             << " pm=" << moea_set.pm << " 目标=";
        for (auto& s : target_object_order) cout << s << " ";
        cout << endl;
    }

    // ===== 研究用：--eval-genes 文件（JSON 数组，每个元素是一条基因向量）→ 逐条调用原目标函数并输出结果，不运行优化 =====
    if (!eval_genes_path.empty()) {
        json genes; { ifstream f(eval_genes_path); f >> genes; }
        json res = json::array();
        std::streambuf* cb = cout.rdbuf();
        if (!show_model_log) cout.rdbuf(&g_nullbuf);
        for (auto& g : genes) {
            vector<float> x(Nvar, 0.0f);
            for (int j = 0; j < Nvar && j < (int)g.size(); ++j) x[j] = g[j].get<float>();
            vector<float> obj(Nobj, 0.0f);
            robot_arrangement_moea(x.data(), obj.data(), Nvar, Nobj);
            const RosterTrace& t = g_roster_trace;
            vector<string> names(t.idx_of.size());
            for (auto& kv : t.idx_of) names[kv.second] = kv.first;
            json robots = json::array();
            for (int r : t.robot_of_shift) robots.push_back(names[r]);
            res.push_back({{"obj", obj}, {"feasible", t.feasible}, {"robots", robots}, {"n_avail", t.n_avail}, {"cap_override", t.cap_override}, {"bt_fixes", t.bt_fixes}});
        }
        cout.rdbuf(cb);
        ofstream o(out_path); o << res.dump() << endl;
        return 0;
    }

    // ===== 3. 求解（与服务端相同）=====
    MOEA_solver solver(moea_set.H, moea_set.rpsLevel, Nvar, Nobj,
                       static_cast<float>(Lbound_value), static_cast<float>(Ubound_value),
                       eval_wrapper, moea_set.hypeSamples, Popsize);
    g_cache_on = sim_mut;
    solver.Initial(moea_set);
    solver.initialize();
    if (seed_rule) {
        std::vector<std::vector<float>> seeds(10, std::vector<float>(Nvar, 0.0f));
        for (int k = 1; k < 10; ++k) for (int j = 0; j < Nvar; ++j) seeds[k][j] = static_cast<float>(0.1 * urand());
        solver.seedIndividuals(seeds);
    }
    if (sim_mut) {
        bool replaced = false;
        for (auto& op : opeList) {
            string u = op; transform(u.begin(), u.end(), u.begin(), [](unsigned char c) { return (char)toupper(c); });
            if (u == "MUTATE" || u == "PM") { op = "sim_mutate"; replaced = true; }
        }
        if (!replaced) opeList.push_back("sim_mutate");
        const int n_types = task.objects_type["Robot"];
        solver.custom_op = [Nvar, n_types](individual* ind) { sim_mutate(ind, Nvar, n_types); };
    }
    if (!opeList.empty()) solver.setOperatorSequence(opeList);

    // 目标函数内部有大量无条件的 [DEBUG] 打印，求解期间把 cout 指向空设备（--show-model-log 可保留）
    std::streambuf* cout_buf = cout.rdbuf();
    if (!show_model_log) cout.rdbuf(&g_nullbuf);
    json history = json::array();
    for (int gen = 0; gen < maxgen; ++gen) {
        if (algorithm == "MOEAD") solver.MOEAD();
        else if (algorithm == "IBEA") solver.IBEA();
        else if (algorithm == "GREA") solver.GrEA();
        else if (algorithm == "HYPE") solver.hypE();
        else if (algorithm == "MOEADD") solver.MOEADD();
        else solver.NSGA();
        float best0 = 1e30f;
        for (const auto& ind : solver.EP) best0 = min(best0, ind.obj[0]);
        history.push_back({{"gen", gen + 1}, {"ep_size", solver.EP.size()}, {"best_obj0", best0}});
        if (!quiet && ((gen + 1) % 10 == 0 || gen + 1 == maxgen))
            cerr << "   第 " << gen + 1 << "/" << maxgen << " 代, 档案大小=" << solver.EP.size()
                 << ", 最小 " << target_object_order[0] << "=" << best0 << endl;
    }

    cout.rdbuf(cout_buf);
    // ===== 4. 输出 =====
    json pareto_objs = json::array(), pareto_vars = json::array();
    int rep = -1; float rep_val = 1e30f;
    for (size_t e = 0; e < solver.EP.size(); ++e) {
        const auto& ind = solver.EP[e];
        json row = json::array();
        for (int k = 0; k < Nobj; ++k) row.push_back(ind.obj[k]);
        pareto_objs.push_back(row);
        pareto_vars.push_back(vector<float>(ind.x, ind.x + Nvar));
        if (ind.obj[0] < rep_val) { rep_val = ind.obj[0]; rep = (int)e; }
    }
    if (detail && rep >= 0) {
        string res_dir = workdir + "/Res";
        set_env("PAIBAN_RES_DIR", res_dir.c_str());
        vector<double> x(solver.EP[rep].x, solver.EP[rep].x + Nvar);
        if (!show_model_log) cout.rdbuf(&g_nullbuf);
        is_final_output = true;
        robot_arrangement(x.data(), Nvar);
        is_final_output = false;
        cout.rdbuf(cout_buf);
        if (!quiet) cout << "[详细] 代表解（" << target_object_order[0] << " 最小）的甘特数据写入 " << res_dir << "/result.json" << endl;
    }
    double secs = chrono::duration<double>(chrono::high_resolution_clock::now() - t0).count();
    json out;
    out["request"] = request_path;
    out["algorithm"] = algorithm;
    out["decoder"] = ROBOT_DECODER == 8 ? "dev_density" : ROBOT_DECODER == 7 ? "adaptive_5_6" : ROBOT_DECODER == 6 ? "rule_sparse_dev" : ROBOT_DECODER == 5 ? "rank_cap_bt" : ROBOT_DECODER == 4 ? "phase_cap" : ROBOT_DECODER == 3 ? "rank_cap" : ROBOT_DECODER == 2 ? "rank" : (ROBOT_DECODER ? "theta" : "orig");
    out["cap_rho_span"] = CAP_RHO_SPAN_VALUE;
    out["graded"] = g_graded; out["sim_mutate"] = sim_mut; out["seed_rule"] = seed_rule;
    out["evaluations"] = g_evals;
    out["sim_mutate_calls"] = g_sim_calls; out["sim_mutate_trace_hits"] = g_sim_hits;
    out["dev_density"] = g_dev_density;
    out["slot_frac"] = g_slot_frac; out["slot_adapt"] = g_slot_adapt;
    out["write_back"] = g_write_back; out["wb_individuals"] = g_wb_inds; out["wb_genes"] = g_wb_genes; out["wb_reverts"] = g_wb_reverts;
#ifdef FORCE_NEW_BAND
    out["force_new_band"] = true;
#endif
    out["operators"] = opeList;
    out["theta"] = ROBOT_DECODER_THETA;
    out["popsize"] = Popsize; out["maxgen"] = maxgen; out["Nvar"] = Nvar; out["Nobj"] = Nobj;
    out["objectives"] = target_object_order;
    out["task_duration"] = task.task_duration;
    out["pareto_objs"] = pareto_objs;
    out["pareto_vars"] = pareto_vars;
    out["history"] = history;
    out["seconds"] = secs;
    ofstream o(out_path); o << setw(2) << out << endl;
    if (!quiet) {
        cout << "[完成] 用时 " << fixed << setprecision(1) << secs << " s，档案 " << solver.EP.size() << " 个解，结果写入 " << out_path << endl;
        for (size_t e = 0; e < min<size_t>(solver.EP.size(), 8); ++e) {
            cout << "   (";
            for (int k = 0; k < Nobj; ++k) cout << (k ? ", " : "") << setprecision(3) << solver.EP[e].obj[k];
            cout << ")" << endl;
        }
    }
    return 0;
}
