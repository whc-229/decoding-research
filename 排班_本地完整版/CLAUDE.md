# 解码研究 —— 给服务器上 Claude Code 的工作说明

本仓库是一篇 IEEE TEVC 论文的全部代码、实例和实验结果。主题：进化算法中"多对一（冗余）解码"的偏置与自由度，
应用于机器人–工具值岗排班，并在柔性作业车间（FJSP）公开基准上验证。

**分工**：claude.ai 上的对话（项目"解码研究"）负责构思和分析，会把要做的实验写进 `TASKS.md`；
你（服务器上的 Claude Code）负责实现、后台运行、核对和汇总，把结果写进 `报告/` 并提交。
项目文档（claude.ai 项目里的 `claude/实验*_结论.md`）是实验结论的正式记录，这里的 `报告/` 是原始汇总。

## 目录
- `src/ include/ build.sh`：C++ 版排班模拟与 NSGA-II（`./build.sh` 生成 `paiban_dec*`，Linux 上需要重新编译）。
- `requests/ requests_family/ requests_family2/`：排班实例（4 个场景 + 12 + 48 个实例族）。`exact/`：下界与等价的 Python 模型（mirror.py）。
- `实验0_表示分析/`：Python 部分（主要工作都在这里）
  - `exp0lib.py`（dec0～dec5 解码）、`sde.py`（稀疏偏离 dec6/dec9）、`ga.py`（Python NSGA-II 算子）
  - `rulegen/`：可插拔规则的稀疏偏离解码（ruledec.py）、LLM 规则进化（rulegen.py）、测试集验证（ga_rule.py、analyze_val.py）。训练/测试划分在 instances.py，**测试实例不得用于训练**。
  - `reroster/`：执行中扰动的重排班（core.py 模拟器、moea.py、analyze.py、scenarios.json、plans/）
  - `theory/`：规则距离模型（model.py）、扫描（sweep*.py）、平均场模型（meanfield.py）
  - `bench/`：FJSP 公开基准（fjsp-instances/、fjsp2.py 插空解码、moea_fjsp2.py、analyze_fjsp2.py）
  - `out*/`：各实验的特征与运行记录；`实验*_报告.md`：各实验报告
- LLM 接口配置：`实验0_表示分析/llm_config.json`（**不要打印或提交 api_key**；需要时用环境变量覆盖）。

## 环境
- Python ≥ 3.10，numpy，scipy；C++ 部分需要 g++（C++17）。
- 每个进程只用 1 个 BLAS 线程：`export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`（多进程时不设会把内存吃光）。
- 运行 rulegen/reroster 脚本前设 `PAIBAN_SRC=<仓库根目录>`（exp0lib 用它找 exact/ 和实例）。

## 规矩
1. **长任务一律后台运行并可续跑**（nohup/tmux）。所有 moea/ga 脚本都会跳过 CSV 里已有的 (实例, 臂, 次)，断了重跑同一条命令即可。
2. **一个 CSV 只能有一个写入进程**。并行请分到不同输出文件，最后合并去重。
3. 改动任何解码器后，先跑对应核对脚本，必须 0 不一致：`check_lib.py`、`check6.py`、`check9.py`、`rulegen/check_ruledec.py`、`reroster/test_core.py`、`bench/check_v2.py`。
4. 统计口径保持一致：每个实例内用所有臂的解统一归一化后算 HV；实例层面配对 Wilcoxon；逐实例 Mann-Whitney（p<0.05）。
5. 不要覆盖已有结果文件；新实验用新文件名，并在 `报告/` 里写一份简短汇总（设定、命令、结果表、异常）。
6. 遇到失败先查原因再重试，不要无限重试；需要决策的问题写进 `TASKS.md` 的"待确认"一节。

## 已完成的主要结果（细节见各报告）
- 排班：LLM 生成的默认规则在 47 个测试实例上比 dec5 高 +0.12～0.16 HV（rulegen/out/val_full.md）。
- 重排班：原计划作为解码偏置比旧解播种高 +0.18～0.21 HV（366 场景，reroster/main_report.md）。
- FJSP v2（插空）：稀疏偏离 sp0.5 对双段随机键 248/26（276 实例，5000 次）；20000 次时间隙 10.2% vs 22.3%（78 实例）。
- 理论：最优槽数小预算 ≈ d、大预算 ≈ d/q；最好解实际用到的偏离数 ≈ qK（编码自带的先验）。
