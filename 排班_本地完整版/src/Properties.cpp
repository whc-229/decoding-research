#include "Properties.h"
#include "workflow.h"

Objects::Objects(const std::string &filename)
{
    // 读取一般属性
    std::ifstream inputFile(filename);
    if (!inputFile.is_open()) {
        throw std::runtime_error("Failed to open file: " + filename);
    }
    json config_j;
    inputFile >> config_j;
    this->category = config_j["category"];
    this->type = config_j["type"];
    this->ID = config_j["ID"]; // 从1开始
    auto normal_property = config_j["normal_property"];
    // 读取普通属性
    for (auto it = normal_property.begin(); it != normal_property.end(); ++it) {
        // std::cout << it.key() << std::endl;
        double temp_normal = it.value();
        this->Properties[it.key()] = temp_normal;
    }

    // 读取列表属性
    auto list_property = config_j["list_property"];
    for (auto it = list_property.begin(); it != list_property.end(); ++it) {
        std::vector<double> temp_list = it.value();
        this->List_Properties[it.key()] = temp_list;
    }
    inputFile.close();

    // 读取工作流程
    // auto work_flows = config_j["workflow"];
    // for (auto it = work_flows.begin(); it != work_flows.end(); ++it)
    // {
    //     std::vector<std::string> temp_list = it.value();
    //     Flow flow;
    //     flow.No = temp_list[0];
    //     flow.True_No = temp_list[1];
    //     flow.False_No = temp_list[2];
    //     this->Workflows[it.key()]=flow;
    // }
    // 读取自定义属性
    auto custom = config_j["Custom"];
    for (auto it = custom.begin(); it != custom.end(); ++it) {
        // std::cout << it.key() << std::endl;
        double temp_custom = it.value();
        this->Custom[it.key()] = temp_custom;
    }
    if (config_j.contains("workflow")){
        json nodes_json = config_j["workflow"];
        std::map<std::string, std::string> standard_map = {
            {"开始", "0"}, 
            {"安装工具", "1"},
            {"去程", "2"},
            {"值班", "3"},
            {"返程", "4"},
            {"拆卸工具", "5"},
            {"检查剩余工时", "6"},
            {"充电", "7"},
            {"维修", "8"},
            {"保养", "9"},
            {"更新剩余工时", "10"},
            {"更新2", "11"},
            {"工具去程", "12"},
            {"工具值班", "13"},
            {"工具返程", "14"},
            {"并行流程起点", "15"},
            {"并行流程终点", "16"},
            {"工具休息", "17"},
            {"结束", "-2"}
        };

        // 临时表：旧编号 -> 新编号
        std::map<std::string, std::string> id_map;
        int auto_id = 1000; // 未匹配节点的编号基准

        // 遍历一次 workflow，建立映射
        for (auto& node_item : nodes_json.items()) {
            std::string old_id = node_item.key();
            std::string name = node_item.value().value("Name", "");

            if (standard_map.count(name)) {
                id_map[old_id] = standard_map[name];
            } else {
                // 自动编号（防止冲突）
                id_map[old_id] = std::to_string(auto_id++);
            }
        }

        // ===================== 生成新的 workflow JSON =====================
        json remapped_workflow;
        for (auto& node_item : nodes_json.items()) {
            std::string old_id = node_item.key();
            json node_data = node_item.value();
            std::string new_id = id_map[old_id];

            // 替换 successors 内的编号
            if (node_data.contains("Successors")) {
                for (auto& succ : node_data["Successors"]) {
                    std::string succ_str = succ.get<std::string>();
                    if (id_map.count(succ_str))
                        succ = id_map[succ_str];
                }
            }

            remapped_workflow[new_id] = node_data;
        }

        // 用映射后的 workflow 替换原有 workflow
        nodes_json = remapped_workflow;
        for (auto& node_item : nodes_json.items()){
            std::string node_id = node_item.key();
            json node_data = node_item.value();
            Workflow w;
            w.Process_No = node_id;
            w.Name = node_data.value("Name", "");
            w.Workflow_Type = node_data.value("Workflow_Type", "");
            if (node_data.contains("Successors")) {
                for (const auto& successor : node_data["Successors"]) {
                    w.successors.push_back(successor);
                }
            }
            // if (node_data.contains("category")) {
            //      for (auto k = node_data["category"].begin(); k != node_data["category"].end(); ++k) {
            //         w.category[k.key()] = k.value();
            //         //w.category["Relationship"]=">="
            //     }
            // }
            // if (w.Workflow_Type == "Decision") {
            //      json category = node_data["category"];
            //      if (category.contains("left")) {
            //         for (auto it = category["left"].begin(); it != category["left"].end(); it++) w.left[it.key()] = it.value();
            //      }
            //      if (category.contains("right")) {
            //         for (auto it = category["right"].begin(); it != category["right"].end(); it++) w.right[it.key()] = it.value();
            //      }
            // }
            if (node_data.contains("category")) {
                json category = node_data["category"];

                if (w.Workflow_Type == "Decision") {
                    // --- 针对 "Decision" 节点的特定解析逻辑 ---
                    if (category.contains("left") && category["left"].is_object()) {
                        for (auto it = category["left"].begin(); it != category["left"].end(); ++it) {
                            w.left[it.key()] = it.value();
                        }
                    }
                    if (category.contains("right") && category["right"].is_object()) {
                        for (auto it = category["right"].begin(); it != category["right"].end(); ++it) {
                            w.right[it.key()] = it.value();
                        }
                    }
                    if (category.contains("Relationship") && category["Relationship"].is_string()) {
                        w.category["Relationship"] = category["Relationship"];
                    }
                } 
                else if (w.Workflow_Type == "Action") {
                    // --- 针对 "Action" 节点的特定解析逻辑 ---
                    if (category.contains("left") && category["left"].is_object()) {
                        for (auto it = category["left"].begin(); it != category["left"].end(); ++it) {
                            // 对应 workflow.cpp 中的 j.left_action
                            w.left_action[it.key()] = it.value(); 
                        }
                    }
                    if (category.contains("right") && category["right"].is_object()) {
                        for (auto it = category["right"].begin(); it != category["right"].end(); ++it) {
                            // 对应 workflow.cpp 中的 j.right_action
                            w.right_action[it.key()] = it.value();
                        }
                    }
                    if (category.contains("Relationship") && category["Relationship"].is_string()) {
                        w.category["Relationship"] = category["Relationship"];
                    }
                }
                else {
                    // --- 针对 "Time", "Action" 等其他节点的通用解析逻辑 ---
                    // 假设这些节点category中的所有键值对都是 string:string 格式
                    for (auto it = category.begin(); it != category.end(); ++it) {
                        if (it.value().is_string()) { // 安全检查，确保值是字符串
                            w.category[it.key()] = it.value();
                        }
                    }
                }
            }
            this->WorkflowNodes[node_id] = w;
        }
        for(auto &p : this->WorkflowNodes){
            for (auto &succ : p.second.successors){
                if (this->WorkflowNodes.count(succ))
                    this->WorkflowNodes[succ].Predecessor_Count++;
            }
        }
    }
}
Objects::Objects()
{
    
}
void Objects::print_property(){
    // 输出实体名称
    std::cout << "添加实体类别为: " << this->category << std::endl;
    //输出不变一般属性
    std::cout << this->category << "类型为：" << this->type << std::endl;
    for (auto it = this->Properties.begin(); it != this->Properties.end(); ++it)
    {
        std::cout << it->first << ": " << it->second << std::endl;
    }
    //输出不变列表属性
    std::cout << this->category << "type" << this->type  << "的列表属性为:" << std::endl; 
     for (auto it = this->List_Properties.begin(); it != this->List_Properties.end(); ++it) {
        std::cout << it->first << ": ";
        for (auto vecIt = it->second.begin(); vecIt != it->second.end(); ++vecIt) {
            std::cout << *vecIt << " ";
        }
        std::cout << std::endl;
    }
}
Objects::~Objects()
{
    // std::cout << "析构完成" << std::endl;
}
////////////////////////////////////////////////////////////////////////////////////////////////////
//Task构造函数
Task::Task(const std::string &filename)
{
    // 读取场景任务属性，这里的任务属性是固定的包含目标函数模式与任务持续时长
    std::ifstream inputFile(filename);
    if (!inputFile.is_open()) {
        throw std::runtime_error("Failed to open file: " + filename);
    }
    json task_j;
    inputFile >> task_j;
    this->objective_mod = task_j["objective_mod"];
    this->objects_num = task_j["objects_num"];
    this->task_duration = task_j["task_duration"];
    this->installation_type = task_j["installation_type"];
    json objects_type = task_j["objects_type"];
    for (auto it = objects_type.begin(); it != objects_type.end(); ++it)
    {
        int temp_type = it.value();
        this->objects_type[it.key()] = it.value();
    }
    inputFile.close();
}
void Task::Set_Task(const std::string &filename)
{
    // 读取场景任务属性，这里的任务属性是固定的包含目标函数模式与任务持续时长
    std::ifstream inputFile(filename);
    if (!inputFile.is_open()) {
        throw std::runtime_error("Failed to open file: " + filename);
    }
    json task_j;
    inputFile >> task_j;
    this->objective_mod = task_j["objective_mod"];
    this->objects_num = task_j["objects_num"];
    this->task_duration = task_j["task_duration"];
    this->installation_type = task_j["installation_type"];
    json objects_type = task_j["objects_type"];
    for (auto it = objects_type.begin(); it != objects_type.end(); ++it)
    {
        int temp_type = it.value();
        this->objects_type[it.key()] = it.value();
    }
    inputFile.close();
}
Task::Task()
{
}
Task::~Task()
{
    // std::cout << "Task析构完成" << std::endl;
}
//将文件名数字进行提取
std::string Get_file_num(const std::string &filename)
{
    std::regex pattern("(\\d+)"); //匹配一个或多个数字
    std::smatch match;
    if(std::regex_search(filename, match, pattern))
    {
        // std::cout << "Filename:" << filename << "数字为:" << match.str(1) << std::endl;
        return match.str(1);
    }
    else
    {
        // std::cout << "No number found" << std::endl;
        return "";
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////////////

Objects_Properties::Objects_Properties(std::string path)
{
    this->Get_path(path.c_str());
    for (std::string i : this->Path_list)
    {
        Objects object(path + i);
        std::tuple<std::string, int, int> pair = {object.category, object.type, object.ID};
        this->Properties_Set[pair] = object;
    }
    Get_entity_limit();
}
Objects_Properties::Objects_Properties()
{

}
bool Objects_Properties::Get_path(const char * path)
{
    //定义存储属性的路径向量

    DIR *dir; // 定义目录指针
    if ((dir=opendir(path)) == nullptr) 
    {
        std::cout << "config 文件夹打开失败" << std::endl;
        return false;
    }
    struct dirent *stdinfo = nullptr;
    while (1)
    {
        if ((stdinfo = readdir(dir)) == nullptr)
            break;
        // std::cout << "文件名为：" << stdinfo->d_name << std::endl;
        std::string temp_d_name(stdinfo->d_name);
        if(Get_file_num(temp_d_name) != "")
        {
            this->Path_list.push_back(temp_d_name);  
        }
    }
    closedir(dir); //关闭目录指针
    return true;
}
double Objects_Properties::Get_property(
    const std::string& category,
    int type,
    int ID,
    const std::string& property)
{
    // 修复：缓存键必须包含 ID
    auto cache_key = std::make_tuple(category, type, ID, property);

    // 1. 先查缓存
    auto cache_it = PropertyCache.find(cache_key);
    if (cache_it != PropertyCache.end()) {
        return cache_it->second;
    }

    // 2. 缓存未命中：查找个体
    auto it = this->Properties_Set.find({category, type, ID});
    if (it == this->Properties_Set.end()) {
        std::cout << "Error: 个体未找到 - category: " << category
                  << ", type: " << type << ", ID: " << ID << std::endl;
        return -1;
    }

    // 3. 查找该个体的属性
    const auto& props = it->second.Properties;
    auto prop_it = props.find(property);
    if (prop_it == props.end()) {
        std::cout << "Error: 属性不存在 - category: " << category
                  << ", type: " << type << ", ID: " << ID
                  << ", property: " << property << std::endl;
        return -1;
    }

    // 4. 缓存结果并返回
    double result = prop_it->second;
    PropertyCache[cache_key] = result;
    return result;
}
std::vector<double> Objects_Properties::Get_list_property(const std::string & category, int type, int ID, const std::string & property)
{
    std::tuple<std::string, int,int> pair = {category, type, ID};
    std::vector<double> temp;
    if (this->Properties_Set.count(pair) > 0)
    {
        Objects object = this->Properties_Set[pair];
        return object.List_Properties[property];
    }
    else
    {
        std::cout <<"category: " << category << ", type: " << type << ", 列表属性: " << property << ", 输入类别和类型错误！" << std::endl;
        return temp;
    }
}
double Objects_Properties::Get_min_stay(const std::string& category)
{
    double min_stay = std::numeric_limits<double>::max();  // 初始化为最大值
    bool found = false;

    for (const auto& item : this->Properties_Set)
    {
        const auto& key = item.first;  // tuple: (category, type, ID)
        const auto& object = item.second;

        // 提取元组中的 category
        if (std::get<0>(key) == category)
        {
            auto prop_it = object.Properties.find("work_time");
            if (prop_it != object.Properties.end()) {
                double current_stay = prop_it->second;
                if (current_stay < min_stay) {
                    min_stay = current_stay;
                }
                found = true;
            }
            // 可选：处理属性不存在的情况
            // else { std::cout << "work_time 不存在\n"; }
        }
    }

    // 如果没有找到任何匹配项
    if (!found) {
        std::cout << "Warning: 没有找到类别 '" << category << "' 的任何对象或 work_time 属性。" << std::endl;
        return -1;  // 或返回 NaN、std::optional<double> 等
    }

    return min_stay;
}
std::map<std::string, double> Objects_Properties::Get_Custom(const std::string & category, int type, int ID)
{
    std::map<std::string, double> temp;
    for (const auto i : this->Properties_Set)
    {
        const auto& key = i.first;  // tuple: (category, type, ID)
        if(std::get<0>(key) == category && std::get<1>(key) == type && std::get<2>(key)== ID)
        {
            return i.second.Custom;
        }
    }
    std::cout << "类别: " << category << ", 型号" << type << ", 没有该类别的Custom" << std::endl;
    return temp;
}
void Objects_Properties::Get_entity_limit()
{
    // 临时结构：统计每个 (category, type) 的个体数量
    std::map<std::string, std::map<int, int>> count_map;

    // 1. 遍历 Properties_Set，统计每个 (category, type) 出现的次数（即个体数）
    for (const auto& item : Properties_Set) {
        const auto& key = item.first;
        const std::string& category = std::get<0>(key);
        int type = std::get<1>(key);

        count_map[category][type]++;  // 每遇到一个个体，对应计数 +1
    }

    // 2. 转换为 entity_limit: map<string, vector<int>>
    //    vector 索引为 type，值为当前该 type 的个体总数
    entity_limit.clear();

    for (const auto& cat_entry : count_map) {
        const std::string& category = cat_entry.first;
        const std::map<int, int>& type_count = cat_entry.second;

        if (type_count.empty()) continue;

        int max_type = type_count.rbegin()->first;
        std::vector<int> vec(max_type + 1, 0);  // 默认 0

        for (const auto& pair : type_count) {
            vec[pair.first] = pair.second;
        }

        entity_limit[category] = std::move(vec);
    }
}
void Objects_Properties::Set_Objects_Properties(std::string path)
{
    Properties_Set.clear();
    this->Get_path(path.c_str());
    for (std::string i : this->Path_list)
    {
        Objects object(path + i);
        std::tuple<std::string, int, int> pair = {object.category, object.type, object.ID};
        this->Properties_Set[pair] = object;
    }
    Get_entity_limit();
}
///////////////////////////////////////////////////////////////////////////////////////////////////////////
// 获取排班实体一般和列表属性路径
std::vector<std::string> Get_path(const char *config_path)
{
    //定义存储属性的路径向量
    std::vector<std::string> path;
    DIR *dir; // 定义目录指针
    if ((dir=opendir(config_path)) == nullptr) 
    {
        std::cout << "config 文件夹打开失败" << std::endl;
        return path;
    }
    struct dirent *stdinfo = nullptr;
    std::vector<std::string> path_temp;
    while (1)
    {
        if ((stdinfo = readdir(dir)) == nullptr)
            break;
        // std::cout << "文件名为：" << stdinfo->d_name << std::endl;
        std::string temp_d_name(stdinfo->d_name);
        if(Get_file_num(temp_d_name) != "")
        {
            path_temp.push_back(temp_d_name);  
        }
    }
    // 初始化第二个 vector
    path.resize(path_temp.size());
    // 使用 std::copy 进行赋值
    std::copy(path_temp.begin(), path_temp.end(), path.begin());
    for (std::string i : path_temp)
    {
        path[stod(Get_file_num(i))-1] = i;
    }
    closedir(dir); //关闭目录指针
    return path;
}
// 获得所属类型所属型号的某一特定属性
double Get_property(std::vector<Objects> & objects_property, std::string category, int type, int ID, std::string property)
{
    bool category_is = 0;
    bool type_is = 0;
    bool ID_is = 0;
    for (Objects i : objects_property)
    {
        if(i.category == category)
        {
            category_is = 1;
            if (i.type == type)
            {
                type_is = 1;
                if(i.ID == ID)
                {
                    ID_is = 1;
                    return i.Properties[property];
                }
                
            }
            
        }
    }
    if (!category_is)
        std::cout << "没有:" << category << " 该类别" << std::endl;
    if (category_is && !type_is)
        std::cout << category << "类别下没有:" << type << " 该型号" << std::endl;
    if (category_is && type_is && !ID_is)
        std::cout << category << "类别下的" << type << "该型号" << "没有对应ID：" << ID << "的实例" << std::endl;
    return -1;
}
std::vector<double> Get_list_property(std::vector<Objects> & objects_property, std::string category, int type, int ID, std::string property)
{
    bool category_is = 0;
    bool type_is = 0;
    bool ID_is = 0;
    std::vector<double> temp_list;
    for (Objects i : objects_property)
    {
        if(i.category == category)
        {
            category_is = 1;
            if (i.type == type)
            {
                type_is = 1;
                if(i.ID == ID)
                {
                    ID_is = 1;
                    return i.List_Properties[property];
                }
                
            }
            
        }
    }
    if (!category_is)
        std::cout << "没有:" << category << " 该类别" << std::endl;
    if (category_is && !type_is)
        std::cout << category << "类别下没有:" << type << " 该型号" << std::endl;
    if (category_is && type_is && !ID_is)
        std::cout << category << "类别下的" << type << "该型号" << "没有对应ID：" << ID << "的实例" << std::endl;
    return temp_list;
}
double Get_min_stay(std::vector<Objects> & objects_property, std::string category)
{
    int min_stay = 1e4;
    int current_stay;
    for (Objects i : objects_property)
    {
        if(i.category == category)
        {
            current_stay = i.Properties["single_work_time"] - i.Properties["out_travel_time"] - i.Properties["return_travel_time"];
        }
        if(current_stay < min_stay)
            min_stay = current_stay;
    }
    return min_stay;
}
