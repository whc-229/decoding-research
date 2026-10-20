#pragma once
#include <vector>
#include <string>
#include <map>
#include <unordered_map>
#include <string>
#include <iostream>
#include <regex>
#include <fstream>
#include <dirent.h>
#include <nlohmann/json.hpp>
#include "Entity.h"
class Workflow;
using json = nlohmann::json;
// 匹配文件的数字名
std::string Get_file_num(const std::string &path);
// 存储一般属性文件路径获取
std::vector<std::string> Get_path(const char *config_path);
typedef struct flow
{
    std::string No;          // 所在流程编号;
    std::string True_No;            // 流程结束时间;
    std::string False_No; // 对应流程编号; 这里需要
} Flow;
struct tuple_hash {
    size_t operator()(const std::tuple<std::string, int, int, std::string>& t) const {
        auto hash1 = std::hash<std::string>{}(std::get<0>(t)); // category
        auto hash2 = std::hash<int>{}(std::get<1>(t));         // type
        auto hash3 = std::hash<int>{}(std::get<2>(t));         // ID
        auto hash4 = std::hash<std::string>{}(std::get<3>(t)); // property

        // 使用黄金比例 0x9e3779b9 作为基础种子，混合四个哈希值
        size_t seed = 0;
        seed ^= hash1 + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        seed ^= hash2 + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        seed ^= hash3 + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        seed ^= hash4 + 0x9e3779b9 + (seed << 6) + (seed >> 2);

        return seed;
    }
};
// Objects***********************************************************************************************
class Objects
{
public:
    Objects();
    Objects(const std::string &filename);
    ~Objects();
public:
    std::string category;                                       // 实体类别;
    int type;                                                // 所属类别下的类型，类别从1开始
    int ID;                                                  // 具体到是同类型下的第几个实例
    std::map<std::string, double> Properties;                   // <共有不变属性的名称, 共有不变属性的值>
    std::map<std::string, std::vector<double>> List_Properties; // <共有不变列表属性的名称, 共有不变列表属性的值>
    std::map<std::string, Flow> Workflows;
    std::map<std::string, Workflow> WorkflowNodes;
    std::map<std::string, double> Custom;                       // 自定义的变量存储;
    void print_property();
};
// Task*************************************************************************************************
class Task{
public:
    int objective_mod;
    double task_duration;
    int objects_num;                   // 总共场景有几个大类物体：例如机器人、工具、AGV等大类
    std::string installation_type;     // 工具安装类型是独立的还是顺序的
    std::map<std::string, int> objects_type; // 对应大类别下有几个小的type，例如都是机器人分为1型机器人，2型机器人
    std::map<std::string, int> information_print; // 统计用了多少实体

public:
    Task(const std::string &filename);
    void Set_Task(const std::string &filename);
    Task();
    ~Task();
};
// Objects_Properties*************************************************************************************

class Objects_Properties{
public:
    std::map<std::tuple<std::string, int, int>, Objects> Properties_Set;  // 利用类别（string）和型号（int)和ID(int)来取得这一类的object对象
    // 新的缓存定义：键包含 category, type, ID, property
    std::unordered_map<std::tuple<std::string, int, int, std::string>, double, tuple_hash> PropertyCache;
    std::map<std::string, std::vector<int>> entity_limit;
    std::vector<std::string> Path_list;

public:
    Objects_Properties();
    Objects_Properties(std::string path);

    bool Get_path(const char * path);
    double Get_property(const std::string& category, int type, int ID, const std::string& property);
    std::vector<double> Get_list_property(const std::string & category, int type, int ID, const std::string & property);
    std::map<std::string, double> Get_Custom(const std::string & category, int type, int ID);
    double Get_min_stay(const std::string & category);
    void Get_entity_limit();
    void Set_Objects_Properties(std::string path);
};
// 工具函数************************************************************************************************

// 获得所属类型所属型号的某一特定属性
double Get_property(std::vector<Objects> & objects_property, std::string category, int type, int ID, std::string property);
// 获取获得所属类型所属型号的某一特定列表属性
std::vector<double> Get_list_property(std::vector<Objects> & objects_property, std::string category, int type, int ID, std::string property);
// 最短在岗机器人时间
