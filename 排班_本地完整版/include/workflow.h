#pragma once
#include "Entity.h"
#include <fstream>
#include <sstream>
// #include <nlohmann/json.hpp>
// using json = nlohmann::json;
// Workflow************************************************************************************************************
class Workflow
{
public:
    std::string Name;                              // 流程名称;
    std::string Process_No;                                // 流程编号;
    std::string Workflow_Type;                     // 流程类型 "Time"时间相关, "Action" 动作相关, "Time_Action" 时间动作都相关, "Start" 开始节点, "End" 结束节点, "Decision"决策;
    std::map<std::string, std::string> category;   // 存储数值或者变量跟类别哪些是挂钩的
    std::map<std::string, std::string> left;         // 存储判断流程左侧变量
    std::map<std::string, std::string> right;         // 存储判断流程右侧变量
    std::map<std::string, std::string> left_action;         // 存储动作流程左侧变量
    std::map<std::string, std::string> right_action;         // 存储动作流程右侧变量
    std::vector<std::string> successors;
    int Predecessor_Count = 0;




public:
    bool Process(ENTITY &entity, Objects_Properties & objects_properties, double start_time);
    bool Time_Process(ENTITY &entity, Objects_Properties & objects_properties, double start_time);                     // 时间处理类型;
    bool Action_Process(ENTITY & entity, Objects_Properties & objects_properties, double start_time);                  // 动作处理类型;
    bool Decision_Process(ENTITY & entity, Objects_Properties & objects_properties, double start_time);                // 判断处理类型;
    double Get_duration(ENTITY &entity, Objects_Properties &objects_properties);                                       // 获取流程持续时间;
    void print_process_time(ENTITY &entity, Time_Record & time);
};
// Workflow_Set********************************************************************************************************
class Workflow_Set
{
public:
    std::map<std::string,Workflow> Workflows;

public:
    Workflow_Set();
    Workflow_Set(std::string path);
    void Set_Workflow_Set(std::string path);
    
};

void parseToolString(const std::string &input, std::string &category, std::string &type, std::string &number);
std::vector<std::string> split(const std::string &str, char delimiter);