# 任务队列（claude.ai 对话写入，服务器 Claude Code 执行）

格式：每个任务写明目的、命令或要实现的内容、输出文件、完成标准。完成后把状态改为 [完成]，并在 `报告/` 写汇总。

## 待做

### T1 [待做] 环境搭建与核对
- 安装依赖，`./build.sh` 编译 C++；设置 PAIBAN_SRC 和 BLAS 线程环境变量。
- 运行全部核对脚本（见 CLAUDE.md 规矩 3），全部 0 不一致才算完成。
- 用一个小实例各跑一次：`实验0_表示分析/bench/moea_fjsp2.py rk,sp0.25 1 2 /tmp/t.csv k1 2000`、`rulegen/ga_rule.py dec5 1 2 /tmp/g.csv E11_480h`。
- 输出：`报告/T1_环境核对.md`（机器配置、CPU 核数、各核对结果、单次运行耗时）。

### T2 [待做] FJSP：Behnke 实例（60 个，最多 500 道工序）
- `python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 5 <进程数> v2_behnke.csv behnke 5000`（在 实验0_表示分析/bench/ 下）
- 输出：v2_behnke.csv、`python analyze_fjsp2.py v2_behnke.csv report_v2_behnke.md`。

## 待确认
（Claude Code 遇到需要决策的问题写在这里）

## 已完成
（移到这里）
