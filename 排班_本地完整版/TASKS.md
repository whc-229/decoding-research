# 任务队列（claude.ai 对话写入，服务器 Claude Code 执行）

格式：每个任务写明目的、命令或要实现的内容、输出文件、完成标准。完成后把状态改为 [完成]，并在 `报告/` 写汇总。

## 待做

> **实验冻结（2026-10-22）**：除了正在跑的 T10 和已排好的 FJSP T6～T9，不再新增实验，转入论文写作。
> 之后只有导师要求修改或审稿意见到来时，才会在这里加新任务（编号 R1、R2…，并注明来源）。
> 跑完 T10、T6～T9 后照常写报告、commit + push；不要自行扩展任务范围，有疑问写进"待确认"。

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

### T9 [待做] FJSP：规则放进初始种群 vs 放进解码器（启发式初始化对照）
- 目的：回答"稀疏编码的好处是否只来自好的起点"。三个新臂都用 rk 解码，只是初始种群不同（bench/seed_fjsp.py）：
  rk+seed（1 个规则解 + 29 个随机）、rk+glr（Zhang 等 2011 的 GS/LS/RS 初始化）、rk+glr+seed（1 个规则解 + 29 个 GLR）。
- 开始前：`cd bench && python check_seed.py`（必须"规则解不一致 0"，336 个实例），再跑 `python check_v2.py`（moea_fjsp2.py 有改动，默认编码行为不变）。
- T8 结束后，bench/ 下（与 T6 的 v3_big 同一批实例、同一预算、同一台机器；预计 2～4 小时）：
  ```
  nohup python moea_fjsp2.py rk+seed,rk+glr,rk+glr+seed 10 6 v3_big_seed.csv big 20000 > v3_big_seed.log 2>&1 &
  ```
- 完成后合并分析（与 v3_big 的 4 个编码统一归一化）：
  ```
  { cat v3_big.csv; tail -n +2 v3_big_seed.csv; } > v3_big_all.csv
  python analyze_fjsp2.py v3_big_all.csv report_v3_big_all.md
  ```
  汇总写 `报告/T9_启发式初始化.md`（运行情况 + 主表即可，解读我来做）。

### T10 [待做] 排班：扩展编码，比较更高的偏离密度（实验 5 任务 D，2026-10-22）
- 目的：现有基因布局最多只放得下 K0.5 的偏离槽，任务 C 只能在 {0.25, 0.5} 里选，"选出 K0.5"等于"越多越好直到上限"。
  扩展编码后比较 K ∈ {0.5, 0.75, 1.0}，看是否存在中间的最优点。只用训练实例选 K，判定规则事先写死。不改 rulegen/。
- 进程数：这台机器同时在跑 FJSP 任务（T6～T9）。开跑前看 `uptime`，两边加起来的进程数不超过物理核数；FJSP 在跑时本任务用 6 个以下。
- D1 新解码 `实验0_表示分析/neural/ruledec_ext.py`：基因布局改为 [2K 个偏离槽基因][1 个默认类型基因][每班 1 个工具基因]，
  K = ceil(kfrac × 班次上界)，基因长度随 K 变化；其余逻辑与 rulegen/ruledec.decode_rule 完全相同。
  自检：把 K0.25、K0.5 的旧布局基因映射到新布局，在 15 个训练实例 × 16 个基因上与 ruledec 逐解相同（必须 0 不一致）。
  先确认 ga.py 的变异概率是否按基因长度缩放（如 1/n），在报告里写明；不为不同 K 调算子参数。
- D2 训练实例 MOEA：15 个训练实例，NSGA-II 465 次，种子 5000+次号；
  臂 = K ∈ {0.5, 0.75, 1.0} × 8 条规则（ES16 s0～s2、GP run1～5）× 5 次；K0.5 用新解码重跑，与任务 C 的 K0.5 对照（自检）。
  同时用代理分（15 实例 × 67 基因，换成对应 K）给每个 K 打分，看代理分是否给出和 MOEA 相同的排序。输出新文件 neural/out/train_Kext.csv。
- D3 判定（跑 D2 之前写好代码并用假数据测试）：每个训练实例内统一归一化，方法层面对 8 条规则 × 5 次取平均，
  平均 HV 最高的 K 为最终 K；ES16、GP 两族分别报告，不一致时以合并结果为准。若最高的是边界 K1.0，报告"在 0.5～1.0 内单调上升"，不再往上加。
- D4 测试集：若选出的 K ≠ 0.5，补跑该 K × 8 条规则的测试集臂（NSGA-II 465）。另外把 K0.75、K1.0 × 8 条规则都跑一遍测试集，
  作为敏感性分析，报告里明确写"不用于选择 K"。写新文件 neural/out/val_Kext.csv（分析时与 val_server.csv 合并统一归一化）。
- D5 报告 `报告/实验5_D_扩展K.md`：训练与测试两条 K—HV 曲线（全部与 E/H/M），以及 C3 的 dev / 槽数在新 K 下的值。
  完成后在 `报告/待检验_偏离偏置与最优K.md` 的"现象"一节补一句 D 的结论。

### T12 [撤销 2026-10-22] 理论 + 排班：多余偏离的代价 λ
- 撤销原因：属于对细节的解释，论文主张不依赖它。论文中只写一句："好规则下最优偏离数大于到最近好解的距离；
  模型显示多目标、以及多余偏离代价低时都会出现，后者在排班上的定量检验留作后续工作。"不要开始做；若已有中间文件，保留即可。

## 待确认
（Claude Code 遇到需要决策的问题写在这里）

- [2026-10-22，给负责 FJSP 的会话] **T9 没有排进任何调度脚本**：run_T8.sh 只跑 T8，T8 结束后 T9 不会自动开始。
  需要在 T8 结束后手动启动 T9（命令见上面 T9 一节，先跑 check_seed.py 和 check_v2.py），或另加一个调度脚本。
- [2026-10-22] T12 已撤销；停之前的中间文件未提交、留在原处（theory/analyze_t12.py、neural/lambda_cost.py、neural/out/lambda/、
  theory/T12_撤销_中间文件/）。不要删，也不要提交；以后若审稿需要再用。

- ~~T3 实际耗时远超预估~~（已解决：继续跑完 5 次，2026-10-21 02:06 结束，共 14.6 小时）。T6 的"约 10 小时"可能也偏乐观。

- [2026-10-20 实验 5] **DeepSeek 余额用完（402）**：rulegen 消融 full_s2、EoH run2/run3 已完成；full_s3（21 个候选）、score_s2（19）、
  score_s3（23）、EoH run1（34 个样本）停在半途，可从断点续跑。充值后在 实验0_表示分析/neural/ 下运行 `bash resume_llm.sh` 即可
  （会把测试集验证临时降到 6 个进程）。参考用量：EoH 每次运行约 60～100 次调用、输入 12～18 万 token、输出 40～52 万 token。

## 已完成
（移到这里）

### T11 [完成] 理论：偏离偏置与最优 K（交给负责实验 6 理论的一方，2026-10-22）
- 读 `报告/待检验_偏离偏置与最优K.md`，在 `实验0_表示分析/theory/` 的抽象模型（model.py / meanfield.py）里做文中的检验 A（偏离值有偏）和 B（多个目标解）。
- 结果写 `报告/T11_偏离偏置与最优K.md`，并把结论补到 `报告/待检验_偏离偏置与最优K.md` 末尾。计算量小，可与其他任务并行（用 1～2 个进程）。
- 结果：A（偏离值有偏）不能复现，d 小时最优 K 仍 ≈ 2～8、K 加倍变差；B（多目标）部分复现，最优 K 跟随平均 d 而非最近 d，但 465 次时加倍仍变差；额外对照 D（多余偏离代价 λ 小）可复现。C3 数据里中位 dev / K0.25 槽数全在 0.88～1.82。见 `报告/T11_偏离偏置与最优K.md`。2026-10-22

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
