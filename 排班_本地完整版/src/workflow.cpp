#include "workflow.h"
extern int generation, MAXGEN;
// 流程是针对实体的状态而言来改变。所以传入的是实体的状态。
bool Workflow::Time_Process(ENTITY & entity, Objects_Properties & objects_properties, double start_time) // **需要修改为个体类中的成员函数
{
    // 先读取关系, 确定处理流程时长
    double Duration = this->Get_duration(entity, objects_properties);
    double end_time = start_time + Duration;
    std::string process_number = this->Process_No;
    Time_Record time_record;
    time_record.begin = start_time;
    time_record.end = end_time;
    time_record.Process_Number = process_number;
    entity.Temp_State.workflow_time.push_back(time_record); // 将一个流程开始结束写入到临时状态变量中
    // print_process_time(entity, time_record);
    return true;
}
void Workflow_Set::Set_Workflow_Set(std::string path)
 {
    Workflows.clear();
    std::ifstream inputFile(path);
    if (!inputFile.is_open()) {
        throw std::runtime_error("Failed to open file: " + path);
    }
    json task_j;
    inputFile >> task_j;
    json workflow_j = task_j["workflow_set"];
    for (auto & i : workflow_j.items())
    {
        auto value = i.value();
        Workflow j;
        j.Name = value["Name"];
        j.Process_No = value["Process_No"];
        j.Workflow_Type = value["Workflow_Type"];
        json category = value["category"];
        if(j.Workflow_Type == "Time")
        {
            for (auto k = category.begin(); k != category.end(); ++k)
            {
                std::string temp = k.value();
                j.category[k.key()] = k.value();
            }
        }
        else if (j.Workflow_Type == "Action")
        {
            json left = category["left"];
            json right = category["right"];
            for (auto it = left.begin(); it != left.end(); it++)
            {
                std::string temp_left = it.value();
                j.left_action[it.key()] = it.value();
            }
            for (auto it = right.begin(); it != right.end(); it++)
            {
                std::string temp_right = it.value();
                j.right_action[it.key()] = it.value();
            }
            j.category["Relationship"] = category["Relationship"];
        }
        else if (j.Workflow_Type == "Time_Action")
        {

        }
        else if(j.Workflow_Type == "Decision")
        {
            json left = category["left"];
            json right = category["right"];
            for (auto it = left.begin(); it != left.end(); it++)
            {
                std::string temp_left = it.value();
                j.left[it.key()] = it.value();
            }
            for (auto it = right.begin(); it != right.end(); it++)
            {
                std::string temp_right = it.value();
                j.right[it.key()] = it.value();
            }
            j.category["Relationship"] = category["Relationship"];
        }
        else if (j.Workflow_Type == "Start" || j.Workflow_Type == "End")
        {
            this->Workflows[j.Process_No] = j;
            continue;
        }
        else
        {
            std::cout << "流程编号：" << j.Process_No << ", 未知流程类型！！" << std::endl;
        }
        
        this->Workflows[j.Process_No] = j;
    }

 }
bool Workflow::Action_Process(ENTITY & entity, Objects_Properties & objects_properties, double start_time) // 需要修改为个体类中的成员函数
{
    // 需要解析用户对什么变量进行了相应的操作，支持简单运算解析
    std::map<std::string, std::function<double(double &, double)>> compute = {
        {"+", [](double &a, double b)
         { a = a + b; return a; }},
        {"-", [](double &a, double b)
         { a = a - b; return a; }},
        {"*", [](double &a, double b)
         { a = a * b; return a; }},
        {"=", [](double &a, double b)
         { a = b; return a; }}, 
         {"/", [](double &a, double b)
               {  if(b != 0)
                a = a / b;
            else
                std::cout << "除数不能为0" << std::endl;
            return a; }}};
    std::string left_action_property, right_action_property;
    double left_action_value, right_action_value;
    std::string entity_category = entity.category;
    if (this->left_action.count("Custom") != 0)
    {
        left_action_property = this->left_action["Custom"]; // ** 这里取判断的左侧，分两种一种是变量，一种是参数。利用custom来辨别,左右值应该都做判断
        left_action_value = entity.Custom[left_action_property]; 
    }
    else if (this->left_action.count(entity_category) != 0)
    {
        left_action_property = this->left_action[entity_category];
        if (entity.Custom.count(left_action_property) != 0) {
            left_action_value = entity.Custom[left_action_property];
        } else {
            left_action_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,left_action_property); 
        }
        // left_action_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,left_action_property); 
    }
    else
    {
        std::cout << "流程编号：" << this->Process_No << "判断左值出现问题" << std::endl;
    }
    // right
    if(this->right_action.count("Custom") != 0)
    {
        std::string right_action_property = this->right_action[entity_category];
        right_action_value = objects_properties.Get_property(entity_category, entity.type, entity.Serial_ID,right_action_property);
    }
    else if(this->right_action.count("Constant") != 0)
    {
        right_action_value = std::stod(this->right_action["Constant"]);
    }
    else if(this->right_action.count(entity_category) != 0)
    {
        right_action_property = this->right_action[entity_category];
        if (entity.Custom.count(right_action_property) != 0) {
            right_action_value = entity.Custom[right_action_property];
        } else {
            right_action_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,right_action_property);  
        }
        // right_action_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,right_action_property); 
    }
    else
    {
        std::cout << "流程编号：" << this->Process_No << "判断右值出现问题" << std::endl;
    }
    std::string action_relationship = this->category["Relationship"];

    compute[action_relationship](entity.Custom[left_action_property], right_action_value);
    Time_Record time_record;
    time_record.begin = start_time;
    time_record.end = start_time;
    time_record.Process_Number = this->Process_No;
    entity.Temp_State.workflow_time.push_back(time_record);
    // print_process_time(entity, time_record);
    return true;
}

bool Workflow::Decision_Process(ENTITY & entity, Objects_Properties & objects_properties, double start_time)
{
    // 将字符串映射到lambda函数上 
    std::map<std::string, std::function<bool(double, double)>> cmp = {
        {">", [](double a, double b){ return a > b; }},
        {"<", [](double a, double b){ return a < b; }},
        {"==", [](double a, double b){ return a == b; }},
        {">=", [](double a, double b){ return a >= b; }},
        {"<=", [](double a, double b){ return a <= b; }},
        {"!=", [](double a, double b){ return a != b; }},
    };
    // 三类判断类型, 这里需要根据用户提供的判断条件进行判断，包括两层判断，一是判断类型，二是判断阈值。
    // 拿到判断关系
    std::string relationship = this->category["Relationship"];
    std::string entity_category = entity.category;
    double right_value;
    double left_value;
    std::string left_property, right_property;
    if (this->left.count("Custom") != 0)
    {
        left_property = this->left["Custom"]; // ** 这里取判断的左侧，分两种一种是变量，一种是参数。利用custom来辨别,左右值应该都做判断
        left_value = entity.Custom[left_property]; 
    }
    else if (this->left.count(entity_category) != 0)
    {
        left_property = this->left[entity_category];
        if (entity.Custom.count(left_property) != 0) {
            left_value = entity.Custom[left_property];
        } else {
            left_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,left_property); 
        }
        // left_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,left_property); 
    }
    else
    {
        std::cout << "流程编号：" << this->Process_No << "判断左值出现问题" << std::endl;
    }
    // right 
    if(this->right.count("Custom") != 0)
    {
        std::string right_property = this->right[entity_category];
        right_value = objects_properties.Get_property(entity_category, entity.type, entity.Serial_ID,right_property);
    }
    else if(this->right.count("Constant") != 0)
    {
        right_value = std::stod(this->right["Constant"]);
    }
    else if(this->right.count(entity_category) != 0)
    {
        right_property = this->right[entity_category];
        if (entity.Custom.count(right_property) != 0) {
            right_value = entity.Custom[left_property];
        } else {
            right_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,right_property);  
        }
        // right_value = objects_properties.Get_property(entity.category,entity.type,entity.Serial_ID,right_property); 
    }
    else
    {
        std::cout << "流程编号：" << this->Process_No << "判断右值出现问题" << std::endl;
    }
    if(cmp[relationship](left_value,right_value))
    {
        Time_Record time_record;
        time_record.begin = start_time;
        time_record.end = start_time;
        time_record.Process_Number = this->Process_No;
        entity.Temp_State.workflow_time.push_back(time_record);
        // print_process_time(entity, time_record);
        return true;
    }
    else
    {
        Time_Record time_record;
        time_record.begin = start_time;
        time_record.end = start_time;
        time_record.Process_Number = this->Process_No;
        entity.Temp_State.workflow_time.push_back(time_record);
        // print_process_time(entity, time_record);
        return false;
    }

}
bool Workflow::Process(ENTITY & entity, Objects_Properties & objects_properties, double start_time)
{
    bool label_true = true;
    if (this->Workflow_Type == "Start")
    {
        if (generation == MAXGEN)
            std::cout << "类别: " << entity.category << " 类型: " << entity.type << " 序号: " << entity.ID << " 开启流程！" << std::endl;
        Time_Record start;
        start.begin = start_time;
        start.end = start_time;
        start.Process_Number = "0";
        entity.Temp_State.workflow_time.push_back(start); // 将起始时间

    }
    else if(this->Workflow_Type == "Time")
    {
        this->Time_Process(entity, objects_properties, start_time);
    }
    else if (this->Workflow_Type == "Action")
    {
        this->Action_Process(entity, objects_properties, start_time);
    }
    else if(this->Workflow_Type == "Decision")
    {
        label_true = this->Decision_Process(entity, objects_properties, start_time);
    }
    else if(this->Workflow_Type == "Split"||this->Workflow_Type == "Join"){
        Time_Record start;
        start.begin = start_time;
        start.end = start_time;
        start.Process_Number = this->Process_No; // 最好也把ID加上
        entity.Temp_State.workflow_time.push_back(start);
    }
    else if(this->Workflow_Type == "End")
    {
        std::cout << "类别: " << entity.category << " 类型: " << entity.type << " 序号: " << entity.ID << " 完成流程！" << std::endl;
    }
    else
    {
        std::cout << "执行流程实体" << entity.ID << ", 型号：" << entity.type <<std::endl;
        std::cout << "流程类型:" << this->Workflow_Type << ", 流程名称: " << this->Name;
        std::cout << ", 未知类型流程，请重新检查流程" << std::endl;
    }

    return label_true;
}
// 找到流程持续时间
double Workflow::Get_duration(ENTITY &entity, Objects_Properties &objects_properties)
{
    // 先读取关系, 确定处理流程时长
    double Duration = 0;
    std::string relationship = this->category["Relationship"];

    auto get_tool_values = [&](std::string property_name) -> std::vector<double> {
        std::vector<double> values;
        // 确保是机器人且携带了工具
        if (!entity.Temp_State.tool_IDs.empty()) {
            for (const std::string &tid : entity.Temp_State.tool_IDs) {
                std::string category, type, number;
                parseToolString(tid, category, type, number); // 解析工具ID
                double val = objects_properties.Get_property(category, std::stoi(type), std::stoi(number), property_name);
                values.push_back(val);
            }
        }
        // 如果是空列表，默认给一个 0 或者处理异常
        if (values.empty()) values.push_back(0.0);
        return values;
    };
    
    if(relationship == "self")
    {
        std::string property = this->category[entity.category]; // 持续时长跟哪个属性相关
        int type = entity.type;                              // 个体的型号
        Duration = objects_properties.Get_property(entity.category, type, entity.Serial_ID,property);
    }
    else if (relationship == "self_max")
    {
        std::string property = this->category[entity.category]; // 持续时长跟哪个属性相关
        int type = entity.type;
        std::vector<double> temp_time_list = objects_properties.Get_list_property(entity.category, type, entity.Serial_ID,property);
        Duration = *std::max_element(temp_time_list.begin(), temp_time_list.end());
    }
    else if (relationship == "self_min")
    {
        std::string property = this->category[entity.category]; // 持续时长跟哪个属性相关
        int type = entity.type;
        std::vector<double> temp_time_list = objects_properties.Get_list_property(entity.category, type, entity.Serial_ID,property);
        Duration = *std::min_element(temp_time_list.begin(), temp_time_list.end());
    }
    else if (relationship == "self_sum")
    {
        std::string property = this->category[entity.category]; // 持续时长跟哪个属性相关
        int type = entity.type;
        std::vector<double> temp_time_list = objects_properties.Get_list_property(entity.category, type, entity.Serial_ID,property);
        Duration = std::accumulate(temp_time_list.begin(), temp_time_list.end(), 0.0);
    }
    // else if (relationship == "other")
    // {
        
    //     std::string other_ID = entity.Temp_State.robot_ID;
    //     std::string property = this->category["other"];
    //     std::string category, type, number;
    //     parseToolString(other_ID, category, type, number);
    //     Duration = objects_properties.Get_property(category, std::stoi(type), std::stoi(number), property);
    // }
    // else if(relationship == "other_sum")
    // {
    //     Duration = std::accumulate(entity.Temp_timelist.begin(), entity.Temp_timelist.end(), 0.0);
    // }
    // else if(relationship == "other_max")
    // {
    //     if (entity.Temp_timelist.empty()) {
    //     Duration = 0.0; // 或者设置为默认值
    //     // std::cout << "Warning: Temp_timelist is empty for other_max, ID: " << entity.ID << std::endl;
    //     } else {
    //     Duration = *std::max_element(entity.Temp_timelist.begin(), entity.Temp_timelist.end());
    //     }
    //     // Duration = *std::max_element(entity.Temp_timelist.begin(), entity.Temp_timelist.end());
    // }
    // else if(relationship == "other_min")
    // {
    //     Duration = *std::min_element(entity.Temp_timelist.begin(), entity.Temp_timelist.end());
    // }



    else if (relationship == "other")
    {
        // 保持原有逻辑：如果是工具找机器人
        if (!entity.Temp_State.robot_ID.empty()) {
            std::string other_ID = entity.Temp_State.robot_ID;
            std::string property = this->category["other"];
            std::string category, type, number;
            parseToolString(other_ID, category, type, number);
            Duration = objects_properties.Get_property(category, std::stoi(type), std::stoi(number), property);
        }
        else {
             // 如果是机器人找工具，默认取第一个工具的属性（或者你可以定义报错）
             std::string property = this->category["other"];
             std::vector<double> vals = get_tool_values(property);
             Duration = vals[0];
        }
    }
    else if(relationship == "other_sum")
    {
        // 从 JSON 中获取 "other": "install_time" 或 "removal_time"
        std::string property = this->category["other"]; 
        std::vector<double> vals = get_tool_values(property);
        Duration = std::accumulate(vals.begin(), vals.end(), 0.0);
    }
    else if(relationship == "other_max")
    {
        // 彻底修复：根据 JSON 指定的属性名 (property) 去查找最大值
        // 这样安装节点查 install_time，拆卸节点查 removal_time
        std::string property = this->category["other"]; 
        std::vector<double> vals = get_tool_values(property);
        Duration = *std::max_element(vals.begin(), vals.end());
    }
    else if(relationship == "other_min")
    {
        std::string property = this->category["other"]; 
        std::vector<double> vals = get_tool_values(property);
        Duration = *std::min_element(vals.begin(), vals.end());
    }
    //修改other相关持续时间获取方式

    
    else if(relationship == "constant")
    {
        Duration = std::stod(this->category["constant"]);
    }
    else
    {
        std::cout << "未知类型关系，请检查流程值的关系类型" << std::endl;
        return false;
    }
    return Duration;
}
void Workflow::print_process_time(ENTITY &entity, Time_Record & time)
{
    std::cout << entity.ID << "——流程名称：" << this->Name << ", 流程编号" << this->Process_No << ", 开始时间：" << time.begin << ", 结束时间" << time.end << std::endl;
}
///////////////////////////////////////////////////////////////////////////////////////////////
// Workflow_Set 建立流程库
Workflow_Set::Workflow_Set(std::string path) 
{
    std::ifstream inputFile(path);
    if (!inputFile.is_open()) {
        throw std::runtime_error("Failed to open file: " + path);
    }
    json task_j;
    inputFile >> task_j;
    json workflow_j = task_j["workflow_set"];
    for (auto & i : workflow_j.items())
    {
        auto value = i.value();
        Workflow j;
        j.Name = value["Name"];
        j.Process_No = value["Process_No"];
        j.Workflow_Type = value["Workflow_Type"];
        json category = value["category"];
        if(j.Workflow_Type == "Time")
        {
            for (auto k = category.begin(); k != category.end(); ++k)
            {
                std::string temp = k.value();
                j.category[k.key()] = k.value();
            }
        }
        else if (j.Workflow_Type == "Action")
        {
            json left = category["left"];
            json right = category["right"];
            for (auto it = left.begin(); it != left.end(); it++)
            {
                std::string temp_left = it.value();
                j.left_action[it.key()] = it.value();
            }
            for (auto it = right.begin(); it != right.end(); it++)
            {
                std::string temp_right = it.value();
                j.right_action[it.key()] = it.value();
            }
            j.category["Relationship"] = category["Relationship"];
        }
        else if (j.Workflow_Type == "Time_Action")
        {

        }
        else if(j.Workflow_Type == "Decision")
        {
            json left = category["left"];
            json right = category["right"];
            for (auto it = left.begin(); it != left.end(); it++)
            {
                std::string temp_left = it.value();
                j.left[it.key()] = it.value();
            }
            for (auto it = right.begin(); it != right.end(); it++)
            {
                std::string temp_right = it.value();
                j.right[it.key()] = it.value();
            }
            j.category["Relationship"] = category["Relationship"];
        }
        else if (j.Workflow_Type == "Start" || j.Workflow_Type == "End")
        {
            this->Workflows[j.Process_No] = j;
            continue;
        }
        else
        {
            std::cout << "流程编号：" << j.Process_No << ", 未知流程类型！！" << std::endl;
        }
        
        this->Workflows[j.Process_No] = j;
    }
}
//默认构造函数
Workflow_Set::Workflow_Set()
{

}
// 

// 功能函数
std::vector<std::string> split(const std::string& str, char delimiter) {
    std::vector<std::string> result;
    std::stringstream ss(str);
    std::string item;
    while (std::getline(ss, item, delimiter)) {
        result.push_back(item);
    }
    return result;
}

// 主函数，提取 category、type、number
void parseToolString(const std::string& input, std::string& category, std::string& type, std::string& number) {
    std::vector<std::string> parts = split(input, '_');
    if (parts.size() == 3) {
        category = parts[0];
        type = parts[1];
        number = parts[2];
    } else {
        std::cerr << "格式错误，无法解析: " << input << std::endl;
    }
}

