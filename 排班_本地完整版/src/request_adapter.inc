// 本文件由 tools/extract_adapter.py 从 model-crow/src/algorithm_routes.cpp 逐字抽取，勿手改
// 包含：MOEA 参数解析、全局参数解析、工作流标准化、前端请求规范化、para_set_robot_solver（生成 config）

static std::string lower_copy(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

static bool read_json_number(const json& item, double& value) {
    try {
        if (item.is_number()) {
            value = item.get<double>();
            return true;
        }
        if (item.is_string()) {
            value = std::stod(item.get<std::string>());
            return true;
        }
    } catch (...) {
    }
    return false;
}

static bool read_param_number(const json& item, double& value) {
    if (item.contains("value") && read_json_number(item["value"], value)) return true;
    if (item.contains("paramValue") && read_json_number(item["paramValue"], value)) return true;
    if (item.contains("inputValue") && read_json_number(item["inputValue"], value)) return true;
    return false;
}

static bool read_json_bool(const json& item, bool& value) {
    if (item.is_boolean()) {
        value = item.get<bool>();
        return true;
    }
    if (item.is_number()) {
        value = item.get<double>() != 0.0;
        return true;
    }
    if (item.is_string()) {
        const std::string text = lower_copy(item.get<std::string>());
        if (text == "true" || text == "1" || text == "yes") {
            value = true;
            return true;
        }
        if (text == "false" || text == "0" || text == "no") {
            value = false;
            return true;
        }
    }
    return false;
}

static bool read_param_bool(const json& item, bool& value) {
    if (item.contains("value") && read_json_bool(item["value"], value)) return true;
    if (item.contains("paramValue") && read_json_bool(item["paramValue"], value)) return true;
    if (item.contains("inputValue") && read_json_bool(item["inputValue"], value)) return true;
    return false;
}

static bool read_param_string(const json& item, std::string& value) {
    try {
        if (item.contains("value") && item["value"].is_string()) {
            value = item["value"].get<std::string>();
            return true;
        }
        if (item.contains("paramValue") && item["paramValue"].is_string()) {
            value = item["paramValue"].get<std::string>();
            return true;
        }
        if (item.contains("inputValue") && item["inputValue"].is_string()) {
            value = item["inputValue"].get<std::string>();
            return true;
        }
    } catch (...) {
    }
    return false;
}

static bool read_param_string_list(const json& item, std::vector<std::string>& value) {
    try {
        if (item.contains("value") && item["value"].is_array()) {
            value = item["value"].get<std::vector<std::string>>();
            return true;
        }
        if (item.contains("paramValue") && item["paramValue"].is_array()) {
            value = item["paramValue"].get<std::vector<std::string>>();
            return true;
        }
        if (item.contains("inputValue") && item["inputValue"].is_array()) {
            value = item["inputValue"].get<std::vector<std::string>>();
            return true;
        }
    } catch (...) {
    }
    return false;
}

static void apply_moea_named_param(const std::string& raw_name, const json& item,
                                   moea_opeset& set, std::string& algorithm,
                                   std::vector<std::string>& operators) {
    const std::string name = lower_copy(raw_name);
    double number_value = 0.0;
    bool bool_value = false;
    std::string string_value;

    if (name == "operator_list" || name == "operatorlist" || name == "opelist" || name == "operator_seq") {
        read_param_string_list(item, operators);
        return;
    }
    if (name == "moea_algorithm" || name == "moeaalgorithm" || name == "solveralgorithm" || name == "algorithm") {
        if (read_param_string(item, string_value)) algorithm = string_value;
        return;
    }
    if (name == "rpslevel" || name == "rps_level") {
        if (read_param_bool(item, bool_value)) set.rpsLevel = bool_value;
        return;
    }
    if (!read_param_number(item, number_value)) {
        return;
    }

    if (name == "h") set.H = static_cast<int>(number_value);
    else if (name == "m" || name == "hypesamples" || name == "probm") set.hypeSamples = static_cast<int>(number_value);
    else if (name == "binarybits" || name == "binary_bits") set.binaryBits = static_cast<int>(number_value);
    else if (name == "pc") set.pc = static_cast<float>(number_value);
    else if (name == "pm") set.pm = static_cast<float>(number_value);
    else if (name == "etac" || name == "eta_c") set.etaC = static_cast<float>(number_value);
    else if (name == "etam" || name == "eta_m") set.etaM = static_cast<float>(number_value);
    else if (name == "f" || name == "def" || name == "de_f") set.F = static_cast<float>(number_value);
    else if (name == "cr" || name == "decr" || name == "de_cr") set.CR = static_cast<float>(number_value);
    else if (name == "cauchyscale" || name == "cauchy_scale") set.cauchyScale = static_cast<float>(number_value);
    else if (name == "somutationpm" || name == "so_mutation_pm") set.soMutationPm = static_cast<float>(number_value);
    else if (name == "ibeakappa" || name == "ibea_kappa" || name == "kappa") set.ibeaKappa = static_cast<float>(number_value);
    else if (name == "tournament") set.tournament = static_cast<int>(number_value);
    else if (name == "rveaalpha" || name == "rvea_alpha") set.rveaAlpha = static_cast<float>(number_value);
    else if (name == "srapc" || name == "sra_pc") set.sraPc = static_cast<float>(number_value);
}

static void apply_moea_params(const json& source, moea_opeset& set,
                              std::string& algorithm,
                              std::vector<std::string>& operators) {
    const std::vector<std::string> top_names = {
        "H", "rpsLevel", "rps_level", "M", "hypeSamples", "probM", "binaryBits", "binary_bits",
        "pc", "pm", "etaC", "eta_c", "etaM", "eta_m", "F", "CR",
        "de_f", "de_cr", "cauchyScale", "cauchy_scale", "soMutationPm", "so_mutation_pm",
        "ibeaKappa", "ibea_kappa", "kappa", "tournament", "rveaAlpha",
        "rvea_alpha", "sraPc", "sra_pc", "moeaAlgorithm",
        "solverAlgorithm", "operatorList", "operator_list", "operator_seq", "opeList"
    };
    for (const auto& name : top_names) {
        if (!source.contains(name)) continue;
        json item;
        item["name"] = name;
        item["value"] = source[name];
        apply_moea_named_param(name, item, set, algorithm, operators);
    }

    if (source.contains("parameterList") && source["parameterList"].is_array()) {
        for (const auto& item : source["parameterList"]) {
            const std::string name = item.value("name", item.value("paramName", ""));
            if (!name.empty()) {
                apply_moea_named_param(name, item, set, algorithm, operators);
            }
        }
    }

    if (set.H <= 0) set.H = 13;
    if (set.hypeSamples <= 0) set.hypeSamples = 1000;
    if (set.binaryBits <= 0) set.binaryBits = 7;
    if (set.tournament <= 0) set.tournament = 2;
}

bool extractGlobalParams(
    const json& globalParamList,
    int& POPSIZE,
    int& Nvar,
    double& Lbound,
    double& Ubound,
    int& MAXGEN,
    int & generation
)
{
    auto read_double = [](const json& v, double fallback) -> double {
        try {
            if (v.is_string()) return std::stod(v.get<string>());
            if (v.is_number_float()) return v.get<double>();
            if (v.is_number_integer()) return static_cast<double>(v.get<long long>());
            if (v.is_number_unsigned()) return static_cast<double>(v.get<unsigned long long>());
        } catch (...) {
        }
        return fallback;
    };

    auto read_int = [](const json& v, int fallback) -> int {
        try {
            if (v.is_string()) return std::stoi(v.get<string>());
            if (v.is_number_integer()) return static_cast<int>(v.get<long long>());
            if (v.is_number_unsigned()) return static_cast<int>(v.get<unsigned long long>());
            if (v.is_number_float()) return static_cast<int>(v.get<double>());
        } catch (...) {
        }
        return fallback;
    };

    try {
        for (const auto& param : globalParamList) {
            if (!param.contains("paramName") || !param.contains("paramValue")) continue;

            std::string name;
            try {
                if (param["paramName"].is_string()) {
                    name = param["paramName"].get<std::string>();
                } else {
                    name = param["paramName"].dump();
                }
            } catch (...) {
                continue; // skip malformed entries instead of throwing
            }

            const json& val = param["paramValue"];

            if (name == "POPSIZE") {
                POPSIZE = read_int(val, POPSIZE);
            } else if (name == "Nvar") {
                Nvar = read_int(val, Nvar);
            } else if (name == "Lbound") {
                Lbound = read_double(val, Lbound);
            } else if (name == "Ubound") {
                Ubound = read_double(val, Ubound);
            } else if (name == "max_iterations") {
                MAXGEN = read_int(val, MAXGEN);
            } else if (name == "current_iter") {
                generation = read_int(val, generation);
            }
        }

        // 允许 Nvar 留空以便后续按问题维度自动计算；只要求 POPSIZE 有效
        if (POPSIZE <= 0) {
            cerr << "缺少必要的整型参数（POPSIZE）" << endl;
            return false;
        }

        return true;

    } catch (const exception& e) {
        cerr << "解析参数时出错: " << e.what() << endl;
        return false;
    }
}

json standardizeWorkflow(const json& raw_workflow) {
    // 1. 定义标准映射表 (必须与 Properties.cpp 中的保持完全一致)
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
        {"结束", "-2"},
        {"单次工作","18"}
    };

    std::map<std::string, std::string> id_map; // 旧 ID -> 新 ID 的映射表
    int auto_id = 1000; // 未匹配节点的自动编号起始值

    // 2. 第一遍遍历：建立 ID 映射关系
    for (auto& item : raw_workflow.items()) {
        std::string old_id = item.key();
        std::string name = item.value().value("Name", "");

        if (standard_map.count(name)) {
            id_map[old_id] = standard_map[name];
        } else {
            // 如果名字不在标准表中，分配一个临时 ID，或者保留原 ID (视需求而定)
            // 这里为了安全，保留原 ID 或者分配新 ID 均可，建议如下：
            id_map[old_id] = std::to_string(auto_id++);
        }
    }

    // 3. 第二遍遍历：构建新的 JSON 对象并替换 Successors
    json new_workflow;
    for (auto& item : raw_workflow.items()) {
        std::string old_id = item.key();

        // 获取新 ID
        std::string new_id = id_map.count(old_id) ? id_map[old_id] : old_id;

        json node_data = item.value();

        // 替换 Successors 列表中的 ID
        if (node_data.contains("Successors")) {
            json new_successors = json::array();
            for (const auto& succ : node_data["Successors"]) {
                std::string old_succ_id = succ.get<std::string>();
                if (id_map.count(old_succ_id)) {
                    new_successors.push_back(id_map[old_succ_id]);
                } else {
                    // 如果找不到映射（通常不应发生），保留原值
                    new_successors.push_back(old_succ_id);
                }
            }
            node_data["Successors"] = new_successors;
        }

        // 使用新 ID 存入新的 workflow 对象
        new_workflow[new_id] = node_data;
    }

    return new_workflow;
}

void clear_runtime_config(const std::string& config_dir) {
    namespace fs = std::filesystem;
    static const std::regex runtime_json(R"(^\d+\.json$)");

    for (const auto& entry : fs::directory_iterator(config_dir)) {
        if (!entry.is_regular_file()) continue;

        const std::string name = entry.path().filename().string();
        if (std::regex_match(name, runtime_json)) {
            fs::remove(entry.path());
        }
    }
}

bool hasWorkflowExamples(const json& entity_data_list) {
    if (!entity_data_list.is_array()) {
        return false;
    }
    for (const auto& entity : entity_data_list) {
        if (!entity.contains("exampleList") || !entity["exampleList"].is_array()) {
            continue;
        }
        for (const auto& example : entity["exampleList"]) {
            if (example.contains("workflow") && example["workflow"].is_object() && !example["workflow"].empty()) {
                return true;
            }
        }
    }
    return false;
}

std::string buildEntityExampleKey(const json& entity, const json& example) {
    return entity.value("englishName", "") + "|" +
           entity.value("entityName", "") + "|" +
           example.value("exampleName", "");
}

json mergeEntityDataList(const json& base_entities, const json& workflow_entities) {
    if (!base_entities.is_array()) {
        return workflow_entities;
    }
    if (!workflow_entities.is_array()) {
        return base_entities;
    }

    json merged = base_entities;
    std::map<std::string, json> workflow_lookup;
    for (const auto& entity : workflow_entities) {
        if (!entity.contains("exampleList") || !entity["exampleList"].is_array()) {
            continue;
        }
        for (const auto& example : entity["exampleList"]) {
            workflow_lookup[buildEntityExampleKey(entity, example)] = example;
        }
    }

    for (auto& entity : merged) {
        if (!entity.contains("exampleList") || !entity["exampleList"].is_array()) {
            continue;
        }
        for (auto& example : entity["exampleList"]) {
            const std::string key = buildEntityExampleKey(entity, example);
            auto it = workflow_lookup.find(key);
            if (it == workflow_lookup.end()) {
                continue;
            }
            if (!example.contains("workflow") && it->second.contains("workflow")) {
                example["workflow"] = it->second["workflow"];
            }
            if (!example.contains("workflowDetail") && it->second.contains("workflowDetail")) {
                example["workflowDetail"] = it->second["workflowDetail"];
            }
        }
    }

    return merged;
}

bool entityContainsParam(const json& entity, const std::string& target_param) {
    if (!entity.contains("exampleList") || !entity["exampleList"].is_array()) {
        return false;
    }

    for (const auto& example : entity["exampleList"]) {
        if (!example.contains("paramList") || !example["paramList"].is_array()) {
            continue;
        }
        for (const auto& param : example["paramList"]) {
            if (param.value("paramEnglishName", "") == target_param) {
                return true;
            }
        }
    }

    return false;
}

int extractExampleId(const json& example, int fallback_id) {
    if (example.contains("exampleId") && example["exampleId"].is_number_integer()) {
        return example["exampleId"].get<int>();
    }

    const std::string example_name = example.value("exampleName", "");
    std::regex pattern("(\\d+)");
    std::smatch match;
    if (std::regex_search(example_name, match, pattern)) {
        return std::stoi(match.str());
    }

    return fallback_id;
}

bool isRobotEntity(const json& entity) {
    return entity.value("englishName", "") == "Robot";
}

bool isToolEntity(const json& entity) {
    return entity.value("englishName", "") == "Tool";
}

bool isTaskEntity(const json& entity) {
    return entity.value("englishName", "") == "Task"
        || entity.value("entityCategoryName", "") == "任务"
        || entity.value("entityName", "") == "任务实体"
        || entityContainsParam(entity, "task_duration")
        || entityContainsParam(entity, "taskDuration");
}

json normalizeRobotSolverParam(const json& raw_param) {
    json normalized = raw_param;

    if (!normalized.contains("globalParamList")
        && raw_param.contains("workflow")
        && raw_param["workflow"].contains("globalParamList")) {
        normalized["globalParamList"] = raw_param["workflow"]["globalParamList"];
    }

    const bool has_root_entity_data =
        normalized.contains("entityDataList") && normalized["entityDataList"].is_array();
    const bool root_has_workflow_examples =
        has_root_entity_data && hasWorkflowExamples(normalized["entityDataList"]);
    const bool needs_entity_workflow = !has_root_entity_data || !root_has_workflow_examples;
    const bool needs_parameter_list = !normalized.contains("parameterList");

    if (!raw_param.contains("workflow")
        || !raw_param["workflow"].contains("nodeList")
        || !raw_param["workflow"]["nodeList"].is_array()
        || (!needs_entity_workflow && !needs_parameter_list)) {
        return normalized;
    }

    const json* selected_node = nullptr;
    for (const auto& node : raw_param["workflow"]["nodeList"]) {
        if (!node.contains("entityDataList") || !node["entityDataList"].is_array()) {
            continue;
        }

        const bool matches_robot_solver =
            node.contains("algorithmMetadata")
            && node["algorithmMetadata"].is_object()
            && node["algorithmMetadata"].value("algorithmEnglishName", "") == "Evaluate_Update";

        const bool contains_robot_entity = std::any_of(
            node["entityDataList"].begin(),
            node["entityDataList"].end(),
            [](const json& entity) { return isRobotEntity(entity); });

        if (matches_robot_solver && contains_robot_entity) {
            selected_node = &node;
            break;
        }
        if (selected_node == nullptr && contains_robot_entity) {
            selected_node = &node;
        }
    }

    if (selected_node == nullptr) {
        return normalized;
    }

    if (needs_entity_workflow) {
        if (has_root_entity_data) {
            normalized["entityDataList"] =
                mergeEntityDataList(normalized["entityDataList"], (*selected_node)["entityDataList"]);
        } else {
            normalized["entityDataList"] = (*selected_node)["entityDataList"];
        }
    }

    if (needs_parameter_list
        && selected_node->contains("algorithmMetadata")
        && (*selected_node)["algorithmMetadata"].contains("parameterList")) {
        normalized["parameterList"] = (*selected_node)["algorithmMetadata"]["parameterList"];
    }

    return normalized;
}

void para_set_robot_solver(json j)
{
    clear_runtime_config(work_path + "config/");

    std::string robottemplate = work_path + "config/robot_template.json";
    std::string scenarioFile = work_path + "config/scenario.json";
    std::string tooltemplate = work_path + "config/tool_template.json";

    std::ifstream inputFile1(robottemplate);
    if (!inputFile1.is_open()) {
        throw std::runtime_error("Failed to open file: " + robottemplate);
    }
    json robot_template;
    inputFile1 >> robot_template;

    std::ifstream inputFile3(scenarioFile);
    if (!inputFile3.is_open()) {
        throw std::runtime_error("Failed to open file: " + scenarioFile);
    }
    json task_j;
    inputFile3 >> task_j;

    std::ifstream inputFile5(tooltemplate);
    if (!inputFile5.is_open()) {
        throw std::runtime_error("Failed to open file: " + tooltemplate);
    }
    json tool_template;
    inputFile5 >> tool_template;

    int file_idx = 1;
    for (const auto& entity : j["entityDataList"]) {
        if (!entity.contains("exampleList") || !entity["exampleList"].is_array()) {
            continue;
        }

        if (isTaskEntity(entity)) {
            for (const auto& example : entity["exampleList"]) {
                if (!example.contains("paramList") || !example["paramList"].is_array()) {
                    continue;
                }
                for (const auto& it : example["paramList"]) {
                    const std::string param_name = it.value("paramEnglishName", "");
                    if ((param_name == "task_duration" || param_name == "taskDuration") && it.contains("inputValue")) {
                        task_j["task_duration"] = it["inputValue"];
                    }
                }
            }
            continue;
        }

        if (isRobotEntity(entity)) {
            for (const auto& example : entity["exampleList"]) {
                json robot_j = robot_template;
                robot_j["ID"] = extractExampleId(example, file_idx);

                if (example.contains("workflow") && example["workflow"].is_object()) {
                    robot_j["workflow"] = standardizeWorkflow(example["workflow"]);
                }

                if (example.contains("paramList") && example["paramList"].is_array()) {
                    for (const auto &it : example["paramList"]) {
                        const std::string name = it.value("paramEnglishName", "");
                        if (!it.contains("inputValue")) {
                            continue;
                        }
                        const auto& val = it["inputValue"];

                        if (name == "single_work_time")
                            robot_j["normal_property"]["single_work_time"] = val;
                        else if (name == "out_travel_time")
                            robot_j["normal_property"]["out_travel_time"] = val;
                        else if (name == "return_travel_time")
                            robot_j["normal_property"]["return_travel_time"] = val;
                        else if (name == "work_time")
                            robot_j["normal_property"]["work_time"] = val;
                        else if (name == "continue_max_work" || name == "maxWorkCont")
                            robot_j["normal_property"]["continue_max_work"] = val;
                        else if (name == "maintenance_time")
                            robot_j["normal_property"]["maintenance_time"] = val;
                        else if (name == "charge_time")
                            robot_j["normal_property"]["charge_time"] = val;
                        else if (name == "carry_num")
                            robot_j["normal_property"]["carry_num"] = val;
                        else if (name == "limit_num")
                            robot_j["normal_property"]["limit_num"] = val;
                        else if (name == "cargo_type_num")
                            robot_j["normal_property"]["cargo_type_num"] = val;
                        else if (name == "cargo_type_list")
                            robot_j["list_property"]["cargo_type_list"] = val;
                        else if (name == "remain_work_time") {
                            robot_j["Custom"]["remain_work_time"] = val;
                            robot_j["normal_property"]["remain_work_time"] = val;
                        } else if (name == "type") {
                            robot_j["type"] = val;
                        }
                    }
                }

                std::string filename = work_path + "config/" + std::to_string(file_idx) + ".json";
                std::ofstream outputFile(filename);
                if (!outputFile.is_open()) {
                    throw std::runtime_error("Failed to open for writing: " + filename);
                }
                outputFile << std::setw(4) << robot_j << std::endl;
                outputFile.close();
                file_idx++;
            }
            continue;
        }

        if (isToolEntity(entity)) {
            for (const auto& example : entity["exampleList"]) {
                json tool_j = tool_template;
                tool_j["ID"] = extractExampleId(example, file_idx);

                if (example.contains("workflow") && example["workflow"].is_object()) {
                    tool_j["workflow"] = standardizeWorkflow(example["workflow"]);
                }

                if (example.contains("paramList") && example["paramList"].is_array()) {
                    for (const auto &it : example["paramList"]) {
                        const std::string name = it.value("paramEnglishName", "");
                        if (!it.contains("inputValue")) {
                            continue;
                        }
                        const auto& val = it["inputValue"];

                        if (name == "install_time")
                            tool_j["normal_property"]["install_time"] = val;
                        else if (name == "removal_time")
                            tool_j["normal_property"]["removal_time"] = val;
                        else if (name == "tool_rest_time")
                            tool_j["normal_property"]["tool_rest_time"] = val;
                        else if (name == "tool_work_time")
                            tool_j["normal_property"]["tool_work_time"] = val;
                        else if (name == "tool_out_time")
                            tool_j["normal_property"]["tool_out_time"] = val;
                        else if (name == "tool_return_time")
                            tool_j["normal_property"]["tool_return_time"] = val;
                        else if (name == "limit_num")
                            tool_j["normal_property"]["limit_num"] = val;
                        else if (name == "type")
                            tool_j["type"] = val;
                    }
                }

                std::string filename = work_path + "config/" + std::to_string(file_idx) + ".json";
                std::ofstream outputFile(filename);
                if (!outputFile.is_open()) {
                    throw std::runtime_error("Failed to open for writing: " + filename);
                }
                outputFile << std::setw(4) << tool_j << std::endl;
                outputFile.close();
                file_idx++;
            }
        }
    }

    std::ofstream outputFile3(scenarioFile);
    if (!outputFile3.is_open()) {
        throw std::runtime_error("Failed to open for writing: " + scenarioFile);
    }
    outputFile3 << std::setw(4) << task_j << std::endl;
    outputFile3.close();
}
