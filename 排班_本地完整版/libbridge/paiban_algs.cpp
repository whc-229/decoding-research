// 面向排班结构的新算法（只复用算法库的公共模块，不改库源码）
//
// 排班前沿的结构：第一目标"资源数"是小范围整数，前沿是一级一级的台阶；资源数有可证明的下界 LB，
// 而实际最关心、也最难的是 LB 这一层上的均衡度（精确最优对比显示各算法在这里差距最大）。
//
// 1) LevelNiche（资源层级小生境环境选择）
//    · 父子代合并后，目标值完全相同的解只保留一个（离散问题里大量重复解会挤占名额）
//    · 按资源数分层，每层内按均衡度排序；"前沿层"= 该层最好均衡度优于所有更低层的层
//    · 先给 LB 层（未知时取当前最低可行层）保留 β·N 个名额，再在前沿层之间轮转取解（每层第 1 好、第 2 好……），
//      然后是被支配的层，最后是重复解和不可行解
//    与非支配排序 + 拥挤距离的区别：同一资源层里会同时保留多个解（它们在第一目标上相同、第二目标上被支配，
//    非支配排序会把它们放到后面的前沿而被淘汰），让 LB 层的均衡度有足够的个体继续改进。
// 2) LB-rNSGA（下界锚定的参考点）：库里 r-NSGA-II 以当前目标范围的中点为参考点，
//    这里改为 (LB, 当前最小均衡度) —— 由问题下界给出的"理想区域"，其余与 r-NSGA-II 相同。
#include <algorithm>
#include <cmath>
#include <map>
#include <vector>
#include "MOEA_solver.h"

float g_paiban_lb = 0.0f;          // 资源数下界（--lb 传入；0 表示未知）
float g_paiban_level_quota = 0.3f; // LB 层保留名额比例 β

static void EnvSelLevelNiche(MOEA_solver &s, individual *mixed, int msize, individual *next, int nsize)
{
    std::vector<int> feas, infeas;
    for (int i = 0; i < msize; i++)
        (mixed[i].obj[0] < 29999.0f ? feas : infeas).push_back(i);
    std::sort(feas.begin(), feas.end(), [&](int a, int b) {
        if (mixed[a].obj[0] != mixed[b].obj[0]) return mixed[a].obj[0] < mixed[b].obj[0];
        return mixed[a].obj[1] < mixed[b].obj[1];
    });
    std::vector<int> uniq, dup;
    for (int i : feas)
    {
        if (!uniq.empty() && std::fabs(mixed[uniq.back()].obj[0] - mixed[i].obj[0]) < 1e-6f &&
            std::fabs(mixed[uniq.back()].obj[1] - mixed[i].obj[1]) < 1e-6f)
            dup.push_back(i);
        else
            uniq.push_back(i);
    }
    std::map<long, std::vector<int>> L;
    for (int i : uniq) L[std::lround(mixed[i].obj[0])].push_back(i);
    std::vector<long> front_lv, dom_lv;
    float best = 1e30f;
    for (auto &kv : L)
    {
        if (mixed[kv.second[0]].obj[1] < best - 1e-9f) { front_lv.push_back(kv.first); best = mixed[kv.second[0]].obj[1]; }
        else dom_lv.push_back(kv.first);
    }
    std::vector<int> order;
    std::vector<char> taken(msize, 0);
    auto take = [&](int i) { if (!taken[i]) { taken[i] = 1; order.push_back(i); } };
    if (!L.empty())
    {
        long l0 = g_paiban_lb > 0 ? std::lround(g_paiban_lb) : L.begin()->first;
        auto it = L.find(l0);
        if (it == L.end()) it = L.begin();     // LB 层还没有解时，给当前最低层
        int q = (int)std::ceil(g_paiban_level_quota * nsize);
        for (int k = 0; k < (int)it->second.size() && k < q; k++) take(it->second[k]);
    }
    for (auto *lvset : {&front_lv, &dom_lv})
        for (size_t r = 0;; r++)
        {
            bool any = false;
            for (long lv : *lvset)
                if (r < L[lv].size()) { take(L[lv][r]); any = true; }
            if (!any || (int)order.size() >= nsize) break;
        }
    for (int i : dup) take(i);
    for (int i : infeas) take(i);
    for (int k = 0; k < nsize && k < (int)order.size(); k++)
        s.copy(next + k, mixed + order[k]);
}

void PaibanLevelNiche(MOEA_solver &s, int gen_mode)
{
    if (gen_mode == 1)
        s.GenerateARSBXOffspring(s.pop_sel, s.Popsize, s.pop_new, s.Popsize);
    else
        s.GenerateGAOffspring(s.pop_sel, s.Popsize, s.pop_new, s.Popsize);
    s.Evaluation(s.pop_new, s.Popsize);
    individual *mixed = s.allocate_memory_indArray(s.fullSize2);
    s.MergePopulation(s.pop_sel, s.Popsize, s.pop_new, s.Popsize, mixed);
    EnvSelLevelNiche(s, mixed, s.fullSize2, s.pop_sel, s.Popsize);
    s.UpdateArchiveFromPopulation(s.pop_sel, s.Popsize);
    s.deallocate_memory_indArray(mixed, s.fullSize2);
}

void PaibanLBRNSGA(MOEA_solver &s)
{
    s.GenerateGAOffspring(s.pop_sel, s.Popsize, s.pop_new, s.Popsize);
    s.Evaluation(s.pop_new, s.Popsize);
    int ms = s.fullSize2;
    individual *mixed = s.allocate_memory_indArray(ms);
    s.MergePopulation(s.pop_sel, s.Popsize, s.pop_new, s.Popsize, mixed);
    std::vector<float> mn(s.Nobj), mx(s.Nobj), pt(s.Nobj), crowd(ms), score(ms);
    s.ObjectiveBounds(mixed, ms, mn.data(), mx.data());
    s.CrowdingDistanceValues(mixed, ms, crowd.data());
    float lb = g_paiban_lb > 0 ? g_paiban_lb : mn[0];
    pt[0] = (mx[0] - mn[0]) > 1e-9f ? std::min(1.0f, std::max(0.0f, (lb - mn[0]) / (mx[0] - mn[0]))) : 0.0f;
    for (int m = 1; m < s.Nobj; m++) pt[m] = 0.0f;
    for (int i = 0; i < ms; i++)
    {
        float diversity = crowd[i] >= INF ? 2.0f : crowd[i];
        score[i] = s.NormalizedDistanceToPoint(mixed[i], pt.data(), mn.data(), mx.data()) - 0.1f * diversity;
    }
    s.EnvironmentalSelectionByScore(mixed, ms, s.pop_sel, s.Popsize, score.data(), true);
    s.UpdateArchiveFromPopulation(s.pop_sel, s.Popsize);
    s.deallocate_memory_indArray(mixed, ms);
}
