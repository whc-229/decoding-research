# 任务队列（claude.ai 对话写入，服务器 Claude Code 执行）

格式：每个任务写明目的、命令或要实现的内容、输出文件、完成标准。完成后把状态改为 [完成]，并在 `报告/` 写汇总。

## 待做

**通用约定（T3～T7）**：在 `实验0_表示分析/` 下运行；先 `export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=/home/hk/解码研究/排班_本地完整版`。
机器有 8 个物理核，另一个对话（neural/）也会用这台机器：**进程数用 6**，开跑前看一眼 `uptime`，负载已经很高就等一等或用 4。
按 T3 → T4 → T5 → T6 → T7 的顺序一个一个跑（同一时间只跑一个任务）。每个任务跑完：运行分析命令、在 `报告/` 写汇总、commit + push，再开始下一个。
本次提交改动了 bench/fjsp2.py（新增 q 参数）和 bench/moea_fjsp2.py（新增 MOEA/D），默认行为不变：开始前先跑 `cd bench && python check_v2.py`（必须 0 不一致），
并抽查 `python moea_fjsp2.py rk,sp0.25 1 2 /tmp/x.csv mk01 2000` 的 465 次结果应与 v2_main.csv 中 mk01 第 0 次相同（rk：55:199;66:195;69:190；sp0.25：45:162;46:161;47:160;49:157）。

### T6 [待做] FJSP：主实验最终版（单机、20 次）
- 目的：论文最终数字全部来自同一台机器、每个实例 20 次。bench/ 下，两条依次跑（共约 10 小时，适合过夜）：
  ```
  nohup python moea_fjsp2.py pd,rk,sp0.1,sp0.25,sp0.5 20 6 v3_main.csv main 5000 > v3_main.log 2>&1 &
  # 上一条结束后：
  nohup python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 6 v3_big.csv big 20000 > v3_big.log 2>&1 &
  ```
- 完成后分别 `python analyze_fjsp2.py v3_main.csv report_v3_main.md`、`... v3_big.csv report_v3_big.md`，汇总写 `报告/T6_FJSP最终版.md`。
- **中期快照（2026-10-21 新增，不要停主进程）**：v3_main.csv 中第 0～9 次全部齐了以后（每个 (实例, 编码, 次) 都有 465/2000/5000 三行），
  把这部分抽出来另存为 `bench/v3_main_r10.csv`（只读 v3_main.csv、另写新文件，不影响正在写入的进程），commit + push，在 `报告/T6_FJSP最终版.md` 记一句快照时间。
  判断"齐了"可以用：
  ```
  python -c "import csv,collections as C;c=C.Counter((r[0],r[1]) for r in csv.reader(open('v3_main.csv')) if r and r[0]!='instance' and r[3]=='5000' and int(r[2])<10);print(len(c),sum(v==10 for v in c.values()))"
  ```
  两个数都等于 276×5=1380 即可（实例数以 main 的实际数为准）。抽取：表头 + `int(run)<10` 的行。主进程照常跑到 20 次。

### T7 [待做] FJSP：Behnke（60 个大实例，原 T2）
- bench/ 下：`nohup python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 6 v3_behnke.csv behnke 5000 > v3_behnke.log 2>&1 &`
- 完成后 `python analyze_fjsp2.py v3_behnke.csv report_v3_behnke.md`，汇总写 `报告/T7_Behnke.md`。

### T8 [待做] FJSP：T3 扫描补点（q = 0.2 的槽数扩到 1.0 以上）
- 目的：T3 中 q = 0.2 的最优槽数顶在网格上限 f = 1.0，"最优期望偏离数随预算变化"一条在 q = 0.2 上被网格截断；补点后还多出一组 q·f = 0.30 的配对（1.5q0.2 / 0.75q0.4 / 0.5q0.6）。
- T7 结束后，bench/ 下（同 T3 的 30 个实例，约 2 小时）：
  ```
  I=$(python -c "import fjsp2 as F;M=F.meta();print(','.join([n for n,d in M.items() if d['path'].startswith('brandimarte')]+['r-la%02d'%i for i in range(16,31)]))")
  nohup python moea_fjsp2.py sp1.5q0.2,sp2.0q0.2,sp3.0q0.2 5 6 v3_qk2.csv $I 20000 > v3_qk2.log 2>&1 &
  ```
- 输出 v3_qk2.csv（新文件，不要写进 v3_qk.csv；分析时我会和 v3_qk.csv 合并统一归一化）。在 `报告/T8_qk补点.md` 写运行情况即可。必须和 v3_qk.csv 在同一台机器上跑。

## 待确认
（Claude Code 遇到需要决策的问题写在这里）

- ~~T3 实际耗时远超预估~~（已解决：继续跑完 5 次，2026-10-21 02:06 结束，共 14.6 小时）。T6 的"约 10 小时"可能也偏乐观。

- [2026-10-20 实验 5] **DeepSeek 余额用完（402）**：rulegen 消融 full_s2、EoH run2/run3 已完成；full_s3（21 个候选）、score_s2（19）、
  score_s3（23）、EoH run1（34 个样本）停在半途，可从断点续跑。充值后在 实验0_表示分析/neural/ 下运行 `bash resume_llm.sh` 即可
  （会把测试集验证临时降到 6 个进程）。参考用量：EoH 每次运行约 60～100 次调用、输入 12～18 万 token、输出 40～52 万 token。

## 已完成
（移到这里）

### T5 [完成] FJSP：MOEA/D 对照（检验结论与搜索算法无关）
- bench/ 下：`nohup python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 6 v3_moead.csv big 5000 moead > v3_moead.log 2>&1 &`
- 完成后：`python analyze_fjsp2.py v3_moead.csv report_v3_moead.md`，汇总写 `报告/T5_MOEAD.md`。
- 结果：78 实例 × 4 编码 × 10 次全部完成（6 进程，113 分钟）；5000 次时 sp0.5 对 rk +0.428 HV，75/0。见 `报告/T5_MOEAD.md`。2026-10-21

### T4 [完成] 排班：测试集验证扩到 20 次（单机重跑）
- 在 rulegen/ 下：`nohup python ga_rule.py dec5,K0.25:default,K0.25:out/full/best_rule.py,K0.25:out/score_best_rule.py 20 6 out/val20.csv test > out/val20.log 2>&1 &`
- 完成后：`python analyze_val.py out/val20.csv out/val20.md`，在 `报告/T4_测试集20次.md` 摘录"全部"和各组的表。
- 结果：47 实例 × 4 臂 × 20 次全部完成（4 进程，350 分钟）；两条 LLM 规则对 dec5 +0.154/+0.155 HV。H01_720h dec5 第 11 次无可行解。见 `报告/T4_测试集20次.md`。2026-10-21

### T3 [完成] FJSP：槽数 × 生效概率扫描（检验解析模型，最优先）
- 目的：理论预测①最好解的偏离数 ≈ qK；②大预算下最优槽数 K 与 q 成反比（K·q ≈ 常数）；③小预算下最优 K 更小。编码名 `sp{比例}q{q}`，q = 随机基因下每个槽生效的概率（默认 0.4）。
- 命令（bench/ 下，约 2～3 小时）：
  ```
  E=rk; for f in 0.05 0.1 0.2 0.35 0.5 0.75 1.0; do for q in 0.2 0.4 0.6; do E=$E,sp${f}q${q}; done; done
  I=$(python -c "import fjsp2 as F;M=F.meta();print(','.join([n for n,d in M.items() if d['path'].startswith('brandimarte')]+['r-la%02d'%i for i in range(16,31)]))")
  nohup python moea_fjsp2.py $E 5 6 v3_qk.csv $I 20000 > v3_qk.log 2>&1 &
  ```
- 输出：v3_qk.csv（30 个实例 × 22 种编码 × 5 次，检查点 465/2000/5000/10000/20000）。分析我来做；你只需在 `报告/T3_qk扫描.md` 写运行情况（耗时、是否完整、异常）。
- 结果：3300 组全部完成、无异常，用时 14.6 小时（6 进程）。见 `报告/T3_qk扫描.md`。2026-10-21

### T1 [完成] 环境搭建与核对
- 安装依赖，`./build.sh` 编译 C++；设置 PAIBAN_SRC 和 BLAS 线程环境变量。
- 运行全部核对脚本（见 CLAUDE.md 规矩 3），全部 0 不一致才算完成。
- 用一个小实例各跑一次：`实验0_表示分析/bench/moea_fjsp2.py rk,sp0.25 1 2 /tmp/t.csv k1 2000`、`rulegen/ga_rule.py dec5 1 2 /tmp/g.csv E11_480h`。
- 输出：`报告/T1_环境核对.md`（机器配置、CPU 核数、各核对结果、单次运行耗时）。
- 结果：6 个核对脚本全部 0 不一致，两次小样例正常（见 `报告/T1_环境核对.md`）。2026-10-20
