#pragma once
#include "Properties.h"


typedef struct time_record
{
    double begin;          // 流程开始时间;
    double end;            // 流程结束时间;
    std::string Process_Number; // 对应流程编号; 这里需要
} Time_Record;
//是排班实体例如具体的机器人各种状态，但是状态是和环节一一挂钩所以，应该先对流程库进行建模
typedef struct entitystate // 这是单次出动的状态，然后汇总到States中
{
    // 这里的时间需要根据环节来定, 每个环节两个时间点记录，开始时刻和结束时刻。
    std::vector<Time_Record> workflow_time;
    int max_prepare_time;                 // 携带的同批工具中保养时间最长的;
    int flight;                           // 所在班次序号;
    std::vector<int> tool_types;          // 机器人一次带多个工具, 对应的货物的类型;
    std::vector<std::string> tool_IDs;            // 机器人一次带多个货物, 对应的工具在Tool_List中的索引位置, 也即是编号;
    std::string robot_ID;                         // 工具一个班次内对应的飞机ID;
    int Pos_index;                                // **记录货物找的机器人的编号，在Car_list中的索引位置(有待优化);
    int current_ready_time;               // 输出的辅助变量，不参与排班;
} ENTITY_STATE;
// Entity**************************************************************************************************************
typedef class Entity
{
public:
    std::string category;                     // 实体类别:机器人 工具
    int type;                                 // 在大的类别下面的所属类别，1型机器人，2型机器人 ;
    std::string ID;                           // 个体编号（“类别_型号_序号”）型号和序号都是从1开始
    int Serial_ID;                            // 单纯的序号
    double Current_Time;                      // **记录当前时间，方便记录每个流程开始结束时间，这里需要特别注意时间的更新正确性;
    bool First_Repair;                        // 是否第一次维修
    std::map<std::string, double> Custom;     // 用户自定义的变量，参数不会变，变量随着进行会发生改变
    int Next_Ready_time;                   // 下次可用时间;
    std::vector<ENTITY_STATE> States;         // 机器人状态集合
    ENTITY_STATE Temp_State;                  // 临时单次出动状态变量，方便加入到States中
    std::vector<double> Temp_timelist;        // **临时时长列表记录容器
    double Temp_time;                        // **临时时长记录容器;
    // std::map<std::string, Flow> entity_workflows; //  个体的流程集合需要支持流程的改变
public:
    // void Add_workflow(Flow flow, std::string pos);       // 在原本流程上增加流程
    // void Remove_workflow(std::string name);              // 在原本流程上删除流程
    // void Change_workflow(std::string name, Flow flow);   // 在原本流程上更改流程
    Time_Record Get_flow_time(std::string Process_Number); // 查询实体在Temp_State中的流程编号对应的开始和结束的时间
    void Clear_TempState();

} ENTITY;

// Entity_Set
class Entity_Set
{
public:
    std::map<std::string, Entity> Entity_Set; // <ID, 对应个体>
    std::vector<std::string> order_id;

public:

    
};
