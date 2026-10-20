# 实验0_表示分析：给 Claude Code 的项目说明

研究：进化算法中"多对一（冗余）解码"，应用于机器人-工具值岗排班（双目标：资源数最少、均衡度最好；NSGA-II，种群 30，465 次评价），目标期刊 IEEE TEVC。
用户用中文交流，报告也用中文；结论写清楚数字和统计口径，不夸大。

## 当前任务（实验 5）：解码规则从哪里来——手写 / 遗传规划 / 神经网络 / LLM
完整交接（目标、进度、已验证的事、下一步、注意事项）见 **neural/交接说明.md**，开始前先读它。

## 目录
- exp0lib.py、sde.py、ga.py：解码器（dec0～dec5）与 NSGA-II；../exact/mirror.py：模拟器（与 C++ 逐解核对过）
- rulegen/：可插拔规则的稀疏偏离解码（ruledec.py）、代理打分（evalrule.py）、LLM 规则进化（rulegen.py）、训练/测试划分（instances.py）、测试集验证（ga_rule.py）
- reroster/：执行中扰动的重排班（实验 4b，已完成）
- neural/：实验 5 的新代码与结果
- bench/：FJSP 公开基准（另一条线，由另一个对话负责，不要改动或重跑）
- 实验0～3b_报告.md：早期实验的完整报告

## 硬性约定
- 不修改 rulegen/、reroster/、bench/ 里的已有文件；需要接口改动先问用户。新代码放 neural/。
- 测试集实例（instances.split() 的第二个返回值，47 个）绝不能用于训练、调参或规则生成。
- 统计口径：实例内用所有臂统一归一化 HV；实例层面配对 Wilcoxon；逐实例 Mann-Whitney（p<0.05 计好/差）；分全部、原/E/H/M 组报告。
- 长任务一律可续跑，在 tmux 里跑；进程数默认 auto（核数 − 1）。
- LLM 接口配置在 llm_config.json（OpenAI 兼容，DeepSeek）。任何输出、日志都不要打印 api_key。
- 同一台机器上 MOEA 结果完全确定；不同机器/numpy 版本之间不逐位一致，所以对比用的全部臂必须在同一台机器上跑。
