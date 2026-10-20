#include "Entity.h"
// 非必要，因为可以从配置文件中重新写入变化的流程。
// 在原有流程基础上增加流程，注意传入的是插入流程所在的原编号
// void Entity::Add_workflow(Flow flow, std::string pos)
// {
    // // 检查加入的流程是否在流程集中
    // int pre_no = -3;                   // 在一开始没有流程编号为-3
    // for (auto i : this->entity_workflows)
    // {
    //     if(i.second.True_No == std::stoi(pos))
    //     {
    //         pre_no = i.second.No;
    //         break;
    //     }
    // }
    // this->entity_workflows[std::to_string(pre_no)].True_No = flow.No;
    // flow.True_No = std::stoi(pos);
// }

// void Entity::Remove_workflow(std::string name)
// {
    
    
// }
// void Entity::Change_workflow(std::string name, Flow flow)
// {
   
// }
Time_Record Entity::Get_flow_time(std::string Process_Number)
{
    Time_Record temp;

    if (Process_Number == "-2")
    {
        temp.begin = 0;
        temp.end = 0;
        temp.Process_Number = "-2";

        return temp;
    }
    for (Time_Record &i : this->Temp_State.workflow_time)
    {
        if(i.Process_Number == Process_Number)
        {
            return i;
        }
        else continue;
    }
    temp.begin = 0;
    temp.end = 0;
    temp.Process_Number = "Not_Found";
    return temp;
}
void Entity::Clear_TempState()
{
    this->Temp_State.workflow_time.clear();
    this->Temp_State.tool_IDs.clear();
    this->Temp_State.tool_types.clear();
}
//Entity_Set类函数//////////////////////////////////////////////////////


