# 任务队列（claude.ai 对话写入，服务器 Claude Code 执行）

格式：每个任务写明目的、命令或要实现的内容、输出文件、完成标准。完成后把状态改为 [完成]，并在 `报告/` 写汇总。

## 待做

> **实验冻结（2026-10-22）**：除了正在跑的 T10 和已排好的 FJSP T6～T9，不再新增实验，转入论文写作。
> 之后只有导师要求修改或审稿意见到来时，才会在这里加新任务（编号 R1、R2…，并注明来源）。
> 例外：R0（2026-10-23，claude.ai 对话与用户商定后补的一项，见下）；T13（2026-10-23，用户同意的已有方法对照，见下）。
> 跑完 T10、T6～T9 后照常写报告、commit + push；不要自行扩展任务范围，有疑问写进"待确认"。

**通用约定（T3～T7）**：在 `实验0_表示分析/` 下运行；先 `export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=/home/hk/解码研究/排班_本地完整版`。
机器有 8 个物理核，另一个对话（neural/）也会用这台机器：**进程数用 6**，开跑前看一眼 `uptime`，负载已经很高就等一等或用 4。
按 T3 → T4 → T5 → T6 → T7 的顺序一个一个跑（同一时间只跑一个任务）。每个任务跑完：运行分析命令、在 `报告/` 写汇总、commit + push，再开始下一个。
本次提交改动了 bench/fjsp2.py（新增 q 参数）和 bench/moea_fjsp2.py（新增 MOEA/D），默认行为不变：开始前先跑 `cd bench && python check_v2.py`（必须 0 不一致），
并抽查 `python moea_fjsp2.py rk,sp0.25 1 2 /tmp/x.csv mk01 2000` 的 465 次结果应与 v2_main.csv 中 mk01 第 0 次相同（rk：55:199;66:195;69:190；sp0.25：45:162;46:161;47:160;49:157）。

### T10 [完成] 排班：扩展编码，比较更高的偏离密度（实验 5 任务 D，2026-10-22）
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
- D3b 变异概率对照（2026-10-22 15:59 加入的固定规则）：**只有当 X0.75 或 X1.0 在训练实例上输给 X0.5 时**，才补一组对照——
  变异概率按 X0.5 的基因长度计算（每个偏离槽的期望变异次数与 X0.5 相同），15 个训练实例 × {X0.75, X1.0} × 8 条规则 × 5 次，其余设置不变；否则不做。
  "输给"按 D3 的判定口径：8 条规则合并的平均 HV（每个训练实例内统一归一化）低于 X0.5。
  **注意时间顺序**：这条规则加入时 D2 已经跑完、D3 已出结果，所以它不是在看到 D2 结果之前写死的。
  按该规则判断：合并 X0.5 0.5416、X0.75 0.5910、X1.0 0.5997，两者都没有输给 X0.5（ES16、GP 两族也都没有输）→ **不做对照**。
- D4 测试集：若选出的 K ≠ 0.5，补跑该 K × 8 条规则的测试集臂（NSGA-II 465）。另外把 K0.75、K1.0 × 8 条规则都跑一遍测试集，
  作为敏感性分析，报告里明确写"不用于选择 K"。写新文件 neural/out/val_Kext.csv（分析时与 val_server.csv 合并统一归一化）。
- D5 报告 `报告/实验5_D_扩展K.md`：训练与测试两条 K—HV 曲线（全部与 E/H/M），以及 C3 的 dev / 槽数在新 K 下的值。
  完成后在 `报告/待检验_偏离偏置与最优K.md` 的"现象"一节补一句 D 的结论。
- 进度（2026-10-22 16:00）：D1 自检 1440 个解码 0 不一致；D2 完成；D3 选出 K = 1.0（边界，0.5～1.0 内单调上升；ES16 族单独看是 X0.75）。
  D4 起初按旧脚本追加到了 val_server.csv（25 行），已停下、把这 25 行移到 neural/out/val_Kext.csv、val_server.csv 恢复原样，改为写 val_Kext.csv 续跑（6 个进程）。
- 结果（2026-10-23 01:25 完成）：训练与测试曲线形状相同——K0.25 → K0.75 上升，K0.75 → K1.0 饱和（训练 +0.005 p = 0.52，测试 +0.003 p = 0.54）；
  E 组数值上超过 dec5 但不显著。报告 报告/实验5_D_扩展K.md，待检验_偏离偏置与最优K.md 的"现象"一节已补。

### T12 [撤销 2026-10-22] 理论 + 排班：多余偏离的代价 λ
- 撤销原因：属于对细节的解释，论文主张不依赖它。论文中只写一句："好规则下最优偏离数大于到最近好解的距离；
  模型显示多目标、以及多余偏离代价低时都会出现，后者在排班上的定量检验留作后续工作。"不要开始做；若已有中间文件，保留即可。

## 待确认
（Claude Code 遇到需要决策的问题写在这里）

- **[2026-10-23] 已决定（用户确认）**：
  - 排班 T4 中 dec5 在 H01_720h 第 11 次没有可行解：与其他分析相同，按 HV = 0 计，不单独处理；表注写明。
  - FJSP T6 用完整 20 次的 v3_main.csv，中期快照 v3_main_r10.csv 只作备份，分析不用。
  - 所有实验已完成，机器上没有任务；之后只有导师或审稿意见才加 R 系列任务。

- **[2026-10-23 T7] Behnke 间隙的参考值**：instances.json 中 Behnke 没有最优值，`fjsp2.refs` 用数据集上界当 BKS；这些上界很弱（纯规则间隙只有 0.007；60 个实例中有 40 个找到了低于上界的解；多个实例共用同一上界，如 87 出现 6 次）。没有任何解低于下界。论文里 Behnke 的间隙是改用下界计算，还是只报告 HV，需要决定。代码未改动。
  → **已决定（2026-10-23，用户确认）**：只报 HV 和赢/输，不报间隙（下界也很弱，如 lar04_5 上界 537、下界 101）；不写"超过已知最好解"。见项目文档 claude/实验6续_FJSP最终结果.md。

- [2026-10-22，给负责 FJSP 的会话] **T9 没有排进任何调度脚本**：run_T8.sh 只跑 T8，T8 结束后 T9 不会自动开始。
  需要在 T8 结束后手动启动 T9（命令见上面 T9 一节，先跑 check_seed.py 和 check_v2.py），或另加一个调度脚本。
  → **已处理，2026-10-23 01:28 按新顺序重排**：TASKS 改为"T6 big → T9 → T7 → T8"后，停掉了 run_T3_T7.sh 与 run_T9.sh 两个调度外壳
  （T6b 的计算进程未中断，继续跑完），换成 `报告/run_T6b_T9_T7.sh`：等 T6b 进程结束 → 续跑同一命令补齐并分析、写 T6b.done →
  T9（先跑 check_seed.py、check_v2.py，任一不为 0 就停；运行后合并成 v3_big_all.csv 并分析）→ T7。run_T8.sh 未动，仍在 T7.done 后接 T8。
  已有进程在写 v3_big_seed.csv 时 T9 不启动，**不要再手动启动 T9**。各任务报告仍由负责 FJSP 的会话写。run_T9.sh 已停用（保留文件）。
- [2026-10-22] T12 已撤销；停之前的中间文件未提交、留在原处（theory/analyze_t12.py、neural/lambda_cost.py、neural/out/lambda/、
  theory/T12_撤销_中间文件/）。不要删，也不要提交；以后若审稿需要再用。

- ~~T3 实际耗时远超预估~~（已解决：继续跑完 5 次，2026-10-21 02:06 结束，共 14.6 小时）。T6 的"约 10 小时"可能也偏乐观。

- [2026-10-20 实验 5] **DeepSeek 余额用完（402）**：rulegen 消融 full_s2、EoH run2/run3 已完成；full_s3（21 个候选）、score_s2（19）、
  score_s3（23）、EoH run1（34 个样本）停在半途，可从断点续跑。充值后在 实验0_表示分析/neural/ 下运行 `bash resume_llm.sh` 即可
  （会把测试集验证临时降到 6 个进程）。参考用量：EoH 每次运行约 60～100 次调用、输入 12～18 万 token、输出 40～52 万 token。

## 已完成
（移到这里）

### T13 [完成] 最接近的已有方法作为对照（用户 2026-10-23 同意的新实验，来源：新颖性检查）
- **目的**：审稿人最可能问"这不就是 LDS / 迭代贪心 / 启发式空间搜索吗"。用同一规则、同一预算比较四种最接近的做法：
  1. **db / D（稠密有偏逐步编码，HBSS / LDS 的逐步版本）**：每步一个基因，以概率 ρ 偏离规则首选，偏离语义与 RDD 相同。
     等价于"每步一个固定位置的偏离槽"——与 RDD 的唯一区别是偏离位置不可进化。**这是对"稀疏偏离槽"这一形式本身的消融，最重要。**
  2. **hs（启发式空间，Storer 等 1992；Dorndorf & Pesch 1995）**：每步一个基因选 6 条派工规则之一（只在 FJSP 上做）。
  3. **ps（问题空间，Storer 等 1992）**：基因扰动加工时间，规则在扰动数据上构造、真实数据上重放（只在 FJSP 上做）。
  4. **pls / P（偏离空间上的 Pareto 局部搜索，LNS / 迭代贪心思想）**：编码与 RDD 相同，不用种群和交叉，从规则解出发每次重抽 j 个偏离槽。
- **新代码（只新增文件，不改已有文件）**：`bench/fjsp_base3.py`、`bench/moea_fjsp3.py`、`bench/check_base3.py`、`bench/choose_t13.py`；
  `neural/base3.py`、`neural/check_base3.py`、`neural/choose_t13.py`。各文件开头有说明。
- **开跑前自检**（必须全部通过）：
  - `cd bench && python check_base3.py`：0 不一致（db 与固定位置 sp 逐解相同；ps 在 ε = 0、hs 全选 ECT 时等于规则解）。
  - `python moea_fjsp3.py rk,sp0.5 1 2 /tmp/t13chk.csv mk01 20000`，再与 `v3_big.csv` 中 mk01 第 0 次的五个检查点逐行比较前沿，必须相同（说明外包一层没有改变原有臂）。
  - `cd neural && python check_base3.py`：0 不一致。
- **第 1 步 FJSP 调参**（pilot 集 = Hurink rdata la16～la30，15 个实例，**不在 big 集里**）：
  `python moea_fjsp3.py rk,sp0.5,hs,db0.04,db0.1,db0.2,db0.4,ps0.05,ps0.1,ps0.2,ps0.4,pls1:sp0.5,pls2:sp0.5,pls4:sp0.5 5 6 pilot_t13.csv pilot 5000`
  然后 `python choose_t13.py pilot_t13.csv 5000`（判定规则已写死：每族取 5000 次时平均 HV 最高的参数）→ choose_t13.json。约 1050 次运行。
- **第 2 步 FJSP 主比较**（big 集 78 个实例 × 10 次 × 20000 次评价，与 v3_big_all.csv 同设置、同种子）：
  `python moea_fjsp3.py hs,<选中的 db>,<选中的 ps>,<选中的 pls> 10 6 v3_big_t13.csv big 20000`
  合并：`{ cat v3_big_all.csv; tail -n +2 v3_big_t13.csv; } > v3_big_all13.csv`，`python analyze_fjsp2.py v3_big_all13.csv report_v3_big_all13.md`。
  另算（报告里给出）：四个新臂各自对 sp0.5 的配对 Wilcoxon（Holm 校正，族 = 4 个臂 × 5 个检查点 = 20 个检验）与逐实例 Mann-Whitney 好/差计数。约 3120 次运行。
- **第 1b 步 FJSP 网格上扩（2026-10-23 22:40 加，必须在第 2 步开始前完成）**：第 1 步选中的 db0.4、pls4 都在网格上端，按"选中值在边界就往外扩一次"补点。
  - **不要修改正在运行的 run_T13.sh**（bash 边读边执行，改文件会出错）。现在就另开一个 tmux 窗口，与第 3 步并行跑，进程数 2：
    `cd bench && python moea_fjsp3.py db0.6,pls8:sp0.5,pls16:sp0.5 5 2 pilot_t13b.csv pilot 5000`（225 次运行，新文件，同种子）
  - 跑完后：`cp choose_t13.json choose_t13_v1.json && python choose_t13.py pilot_t13.csv,pilot_t13b.csv 5000`（choose_t13.py 已加入新候选，17 个臂合并归一化）。
    新的 choose_t13.json 会被第 2 步读取。若再次选中新的边界值（db0.6 或 pls16），**不再继续扩**，就用它，并在报告里写明"仍在网格上端"。
  - 若第 3 步结束时第 1b 步还没跑完：在第 2 步开始前停下调度（kill 调度进程，标记机制可续跑），等 1b 完成后重新启动 run_T13.sh。
- **第 1c 步 + 第 2b 步：规则组合偏离 spr（用户 2026-10-23 22:31 同意加；看到 pilot 上 hs 最好之后设计的变体，论文中须注明）**
  - 编码见 `bench/fjsp_base3.py` 开头：偏离槽与 sp 完全相同，只把"偏离时在其余候选里均匀选"换成"在 ECT 以外 5 条规则的首选里选"。`check_base3.py` 已加 spr 的核对（756 项 0 不一致）。
  - 第 1c 步（pilot，与 1b 一样与第 3 步并行、2 个进程，新文件）：
    `cd bench && python moea_fjsp3.py spr0.1,spr0.25,spr0.5,spr1.0,spr2.0 5 2 pilot_t13c.csv pilot 5000`（375 次运行）
  - 1b、1c 都跑完后再判定一次：`python choose_t13.py pilot_t13.csv,pilot_t13b.csv,pilot_t13c.csv 5000`（覆盖 choose_t13.json；旧的已存为 choose_t13_v1.json）。
    若 spr 选中 spr2.0（网格上端），不再扩，照用并在报告注明。
  - 第 2b 步（big 集，78 个实例 × 10 次 × 20000 次评价，同种子）：`python moea_fjsp3.py <选中的 spr> 10 6 v3_big_t13b.csv big 20000`。
    如果第 2 步已经按旧 json 开跑，不要停它，2b 单独跑即可；分析时把 v3_big_all.csv、v3_big_t13.csv、v3_big_t13b.csv 合并统一归一化，
    并补算 spr 对 hs、对 sp0.5 的配对 Wilcoxon（与第 2 步的 20 个检验合为一族做 Holm）。约 780 次运行。
- **附带记录（2026-10-23）**：Hurink 全部 198 个、Barnes 全部 21 个、Dauzère 18 个中的 9 个实例，每道工序在所有可选机器上的加工时间相同，
  所以总负荷是常数，这些实例上的双目标问题实际只有 makespan（前沿只有 1 个点）。分析不用改，报告里注明即可。
- **第 3 步 排班调参**（15 个训练实例，8 条规则 × 5 次，NSGA-II 465，种子 5000 + 次号）：臂 = D0.2、D0.4、D0.6、P1、P2、P4，每个 × 8 条规则，
  臂名写成 `D0.4:ES16(s0)=D0.4:nn:out/es/il_h16/best.npz`、`P2:GP(run1)=P2:X1.0:../neural/out/gp/run1/best_rule.py`（规则路径同 run_R0.sh 的 rules()）。
  `python base3.py "<48 个臂>" 5 6 out/train_t13.csv train --seed-base 5000`，然后 `python choose_t13.py out/train_t13.csv` → out/choose_t13.json。约 3600 次运行。
- **第 4 步 排班测试集**（47 个测试实例，8 条规则 × 5 次，种子 1000 + 次号，与 val_Kext.csv 相同）：只跑第 3 步选中的 D 与 P → `out/val_t13.csv`。约 3760 次运行。
  分析：与 val_Kext.csv 的 X1.0 臂（最终方法 ρ = 0.4）和 val_server.csv 的 dec5 合并，每个实例内统一归一化；方法层面对 8 条规则 × 5 次取平均；
  报告 D、P 各自对 X1.0 与对 dec5 的差（Holm 校正，族 = 4 个检验）、逐实例 Mann-Whitney 好/差，并按 E/H/M 分组。
- **顺序与进程**：第 1 步 → 第 3 步 → 第 2 步 → 第 4 步，一次一个，进程数 6（看 uptime）。所有臂必须在服务器上跑（与已有结果同一台机器）。
- **报告**：`报告/T13_已有方法对照.md`（设定、命令、判定结果、主表、异常）。只写运行情况和数字，解读由 claude.ai 对话负责。
- **注意**：claude.ai 对话在云端容器里只做了小样试跑（3 个实例 × 1 次），数字不作数；第 1 步的 pilot 在容器里也开了一份，只用来提前看方向，正式判定以服务器的 pilot_t13.csv 为准。
- 结果：全部步骤完成（1 → 3 → 1b/1c/重新判定 → 2 → 2b → 4）。FJSP 选中 db0.4 / ps0.1 / pls8 / spr2.0，排班选中 D0.2 / P4；FJSP 最终补算 Holm 30 检验见 bench/stats_t13_final.md，排班第 4 步见 neural/out/stats_t13_val.md。见 `报告/T13_已有方法对照.md`。2026-10-26

### T8 [完成] FJSP：T3 扫描补点（q = 0.2 的槽数扩到 1.0 以上）
- 目的：T3 中 q = 0.2 的最优槽数顶在网格上限 f = 1.0，"最优期望偏离数随预算变化"一条在 q = 0.2 上被网格截断；补点后还多出一组 q·f = 0.30 的配对（1.5q0.2 / 0.75q0.4 / 0.5q0.6）。
- T7 结束后，bench/ 下（同 T3 的 30 个实例，约 2 小时）：
  ```
  I=$(python -c "import fjsp2 as F;M=F.meta();print(','.join([n for n,d in M.items() if d['path'].startswith('brandimarte')]+['r-la%02d'%i for i in range(16,31)]))")
  nohup python moea_fjsp2.py sp1.5q0.2,sp2.0q0.2,sp3.0q0.2 5 6 v3_qk2.csv $I 20000 > v3_qk2.log 2>&1 &
  ```
- 输出 v3_qk2.csv（新文件，不要写进 v3_qk.csv；分析时我会和 v3_qk.csv 合并统一归一化）。在 `报告/T8_qk补点.md` 写运行情况即可。必须和 v3_qk.csv 在同一台机器上跑。
- 结果：30 实例 × 3 编码 × 5 次全部完成（6 进程，91 分钟），可与 v3_qk.csv 直接拼接。见 `报告/T8_qk补点.md`。2026-10-23

### T7 [完成] FJSP：Behnke（60 个大实例，原 T2）
- bench/ 下：`nohup python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 6 v3_behnke.csv behnke 5000 > v3_behnke.log 2>&1 &`
- 完成后 `python analyze_fjsp2.py v3_behnke.csv report_v3_behnke.md`，汇总写 `报告/T7_Behnke.md`。
- 结果：60 实例 × 4 编码 × 10 次全部完成（6 进程，518 分钟）；sp 三档对 rk 全部 60/0。Behnke 的参考上界偏弱，间隙列不可比（见待确认）。见 `报告/T7_Behnke.md`。2026-10-23

### T9 [完成] FJSP：规则放进初始种群 vs 放进解码器（启发式初始化对照）
- 目的：回答"稀疏编码的好处是否只来自好的起点"。三个新臂都用 rk 解码，只是初始种群不同（bench/seed_fjsp.py）：
  rk+seed（1 个规则解 + 29 个随机）、rk+glr（Zhang 等 2011 的 GS/LS/RS 初始化）、rk+glr+seed（1 个规则解 + 29 个 GLR）。
- 开始前：`cd bench && python check_seed.py`（必须"规则解不一致 0"，336 个实例），再跑 `python check_v2.py`（moea_fjsp2.py 有改动，默认编码行为不变）。
- **顺序调整（2026-10-22）：T6 big 完成后先跑 T9，再跑 T7、T8**（T9 对论文结论更关键）。bench/ 下（与 T6 的 v3_big 同一批实例、同一预算、同一台机器；预计 3～8 小时）：
  ```
  nohup python moea_fjsp2.py rk+seed,rk+glr,rk+glr+seed 10 6 v3_big_seed.csv big 20000 > v3_big_seed.log 2>&1 &
  ```
- 完成后合并分析（与 v3_big 的 4 个编码统一归一化）：
  ```
  { cat v3_big.csv; tail -n +2 v3_big_seed.csv; } > v3_big_all.csv
  python analyze_fjsp2.py v3_big_all.csv report_v3_big_all.md
  ```
  汇总写 `报告/T9_启发式初始化.md`（运行情况 + 主表即可，解读我来做）。
- 结果：78 实例 × 3 臂 × 10 次全部完成（4 进程，217 分钟），核对 0 不一致；合并分析 report_v3_big_all.md。见 `报告/T9_启发式初始化.md`。2026-10-23

### R0 [完成] 排班：偏离率扫描——在 κ = 1.0 下提高生效概率 q（冻结后补，2026-10-23）
- 目的：排班上只改过 κ（q 固定 0.4），最大偏离率 q·κ 只到 0.4，只看到"先升后饱和"，没看到"自由度太多变差"的一段。
  FJSP（报告/T3_分析.md）在 q·f 上有清楚的中间最优点（465 次：q = 0.4 时 f = 0.2 峰值 0.793，f = 1.0 降到 0.725；q = 0.6 时降到 0.635）。
  本任务在排班主应用上检验是否也有下降段，并检验"起作用的是 q·κ 而不是 κ"。只用训练实例。
- 进程数：与 FJSP 任务并行，6 个以下，开跑前看 `uptime`。
- R0-1 实现：在 neural/ruledec_ext.py 增加参数 dev_on（偏离槽 a ≥ dev_on 生效，q = 1 − dev_on；强度 (a − dev_on)/(1 − dev_on)），默认 0.6 = 现状。
  自检：dev_on = 0.6 时与现有 X1.0 在 15 个训练实例 × 16 个基因上逐解相同，并在 2 个训练实例上重跑 X1.0 的 MOEA，与 train_Kext.csv 逐位相同。
- R0-2 训练实例 MOEA：15 个训练实例 × 8 条规则（ES16 s0～s2、GP run1～5）× 5 次，NSGA-II 465 次，种子 5000+次号；新文件 neural/out/train_q.csv。臂：
  - κ = 1.0，q ∈ {0.6, 0.8}（q = 0.4 直接用 train_Kext.csv 中的 X1.0，同一台机器）；
  - κ = 0.5，q = 0.8（q·κ = 0.4，与 κ = 1.0、q = 0.4 相同）——检验"相同 q·κ 是否给出相近的 HV"。
  共 3 × 8 × 5 × 15 = 1800 次运行。分析时与 train_Kext.csv 的 X0.5、X0.75、X1.0（q = 0.4）合并，在每个实例内统一归一化。
- R0-3 判定（跑 R0-2 之前写好代码并用假数据测试）：
  - 最终方法在 κ = 1.0 的 q ∈ {0.4, 0.6, 0.8} 中按 8 条规则合并的训练平均 HV 选；若最高者与 q = 0.4 的配对 Wilcoxon（15 个实例）p ≥ 0.05，保留 q = 0.4，不改最终方法。
  - 若最终方法改变：补跑该 (κ, q) × 8 条规则的测试集臂（NSGA-II 465，新文件 neural/out/val_q.csv，分析时与 val_server.csv、val_Kext.csv 合并归一化）。不改变则不跑测试集。
- **进度（2026-10-23 02:05）**：R0-1 完成——check_q.py 720 个解码 0 不一致（随机基因生效比例 q = 0.4/0.6/0.8 时为 0.394/0.597/0.794）；
  moea_q.py（包 moea_any.run_nsga2，另记前沿解的偏离数）在 E11_480h、H11_480h 上重跑 X1.0 与 train_Kext.csv 逐位相同（80/80）。
  R0-3 判定脚本 neural/r0_choose.py 已写好，假数据三种情形全部通过（`python r0_choose.py selftest`）。R0-2 已在后台运行（`neural/run_R0.sh`，4 个进程，日志 out/r0.log），
  之后自动补跑其余 13 个实例的 X1.0（只为记录 q = 0.4 的偏离数，HV 仍用 train_Kext.csv）→ 判定 → 若最终方法改变才跑测试集。
- R0-4 报告 `报告/R0_偏离率扫描.md`：以 q·κ 为横轴的训练 HV 曲线（全部与 E/H/M），标出是否出现下降段；κ = 0.5、q = 0.8 与 κ = 1.0、q = 0.4 的差（配对 Wilcoxon）；
  最好解实际用到的偏离数 / 班次数（对照 FJSP 的 P1）。结论补一句到 `报告/待检验_偏离偏置与最优K.md` 的"现象"一节。
- 结果：κ = 1.0 一线 q = 0.4 最高（0.606；q0.6 0.590、q0.8 0.578，q0.8 对 q0.4 −0.028，p = 0.15），按规则**保留 κ = 1.0、q = 0.4**，不跑测试集；没有显著下降段。q·κ 相同的 κ0.5 q0.8 与 κ1.0 q0.4 只差 −0.007（p = 0.47）。前沿解生效槽占比 ≈ q。见 `报告/R0_偏离率扫描.md`。2026-10-23

### T6 [完成] FJSP：主实验最终版（单机、20 次）
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
- 结果：v3_main 27600 组齐全（6 进程，29.6 小时）；v3_big 3120 组齐全（4 进程，12.3 小时）；中期快照 v3_main_r10.csv 已提交。见 `报告/T6_FJSP最终版.md`。2026-10-23

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
