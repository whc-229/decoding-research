#!/usr/bin/env bash
# T13 调度：已有方法对照。按 TASKS.md 的顺序 第 1 步（FJSP pilot 调参）→ 第 3 步（排班训练集调参）→ 第 2 步（FJSP big 主比较）
# → 第 4 步（排班测试集），同一时间只跑一步。第 2、4 步的臂由第 1、3 步的 choose_t13.json 决定。
# 可续跑：已完成的步骤有标记 报告/T13_标记/sN.done，直接跳过；未完成的步骤重跑同一命令，脚本会跳过 CSV 中已有的行。
# 环境：FJSP 用 conda 环境 ana（与 v3_big 相同）；排班 MOEA 用 LLM-CP（与 train_Kext / val_Kext 相同），判定脚本用 ana（同 run_R0.sh）。
# 用法：在 tmux 里 bash 报告/run_T13.sh；日志写到 报告/T13_调度.log。
R=/home/hk/解码研究/排班_本地完整版; E=$R/实验0_表示分析; B=$E/bench; N=$E/neural
MARK=$R/报告/T13_标记; LOG=$R/报告/T13_调度.log
ANA=/home/hk/miniconda3/envs/ana/bin/python
LCP=/home/hk/miniconda3/envs/LLM-CP/bin/python
mkdir -p $MARK
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=$R

# 写一行带时间戳的调度日志
log() { echo "$(date '+%F %T') $*" | tee -a $LOG; }

# 估计其他程序占用的核数：30 秒内每秒读一次 /proc/loadavg 中正在运行的进程数（减去读取本身），取平均
others_busy() {
  local s=0
  for i in $(seq 30); do s=$((s + $(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1) - 1)); sleep 1; done
  echo $((s / 30))
}

# 决定进程数 P：其他占用 ≤2 用 6，≤10 用 4，否则每 5 分钟重查，最多等 2 小时后用 4（与 run_T3_T7.sh 相同）
pick_procs() {
  local waited=0 busy
  while true; do
    busy=$(others_busy)
    if [ $busy -le 2 ]; then P=6; break; fi
    if [ $busy -le 10 ]; then P=4; break; fi
    if [ $waited -ge 120 ]; then P=4; log "已等 ${waited} 分钟，其他占用仍为 $busy，改用 4 个进程"; break; fi
    log "其他程序占用约 $busy 个核，等待 5 分钟（已等 ${waited} 分钟）"
    sleep 270; waited=$((waited + 5))
  done
  log "其他占用约 $busy 个核 → 进程数 $P"
}

# 运行一步：$1 = 步骤名，$2 = 函数；成功后写标记文件，失败则停止整个调度
run_step() {
  local name=$1 fn=$2
  if [ -f $MARK/$name.done ]; then log "T13 $name 已完成，跳过"; return; fi
  pick_procs
  log "T13 $name 开始（进程数 $P）"
  local t0=$(date +%s)
  if $fn; then
    echo "进程数 $P，开始 $(date -d @$t0 '+%F %T')，结束 $(date '+%F %T')，用时 $(( ($(date +%s) - t0) / 60 )) 分钟" > $MARK/$name.done
    log "T13 $name 完成：$(cat $MARK/$name.done)"
  else
    log "T13 $name 失败（退出码 $?），调度停止，等待排查"; exit 1
  fi
}

# 排班的 8 条规则臂（与 run_R0.sh / run_D.sh 的 rules() 相同的规则）。$1 = 臂名前缀（D0.4 / P2），$2 = 规则写法前缀（D0.4 / P2:X1.0）
rules() {
  local L=$1 S=$2 out=""
  for s in 0 1 2; do out="$out,$L:ES16(s$s)=$S:nn:out/es/il_h16$([ $s = 0 ] || echo _s$s)/best.npz"; done
  for r in 1 2 3 4 5; do out="$out,$L:GP(run$r)=$S:../neural/out/gp/run$r/best_rule.py"; done
  echo "${out#,}"
}

# 第 1 步：FJSP pilot 调参（Hurink rdata la16～la30，15 个实例 × 14 臂 × 5 次，5000 次评价）→ bench/choose_t13.json
s1() {
  cd $B || return 1
  $ANA moea_fjsp3.py rk,sp0.5,hs,db0.04,db0.1,db0.2,db0.4,ps0.05,ps0.1,ps0.2,ps0.4,pls1:sp0.5,pls2:sp0.5,pls4:sp0.5 5 $P pilot_t13.csv pilot 5000 >> pilot_t13.log 2>&1 || return 1
  $ANA choose_t13.py pilot_t13.csv 5000 >> pilot_t13.log 2>&1
}

# 第 3 步：排班训练集调参（15 个训练实例 × 48 臂 × 5 次，种子 5000 + 次号）→ neural/out/choose_t13.json
s3() {
  cd $N || return 1
  local A="$(rules D0.2 D0.2),$(rules D0.4 D0.4),$(rules D0.6 D0.6),$(rules P1 P1:X1.0),$(rules P2 P2:X1.0),$(rules P4 P4:X1.0)"
  $LCP base3.py "$A" 5 $P out/train_t13.csv train --seed-base 5000 >> out/train_t13.log 2>&1 || return 1
  $ANA choose_t13.py out/train_t13.csv >> out/train_t13.log 2>&1
}

# 第 2 步：FJSP big 主比较（78 个实例 × 4 臂 × 10 次，20000 次评价），臂 = hs + 第 1 步选中的 db / ps / pls；合并 v3_big_all.csv 后分析
s2() {
  cd $B || return 1
  local A
  A=$($ANA -c "import json;p=json.load(open('choose_t13.json'))['pick'];print('hs,'+','.join([p['db'],p['ps'],p['pls']]))") || return 1
  log "T13 s2 臂：$A"
  $ANA moea_fjsp3.py $A 10 $P v3_big_t13.csv big 20000 >> v3_big_t13.log 2>&1 || return 1
  { cat v3_big_all.csv; tail -n +2 v3_big_t13.csv; } > v3_big_all13.csv
  $ANA analyze_fjsp2.py v3_big_all13.csv report_v3_big_all13.md >> v3_big_t13.log 2>&1
}

# 第 4 步：排班测试集（47 个测试实例 × 第 3 步选中的 D、P 各 8 条规则 × 5 次，种子 1000 + 次号，同 val_Kext.csv）
s4() {
  cd $N || return 1
  local D Pj
  D=$($ANA -c "import json;print(json.load(open('out/choose_t13.json'))['pick']['D'])") || return 1
  Pj=$($ANA -c "import json;print(json.load(open('out/choose_t13.json'))['pick']['P'])") || return 1
  log "T13 s4 臂：$D、$Pj（各 8 条规则）"
  $LCP base3.py "$(rules $D $D),$(rules $Pj $Pj:X1.0)" 5 $P out/val_t13.csv test >> out/val_t13.log 2>&1
}

log "===== T13 调度启动（顺序 s1 → s3 → s2 → s4）====="
run_step s1 s1
run_step s3 s3
run_step s2 s2
run_step s4 s4
log "===== T13 四步运行全部完成（第 2、4 步的另算统计由 Claude Code 补做）====="
