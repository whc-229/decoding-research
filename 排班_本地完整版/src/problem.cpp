// 排班类目标函数
#include "problem.h"
#include <random>
#include <vector>
#include <algorithm> // for std::sort
#include <numeric>   // for std::accumulate
#include <cmath>// for std::pow and std::sqrt
#include <queue>
#include <map>
#include <filesystem>
#include <cerrno>
#include <cstring>
#include <cstdlib>
using namespace std;
extern int generation, MAXGEN;
extern Workflow_Set Workflows;
int shift = 0;
bool is_final_output = false;
// bool isFinal = true;
std::string objects;
std::map<std::string, double> target_objects;
RosterTrace g_roster_trace;   // 解码轨迹（研究用插桩）

// ===================== 机器人选择解码方式（2026-10-13 新增） =====================
// ROBOT_DECODER = 0：原解码  select = (x - 1e-3) * (可用机器人数 + 机器人类型数)
//                   "复用还是新开"的含义随可用列表长度漂移，且新开概率 = 类型数/(可用数+类型数)，天然偏向不断新开。
// ROBOT_DECODER = 1：阈值解码  有可用机器人且 x < θ → 复用第 int(x/θ·可用数) 台；
//                   否则新开类型 int((x-θ)/(1-θ)·类型数)（无可用机器人时直接按 x 选类型）。
//                   "复用/新开"的决策与可用列表长度解耦。返回值的含义与原解码相同，后续分支无需改动：
//                   < 可用数 → 复用；否则 减去可用数 = 新开的类型下标。
// 编译时用 -DROBOT_DECODER=1 切换，-DROBOT_DECODER_THETA=0.85 调阈值。默认 0，行为与原版完全一致。
// ROBOT_DECODER = 2（仅本地研究版）：阈值解码 + 可用机器人按出勤次数升序（同次数时剩余工时多者优先）。
#ifndef ROBOT_DECODER
#define ROBOT_DECODER 0
#endif
#ifndef ROBOT_DECODER_THETA
#define ROBOT_DECODER_THETA 0.85
#endif
static int decode_robot_select(double x, int n_avail, int n_types)
{
#if ROBOT_DECODER >= 1   // 1 = 阈值解码；2 = 阈值解码 + 可用机器人按出勤次数排序（排序在调用处）
    const double th = ROBOT_DECODER_THETA;
    if (n_avail > 0 && x < th)
    {
        int s = static_cast<int>(x / th * n_avail);
        return std::min(std::max(s, 0), n_avail - 1);
    }
    double u = (n_avail > 0) ? (x - th) / (1.0 - th) : x;
    int t = static_cast<int>(std::max(u, 0.0) * n_types);
    return n_avail + std::min(std::max(t, 0), n_types - 1);
#else
    return static_cast<int>((x - 1e-3) * (n_avail + n_types));
#endif
}
// ROBOT_DECODER = 4（仅本地研究版）：维修相位排序 + 容量预判。可用机器人按"剩余工时少（离维修近）优先、出勤少其次"排序。
//   依据：把"剩余工时最少者优先"当作整条规则就能在 4 个场景都达到资源数下界（让机器人错开进入维修），
//   而"出勤最少优先"当作规则会把资源数推到 11～17；排序决定了基因取 0 附近时的默认行为。
// ROBOT_DECODER = 3（仅本地研究版）：排序解码 + 容量预判。
//   解码到"新开机器人"、且当前有可用机器人时，先估计现有机器人在剩余时域内最多还能提供多少值岗时长：
//     · 每台机器人单独按"一就绪就出勤"推演（出勤—充电—维修周期全部取自它自己的工作流参数，拆卸取可带工具中最短的）
//     · 两次出勤之间的空档必须由别的机器人的值岗恰好填满，所以空档向上取到"各类型值岗时长的非负整数组合"中
//       不小于它的最小值（值岗都是 10 h 时就是取整到 10 的倍数）
//     这是一个上界：现有机器人的总上界都不够剩余时长，就一定还要新开；够了，新开就不是覆盖所必需的。
//   若 总上界 ≥ ρ × 剩余时长，则把"新开"改成复用（复用第 int(u·可用数) 台，u 为该基因在新开区间内的相对位置）。
//   ρ = 1 + CAP_RHO_SPAN × 裕度基因，裕度基因是编码末尾额外的一位（main_cli 在 Nvar 上 +2，末位不参与班次解码），
//   让每个个体自带"多大的富余才不新开"，前沿上资源多、均衡好的解仍然能被保留。CAP_RHO_SPAN=0 时 ρ 固定为 1。
#ifndef CAP_RHO_SPAN
#define CAP_RHO_SPAN 1.0
#endif
#if ROBOT_DECODER >= 3
static std::vector<char> g_rep;            // g_rep[t]=1：t 可以表示为各类型值岗时长的非负整数组合
static std::vector<int> g_rep_durs;
static double rep_ceil(double g)
{
    if (g <= 1e-9) return 0.0;
    if (g_rep_durs.empty())
    {
        for (int ty = 0; ty < task.objects_type["Robot"]; ++ty)
            if (properties.entity_limit["Robot"][ty] > 0)
                g_rep_durs.push_back((int)std::lround(properties.Get_property("Robot", ty, 1, "work_time")));
        g_rep.assign(1, 1);
    }
    int need = (int)std::ceil(g - 1e-9);
    while ((int)g_rep.size() <= need + 200)
    {
        int t = (int)g_rep.size();
        char ok = 0;
        for (int dd : g_rep_durs) if (dd > 0 && t >= dd && g_rep[t - dd]) { ok = 1; break; }
        g_rep.push_back(ok);
    }
    for (int t = need; ; ++t)
    {
        if (t >= (int)g_rep.size())
        {
            char ok = 0;
            for (int dd : g_rep_durs) if (dd > 0 && t >= dd && g_rep[t - dd]) { ok = 1; break; }
            g_rep.push_back(ok);
        }
        if (g_rep[t]) return (double)t;
    }
}
static double robot_capacity_hours(Entity& r, double E, double T)
{
    auto P = [&](const char* n) { return properties.Get_property(r.category, r.type, r.Serial_ID, n); };
    const double out = P("out_travel_time"), ret = P("return_travel_time"), d = P("work_time");
    const double ch = P("charge_time"), mt = P("maintenance_time"), single = P("single_work_time"), cmax = P("continue_max_work");
    double remmin = 1e18;
    for (double t : properties.Get_list_property(r.category, r.type, r.Serial_ID, "cargo_type_list"))
        if (properties.entity_limit["Tool"][(int)t] > 0)
            remmin = std::min(remmin, properties.Get_property("Tool", (int)t, 1, "removal_time"));
    if (remmin > 1e17) remmin = 0.0;
    double remain = r.Custom["remain_work_time"], hours = 0.0;
    double s = E + rep_ceil(r.Next_Ready_time + out - E);
    while (s < T)
    {
        hours += std::min(d, T - s);
        double end = s + d;
        remain -= single;
        double ready = end + ret + remmin;
        if (remain >= single) ready += ch; else { ready += mt; remain = cmax; }
        s = end + rep_ceil(ready + out - end);
    }
    return hours;
}
// 返回修正后的选择；n_avail==0 或解码为复用时原样返回
static int capacity_override(int select_robot, double x, double rho_gene, std::vector<std::string>& avail,
                             Entity_Set& Robots, double E, double T)
{
    const int n_avail = (int)avail.size();
    if (n_avail == 0 || select_robot < n_avail) return select_robot;
#ifdef FORCE_NEW_BAND
    {   // 实验0：新开区间内每个类型子区间的上 30% 为"强制新开"，不受容量预判改写（恢复被切掉的解的可达性）
        const double th0 = ROBOT_DECODER_THETA;
        const int nT = task.objects_type["Robot"];
        double u0 = (x - th0) / (1.0 - th0) * nT;
        int t0 = std::min(std::max((int)u0, 0), nT - 1);
        if (u0 - t0 > 0.7) return select_robot;
    }
#endif
    double cap = 0.0;
    for (const std::string& id : Robots.order_id) cap += robot_capacity_hours(Robots.Entity_Set[id], E, T);
    const double rho = 1.0 + CAP_RHO_SPAN * rho_gene;
    if (cap + 1e-9 < rho * (T - E)) return select_robot;
    const double th = ROBOT_DECODER_THETA;
    double u = (x - th) / (1.0 - th);
    int k = static_cast<int>(std::max(u, 0.0) * n_avail);
    g_roster_trace.cap_override++;
    return std::min(std::max(k, 0), n_avail - 1);
}
#endif
// ==================================================================================
std::vector<std::string> target_object_order;
double g_dev_density = -1.0;   // 实验3：--dev-density（解码 8 用；≤ 0 表示自适应）
double g_slot_frac = 0.25;   // 实验3：解码 6 的偏离槽数 K = max(4, ⌈g_slot_frac·Nmax⌉)，要求 ≤ 0.5
int g_slot_adapt = 0;         // 实验3：1 = 实际启用的槽数由末位基因决定：K_eff = max(1, ⌈K·x[末位]⌉)

double robot_arrangement(double *var, int num)
{
    double fitness=0.0;
    shift = 0;
    std::vector<int> robot_select_var;                            // **用于存放机器人解码之后的元素，考虑如何脱离场景;
    std::vector<int> tool_select_var;                             // **用于存放工具解码之后的元素，同上;

    double Empty_Time = 0;                                           // 表示当前时刻（以到达目的地为准，来进行推进）;                                               // 记录当前班次序号;
    std::vector<int> Res_Robot_Num(task.objects_type["Robot"]);   // 存放剩余机器人可用数量，所以一开始初始化变为各机器人的上限，索引为type-1;
    std::vector<int> Res_Tool_Num(task.objects_type["Tool"]);     // 存放工具可用数量，所以一开始初始化变为各工具的上限,索引为type-1;
    // Get_Res(Res_Robot_Num, Res_Tool_Num, properties);       // 获取各个类别类型的上限数量
    Res_Robot_Num = properties.entity_limit["Robot"];
    Res_Tool_Num = properties.entity_limit["Tool"];

    int Next_inListReady_Time = 0;                                // 剩余最少工作次数的机器人编号;
    int min_remain_num = 0, min_remain_index = 0;                 // 剩余最少得工作次数;
    int Cover_Time = task.task_duration;                          // 任务持续时间;

    std::vector<std::string> available_robot_list;                        // **可用机器人列表;
    std::vector<std::string> available_tool_list;                         // **可用工具列表;

    int i = 0;                                                    // 班次数量记录;

    Entity_Set Robots;                                   // **从这步就该是配置
    Entity_Set Tool;
    while (Empty_Time < Cover_Time && i < num / 2)
    {
        shift++;
        if(generation == MAXGEN)
            std::cout << "***********************************第" << shift << "班次*************************************" << std::endl
                      << std::endl;
        // 当前可用的机器人列表
        available_robot_list.clear();
        Get_available_Robot(Empty_Time, available_robot_list, Robots, properties, Workflows);
#if ROBOT_DECODER >= 2
        std::stable_sort(available_robot_list.begin(), available_robot_list.end(),
                         [&](const std::string& a, const std::string& b) {
                             Entity& ea = Robots.Entity_Set[a];
                             Entity& eb = Robots.Entity_Set[b];
#if ROBOT_DECODER == 4   // 维修相位排序：剩余工时少（离维修近）者优先，同剩余工时时出勤少者优先
                             if (ea.Custom["remain_work_time"] != eb.Custom["remain_work_time"])
                                 return ea.Custom["remain_work_time"] < eb.Custom["remain_work_time"];
                             return ea.States.size() < eb.States.size();
#else
                             if (ea.States.size() != eb.States.size()) return ea.States.size() < eb.States.size();
                             return ea.Custom["remain_work_time"] > eb.Custom["remain_work_time"];
#endif
                         });
#endif

        int select_robot = decode_robot_select(var[i], (int)available_robot_list.size(), task.objects_type["Robot"]);
#if ROBOT_DECODER >= 3
        select_robot = capacity_override(select_robot, var[i], var[num - 1], available_robot_list, Robots, Empty_Time, Cover_Time);
#endif
        robot_select_var.push_back(select_robot);
        if(generation == MAXGEN)
        {
            std::cout << "var[i]:" << var[i] << ", available_robot_list.size(): " << available_robot_list.size() << ", 机器人类型数量: " << task.objects_type["Robot"] << std::endl;
            std::cout << "第" << shift << "班次可用机器人列表:";
            for (std::string i : available_robot_list)
            {
                std::cout << i << ", ";
            }
           std::cout << std::endl;
        }
        if(select_robot < available_robot_list.size()) // 解码到可用列表内，不用新开机器人
        {
            
            // std::string the_ID = robot_select_strategy3(available_robot_list, Robots);
            std::string the_ID = available_robot_list[select_robot];
            if(generation == MAXGEN)
            {
                std::cout << "第" << shift << "班次派出机器人: " << the_ID << endl;
            }
            Entity &robot = Robots.Entity_Set[the_ID];

            if (!entity_workflow_process(robot,
                                         Workflows,
                                         properties,
                                         Tool,
                                         Empty_Time,
                                         Res_Tool_Num,
                                         available_tool_list,
                                         var,
                                         i,
                                         num,
                                         task))
                                         {
                                            if(generation == MAXGEN)
                                            {
                                                Count_Entity_Types(Robots, task);
                                                Count_Entity_Types(Tool, task);
                                                std::vector<Entity_Set> vector_entity_set;
                                                vector_entity_set.push_back(Robots);
                                                vector_entity_set.push_back(Tool);
                                                // Entity_Set2File(vector_entity_set, task);
                                            }
                                            // if(objects == "min_num"){
                                            //     // cout << "最少机器人数量" << endl;
                                            //     std::vector<Entity_Set> vector_entity_set;
                                            //     vector_entity_set.push_back(Robots);
                                            //     vector_entity_set.push_back(Tool);
                                            //     Entity_Set2File(vector_entity_set, task);
                                            //     return 30000;
                                            // }else{
                                            //     // cout << "最大均衡度" << endl;
                                            //     std::vector<Entity_Set> vector_entity_set;
                                            //     vector_entity_set.push_back(Robots);
                                            //     vector_entity_set.push_back(Tool);
                                            //     Entity_Set2File(vector_entity_set, task);
                                            //     return 30000;
                                            // }
                                            if (target_objects.count("min_num") > 0) {
                                                cout << "目标包含最少机器人数量，触发失败惩罚" << endl;
                                            } 
                                            if (target_objects.count("max_balance") > 0) {
                                                cout << "目标包含最大均衡度，触发失败惩罚" << endl;
                                            }
                                            std::vector<Entity_Set> vector_entity_set;
                                            vector_entity_set.push_back(Robots);
                                            vector_entity_set.push_back(Tool);
                                            Entity_Set2File(vector_entity_set, task);

                                            return 30000;
                                         }
                
        }
        else
        {
            robot_select_var[i] -= available_robot_list.size(); // 解码为类型的索引，下面的是存放各类型的数量上限
            // robot_select_var[i] = (var[i] - 1e-3) * task.objects_type["Robot"];
            ENTITY robot;
            bool non_avai_robot_flag = true;
            if(generation == MAXGEN)
                std::cout << "第" << shift << "班次,解码新增类型：" << robot_select_var[i] << std::endl;
            entity_remain(robot_select_var[i], task, Res_Robot_Num, non_avai_robot_flag);
            if (non_avai_robot_flag)
            {
                if(generation == MAXGEN)
                {
                    std::cout << "没有可用机器人了" << std::endl;
                    Count_Entity_Types(Robots, task);
                    Count_Entity_Types(Tool, task);
                }
                robot_select_var.clear();
                tool_select_var.clear();
                // if(objects == "min_num"){
                //     cout << "没有可用机器人min_num" << endl;
                //     std::vector<Entity_Set> vector_entity_set;
                //     vector_entity_set.push_back(Robots);
                //     vector_entity_set.push_back(Tool);
                //     Entity_Set2File(vector_entity_set, task);
                //     return 30000;
                // }
                // else
                // {
                //     cout << "没有可用机器人max_balance" << endl;
                //     std::vector<Entity_Set> vector_entity_set;
                //     vector_entity_set.push_back(Robots);
                //     vector_entity_set.push_back(Tool);
                //     Entity_Set2File(vector_entity_set, task);
                //     return 30000;
                // }
                // 打印提示信息（可选，用于调试）
                if (target_objects.count("min_num") > 0) {
                    cout << "目标包含最少机器人数量，触发失败惩罚" << endl;
                } 
                if (target_objects.count("max_balance") > 0) {
                    cout << "目标包含最大均衡度，触发失败惩罚" << endl;
                }
                std::vector<Entity_Set> vector_entity_set;
                vector_entity_set.push_back(Robots);
                vector_entity_set.push_back(Tool);
                Entity_Set2File(vector_entity_set, task);

                return 30000;
            }
            entity_create(robot, "Robot", robot_select_var[i], Res_Robot_Num, properties);
            if (!entity_workflow_process(robot,
                                         Workflows,
                                         properties,
                                         Tool,
                                         Empty_Time,
                                         Res_Tool_Num,
                                         available_tool_list,
                                         var,
                                         i,
                                         num,
                                         task))
                                         {
                                            if(generation == MAXGEN)
                                            {
                                                Count_Entity_Types(Robots, task);
                                                Count_Entity_Types(Tool, task);
                                                std::vector<Entity_Set> vector_entity_set;
                                                vector_entity_set.push_back(Robots);
                                                vector_entity_set.push_back(Tool);
                                                // Entity_Set2File(vector_entity_set, task);
                                            }
                                            // if(objects == "min_num"){
                                            //     // cout << "最少机器人数量" << endl;
                                            //     std::vector<Entity_Set> vector_entity_set;
                                            //     vector_entity_set.push_back(Robots);
                                            //     vector_entity_set.push_back(Tool);
                                            //     Entity_Set2File(vector_entity_set, task);
                                            //     return 30000; 
                                            // }else{
                                            //     // cout << "最大均衡度" << endl;
                                            //     std::vector<Entity_Set> vector_entity_set;
                                            //     vector_entity_set.push_back(Robots);
                                            //     vector_entity_set.push_back(Tool);
                                            //     Entity_Set2File(vector_entity_set, task);
                                            //     return 30000;
                                            // }
                                            if (target_objects.count("min_num") > 0) {
                                                cout << "目标包含最少机器人数量，触发失败惩罚" << endl;
                                            } 
                                            if (target_objects.count("max_balance") > 0) {
                                                cout << "目标包含最大均衡度，触发失败惩罚" << endl;
                                            }
                                            std::vector<Entity_Set> vector_entity_set;
                                            vector_entity_set.push_back(Robots);
                                            vector_entity_set.push_back(Tool);
                                            Entity_Set2File(vector_entity_set, task);

                                            return 30000;
                                         }
                
            Robots.Entity_Set[robot.ID] = robot;
            Robots.order_id.push_back(robot.ID);
        }
        i++;
    }
    // ===== 覆盖检查（2026-10-14 新增）=====
    // 班次循环在"基因用完"时也会结束；此时若值岗尚未覆盖完任务时长，方案不可行（原代码缺少这一步，
    // Nvar 偏小时会把没排满的方案当成可行解）
    if (Empty_Time < Cover_Time)
    {
        if (is_final_output)
            std::cout << "[覆盖检查] 编码长度不足：值岗只覆盖到 " << Empty_Time << " h，任务时长 " << Cover_Time << " h" << std::endl;
        return 30000;
    }
    // 返回所有robot和tool的流程结果
    // if(generation == MAXGEN)
    if (is_final_output)
    {
        Count_Entity_Types(Robots, task);
        Count_Entity_Types(Tool, task);
        std::vector<Entity_Set> vector_entity_set;
        vector_entity_set.push_back(Robots);
        vector_entity_set.push_back(Tool);
        Entity_Set2File(vector_entity_set, task);
    }
    // return Robots.Entity_Set.size();
    // return Robots.Entity_Set.size() + Tool.Entity_Set.size(); // 返回使用到的机器人和工具的数量
    if(target_objects.count("min_num") && target_objects["min_num"] > 0){
        fitness += (Robots.Entity_Set.size() + Tool.Entity_Set.size()) * target_objects["min_num"];
        cout << "最少机器人数量" << endl;
    }
    if (target_objects.count("max_balance") && target_objects["max_balance"] > 0){
        cout << "最大均衡度" << endl;
        // std::vector<double> repair_start_time;
        // for(const auto& pair:Robots.Entity_Set){
        //     const Entity &robot = pair.second;
        //     bool first_repair = false;
        //     for(const auto& state:robot.States){
        //         for(const auto&event:state.workflow_time){
        //             if(event.Process_Number == "8"){
        //                 repair_start_time.push_back(event.begin);
        //                 first_repair = true;
        //                 break;
        //             }
        //         }
        //         if(first_repair){
        //             break;
        //         }
        //     }
        // }
        // std::sort(repair_start_time.begin(), repair_start_time.end());
        // std::vector<double> intervals;
        // for (size_t k = 0; k < repair_start_time.size() - 1; ++k){
        //     intervals.push_back(repair_start_time[k + 1] - repair_start_time[k]);
        // }     
        // double sum_of_intervals = std::accumulate(intervals.begin(), intervals.end(), 0.0);
        // double avg_interval = sum_of_intervals / intervals.size();//平均间隔
        // double sum_sq_diff = 0.0;
        // for (double interval : intervals) {
        //     sum_sq_diff += std::pow(interval - avg_interval, 2);
        // }
        // fitness = std::sqrt(sum_sq_diff / intervals.size());
        std::vector<int> work_counts;          // 每个机器人工作次数
        std::vector<double> work_durations;    // 每个机器人总工作时长
        std::vector<double> repair_start_time; // 每个机器人第一次进入维修流程的时间

        for (const auto& pair : Robots.Entity_Set) {
            const Entity& robot = pair.second;
            int count = 0;
            double total_time = 0.0;
            bool first_repair_found = false;

            for (const auto& state : robot.States) {
                for (const auto& event : state.workflow_time) {
                    // 统计工作阶段（Process_Number == "3"）
                    if (event.Process_Number == "3") {
                        count++;
                        total_time += (event.end - event.begin);
                    }
                    // 记录第一次维修开始时间（Process_Number == "8"）
                    if (!first_repair_found && event.Process_Number == "8") {
                        repair_start_time.push_back(event.begin);
                        first_repair_found = true;
                    }
                }
            }

            work_counts.push_back(count);
            work_durations.push_back(total_time);

            // 如果该机器人从未维修，则可推入一个默认值（如 -1），后续处理
            if (!first_repair_found) {
                // 可选择：忽略、设为极大值、或用平均值填充
                // 这里我们暂不添加，只记录有维修行为的机器人
                // 注意：这会导致 repair_start_time.size() <= work_counts.size()
            }
        }

        // 标准差计算 Lambda（总体标准差）
        auto calc_std = [](const std::vector<double>& vec) -> double {
            size_t n = vec.size();
            if (n <= 1) return 0.0;

            double sum = std::accumulate(vec.begin(), vec.end(), 0.0);
            double mean = sum / static_cast<double>(n);

            double sq_diff_sum = 0.0;
            for (size_t i = 0; i < n; ++i) {
                double diff = vec[i] - mean;
                sq_diff_sum += (diff * diff);
            }
            return std::sqrt(sq_diff_sum / n);
        };

        // === 1. 工作次数均衡性 ===
        std::vector<double> work_counts_double;
        for (int cnt : work_counts) {
            work_counts_double.push_back(static_cast<double>(cnt));
        }
        double std_counts = calc_std(work_counts_double);

        // === 2. 工作时长均衡性 ===
        double std_durations = calc_std(work_durations);

        // === 3. 维修开始时间间隔的均匀性（关键新增项）===
        double std_repair_intervals = 0.0;

        if (repair_start_time.size() > 1) {
            // 排序以获取时间顺序
            std::vector<double> sorted_times = repair_start_time;
            std::sort(sorted_times.begin(), sorted_times.end());

            // 计算相邻维修开始时间的间隔
            std::vector<double> intervals;
            for (size_t i = 0; i < sorted_times.size() - 1; ++i) {
                intervals.push_back(sorted_times[i + 1] - sorted_times[i]);
            }

            // 计算这些时间间隔的方差 → 衡量“是否均匀发生维修”
            std_repair_intervals = calc_std(intervals);
        }
        // 若少于两个机器人维修，则视为无分布差异
        else {
            std_repair_intervals = 0.0;
        }

        // === 输出各项指标 ===
        // std::cout << "工作次数标准差: " << std_counts << std::endl;
        // std::cout << "工作时长标准差: " << std_durations << std::endl;
        // std::cout << "维修间隔标准差: " << std_repair_intervals << std::endl;

        // === 加权融合（权重可调）===
        double alpha = 0.3;   // 权重：工作次数均衡
        double beta  = 0.4;   // 权重：工作时长均衡
        double gamma = 0.3;   // 权重：维修分布均衡

        fitness += (alpha * std_counts +
                        beta  * std_durations +
                        gamma * std_repair_intervals) * target_objects["max_balance"];
    }
    return fitness;
}


#if ROBOT_DECODER >= 5
// ===================== ROBOT_DECODER = 5（仅本地研究版）：排序 + 容量预判 + 回溯修复 =====================
// 在解码 3（出勤少优先排序 + 容量预判，ρ=1）的基础上：某班出现"没有可用机器人"（只能新开）时，
// 先回到前 BT_WINDOW 班，依次尝试把其中一班改派成另一台可用机器人，其余基因不变地重新推进到该班；
// 若推进过程中没有新开机器人、且到该班时有了可用机器人，就采用这个改派（在必要处自动"偏离规则"），否则才新开。
// 依据：精确最优解基本就是"出勤最少优先"，只在少数关键班次偏离；整条照搬这个规则会因维修同步而断档、被迫新开。
#ifndef BT_WINDOW
#define BT_WINDOW 12
#endif
struct BtState {
    double E = 0;
    std::vector<int> resR, resT;
    Entity_Set R, T;
    std::vector<std::string> seq;
    std::vector<int> nav, act;   // 实验0：每班 (可用数, 实际动作)
};
static void bt_avail(BtState& s, std::vector<std::string>& av)
{
    av.clear();
    Get_available_Robot(s.E, av, s.R, properties, Workflows);
    std::stable_sort(av.begin(), av.end(), [&](const std::string& a, const std::string& b) {
        Entity& ea = s.R.Entity_Set[a];
        Entity& eb = s.R.Entity_Set[b];
        if (ea.States.size() != eb.States.size()) return ea.States.size() < eb.States.size();
        return ea.Custom["remain_work_time"] > eb.Custom["remain_work_time"];
    });
}
// 执行第 i 班；forced >= 0 表示复用可用列表中的第 forced 台。返回 0 = 复用，1 = 新开，-1 = 不可行
static int bt_step(BtState& s, int i, int forced, std::vector<double>& var, int Nvar)
{
    std::vector<std::string> av, tl;
    bt_avail(s, av);
    const int n = (int)av.size();
    int sel;
    if (forced >= 0) sel = forced;
    else
    {
        sel = decode_robot_select(var[i], n, task.objects_type["Robot"]);
        sel = capacity_override(sel, var[i], var[Nvar - 1], av, s.R, s.E, task.task_duration);
    }
    if (sel < n)
    {
        Entity& robot = s.R.Entity_Set[av[sel]];
        if (!entity_workflow_process(robot, Workflows, properties, s.T, s.E, s.resT, tl, var.data(), i, Nvar, task))
            return -1;
        s.seq.push_back(av[sel]);
        s.nav.push_back(n); s.act.push_back(sel);
        return 0;
    }
    int ty = sel - n;
    ENTITY robot;
    bool flag = true;
    entity_remain(ty, task, s.resR, flag);
    if (flag) return -1;
    entity_create(robot, "Robot", ty, s.resR, properties);
    if (!entity_workflow_process(robot, Workflows, properties, s.T, s.E, s.resT, tl, var.data(), i, Nvar, task))
        return -1;
    s.R.Entity_Set[robot.ID] = robot;
    s.R.order_id.push_back(robot.ID);
    s.seq.push_back(robot.ID);
    s.nav.push_back(n); s.act.push_back(n + ty);
    return 1;
}
static void roster_objectives(Entity_Set& Robots, Entity_Set& Tool, float* obj, int Nobj);
static void robot_arrangement_bt(float* x, float* obj, int Nvar, int Nobj)
{
    std::vector<double> var(Nvar, 0.0);
    for (int k = 0; k < Nvar; ++k) var[k] = static_cast<double>(x[k]);
    for (int k = 0; k < Nobj; ++k) obj[k] = 30000.0f;
    shift = 0;
    g_roster_trace.clear();
    const double T = task.task_duration;
    const int h = Nvar / 2;
    BtState s;
    s.resR = properties.entity_limit["Robot"];
    s.resT = properties.entity_limit["Tool"];
    std::vector<BtState> snaps;
    std::map<int, int> forced;
    auto fget = [&](int j) { auto it = forced.find(j); return it == forced.end() ? -1 : it->second; };
    int i = 0;
    while (s.E < T && i < h)
    {
        g_roster_trace.cur_shift = i;
        g_roster_trace.progress = s.E / T;
        snaps.resize(i);
        snaps.push_back(s);
        std::vector<std::string> av;
        bt_avail(s, av);
        if (av.empty() && !s.R.order_id.empty() && BT_WINDOW > 0)
        {
            int tfix = -1;
            for (int t = i - 1; t >= std::max(0, i - BT_WINDOW) && tfix < 0; --t)
            {
                std::vector<std::string> avt;
                bt_avail(snaps[t], avt);
                const int cur = fget(t);
                for (int alt = 0; alt < (int)avt.size(); ++alt)
                {
                    if (alt == cur) continue;
                    BtState trial = snaps[t];
                    bool ok = true;
                    for (int j = t; j < i; ++j)
                        if (bt_step(trial, j, j == t ? alt : -1, var, Nvar) != 0) { ok = false; break; }
                    if (ok)
                    {
                        std::vector<std::string> a2;
                        bt_avail(trial, a2);
                        ok = !a2.empty();
                    }
                    if (ok)
                    {
                        std::map<int, int> nf;
                        for (auto& kv : forced) if (kv.first < t) nf[kv.first] = kv.second;
                        nf[t] = alt;
                        forced.swap(nf);
                        tfix = t;
                        g_roster_trace.bt_fixes++;
                        break;
                    }
                }
            }
            if (tfix >= 0)
            {
                BtState s2 = snaps[tfix];
                snaps.resize(tfix);
                for (int j = tfix; j < i; ++j)
                {
                    snaps.push_back(s2);
                    bt_step(s2, j, fget(j), var, Nvar);
                }
                s = s2;
                snaps.push_back(s);
            }
        }
        if (bt_step(s, i, fget(i), var, Nvar) < 0)
            return;
        i++;
    }
    g_roster_trace.cur_shift = i;
    g_roster_trace.progress = s.E / T;
    for (auto& id : s.seq) g_roster_trace.robot_of_shift.push_back(g_roster_trace.index_of(id));
    if (s.E < T)
        return;
    g_roster_trace.feasible = true;
    g_roster_trace.act_nav = s.nav;
    g_roster_trace.act_sel = s.act;
    roster_objectives(s.R, s.T, obj, Nobj);
}
#endif

#if ROBOT_DECODER >= 6
// ===================== ROBOT_DECODER = 6（实验1，仅本地研究版）：规则 + 稀疏偏离编码 =====================
// 默认规则：每班复用"出勤最少（同则剩余工时多）"的可用机器人；没有可用机器人时先回溯修复（同解码 5），修复不了才新开，
// 新开类型由全局"默认类型基因"决定。基因只编码"在哪几班、怎么偏离规则"：
//   机器人半段：K = max(4, ⌈0.25·Nmax⌉) 个偏离槽 (p_k, a_k)，之后 1 个默认类型基因；其余位置不用。Nmax = Nvar/2 − 1。
//     a_k < 0.6 → 该槽不起作用；否则第 int(p_k·Nmax) 班偏离，u = (a_k − 0.6)/0.4：
//       u < 0.85 → 改派给排名第 2…n 的可用机器人（按 u 均分；可用数 < 2 时偏离作废）；
//       u ≥ 0.85 → 新开类型 int((u−0.85)/0.15·T)，受容量预判约束（现有机器人够覆盖剩余时长时偏离作废）。
//     同一班有多个槽时，编号大的槽生效。
//   工具半段：与原来相同。
// 与解码 5 的区别：偏离之后的班次按规则继续推进，不由逐班基因决定，改一个基因只改变一个决策。
#ifndef SDE_REUSE_SHARE
#define SDE_REUSE_SHARE 0.85   // 偏离取值中"改派"占的比例，其余为"新开"
#endif
#ifndef SDE_NEW_CAP
#define SDE_NEW_CAP 1          // 1 = 新开偏离受容量预判约束；0 = 新开偏离总是执行（让前沿能覆盖资源更多、均衡更好的解）
#endif
struct SdeCtx {
    std::map<int, double> dev;
    int tdef = 0;
};
static SdeCtx g_sde;
// 返回选择：< n 为复用下标，否则 n + 新开类型
static int sde_choose(BtState& s, int i, int n)
{
    const int nT = task.objects_type["Robot"];
    auto it = g_sde.dev.find(i);
    if (it != g_sde.dev.end())
    {
        const double u = it->second;
        const double rs = SDE_REUSE_SHARE;
        if (u < rs)
        {
            if (n >= 2) return 1 + std::min((int)(u / rs * (n - 1)), n - 2);
        }
        else
        {
            int ty = std::min((int)((u - rs) / (1.0 - rs) * nT), nT - 1);
            if (n == 0 || !SDE_NEW_CAP) return n + ty;
            double cap = 0.0;
            for (const std::string& id : s.R.order_id) cap += robot_capacity_hours(s.R.Entity_Set[id], s.E, task.task_duration);
            if (cap + 1e-9 < task.task_duration - s.E) return n + ty;
        }
    }
    if (n > 0) return 0;
    return n + g_sde.tdef;
}
static int sde_step(BtState& s, int i, int forced, std::vector<double>& var, int Nvar)
{
    std::vector<std::string> av, tl;
    bt_avail(s, av);
    const int n = (int)av.size();
    int sel = forced >= 0 ? forced : sde_choose(s, i, n);
    if (sel < n)
    {
        Entity& robot = s.R.Entity_Set[av[sel]];
        if (!entity_workflow_process(robot, Workflows, properties, s.T, s.E, s.resT, tl, var.data(), i, Nvar, task))
            return -1;
        s.seq.push_back(av[sel]);
        s.nav.push_back(n); s.act.push_back(sel);
        return 0;
    }
    int ty = sel - n;
    ENTITY robot;
    bool flag = true;
    entity_remain(ty, task, s.resR, flag);
    if (flag) return -1;
    entity_create(robot, "Robot", ty, s.resR, properties);
    if (!entity_workflow_process(robot, Workflows, properties, s.T, s.E, s.resT, tl, var.data(), i, Nvar, task))
        return -1;
    s.R.Entity_Set[robot.ID] = robot;
    s.R.order_id.push_back(robot.ID);
    s.seq.push_back(robot.ID);
    s.nav.push_back(n); s.act.push_back(n + ty);
    return 1;
}
static void robot_arrangement_sde(float* x, float* obj, int Nvar, int Nobj)
{
    std::vector<double> var(Nvar, 0.0);
    for (int k = 0; k < Nvar; ++k) var[k] = static_cast<double>(x[k]);
    for (int k = 0; k < Nobj; ++k) obj[k] = 30000.0f;
    shift = 0;
    g_roster_trace.clear();
    const double T = task.task_duration;
    const int h = Nvar / 2;
    const int nmax = h - 1;
    const int K = std::max(4, (int)std::ceil(g_slot_frac * nmax - 1e-9));
    const int Keff = g_slot_adapt ? std::max(1, (int)std::ceil(K * (double)x[Nvar - 1] - 1e-9)) : K;
    const int nT = task.objects_type["Robot"];
    g_sde.dev.clear();
    for (int k = 0; k < Keff && 2 * k + 1 < h; ++k)
    {
        const double p = var[2 * k], a = var[2 * k + 1];
        if (a >= 0.6) g_sde.dev[std::min((int)(p * nmax), nmax - 1)] = (a - 0.6) / 0.4;
    }
    g_sde.tdef = std::min((int)(var[2 * K] * nT), nT - 1);
    BtState s;
    s.resR = properties.entity_limit["Robot"];
    s.resT = properties.entity_limit["Tool"];
    std::vector<BtState> snaps;
    std::map<int, int> forced;
    auto fget = [&](int j) { auto it = forced.find(j); return it == forced.end() ? -1 : it->second; };
    int i = 0;
    while (s.E < T && i < h)
    {
        g_roster_trace.cur_shift = i;
        g_roster_trace.progress = s.E / T;
        snaps.resize(i);
        snaps.push_back(s);
        std::vector<std::string> av;
        bt_avail(s, av);
        if (av.empty() && !s.R.order_id.empty() && BT_WINDOW > 0 && g_sde.dev.find(i) == g_sde.dev.end())
        {
            int tfix = -1;
            for (int t = i - 1; t >= std::max(0, i - BT_WINDOW) && tfix < 0; --t)
            {
                std::vector<std::string> avt;
                bt_avail(snaps[t], avt);
                const int cur = fget(t);
                for (int alt = 0; alt < (int)avt.size(); ++alt)
                {
                    if (alt == cur) continue;
                    BtState trial = snaps[t];
                    bool ok = true;
                    for (int j = t; j < i; ++j)
                        if (sde_step(trial, j, j == t ? alt : -1, var, Nvar) != 0) { ok = false; break; }
                    if (ok)
                    {
                        std::vector<std::string> a2;
                        bt_avail(trial, a2);
                        ok = !a2.empty();
                    }
                    if (ok)
                    {
                        std::map<int, int> nf;
                        for (auto& kv : forced) if (kv.first < t) nf[kv.first] = kv.second;
                        nf[t] = alt;
                        forced.swap(nf);
                        tfix = t;
                        g_roster_trace.bt_fixes++;
                        break;
                    }
                }
            }
            if (tfix >= 0)
            {
                BtState s2 = snaps[tfix];
                snaps.resize(tfix);
                for (int j = tfix; j < i; ++j)
                {
                    snaps.push_back(s2);
                    sde_step(s2, j, fget(j), var, Nvar);
                }
                s = s2;
                snaps.push_back(s);
            }
        }
        if (sde_step(s, i, fget(i), var, Nvar) < 0)
            return;
        i++;
    }
    g_roster_trace.cur_shift = i;
    g_roster_trace.progress = s.E / T;
    for (auto& id : s.seq) g_roster_trace.robot_of_shift.push_back(g_roster_trace.index_of(id));
    if (s.E < T)
        return;
    g_roster_trace.feasible = true;
    roster_objectives(s.R, s.T, obj, Nobj);
}
#endif
#if ROBOT_DECODER >= 8
// ===================== ROBOT_DECODER = 8（实验3，仅本地研究版）：偏离密度编码 =====================
// 每班一个机器人基因 x[i]，τ = 1 − d：x[i] < τ 按规则（复用出勤最少的可用机器人；无可用时先回溯修复，修复不了才新开，
// 新开类型 = int(x[i]/τ·T)）；x[i] ≥ τ 偏离：u = (x[i] − τ)/d，u < 0.7 改派给排名第 2…n 的可用机器人（可用数 < 2 时按规则），
// u ≥ 0.7 新开类型 int((u−0.7)/0.3·T)（不受容量预判约束）。
// d 来自命令行 --dev-density（> 0 时固定），否则自适应：d = 0.02·30^x[末位]（0.02～0.6 对数均匀）。
static double g_dd = 0.1;
static int dd_choose(int i, int n, const std::vector<double>& var)
{
    const int nT = task.objects_type["Robot"];
    const double tau = 1.0 - g_dd;
    const double xi = var[i];
    if (xi >= tau)
    {
        const double u = (xi - tau) / g_dd;
        if (u < 0.7)
        {
            if (n >= 2) return 1 + std::min((int)(u / 0.7 * (n - 1)), n - 2);
        }
        else return n + std::min((int)((u - 0.7) / 0.3 * nT), nT - 1);
    }
    if (n > 0) return 0;
    return n + std::min((int)(std::min(xi, tau) / tau * nT), nT - 1);
}
static int dd_step(BtState& s, int i, int forced, std::vector<double>& var, int Nvar)
{
    std::vector<std::string> av, tl;
    bt_avail(s, av);
    const int n = (int)av.size();
    int sel = forced >= 0 ? forced : dd_choose(i, n, var);
    if (sel < n)
    {
        Entity& robot = s.R.Entity_Set[av[sel]];
        if (!entity_workflow_process(robot, Workflows, properties, s.T, s.E, s.resT, tl, var.data(), i, Nvar, task))
            return -1;
        s.seq.push_back(av[sel]);
        s.nav.push_back(n); s.act.push_back(sel);
        return 0;
    }
    int ty = sel - n;
    ENTITY robot;
    bool flag = true;
    entity_remain(ty, task, s.resR, flag);
    if (flag) return -1;
    entity_create(robot, "Robot", ty, s.resR, properties);
    if (!entity_workflow_process(robot, Workflows, properties, s.T, s.E, s.resT, tl, var.data(), i, Nvar, task))
        return -1;
    s.R.Entity_Set[robot.ID] = robot;
    s.R.order_id.push_back(robot.ID);
    s.seq.push_back(robot.ID);
    s.nav.push_back(n); s.act.push_back(n + ty);
    return 1;
}
static void robot_arrangement_dd(float* x, float* obj, int Nvar, int Nobj)
{
    std::vector<double> var(Nvar, 0.0);
    for (int k = 0; k < Nvar; ++k) var[k] = static_cast<double>(x[k]);
    for (int k = 0; k < Nobj; ++k) obj[k] = 30000.0f;
    shift = 0;
    g_roster_trace.clear();
    const double T = task.task_duration;
    const int h = Nvar / 2;
    g_dd = g_dev_density > 0 ? g_dev_density : 0.02 * std::pow(30.0, (double)x[Nvar - 1]);
    const double tau = 1.0 - g_dd;
    BtState s;
    s.resR = properties.entity_limit["Robot"];
    s.resT = properties.entity_limit["Tool"];
    std::vector<BtState> snaps;
    std::map<int, int> forced;
    auto fget = [&](int j) { auto it = forced.find(j); return it == forced.end() ? -1 : it->second; };
    int i = 0;
    while (s.E < T && i < h)
    {
        g_roster_trace.cur_shift = i;
        g_roster_trace.progress = s.E / T;
        snaps.resize(i);
        snaps.push_back(s);
        std::vector<std::string> av;
        bt_avail(s, av);
        if (av.empty() && !s.R.order_id.empty() && BT_WINDOW > 0 && var[i] < tau)
        {
            int tfix = -1;
            for (int t = i - 1; t >= std::max(0, i - BT_WINDOW) && tfix < 0; --t)
            {
                std::vector<std::string> avt;
                bt_avail(snaps[t], avt);
                const int cur = fget(t);
                for (int alt = 0; alt < (int)avt.size(); ++alt)
                {
                    if (alt == cur) continue;
                    BtState trial = snaps[t];
                    bool ok = true;
                    for (int j = t; j < i; ++j)
                        if (dd_step(trial, j, j == t ? alt : -1, var, Nvar) != 0) { ok = false; break; }
                    if (ok)
                    {
                        std::vector<std::string> a2;
                        bt_avail(trial, a2);
                        ok = !a2.empty();
                    }
                    if (ok)
                    {
                        std::map<int, int> nf;
                        for (auto& kv : forced) if (kv.first < t) nf[kv.first] = kv.second;
                        nf[t] = alt;
                        forced.swap(nf);
                        tfix = t;
                        g_roster_trace.bt_fixes++;
                        break;
                    }
                }
            }
            if (tfix >= 0)
            {
                BtState s2 = snaps[tfix];
                snaps.resize(tfix);
                for (int j = tfix; j < i; ++j)
                {
                    snaps.push_back(s2);
                    dd_step(s2, j, fget(j), var, Nvar);
                }
                s = s2;
                snaps.push_back(s);
            }
        }
        if (dd_step(s, i, fget(i), var, Nvar) < 0)
            return;
        i++;
    }
    g_roster_trace.cur_shift = i;
    g_roster_trace.progress = s.E / T;
    for (auto& id : s.seq) g_roster_trace.robot_of_shift.push_back(g_roster_trace.index_of(id));
    if (s.E < T)
        return;
    g_roster_trace.feasible = true;
    roster_objectives(s.R, s.T, obj, Nobj);
}
#endif

void robot_arrangement_moea(float* x, float* obj, int Nvar, int Nobj)
{
#if ROBOT_DECODER == 8
    robot_arrangement_dd(x, obj, Nvar, Nobj);
    return;
#elif ROBOT_DECODER == 7
    // 实验2：解码方式基因（末位，dec5/dec6 都不用这一位）：< 0.5 按解码 5（逐班基因 + 回溯修复），≥ 0.5 按解码 6（规则 + 稀疏偏离）
    if (x[Nvar - 1] < 0.5f) robot_arrangement_bt(x, obj, Nvar, Nobj);
    else robot_arrangement_sde(x, obj, Nvar, Nobj);
    return;
#elif ROBOT_DECODER == 6
    robot_arrangement_sde(x, obj, Nvar, Nobj);
    return;
#elif ROBOT_DECODER >= 5
    robot_arrangement_bt(x, obj, Nvar, Nobj);
    return;
#endif
    std::vector<double> var(Nvar, 0.0);
    for (int i = 0; i < Nvar; ++i) {
        var[i] = static_cast<double>(x[i]);
    }

    for (int i = 0; i < Nobj; ++i) {
        obj[i] = 30000.0f;
    }

    shift = 0;
    g_roster_trace.clear();
    std::vector<int> robot_select_var;
    std::vector<int> tool_select_var;

    double Empty_Time = 0;
    std::vector<int> Res_Robot_Num(task.objects_type["Robot"]);
    std::vector<int> Res_Tool_Num(task.objects_type["Tool"]);
    Res_Robot_Num = properties.entity_limit["Robot"];
    Res_Tool_Num = properties.entity_limit["Tool"];

    int Cover_Time = task.task_duration;
    std::vector<std::string> available_robot_list;
    std::vector<std::string> available_tool_list;
    int i = 0;

    Entity_Set Robots;
    Entity_Set Tool;
    while (Empty_Time < Cover_Time && i < Nvar / 2)
    {
        shift++;
        g_roster_trace.cur_shift = i;
        g_roster_trace.progress = Empty_Time / Cover_Time;
        if(generation == MAXGEN)
            std::cout << "***********************************第" << shift << "班次*************************************" << std::endl
                      << std::endl;

        available_robot_list.clear();
        Get_available_Robot(Empty_Time, available_robot_list, Robots, properties, Workflows);
#if ROBOT_DECODER >= 2
        std::stable_sort(available_robot_list.begin(), available_robot_list.end(),
                         [&](const std::string& a, const std::string& b) {
                             Entity& ea = Robots.Entity_Set[a];
                             Entity& eb = Robots.Entity_Set[b];
#if ROBOT_DECODER == 4   // 维修相位排序：剩余工时少（离维修近）者优先，同剩余工时时出勤少者优先
                             if (ea.Custom["remain_work_time"] != eb.Custom["remain_work_time"])
                                 return ea.Custom["remain_work_time"] < eb.Custom["remain_work_time"];
                             return ea.States.size() < eb.States.size();
#else
                             if (ea.States.size() != eb.States.size()) return ea.States.size() < eb.States.size();
                             return ea.Custom["remain_work_time"] > eb.Custom["remain_work_time"];
#endif
                         });
#endif

        int select_robot = decode_robot_select(var[i], (int)available_robot_list.size(), task.objects_type["Robot"]);
#if ROBOT_DECODER >= 3
        select_robot = capacity_override(select_robot, var[i], var[Nvar - 1], available_robot_list, Robots, Empty_Time, Cover_Time);
#endif
        g_roster_trace.n_avail.push_back((int)available_robot_list.size());
        robot_select_var.push_back(select_robot);
        if(generation == MAXGEN)
        {
            std::cout << "var[i]:" << var[i] << ", available_robot_list.size(): " << available_robot_list.size() << ", 机器人类型数量: " << task.objects_type["Robot"] << std::endl;
            std::cout << "第" << shift << "班次可用机器人列表:";
            for (std::string robot_id : available_robot_list)
            {
                std::cout << robot_id << ", ";
            }
           std::cout << std::endl;
        }

        if(select_robot < available_robot_list.size())
        {
            std::string the_ID = available_robot_list[select_robot];
            g_roster_trace.robot_of_shift.push_back(g_roster_trace.index_of(the_ID));
            if(generation == MAXGEN)
            {
                std::cout << "第" << shift << "班次派出机器人: " << the_ID << endl;
            }
            Entity &robot = Robots.Entity_Set[the_ID];

            if (!entity_workflow_process(robot,
                                         Workflows,
                                         properties,
                                         Tool,
                                         Empty_Time,
                                         Res_Tool_Num,
                                         available_tool_list,
                                         var.data(),
                                         i,
                                         Nvar,
                                         task))
            {
                if(generation == MAXGEN)
                {
                    Count_Entity_Types(Robots, task);
                    Count_Entity_Types(Tool, task);
                }
                return;
            }
        }
        else
        {
            robot_select_var[i] -= available_robot_list.size();
            ENTITY robot;
            bool non_avai_robot_flag = true;
            if(generation == MAXGEN)
                std::cout << "第" << shift << "班次,解码新增类型：" << robot_select_var[i] << std::endl;
            entity_remain(robot_select_var[i], task, Res_Robot_Num, non_avai_robot_flag);
            if (non_avai_robot_flag)
            {
                if(generation == MAXGEN)
                {
                    std::cout << "没有可用机器人了" << std::endl;
                    Count_Entity_Types(Robots, task);
                    Count_Entity_Types(Tool, task);
                }
                robot_select_var.clear();
                tool_select_var.clear();
                return;
            }
            entity_create(robot, "Robot", robot_select_var[i], Res_Robot_Num, properties);
            g_roster_trace.robot_of_shift.push_back(g_roster_trace.index_of(robot.ID));
            g_roster_trace.new_shift.push_back(i);
            if (!entity_workflow_process(robot,
                                         Workflows,
                                         properties,
                                         Tool,
                                         Empty_Time,
                                         Res_Tool_Num,
                                         available_tool_list,
                                         var.data(),
                                         i,
                                         Nvar,
                                         task))
            {
                if(generation == MAXGEN)
                {
                    Count_Entity_Types(Robots, task);
                    Count_Entity_Types(Tool, task);
                }
                return;
            }

            Robots.Entity_Set[robot.ID] = robot;
            Robots.order_id.push_back(robot.ID);
        }
        i++;
    }

    // ===== 覆盖检查（2026-10-14 新增）=====
    // 基因用完而值岗尚未覆盖完任务时长 → 不可行（obj 已在函数开头置为 30000）
    g_roster_trace.cur_shift = i;
    g_roster_trace.progress = Empty_Time / Cover_Time;
    if (Empty_Time < Cover_Time)
        return;
    g_roster_trace.feasible = true;

    double min_num_value = static_cast<double>(Robots.Entity_Set.size() + Tool.Entity_Set.size());
    double max_balance_value = 0.0;

    std::vector<int> work_counts;
    std::vector<double> work_durations;
    std::vector<double> repair_start_time;

    for (const auto& pair : Robots.Entity_Set) {
        const Entity& robot = pair.second;
        int count = 0;
        double total_time = 0.0;
        bool first_repair_found = false;

        for (const auto& state : robot.States) {
            for (const auto& event : state.workflow_time) {
                if (event.Process_Number == "3") {
                    count++;
                    total_time += (event.end - event.begin);
                }
                if (!first_repair_found && event.Process_Number == "8") {
                    repair_start_time.push_back(event.begin);
                    first_repair_found = true;
                }
            }
        }

        work_counts.push_back(count);
        work_durations.push_back(total_time);
    }

    auto calc_std = [](const std::vector<double>& vec) -> double {
        size_t n = vec.size();
        if (n <= 1) return 0.0;

        double sum = std::accumulate(vec.begin(), vec.end(), 0.0);
        double mean = sum / static_cast<double>(n);

        double sq_diff_sum = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double diff = vec[i] - mean;
            sq_diff_sum += (diff * diff);
        }
        return std::sqrt(sq_diff_sum / n);
    };

    std::vector<double> work_counts_double;
    for (int cnt : work_counts) {
        work_counts_double.push_back(static_cast<double>(cnt));
    }
    double std_counts = calc_std(work_counts_double);
    double std_durations = calc_std(work_durations);

    double std_repair_intervals = 0.0;
    if (repair_start_time.size() > 1) {
        std::vector<double> sorted_times = repair_start_time;
        std::sort(sorted_times.begin(), sorted_times.end());

        std::vector<double> intervals;
        for (size_t i = 0; i < sorted_times.size() - 1; ++i) {
            intervals.push_back(sorted_times[i + 1] - sorted_times[i]);
        }
        std_repair_intervals = calc_std(intervals);
    }

    double alpha = 0.3;
    double beta  = 0.4;
    double gamma = 0.3;
    max_balance_value = alpha * std_counts +
                        beta  * std_durations +
                        gamma * std_repair_intervals;

    std::vector<std::string> objective_order = target_object_order;
    if (objective_order.empty()) {
        for (const auto& item : target_objects) {
            objective_order.push_back(item.first);
        }
    }
    if (objective_order.empty()) {
        objective_order.push_back("min_num");
        objective_order.push_back("max_balance");
    }

    for (int k = 0; k < Nobj; ++k) {
        if (k >= static_cast<int>(objective_order.size())) {
            obj[k] = 30000.0f;
            continue;
        }

        const std::string& objective_name = objective_order[k];
        if (objective_name == "min_num") {
            obj[k] = static_cast<float>(min_num_value);
        } else if (objective_name == "max_balance") {
            obj[k] = static_cast<float>(max_balance_value);
        } else {
            obj[k] = 30000.0f;
        }
    }
}

#if ROBOT_DECODER >= 5
// 与 robot_arrangement_moea 末尾完全相同的目标值计算（复制，避免改动原路径）
static void roster_objectives(Entity_Set& Robots, Entity_Set& Tool, float* obj, int Nobj)
{
    double min_num_value = static_cast<double>(Robots.Entity_Set.size() + Tool.Entity_Set.size());
    double max_balance_value = 0.0;

    std::vector<int> work_counts;
    std::vector<double> work_durations;
    std::vector<double> repair_start_time;

    for (const auto& pair : Robots.Entity_Set) {
        const Entity& robot = pair.second;
        int count = 0;
        double total_time = 0.0;
        bool first_repair_found = false;

        for (const auto& state : robot.States) {
            for (const auto& event : state.workflow_time) {
                if (event.Process_Number == "3") {
                    count++;
                    total_time += (event.end - event.begin);
                }
                if (!first_repair_found && event.Process_Number == "8") {
                    repair_start_time.push_back(event.begin);
                    first_repair_found = true;
                }
            }
        }

        work_counts.push_back(count);
        work_durations.push_back(total_time);
    }

    auto calc_std = [](const std::vector<double>& vec) -> double {
        size_t n = vec.size();
        if (n <= 1) return 0.0;

        double sum = std::accumulate(vec.begin(), vec.end(), 0.0);
        double mean = sum / static_cast<double>(n);

        double sq_diff_sum = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double diff = vec[i] - mean;
            sq_diff_sum += (diff * diff);
        }
        return std::sqrt(sq_diff_sum / n);
    };

    std::vector<double> work_counts_double;
    for (int cnt : work_counts) {
        work_counts_double.push_back(static_cast<double>(cnt));
    }
    double std_counts = calc_std(work_counts_double);
    double std_durations = calc_std(work_durations);

    double std_repair_intervals = 0.0;
    if (repair_start_time.size() > 1) {
        std::vector<double> sorted_times = repair_start_time;
        std::sort(sorted_times.begin(), sorted_times.end());

        std::vector<double> intervals;
        for (size_t i = 0; i < sorted_times.size() - 1; ++i) {
            intervals.push_back(sorted_times[i + 1] - sorted_times[i]);
        }
        std_repair_intervals = calc_std(intervals);
    }

    double alpha = 0.3;
    double beta  = 0.4;
    double gamma = 0.3;
    max_balance_value = alpha * std_counts +
                        beta  * std_durations +
                        gamma * std_repair_intervals;

    std::vector<std::string> objective_order = target_object_order;
    if (objective_order.empty()) {
        for (const auto& item : target_objects) {
            objective_order.push_back(item.first);
        }
    }
    if (objective_order.empty()) {
        objective_order.push_back("min_num");
        objective_order.push_back("max_balance");
    }

    for (int k = 0; k < Nobj; ++k) {
        if (k >= static_cast<int>(objective_order.size())) {
            obj[k] = 30000.0f;
            continue;
        }

        const std::string& objective_name = objective_order[k];
        if (objective_name == "min_num") {
            obj[k] = static_cast<float>(min_num_value);
        } else if (objective_name == "max_balance") {
            obj[k] = static_cast<float>(max_balance_value);
        } else {
            obj[k] = 30000.0f;
        }
    }
}
#endif

// 获得各类别的数量上限
// void Get_Res(std::vector<int> & Res_Robot_Num,  std::vector<int> & Res_Tool_Num, Objects_Properties & properties)
// {
//     for (const auto & i : properties.Properties_Set)
//     {
//         if(i.first.first == "Robot")
//         {
//             Res_Robot_Num[i.first.second] = i.second.Properties.at("limit_num"); // 由于型号都是从1开始的，所以Res_Robot_Num存放的索引0对应1型号;
//         }
//         if(i.first.first == "Tool")
//         {
//             Res_Tool_Num[i.first.second] = i.second.Properties.at("limit_num");
//         }
//     }
// }
// 获得可用机器人序号列表
// 

void Get_available_Robot(int Empty_Time,
                         std::vector<std::string> &available_robot_list,
                         Entity_Set &Robots,
                         Objects_Properties &objects_properties,
                         Workflow_Set &workflow_set)
{
    available_robot_list.clear();
    available_robot_list.reserve(Robots.order_id.size());

    std::cout << "\n[DEBUG] >>> 开始筛选可出动机器人，目标对齐时间(上一机器人3节点结束) = " 
              << Empty_Time << std::endl;

    for (std::string j : Robots.order_id) {
        Entity &i = Robots.Entity_Set[j];
        auto &wf_nodes = objects_properties.Properties_Set[{i.category, i.type, i.Serial_ID}].WorkflowNodes;
        double path_dur = ComputePathDuration(wf_nodes, objects_properties, i, "0", "3");

        // 反推：若节点3应在 Empty_Time 对齐结束，则机器人应当在 (Empty_Time - path_dur) 启动
        double required_start = Empty_Time - path_dur;
        double single_out_time = objects_properties.Get_property(i.category, i.type, i.Serial_ID, "single_work_time");

        bool ready_ok = (Empty_Time == 0) ? (i.Next_Ready_time <= 0.0) : (i.Next_Ready_time <= (Empty_Time - path_dur) + 1e-9 );
        bool time_ok  = (i.Custom["remain_work_time"] >= single_out_time);

        if (ready_ok && time_ok) {
            available_robot_list.push_back(i.ID);
            if (generation == MAXGEN)
                std::cout << "[DEBUG] ✅ 可出动机器人: " << i.ID
                        << " | required_start=" << required_start
                        << " | path_dur=" << path_dur
                        << " | NextReady=" << i.Next_Ready_time
                        << " | remain=" << i.Custom["remain_work_time"]
                        << " | ready=" << ready_ok
                        << " | enough=" << time_ok << std::endl;
        }
    }

    if (available_robot_list.empty())
        std::cout << "[WARN] ❌ 当前无可出动机器人，请等待时间推进或维护完毕。" << std::endl;
    else
        std::cout << "[INFO] 共找到 " << available_robot_list.size() << " 台可出动机器人。" << std::endl;
}

// 
double ComputePathDuration(
    std::map<std::string, Workflow> &nodes,
    Objects_Properties &props,
    ENTITY &entity,
    const std::string &start,
    const std::string &end,
    std::unordered_set<std::string> visited
) {
    if (start == end) return 0.0;
    if (!nodes.count(start) || visited.count(start)) return 1e18;

    visited.insert(start);
    Workflow &wf = nodes.at(start);

    double self_dur = (wf.Workflow_Type == "Time") ? wf.Get_duration(entity, props) : 0.0;
    double best;

    // 【修正逻辑开始】
    if (wf.Workflow_Type == "Split" || wf.Workflow_Type == "Join") {
        best = 0.0;
        bool found_valid_path = false; // 标记是否找到了至少一条有效路径

        for (auto &succ : wf.successors) {
            double d = ComputePathDuration(nodes, props, entity, succ, end, visited);
            
            // 只有当路径是可达的（小于一个极大值阈值）才参与 max 计算
            if (d < 1e17) { 
                if (d > best) best = d;
                found_valid_path = true;
            }
        }

        // 如果所有分支都不可达，则认为该节点不可达
        if (!found_valid_path) {
            best = 1e18;
        }
    } 
    // 【修正逻辑结束】
    else {
        // 普通节点（Time, Decision等）取最小值（最短路径或唯一路径）
        best = 1e18;
        for (auto &succ : wf.successors) {
            double d = ComputePathDuration(nodes, props, entity, succ, end, visited);
            if (d < best) best = d;
        }
    }

    if (best >= 1e17) return 1e18; // 使用略小于 1e18 的阈值防止浮点误差
    return self_dur + best;
}

// 解码选择策略选择最早准备好的机器人执行任务
std::string robot_select_strategy3(std::vector<std::string> & available_robot_list, Entity_Set & Robots)
{
    std::string selectCarID;
    int earlist_readyTime = 1e6;
    for (std::string i : available_robot_list)
    {
        if(Robots.Entity_Set[i].Next_Ready_time < earlist_readyTime)
        {
            earlist_readyTime = Robots.Entity_Set[i].Next_Ready_time;
            selectCarID = i;
        }
    }
    return selectCarID;
}

// 利用DFS查询从out到work总共有路径可选
void dfs(const std::string& current, const std::string& target,
    std::map<std::string, Flow>& graph,
    std::vector<std::string>& path,
    std::vector<std::vector<std::string>>& all_paths,
    std::unordered_set<std::string>& visited) {

if (current == "-1") return; // 非法流程节点
if (visited.count(current)) return; // 避免环路

path.push_back(current);
visited.insert(current);

if (current == target) {
   all_paths.push_back(path);
} else if (graph.count(current)) { // 确保节点存在
   const Flow& node = graph[current];

   if (node.False_No == "-1") {
       // 非判断流程，直接走 True_No
       dfs(node.True_No, target, graph, path, all_paths, visited);
   } else {
       // 判断流程，两个方向都尝试
       dfs(node.True_No, target, graph, path, all_paths, visited);
       dfs(node.False_No, target, graph, path, all_paths, visited);
   }
}

visited.erase(current);
path.pop_back(); // 回溯
}

// 包装函数
std::vector<std::vector<std::string>> findAllPaths(const std::string& start, const std::string& target, std::map<std::string, Flow>& graph) 
{
    static std::unordered_map<std::string, std::vector<std::vector<std::string>>> path_cache;
    std::string cache_key = start + "_" + target;
    auto it = path_cache.find(cache_key);
    if(it != path_cache.end()) {
        return it->second;
    }
    
    std::vector<std::vector<std::string>> all_paths;
    std::vector<std::string> path;
    std::unordered_set<std::string> visited;
    dfs(start, target, graph, path, all_paths, visited);
    
    path_cache[cache_key] = all_paths;
    return all_paths;
}

// 流程处理
// void Workflow_Process(Entity & entity, Workflow_Set & Workflows, std::map<std::string, Flow> & workflow_temp, Objects_Properties & properties, double start_time, std::string start_flow_No, std::string end_flow_name) // 这里没有包含最后一个流程
// {
//     std::string next_flow = start_flow_No;
//     std::string flow_name = Workflows.Workflows[start_flow_No].Name;
//     while(flow_name != end_flow_name)
//     {
//         bool label_true = 0;
//         label_true = Workflows.Workflows[next_flow].Process(entity, properties, start_time);
//         start_time = entity.Temp_State.workflow_time.back().end;
//         if (label_true) // 根据类型和类别存储的流程顺序进行跳转
//         {
//             next_flow = workflow_temp[next_flow].True_No;
//             flow_name = Workflows.Workflows[next_flow].Name; // 更新流程名字
//         }
//         else
//         {
//             next_flow = workflow_temp[next_flow].False_No;
//             flow_name = Workflows.Workflows[next_flow].Name;
//         }
//     }
//     if(end_flow_name == "End")
//     {
//         entity.Next_Ready_time = entity.Temp_State.workflow_time.back().end;
//         // **需要进行更新操作
//     }
// }

// 

// double Workflow_Process(
//     ENTITY &entity,
//     std::map<std::string, Workflow> &nodes,
//     Objects_Properties &props,
//     double start_time)
// {
//     std::cout << "[DEBUG] 进入 Workflow_Process, 节点数=" << nodes.size() << " start_time=" << start_time << std::endl;
//     if (nodes.empty()) return start_time;

//     std::map<std::string, double> node_start;
//     std::map<std::string, int> ready_count;
//     std::queue<std::string> q;

//     // 1. 找到所有起始节点：Workflow_Type=="Start" 或 Predecessor_Count==0
//     for (auto &kv : nodes) {
//         if (kv.second.Workflow_Type=="Start" || kv.second.Predecessor_Count==0) {
//             q.push(kv.first);
//             node_start[kv.first] = start_time;
//         }
//     }

//     double global_end = start_time;
//     entity.Temp_State.workflow_time.clear();

//     while(!q.empty()) {
//         std::string id = q.front(); q.pop();
//         Workflow &wf = nodes.at(id);
//         double begin = node_start[id];
//         wf.Process(entity, props, begin);          // 这里内部会调用 Decision_Process 等
//         double endt = entity.Temp_State.workflow_time.back().end;
//         global_end  = std::max(global_end, endt);

//         if (wf.Workflow_Type == "End"){
//             entity.Next_Ready_time = entity.Temp_State.workflow_time.back().end;
//         }

//         if (wf.Workflow_Type == "Decision") {
//             // 由 Decision_Process 决定分支
//             bool result = wf.Decision_Process(entity, props, begin);
//             int idx = result ? 0 : 1;
//             if (idx < wf.successors.size()) {
//                 std::string nxt = wf.successors[idx];
//                 node_start[nxt] = endt;
//                 q.push(nxt);
//                 std::cout << "[DEBUG] Decision " << wf.Process_No 
//                   << " result=" << result 
//                   << " -> next=" << nxt << std::endl;
//             }
//         } 
//          if (wf.Workflow_Type == "Split") {
//             for (auto &succ : wf.successors) {
//                 if (!nodes.count(succ)) continue;
//                 node_start[succ] = std::max(node_start[succ], endt);
//                 q.push(succ);
//             }
//             continue;
//         }
//             // 普通节点
//         for (auto &succ : wf.successors) {
//             if (!nodes.count(succ))
//                 throw std::runtime_error(id + "节点无法到达" + succ);

//             Workflow &next = nodes.at(succ);
//             node_start[succ] = std::max(node_start[succ], endt);

//             if (next.Workflow_Type == "Join") {
//                 ready_count[succ]++;
//                 if (ready_count[succ] >= next.Predecessor_Count)
//                     q.push(succ);
//             } else {
//                 // ✅ 新增保护：如果该节点的所有前驱尚未全部完成，不入队
//                 if (++ready_count[succ] >= next.Predecessor_Count)
//                     q.push(succ);
//             }
//         }
//     }
//     if (generation == MAXGEN) {
//         std::cout << "\n[SUMMARY] " << entity.ID << " 流程时间表:" << std::endl;
//         for (auto &rec : entity.Temp_State.workflow_time) {
//             std::cout << "  节点 " << rec.Process_Number
//                     << " | 开始=" << rec.begin
//                     << " | 结束=" << rec.end
//                     << std::endl;
//         }
//     }
//     return global_end;
// }这一版是对的

double Workflow_Process(
    ENTITY &entity,
    std::map<std::string, Workflow> &nodes,
    Objects_Properties &props,
    double start_time)
{
    if (nodes.empty()) return start_time;

    std::map<std::string, double> node_start;
    std::map<std::string, int> ready_count;
    std::queue<std::string> q;

    for (auto &kv : nodes) {
        if (kv.second.Workflow_Type == "Start" || kv.second.Predecessor_Count == 0) {
            q.push(kv.first);
            node_start[kv.first] = start_time;
        }
    }

    double global_end = start_time;
    entity.Temp_State.workflow_time.clear();

    while(!q.empty()) {
        std::string id = q.front(); q.pop();
        Workflow &wf = nodes.at(id);
        double begin = node_start[id];

        // 修复1：利用 wf.Process 的返回值获取 Decision 结果，避免重复执行
        bool result = wf.Process(entity, props, begin); 
        double endt = entity.Temp_State.workflow_time.back().end;
        global_end  = std::max(global_end, endt);

        if (wf.Workflow_Type == "End"){
            entity.Next_Ready_time = endt;
            continue; // End 节点无后继，阻断向下执行
        }

        if (wf.Workflow_Type == "Decision") {
            int idx = result ? 0 : 1;
            if (idx < wf.successors.size()) {
                std::string nxt = wf.successors[idx];
                if (nodes.count(nxt)) {
                    node_start[nxt] = std::max(node_start[nxt], endt);
                    q.push(nxt);
                }
            }
            continue; // 修复2：加上 continue，防止掉入普通节点遍历导致的重复推入
        } 
        
        if (wf.Workflow_Type == "Split") {
            for (auto &succ : wf.successors) {
                if (!nodes.count(succ)) continue;
                node_start[succ] = std::max(node_start[succ], endt);
                q.push(succ);
            }
            continue;
        }
        
        // 普通节点处理 (包含 Join)
        for (auto &succ : wf.successors) {
            if (!nodes.count(succ)) continue;

            Workflow &next = nodes.at(succ);
            node_start[succ] = std::max(node_start[succ], endt);

            if (next.Workflow_Type == "Join") {
                // 并发汇聚点 (AND)：必须等待所有前驱都完成才能放行
                ready_count[succ]++;
                if (ready_count[succ] >= next.Predecessor_Count) {
                    q.push(succ);
                }
            } else {
                // 修复3：互斥汇聚点 (OR，如节点 4)：一经合法路径到达，立刻入队放行
                q.push(succ);
            }
        }
    }
    return global_end;
}

void entity_remain(int & select, Task & task, std::vector<int> Res_Num, bool & flag) // 查看解码是之后是否有资源剩余
{
    int k = 0;
    while(k < task.objects_type["Robot"])  // 机器人的类型数量
    {
        if(Res_Num[select] <= 0)
        {
            
            select = (select + 1) % task.objects_type["Robot"];
            if(generation == MAXGEN)
            std::cout << "类型用完了，现在新增机器人类型是：" << select << std::endl;
        }
        else
        {
            flag = false;
            break;
        }
        k++;
    }
}

void entity_create(ENTITY & entity, std::string  category, int type, std::vector<int> & Res_num, Objects_Properties & properties)
{
    if(generation == MAXGEN)
    {
        std::cout << "———创建实体————> 创建类别：" << category << ", 类型" << type << std::endl;
        std::cout << "剩余数量：" << Res_num[type] << std::endl;
    }
    Res_num[type]--;
    int ID = properties.entity_limit[category][type] - Res_num[type];
    entity.type = type;
    entity.category = category;
    entity.Serial_ID = ID;
    entity.Custom = properties.Get_Custom(category, type, ID);
    entity.ID = entity.category + "_" + std::to_string(entity.type) + "_" + std::to_string(ID);
    entity.First_Repair = false;
}

// 不包含头和尾
double Flow2flow(std::map<std::string, Flow> &workflow_temp, std::vector<std::vector<std::string>> &all_path, std::string start_No, std::string end_No, Objects_Properties &properties, Workflow_Set & Workflows, Entity & entity, int Empty_Time, std::string min_max)
{
    std::vector<double> time_record;
    all_path = findAllPaths(start_No, end_No, workflow_temp);
    int count = 0;
    for (std::vector<std::string> &i : all_path)
    {
        time_record.push_back(0);
        for (auto it = i.begin()+1; it != i.end() - 1; ++it)
        {
            std::string &j = *it;
            time_record[count] += Workflows.Workflows[j].Get_duration(entity,properties);
        }
        count++;
    }
    double min_time, max_time;
    for (int i = 0; i < time_record.size(); i++)
    {
        time_record[i] = Empty_Time - time_record[i];
    }
    if (!time_record.empty()) {
        min_time = *std::min_element(time_record.begin(), time_record.end()); // 安装完成的最早时间
        max_time = *std::max_element(time_record.begin(), time_record.end()); // 安装完成的最晚时间
    } else {
        return 0;
        std::cout << "time_record is empty!\n";
    }
    if(min_max == "min")
        return min_time;
    else if (min_max == "max")
    {
        return max_time;
    }
    else
    {
        std::cout << "输入最大值最小值模式错误，min or max。" << std::endl;
        return -1000;
    }
}

// void tool_select_list(std::vector<std::string> &available_tool_list, 
//     Entity_Set & Tool, 
//     Objects_Properties & properties, 
//     Entity & entity, 
//     double min_time, 
//     Workflow_Set & Workflows, 
//     int Empty_Time, 
//     Task &task)
// {
//     available_tool_list.clear();
//     available_tool_list.reserve(Tool.order_id.size()); // 预分配空间

//     // 缓存静态变量
//     static std::unordered_map<std::string, double> max_time_cache;
//     static std::mutex cache_mutex; // 多线程安全

//     // 预获取常用属性
//     const auto & right_type_list = properties.Get_list_property(entity.category, entity.type, entity.Serial_ID, "cargo_type_list");
//     Set_Entity_Timelist(entity, properties);
//     const double max_installation_time = entity.Temp_timelist[0];
//     const int tool_install_num = right_type_list.size();
//     const std::string install_type = task.installation_type;

//     for (const std::string& tool_id : Tool.order_id) 
//     {
//         Entity& tool = Tool.Entity_Set[tool_id];

//         // 检查工具类型是否匹配
//         auto right_type = std::find(right_type_list.begin(), right_type_list.end(), tool.type);
//         if (right_type == right_type_list.end()) 
//         {
//             continue;
//         }

//         // 计算或获取缓存的max_time
//         double max_time;
//         {
//             std::string cache_key = tool_id + "_" + std::to_string(Empty_Time);
//             std::lock_guard<std::mutex> lock(cache_mutex);
//             auto it = max_time_cache.find(cache_key);
//             if (it != max_time_cache.end()) 
//             {
//                 max_time = it->second;
//             } 
//             else 
//             {
//                 std::vector<std::vector<std::string>> all_path;
//                 std::map<std::string, Flow>& workflow_temp = 
//                 properties.Properties_Set[{tool.category, tool.type, tool.Serial_ID}].Workflows;
//                 max_time = Empty_Time - Flow2flow(workflow_temp, all_path, "0", "1", 
//                                             properties, Workflows, 
//                                             tool, Empty_Time, "min");
//                 max_time_cache[cache_key] = max_time;
//             }
//         }

//         // 根据安装类型判断
//         bool is_available = false;
//         if (install_type == "separate") 
//         {
//             if (generation == MAXGEN) 
//             {
//                 std::cout << "工具ID: " << tool.ID << "下次可用时间：" << tool.Next_Ready_time 
//                         << ", 判断时间：" << tool.Next_Ready_time + properties.Get_property(tool.category, tool.type, tool.Serial_ID, "install_time") 
//                         << ", min_time: " << min_time << std::endl;
//             }
//             is_available = (tool.Next_Ready_time + max_time + properties.Get_property(tool.category, tool.type, tool.Serial_ID, "install_time")) <= min_time;
//         } 
//         else if (install_type == "sequential")
//         {
//             int index = std::distance(right_type_list.begin(), right_type) + 1;
//             is_available = (tool.Next_Ready_time + max_time + properties.Get_property(tool.category, tool.type, tool.Serial_ID,"install_time")) <= (min_time - (tool_install_num - index) * max_installation_time);
//         } 
//         else
//         {
//             std::cout << "选择工具的安装类型未知类型" << std::endl;
//         }

//         if (is_available) 
//         {
//             available_tool_list.push_back(tool_id);
//         }
//     }

//     // 调试输出
//     if (generation == MAXGEN) 
//     {
//         std::cout << "可用工具列表";
//         for (const auto& id : available_tool_list) 
//         {
//             std::cout << id << ", ";
//         }
//         std::cout << std::endl;
//     }

// // 选择工具
//     const int carry_num = properties.Get_property(entity.category, entity.type, entity.Serial_ID, "carry_num");
//     for (auto it = available_tool_list.begin(); it != available_tool_list.end() && entity.Temp_State.tool_IDs.size() < carry_num; ) 
//     {
//         Entity& tool = Tool.Entity_Set[*it];
//         entity.Temp_State.tool_types.push_back(tool.type);
//         entity.Temp_State.tool_IDs.push_back(tool.ID);
//         it = available_tool_list.erase(it);
//     }
// }

void tool_select_list(std::vector<std::string> &available_tool_list, 
    Entity_Set & Tool, 
    Objects_Properties & objects_properties, 
    Entity & entity, 
    double min_time,                 // ← 这里的 min_time = 目标“安装节点1”的开始时间（或顺序排布后的该工具安装槽位时间）
    Workflow_Set & workflow_set, 
    int Empty_Time,                  // ← 仍保留参数，但在新版逻辑中不会再参与判断（避免首班次负数问题）
    Task &task)
{
    available_tool_list.clear();
    available_tool_list.reserve(Tool.order_id.size());

    // ========== 缓存 ==========
    // FIX: 缓存仅与工具自身相关，这里缓存 0->1 的路径耗时，不再掺入 Empty_Time
    static std::unordered_map<std::string, double> path01_cache;
    static std::mutex cache_mutex;

    // ========== 预取数据 ==========
    const auto & right_type_list = objects_properties.Get_list_property(entity.category, entity.type, entity.Serial_ID, "cargo_type_list");
    Set_Entity_Timelist(entity, objects_properties);

    double max_installation_time = 0.0;
    if (!entity.Temp_timelist.empty()) {
        max_installation_time = entity.Temp_timelist[0];
    } else {
        // 安全兜底，避免越界
        max_installation_time = objects_properties.Get_property(entity.category, entity.type, entity.Serial_ID, "work_time");
        if (generation == MAXGEN) {
            std::cout << "[WARN] entity.Temp_timelist 为空，使用 work_time 作为安装步长兜底: " 
                      << max_installation_time << std::endl;
        }
    }

    const int tool_install_num = (int)right_type_list.size();
    const std::string install_type = task.installation_type;

    // 我们先收集“候选工具 + 其最早可达安装点时间”，之后排序挑选
    struct Candidate {
        std::string id;
        double earliest_ready_at_install; // NextReady + path(0->1)
    };
    std::vector<Candidate> candidates;
    candidates.reserve(Tool.order_id.size());

    for (const std::string& tool_id : Tool.order_id) 
    {
        Entity& tool = Tool.Entity_Set[tool_id];

        // 1) 类型过滤：工具类型必须在机器人允许列表中
        auto it_type = std::find(right_type_list.begin(), right_type_list.end(), tool.type);
        if (it_type == right_type_list.end()) {
            continue;
        }

        // 2) 拿 0->1 路径耗时（缓存）
        double path_0_to_1 = 1e18;
        {
            std::lock_guard<std::mutex> lock(cache_mutex);
            auto it = path01_cache.find(tool_id);
            if (it != path01_cache.end()) {
                path_0_to_1 = it->second;
            } else {
                auto &tool_nodes = objects_properties.Properties_Set[{tool.category, tool.type, tool.Serial_ID}].WorkflowNodes;
                path_0_to_1 = ComputePathDuration(tool_nodes, objects_properties, tool, "0", "1");
                if (path_0_to_1 < 1e17) {
                    path01_cache[tool_id] = path_0_to_1;
                }
            }
        }
        if (path_0_to_1 >= 1e17) {
            std::cerr << "[ERROR] 工具 " << tool.ID << " 路径 0->1 不可达，跳过。\n";
            continue;
        }

        // 3) 计算“最早可达安装点时间”
        double earliest_ready_at_install = tool.Next_Ready_time + path_0_to_1;

        // 4) 目标安装时刻（根据安装顺序类型决定本工具的 deadline）
        double deadline = min_time; // separate: 全部与 min_time 同步； sequential: 有序偏移
        if (install_type == "sequential") {
            int index = (int)std::distance(right_type_list.begin(), it_type) + 1; // 1-based
            // 顺序安装：最后一个工具最接近 min_time，前面的要更早就绪
            deadline = min_time - (tool_install_num - index) * max_installation_time;
        } else if (install_type != "separate") {
            std::cout << "[WARN] 未知安装类型: " << install_type << "，按 separate 处理。\n";
        }

        // 5) 判定可用性：只要能在 deadline 前“到达安装点”即可（安装动作本身与机器人 1 同步开始）
        bool is_available = (earliest_ready_at_install <= deadline + 1e-9);

        if (generation == MAXGEN) {
            std::cout << "工具ID: " << tool.ID 
                      << " | NextReady=" << tool.Next_Ready_time
                      << " | path(0->1)=" << path_0_to_1
                      << " | earliest_ready_at_install=" << earliest_ready_at_install
                      << " | deadline=" << deadline
                      << " | 可用=" << (is_available ? "是" : "否")
                      << std::endl;
        }

        if (is_available) {
            candidates.push_back({tool_id, earliest_ready_at_install});
        }
    }

    // 6) 候选工具按“越早能到安装点越优先”排序
    std::sort(candidates.begin(), candidates.end(),
              [](const Candidate &a, const Candidate &b){
                  return a.earliest_ready_at_install < b.earliest_ready_at_install;
              });

    // 7) 选到机器人“可携带数量”个，并落盘到 entity.Temp_State
    const int carry_num = (int)objects_properties.Get_property(entity.category, entity.type, entity.Serial_ID, "carry_num");
    for (const auto &c : candidates) {
        if ((int)entity.Temp_State.tool_IDs.size() >= carry_num) break;
        Entity& tool = Tool.Entity_Set[c.id];
        entity.Temp_State.tool_types.push_back(tool.type);
        entity.Temp_State.tool_IDs.push_back(tool.ID);
        available_tool_list.push_back(tool.ID); // 同步输出可用列表（保留你的行为）
    }

    // 调试输出
    if (generation == MAXGEN) {
        std::cout << "可用工具列表";
        for (const auto& id : available_tool_list) std::cout << id << ", ";
        std::cout << std::endl;
    }
}

bool Add_tool(Entity & entity, Objects_Properties & properties, int select_tool, std::vector<int> & Res_Tool_Num, Entity_Set & Tool)
{
    
    while(entity.Temp_State.tool_IDs.size() <  properties.Get_property(entity.category, entity.type, entity.Serial_ID, "carry_num"))
    {
        Entity tool;
        bool non_avai_tool_flag = true;
        int indd = select_tool; //** 做了简化处理
        // std::cout << "indd: " << indd << std::endl;
        int tool_type;
        int k = 0;
        for (k = 0; k < properties.Get_property(entity.category, entity.type,entity.Serial_ID, "cargo_type_num"); k++, indd++)
        {
            if(indd >= properties.Get_property(entity.category, entity.type, entity.Serial_ID,"cargo_type_num") || indd <0)
                indd = 0;
            if(Res_Tool_Num[properties.Get_list_property(entity.category, entity.type, entity.Serial_ID,"cargo_type_list")[indd]] > 0)
            {
                non_avai_tool_flag = false;
                tool_type = properties.Get_list_property(entity.category, entity.type, entity.Serial_ID,"cargo_type_list")[indd]; // 这里拿到的是工具类型
                // std::cout << "properties[indd]: " << select_tool << ", entity.category, entity.type" << entity.category << ", " << entity.type << std::endl;
                if(generation == MAXGEN)
                    std::cout << "indd: " << indd << "选择新增的工具类型" << select_tool << std::endl;
                break;
            }
            
        }

    // 需要携带的工具都没有了，数量用完了
        if(non_avai_tool_flag && k>= properties.Get_property(entity.category, entity.type, entity.Serial_ID,"cargo_type_num"))
        {
            if(generation == MAXGEN)
                std::cout << "错误：新增工具数量不足，" << "ID:" <<entity.ID << std::endl;
            return false;
        }
        if(!non_avai_tool_flag)
        {
            entity_create(tool, "Tool", tool_type, Res_Tool_Num, properties);
            tool.States.clear();
            tool.Next_Ready_time = 0;
            Tool.Entity_Set[tool.ID] = tool;
            Tool.order_id.push_back(tool.ID);
            entity.Temp_State.tool_types.push_back(tool.type);
            entity.Temp_State.tool_IDs.push_back(tool.ID);
        }
        
    }
    if(generation == MAXGEN)
    {
        std::cout << "携带的工具编号为: ";
        for(std::string i : entity.Temp_State.tool_IDs)
        {
          std::cout  << i <<", ";
        }
        std::cout << "，tool_IDs个数为" << entity.Temp_State.tool_IDs.size() << std::endl;
    }
    return true;
}

void robot_time_list(Entity & entity, Entity_Set & Tool, Objects_Properties & properties)
{
    entity.Temp_timelist.clear();
    for (std::string &i : entity.Temp_State.tool_IDs)
    {
        std::string i_category = Tool.Entity_Set[i].category;
        int i_type = Tool.Entity_Set[i].type;
        int i_ID = Tool.Entity_Set[i].Serial_ID;
        double i_installation = properties.Get_property(i_category, i_type, i_ID, "install_time"); //** 修改为与安装流程的category一致
        entity.Temp_timelist.push_back(i_installation);
    }
}

// bool entity_workflow_process(Entity &entity,
//                              Workflow_Set &Workflows,
//                              Objects_Properties &props,
//                              Entity_Set &Tool,
//                              double &Empty_Time,
//                              std::vector<int> &Res_Tool_Num,
//                              std::vector<std::string> &available_tool_list,
//                              double *var,
//                              int i,
//                              int num,
//                              Task &task)
// {
//     auto &flow = props.Properties_Set.at({entity.category, entity.type, entity.Serial_ID}).WorkflowNodes;
//     if (flow.empty()) return false;

//     // 工具选择逻辑保持原样
//     int select_tool = (var[i + num / 2] - 1e-3) *
//                       props.Get_property(entity.category, entity.type, entity.Serial_ID,"cargo_type_num");
//     // if(!Add_tool(entity, props, select_tool, Res_Tool_Num, Tool)) return false;
//     // robot_time_list(entity, Tool, props);
//     if(!Add_tool(entity, props, select_tool, Res_Tool_Num, Tool)) return false;
//     for (auto &tid : entity.Temp_State.tool_IDs) {
//         Entity &carry_tool = Tool.Entity_Set[tid];
//         carry_tool.Temp_State.robot_ID = entity.ID;   // 关键赋值//修改痕迹
//     }

//     // ★ 使用并行执行
//     double robot_end = Workflow_Process(entity, flow, props, Empty_Time);
//     entity.States.push_back(entity.Temp_State);
//     //更新机器人状态
//     entity.Next_Ready_time = robot_end;
//     // 工具流程同样使用并行执行
//     Empty_Time = robot_end;
//     for (auto &tid : entity.Temp_State.tool_IDs) {
//         Entity &tool = Tool.Entity_Set[tid];
//         auto &tool_flow = props.Properties_Set.at({tool.category, tool.type, tool.Serial_ID}).WorkflowNodes;
//         double tool_start = robot_end; // 或更精确的开始时间
//         Workflow_Process(tool, tool_flow, props, tool_start);
//         tool.States.push_back(tool.Temp_State);
//         tool.Clear_TempState();
//     }

//     entity.Clear_TempState();
//     return true;
// }

bool entity_workflow_process(Entity &entity,
                             Workflow_Set &workflow_set,
                             Objects_Properties &objects_properties,
                             Entity_Set &Tool,
                             double &Empty_Time,
                             std::vector<int> &Res_Tool_Num,
                             std::vector<std::string> &available_tool_list,
                             double *var,
                             int i,
                             int num,
                             Task &task)
{
    std::cout << "\n[DEBUG] >>> 进入 entity_workflow_process(): " 
              << entity.ID << "，当前 Empty_Time=" << Empty_Time << std::endl;

    // ========== 1. 获取机器人工作流 ==========
    auto &wf_nodes = objects_properties.Properties_Set[{entity.category, entity.type, entity.Serial_ID}].WorkflowNodes;
    if (wf_nodes.empty()) {
        std::cerr << "[ERROR] Robot workflow is empty for " << entity.ID << std::endl;
        return false;
    }

    // ========== 2. 工具选择 ==========
    available_tool_list.clear();
    double path_1_to_3 = ComputePathDuration(wf_nodes, objects_properties, entity, "1", "3", {});
    double target_install_time = std::max(0.0, Empty_Time - path_1_to_3);

    // 把 target_install_time 传进去，而不是 Empty_Time
    tool_select_list(available_tool_list, Tool, objects_properties, entity, target_install_time, workflow_set, Empty_Time, task);
    // tool_select_list(available_tool_list, Tool, objects_properties, entity, Empty_Time, workflow_set, Empty_Time, task);

    int select_tool = (int)(var[i + num / 2] *
        (objects_properties.Get_property(entity.category, entity.type, entity.Serial_ID, "cargo_type_num") - 1));
    if (select_tool >= objects_properties.Get_property(entity.category, entity.type, entity.Serial_ID, "cargo_type_num"))
        select_tool = 0;

    if (!Add_tool(entity, objects_properties, select_tool, Res_Tool_Num, Tool)) {
        std::cerr << "[ERROR] 添加工具失败: " << entity.ID << std::endl;
        return false;
    }

    for (auto &tid : entity.Temp_State.tool_IDs)
        Tool.Entity_Set[tid].Temp_State.robot_ID = entity.ID;

    // ========== 3. 初始化时间数据 ==========
    robot_time_list(entity, Tool, objects_properties);

    // 计算 0->3 的最短路径（用于后续启动时间确定）
    double preheat_time = ComputePathDuration(wf_nodes, objects_properties, entity, "0", "3", {});
    if (preheat_time >= 1e17) {
        std::cerr << "[ERROR] Robot flow 0->3 不可达: " << entity.ID << std::endl;
        return false;
    }

    // 当前机器人启动时间（对齐上一个机器人3节点）
    double start_time = (Empty_Time == 0) ? 0 : std::max(0.0, Empty_Time - preheat_time);
    std::cout << "[DEBUG] 当前机器人启动时间: " << start_time << std::endl;

    // ========== 4. 执行机器人主流程 ==========
    Workflow_Process(entity, wf_nodes, objects_properties, start_time);

    // 找出节点3的时间范围
    double work3_begin = -1, work3_end = -1;
    double install_begin = -1, remove_begin = -1;
    for (auto &rec : entity.Temp_State.workflow_time) {
        if (rec.Process_Number == "1") install_begin = rec.begin; // 安装节点
        if (rec.Process_Number == "3") { work3_begin = rec.begin; work3_end = rec.end;};
        if (rec.Process_Number == "5") remove_begin = rec.begin; // 卸载节点
    }

    if (work3_begin < 0 || install_begin < 0) {
        std::cerr << "[ERROR] 未找到节点1或3（安装/工作）" << std::endl;
        return false;
    }

    // 时间平移：让节点3开始与 Empty_Time 对齐
    if (Empty_Time != 0) {
        double delta = Empty_Time - work3_begin;
        for (auto &rec : entity.Temp_State.workflow_time) {
            rec.begin += delta;
            rec.end += delta;
        }
        work3_begin += delta;
        work3_end += delta;
        install_begin += delta;
        remove_begin += delta;
    }
    Empty_Time = work3_end; // 更新为当前机器人3节点结束时间

    std::cout << "[DEBUG] 节点3已对齐: 3.begin=" << work3_begin 
              << "，3.end=" << work3_end << "，安装节点1.begin=" << install_begin << std::endl;

    // ========== 5. 工具流程：与机器人节点1对齐 ==========
    // for (auto &tid : entity.Temp_State.tool_IDs) {
    //     Entity &tool = Tool.Entity_Set[tid];
    //     auto &tool_nodes = objects_properties.Properties_Set[{tool.category, tool.type, tool.Serial_ID}].WorkflowNodes;

    //     double tool_start_time = install_begin; // 工具与机器人节点1对齐
    //     std::cout << "[DEBUG] 工具 " << tool.ID << " 与机器人节点1同步启动，时间 = " << tool_start_time << std::endl;

    //     tool.Temp_timelist = entity.Temp_timelist;
    //     Workflow_Process(tool, tool_nodes, objects_properties, tool_start_time);
    //     tool.Next_Ready_time = tool.Temp_State.workflow_time.back().end;

    //     tool.States.push_back(tool.Temp_State);
    //     Tool.Entity_Set[tool.ID] = tool;
    //     tool.Clear_TempState();
    // }
    // ========== 5. 工具流程：节点 1、3、5 分别与机器人对应节点对齐 ==========

    for (auto &tid : entity.Temp_State.tool_IDs) {
        Entity &tool = Tool.Entity_Set[tid];
        auto &tool_nodes =
            objects_properties.Properties_Set[{tool.category, tool.type, tool.Serial_ID}].WorkflowNodes;

        // 1. 先完整运行工具自己的 workflow
        Workflow_Process(tool, tool_nodes, objects_properties, 0.0);

        // 2. 找机器人安装节点时间
        double robot_install_begin = install_begin;

        // 3. 找工具安装节点时间
        double tool_install_begin = -1.0;
        for (const auto &rec : tool.Temp_State.workflow_time) {
            if (rec.Process_Number == "1") {
                tool_install_begin = rec.begin;
                break;
            }
        }

        if (tool_install_begin < 0) {
            std::cerr << "[ERROR] 工具 " << tool.ID << " 没有安装节点 1，无法和机器人对齐\n";
            continue;
        }

        // 4. 整体平移工具时间线，只让安装节点对齐
        double delta = robot_install_begin - tool_install_begin;

        for (auto &rec : tool.Temp_State.workflow_time) {
            rec.begin += delta;
            rec.end += delta;

            if (rec.end < rec.begin) {
                std::cerr << "[ERROR] 工具 " << tool.ID
                        << " 节点 " << rec.Process_Number
                        << " 时间非法: " << rec.begin << " -> " << rec.end << "\n";
            }
        }

        // 5. 工具下一次可用时间取完整 workflow 最后一个节点结束时间
        double tool_ready = 0.0;
        for (const auto &rec : tool.Temp_State.workflow_time) {
            tool_ready = std::max(tool_ready, rec.end);
        }

        tool.Next_Ready_time = tool_ready;
        tool.States.push_back(tool.Temp_State);
        Tool.Entity_Set[tool.ID] = tool;
        tool.Clear_TempState();
    // for (auto &tid : entity.Temp_State.tool_IDs) {
    //     Entity &tool = Tool.Entity_Set[tid];
    //     auto &tool_nodes = objects_properties.Properties_Set[{tool.category, tool.type, tool.Serial_ID}].WorkflowNodes;

    //     // 执行工具流程一次，拿到默认时长
    //     Workflow_Process(tool, tool_nodes, objects_properties, 0.0);

    //     // 获取各节点的原始持续时间
    //     double install_dur = 0, work_dur = 0, remove_dur = 0;
    //     for (auto &rec : tool.Temp_State.workflow_time) {
    //         if (rec.Process_Number == "1") install_dur = rec.end - rec.begin;
    //         if (rec.Process_Number == "3") work_dur    = rec.end - rec.begin;
    //         if (rec.Process_Number == "5") remove_dur  = rec.end - rec.begin;
    //     }

    //     // 清空重新写入
    //     tool.Temp_State.workflow_time.clear();

    //     // --- 节点 1：安装 ---
    //     if (install_begin >= 0) {
    //         Time_Record rec;
    //         rec.Process_Number = "1";
    //         rec.begin = install_begin;
    //         rec.end = install_begin + install_dur;
    //         tool.Temp_State.workflow_time.push_back(rec);
    //     }

    //     if (work3_begin >= 0) {
    //         Time_Record rec;
    //         rec.Process_Number = "3";
    //         rec.begin = work3_begin;
    //         rec.end = work3_begin + work_dur;
    //         tool.Temp_State.workflow_time.push_back(rec);
    //     }

    //     if (remove_begin >= 0) {
    //         Time_Record rec;
    //         rec.Process_Number = "5";
    //         rec.begin = remove_begin;
    //         rec.end = remove_begin + remove_dur;
    //         tool.Temp_State.workflow_time.push_back(rec);
    //     }


    //     // 工具的 Next_Ready_time = 拆卸节点结束时间
    //     tool.Next_Ready_time = remove_begin + remove_dur;

    //     tool.States.push_back(tool.Temp_State);
    //     Tool.Entity_Set[tool.ID] = tool;
    //     tool.Clear_TempState();
    }
    // 遍历每一个携带的工具
    // for (auto &tid : entity.Temp_State.tool_IDs) {
    //     Entity &tool = Tool.Entity_Set[tid];
    //     auto &tool_nodes = objects_properties.Properties_Set[{tool.category, tool.type, tool.Serial_ID}].WorkflowNodes;

    //     // 1. 预执行一次工具流程，主要为了获取默认的各阶段时长（特别是安装和拆卸）
    //     Workflow_Process(tool, tool_nodes, objects_properties, 0.0);

    //     double install_dur = 0, remove_dur = 0;
    //     // 注意：这里我们只取安装和拆卸的时长，中间的工作/路程时长直接跟随机器人
    //     for (auto &rec : tool.Temp_State.workflow_time) {
    //         if (rec.Process_Number == "1") install_dur = rec.end - rec.begin;
    //         if (rec.Process_Number == "5") remove_dur  = rec.end - rec.begin;
    //     }

    //     // 2. 清空工具的临时时间表，准备根据机器人重写
    //     tool.Temp_State.workflow_time.clear();

    //     // --- 节点 1：安装 (跟机器人对齐开始，时长用工具自己的) ---
    //     if (install_begin >= 0) {
    //         Time_Record rec;
    //         rec.Process_Number = "1";
    //         rec.begin = install_begin;
    //         rec.end = install_begin + install_dur; 
    //         tool.Temp_State.workflow_time.push_back(rec);
    //     }

    //     // --- 节点 12：工具去程 (填补安装后、工作前的空白) ---
    //     // 逻辑：如果机器人有路程(2)，工具就生成(12)
    //     // 你的属性里有 out_travel_time = 1，所以这里必须补上
    //     double robot_travel_out_begin = install_begin + install_dur; // 假设紧接着安装
    //     // 或者更准确地，遍历机器人时间表找到节点 "2" 的起止时间：
    //     // (由于你在前面的代码里可能没把 robot_travel_out_begin 存下来，这里建议简单处理：)
    //     // 工具去程的开始 = 安装结束；工具去程的结束 = 工作开始。
    //     if (work3_begin > (install_begin + install_dur)) {
    //          Time_Record rec;
    //          rec.Process_Number = "12"; // 工具去程
    //          rec.begin = install_begin + install_dur;
    //          rec.end = work3_begin;     // 填满直到工作开始
    //          tool.Temp_State.workflow_time.push_back(rec);
    //     }

    //     // --- 节点 13：工具工作 (核心修正：ID改 13，时间完全跟随机器人) ---
    //     if (work3_begin >= 0) {
    //         Time_Record rec;
    //         rec.Process_Number = "13"; // 【修正】这里是13，不是3
    //         rec.begin = work3_begin;
    //         rec.end = work3_end;       // 【修正】强制对齐机器人的结束时间，物理绑定
    //         tool.Temp_State.workflow_time.push_back(rec);
    //     }

    //     // --- 节点 14：工具返程 (填补工作后、拆卸前的空白) ---
    //     if (remove_begin > work3_end) {
    //          Time_Record rec;
    //          rec.Process_Number = "14"; // 工具返程
    //          rec.begin = work3_end;
    //          rec.end = remove_begin;    // 填满直到拆卸开始
    //          tool.Temp_State.workflow_time.push_back(rec);
    //     }

    //     // --- 节点 5：拆卸 ---
    //     if (remove_begin >= 0) {
    //         Time_Record rec;
    //         rec.Process_Number = "5";
    //         rec.begin = remove_begin;
    //         rec.end = remove_begin + remove_dur;
    //         tool.Temp_State.workflow_time.push_back(rec);
    //     }

    //     // 更新工具状态
    //     tool.Next_Ready_time = remove_begin + remove_dur;
    //     tool.States.push_back(tool.Temp_State);
    //     Tool.Entity_Set[tool.ID] = tool;
    //     tool.Clear_TempState();
    // }


        // ========== 6. 更新机器人状态 ==========
        entity.Next_Ready_time = entity.Temp_State.workflow_time.back().end;
        entity.States.push_back(entity.Temp_State);
        entity.Clear_TempState();

        std::cout << "[DEBUG] <<< 退出 entity_workflow_process(): " << entity.ID
                << "，更新后 Empty_Time=" << Empty_Time << "\n" << std::endl;

        return true;
}

// bool entity_workflow_process(Entity &entity,
//                              Workflow_Set &Workflows,
//                              Objects_Properties &properties,
//                              Entity_Set &Tool,
//                              double &Empty_Time,
//                              std::vector<int> &Res_Tool_Num,
//                              std::vector<std::string> &available_tool_list,
//                              double *var,
//                              int i,
//                              int num,
//                              Task &task)
// {
//     std::vector<std::vector<std::string>> all_path; // 安装流程和工作流程这两个点是固定的。名称和编号是固定的
//     std::map<std::string, Flow> & workflow_temp = properties.Properties_Set[{entity.category, entity.type, entity.Serial_ID}].Workflows;
//     double min_time = Flow2flow(workflow_temp, all_path, "1", "3", properties, Workflows, entity, Empty_Time, "min"); // 安装完工具的最早时间点
//     available_tool_list.clear();
//     tool_select_list(available_tool_list, Tool, properties, entity, min_time, Workflows, Empty_Time, task);
    
    // int select_tool  = var[i + num / 2] * (properties.Get_property(entity.category, entity.type, entity.Serial_ID, "cargo_type_num") - 1); // 解码为工具类型在携带工具类型列表的位置
//     if(generation == MAXGEN)
//         std::cout << "var[i + num / 2]: " << var[i + num / 2] << ", 工具解码到机器人可携带位置为: " << select_tool << std::endl;
//     if (select_tool >= properties.Get_property(entity.category, entity.type, entity.Serial_ID,"cargo_type_num"))
//     {
//         // std::vector<double> tool_type_list = properties.Get_list_property(entity.category, entity.type, "cargo_type_list");
//         // // 定义随机数生成器
//         // std::random_device rd;
//         // std::mt19937 gen(rd());
//         // std::uniform_int_distribution<> distrib(0, tool_type_list.size() - 1);

//         // if (!tool_type_list.empty()) {
//         //     int random_index = distrib(gen);
//         //     select_tool = tool_type_list[random_index];
//         // } else {
//         //     select_tool = 0;
//         // }
//         select_tool = 0;
//     }
//     if(!Add_tool(entity, properties, select_tool, Res_Tool_Num, Tool))
//     {
//         cout << "添加工具失败" << endl;
//         return false;
//     }
//     robot_time_list(entity, Tool, properties);
//     Workflow_Process(entity, Workflows, workflow_temp, properties, 0, "0","Work");

//     // 进行时间更正
//     int work_before_end = entity.Temp_State.workflow_time.back().end;
//     // if(work_before_end > Empty_Time)
//     //     std::cout << "求解失败" << std::endl;
//     int difference_value = Empty_Time - work_before_end;
//     for(Time_Record & i : entity.Temp_State.workflow_time)
//     {
//         i.begin = i.begin + difference_value;
//         i.end = i.end + difference_value; 
//     }
//     double time = entity.Temp_State.workflow_time.back().end;
//     Workflow_Process(entity, Workflows, workflow_temp, properties, entity.Temp_State.workflow_time.back().end, "3", "End");
//     entity.States.push_back(entity.Temp_State);
//     if(generation == MAXGEN)
//     {
//         Print_Temp_State(entity, Workflows);
//     }
//     // std::cout << entity.ID << ", 剩余工作时间: " << entity.Custom["remain_work_time"] << std::endl;
//     // 接下来是tool的流程处理** 这里应该统一起来，针对不同的类型的实体流程处理应该是统一的模式
//     // 获得该机器人携带工具的ID列表
//     if(generation == MAXGEN)
//     {
//         print_carry_entity(entity);
//     }   
    

//     std::vector<std::string> robot_tool = entity.Temp_State.tool_IDs;
//     Empty_Time += properties.Get_property(entity.category, entity.type, entity.Serial_ID,"work_time");
//     for(std::string & i : robot_tool)
//     {
//         Entity &carry_tool = Tool.Entity_Set[i];
//         carry_tool.Temp_State.robot_ID = entity.ID;
//         carry_tool.Temp_timelist.push_back(properties.Get_property(entity.category, entity.type, entity.Serial_ID,"work_time"));
//         std::map<std::string, Flow> & tool_workflow_temp = properties.Properties_Set[{carry_tool.category, carry_tool.type, carry_tool.Serial_ID}].Workflows;
//         std::string tool_next_flow = tool_workflow_temp["0"].True_No; // **开始时间点确定
//         std::string tool_flow_name = Workflows.Workflows[tool_next_flow].Name;

//         Time_Record tool_start = entity.Get_flow_time(tool_next_flow);
//         double tool_start_time = tool_start.begin;
//         // 需要跟新i的time_list供工具安装和拆卸。
//         carry_tool.Temp_timelist = entity.Temp_timelist;
//         Workflow_Process(carry_tool, Workflows, tool_workflow_temp, properties, tool_start_time, "0", "End");
//         Tool.Entity_Set[carry_tool.ID] = carry_tool;
//         carry_tool.States.push_back(carry_tool.Temp_State);
//         if(generation == MAXGEN)
//         {
//             Print_Temp_State(carry_tool, Workflows);
//         }
//         carry_tool.Clear_TempState();
//     }
//     entity.Clear_TempState();
//     return true;
// }

// 打印携带的工具
void print_carry_entity(Entity & entity)
{
    if(entity.Temp_State.tool_IDs.size() != 0)
    {
        std::cout << "携带的工具: "; 
        for (std::string i : entity.Temp_State.tool_IDs)
        {
            std::cout << i << ", ";
        }
        std::cout << std::endl;
    }
}
void Print_Temp_State(Entity & entity, Workflow_Set & Workflows)
{
    
    for (const Time_Record &i : entity.Temp_State.workflow_time)
    {
        std::string Process_No = i.Process_Number;
        std::string Process_Name = Workflows.Workflows[Process_No].Name;
        std::cout << entity.ID << "————" << "流程名称：" << Process_Name << ", 流程编号：" << Process_No << ", 开始时间：" << i.begin << ", 结束时间：" << i.end << std::endl;
    }
    std::cout << std::endl;
}
void Count_Entity_Types(const Entity_Set& entity_set, Task& task) 
{
    std::map<std::string, std::map<std::string, int>> counter;

    for (const auto& it : entity_set.Entity_Set)
    {
        counter[it.second.category][std::to_string(it.second.type)]++;
    }

    std::cout << "===== 实体分类统计 =====" << std::endl;

    for (const auto& cat_pair : counter)
    {
        const std::string& category = cat_pair.first;
        for (const auto& type_pair : cat_pair.second)
        {
            const std::string& type = type_pair.first;
            int count = type_pair.second;

            std::string key = category + "-" + type;
            task.information_print[key] = count;

            // 直接在这里打印统计数量
            std::cout << "类别: " << category 
                      << " 型号: " << type 
                      << " 数量: " << count << std::endl;
        }
    }

    std::cout << "=======================" << std::endl;
}
// 选择带入的是最小安装时间
void Set_Entity_Timelist(Entity & entity, Objects_Properties & properties)
{
    entity.Temp_timelist.clear();
    std::vector<double> list_type = properties.Get_list_property(entity.category, entity.type, entity.Serial_ID,"cargo_type_list");
    double install_max_time = -1;
    double install_min_time = 1e4;
    for (int i : list_type)
    {
        double i_time;
        int num = properties.entity_limit["Tool"][i];
        for (int j = 0; j < num;j++)
        {
            i_time = properties.Get_property("Tool", i, j+1,"install_time");
            if(i_time > install_max_time)
                install_max_time = i_time;
            if(i_time < install_min_time)
                install_min_time = i_time;
        }  
    }
    double carry_num = properties.Get_property(entity.category, entity.type, entity.Serial_ID,"carry_num");
    for (int i = 0; i < carry_num; i++)
    {
        // entity.Temp_timelist.push_back(install_max_time);
        entity.Temp_timelist.push_back(install_min_time);
    }
}

// bool Entity_Set2File(std::vector<Entity_Set> & vector_entity_set, Task & task)
// {
//     std::string file_name = "../Res/result.json";
//     json file;
//     json entity_workflow;
//     std::vector<json> entity_workflow_set;
//     for (Entity_Set &i : vector_entity_set)
//     {
//         for (auto j = i.Entity_Set.begin(); j != i.Entity_Set.end(); j++)
//         {
//             std::string category = j->second.category;
//             std::string ID = j->second.ID;
//             for (auto k = j->second.States.begin(); k != j->second.States.end(); k++)
//             {
//                 for (auto m = k->workflow_time.begin(); m != k->workflow_time.end(); m++)
//                 {
//                     entity_workflow.clear();
//                     entity_workflow.push_back(m->begin);
//                     entity_workflow.push_back(m->end);
//                     entity_workflow.push_back(m->Process_Number);
//                     entity_workflow_set.push_back(entity_workflow);
//                 }
                
//             }
//             file[category][ID] = entity_workflow_set;
//             entity_workflow_set.clear();
//         }
//     }
//     // 写入到文件
//     std::ofstream file_json(file_name);
//     if(file_json.is_open())
//     {
//         file_json << file.dump(4); // 控制缩进 4 空格
//         file_json.close();
//         std::cout << "结果JSON文件写入完成！" << std::endl;
//         return true;
//     }
//     else
//     {
//         std::cerr << "文件无法打开" << std::endl;
//         return false;
//     }
// }

// 确保头文件中有这句声明，或者直接在 problem.cpp 顶部添加

bool Entity_Set2File(std::vector<Entity_Set> & vector_entity_set, Task & task)
{
    cout << "写入result" << endl;
    // std::string file_name = "../Res/result.json";
    const std::filesystem::path output_dir = (std::getenv("PAIBAN_RES_DIR") ? std::getenv("PAIBAN_RES_DIR") : "./Res");  // 本地版：可用环境变量指定
    std::error_code ec;
    std::filesystem::create_directories(output_dir, ec);
    if (ec) {
        std::cerr << "结果目录创建失败: " << output_dir
                  << ", reason: " << ec.message() << std::endl;
        return false;
    }
    const std::filesystem::path file_name = output_dir / "result.json";

    // 1. 创建最终要写入文件的总JSON对象
    json final_json;
    
    // 2. 创建用于存放甘特图数据的JSON对象 (将被嵌套)
    json gantt_data;
    
    // --- 这部分是您原有的逻辑，但写入目标是 gantt_data ---
    json entity_workflow;
    std::vector<json> entity_workflow_set;
    for (Entity_Set &i : vector_entity_set)
    {
        for (auto j = i.Entity_Set.begin(); j != i.Entity_Set.end(); j++)
        {
            std::string category = j->second.category;
            std::string ID = j->second.ID;
            for (auto k = j->second.States.begin(); k != j->second.States.end(); k++)
            {
                for (auto m = k->workflow_time.begin(); m != k->workflow_time.end(); m++)
                {
                    entity_workflow.clear();
                    entity_workflow.push_back(m->begin);
                    entity_workflow.push_back(m->end);
                    entity_workflow.push_back(m->Process_Number);
                    entity_workflow_set.push_back(entity_workflow);
                }
            }
            gantt_data[category][ID] = entity_workflow_set;
            entity_workflow_set.clear();
        }
    }
    
    // 3. (新增) 创建图例(legend)的JSON对象
    json legend;
    // 从全局的 Workflows 对象中遍历所有已知的流程
    for (const auto& pair : Workflows.Workflows) {
        // pair.first 是流程编号(string), pair.second.Name 是流程名称(string)
        legend[pair.first] = pair.second.Name;
    }
    
    // 4. (新增) 组装最终的JSON结构
    final_json["xAxisLabel"] = "时间";
    final_json["yAxisLabel"] = "实体ID";
    final_json["legend"] = legend;
    final_json["ganttData"] = gantt_data; // 将原始数据嵌套进去

    std::ifstream old_result_file(file_name);
    if (old_result_file.is_open()) {
        try {
            json old_result_json;
            old_result_file >> old_result_json;
            if (old_result_json.contains("multiObjectiveResult")) {
                final_json["multiObjectiveResult"] = old_result_json["multiObjectiveResult"];
            }
        } catch (const std::exception& e) {
            std::cout << "保留多目标结果时读取旧result.json失败: " << e.what() << std::endl;
        }
        old_result_file.close();
    }
    
    // 5. 将组装好的 final_json 写入文件
    errno = 0;
    std::ofstream file_json(file_name);
    if(file_json.is_open())
    {
        file_json << final_json.dump(4); // 控制缩进 4 空格
        file_json.close();
        std::cout << "结果JSON文件写入完成！" << std::endl;
        return true;
    }
    else
    {
        std::cerr << "文件无法打开: " << file_name
                  << ", reason: " << std::strerror(errno) << std::endl;
        return false;
    }
}

// ===================== 编码长度（2026-10-14 修订：按最短值岗时长推班次上界） =====================
// 时间轴推进规则（见 entity_workflow_process）：第 1 班的值岗结束时刻 = 准备时长（0→3）+ 值岗时长；
// 之后每班的值岗都紧接上一班值岗结束开始，Empty_Time 每班恰好前进该机器人值岗节点 "3" 的时长。
// 因此 N 班之后 Empty_Time ≥ N × d_min（d_min = 所有机器人中最短的值岗时长），
// 覆盖任务时长 T 所需的班次数一定 ≤ N_max = ⌈T / d_min⌉，这是严格上界（全部派值岗最短的机器人时取到）。
// 每班 2 个基因（前半段选机器人、后半段选工具）→ 所需编码长度 Nvar = 2 × N_max。
// 编码比这长：后段基因永远用不到，截断；比这短：可能排不满，补足。
// 依赖全局 task / properties，须在 task.Set_Task、properties.Set_Objects_Properties 之后调用。
static double robot_duty_time(const std::tuple<std::string, int, int>& key, Objects& obj)
{
    // 值岗节点 "3" 的时长：Relationship 为 self 时取其指向的属性，否则取 work_time
    std::string prop = "work_time";
    auto it = obj.WorkflowNodes.find("3");
    if (it != obj.WorkflowNodes.end())
    {
        auto& cat = it->second.category;
        auto rel = cat.find("Relationship");
        auto rp = cat.find("Robot");
        if (rel != cat.end() && rel->second == "self" && rp != cat.end()) prop = rp->second;
    }
    return properties.Get_property("Robot", std::get<1>(key), std::get<2>(key), prop);
}
int estimate_robot_nvar()
{
    double d_min = 1e18;
    for (auto& kv : properties.Properties_Set)
    {
        if (std::get<0>(kv.first) != "Robot") continue;
        double d = robot_duty_time(kv.first, kv.second);
        if (d > 0 && d < d_min) d_min = d;
    }
    if (d_min >= 1e18) return 0;   // 场景中没有机器人
    int n_max = static_cast<int>(std::ceil(task.task_duration / d_min - 1e-9));
    return 2 * std::max(n_max, 1);
}
// 返回本场景所需的编码长度；与请求值不同时打印说明（多则截断、少则补足）
int ensure_robot_nvar(int requested)
{
    int need = estimate_robot_nvar();
    if (need <= 0) return requested;
    if (need != requested)
        std::cout << "[编码长度] 任务时长 " << task.task_duration << " h，班次数上界 " << need / 2
                  << "，Nvar 由 " << requested << (need < requested ? " 截断为 " : " 补足为 ") << need << std::endl;
    return need;
}
// ==================================================================================
