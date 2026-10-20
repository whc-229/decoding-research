#!/usr/bin/env bash
# T3～T7 调度：按顺序逐个运行（同一时间只跑一个任务），每个任务跑完立即执行其分析命令。
# 可续跑：已完成的任务有标记文件 报告/T3_T7_标记/Tn.done，直接跳过；未完成的任务重跑同一命令，脚本会跳过 CSV 中已有的行。
# 用法：在 tmux 里 bash 报告/run_T3_T7.sh；调度日志写到 报告/T3_T7_调度.log。
R=/home/hk/解码研究/排班_本地完整版; E=$R/实验0_表示分析; B=$E/bench; G=$E/rulegen
MARK=$R/报告/T3_T7_标记; LOG=$R/报告/T3_T7_调度.log
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

# 决定进程数（结果写入全局变量 P）：其他占用 ≤2 用 6，≤10 用 4，否则每 5 分钟重查，最多等 2 小时后用 4
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

# 运行一个任务：$1 = 任务名，$2 = 要执行的函数；成功后写标记文件，失败则停止整个调度
run_task() {
  local name=$1 fn=$2
  if [ -f $MARK/$name.done ]; then log "$name 已完成，跳过"; return; fi
  pick_procs
  log "$name 开始（进程数 $P）"
  local t0=$(date +%s)
  if $fn; then
    echo "进程数 $P，开始 $(date -d @$t0 '+%F %T')，结束 $(date '+%F %T')，用时 $(( ($(date +%s) - t0) / 60 )) 分钟" > $MARK/$name.done
    log "$name 完成：$(cat $MARK/$name.done)"
  else
    log "$name 失败（退出码 $?），调度停止，等待排查"; exit 1
  fi
}

# T3：FJSP 槽数 × 生效概率扫描（无分析命令）
t3() {
  cd $B || return 1
  local enc=rk f q I
  for f in 0.05 0.1 0.2 0.35 0.5 0.75 1.0; do for q in 0.2 0.4 0.6; do enc=$enc,sp${f}q${q}; done; done
  I=$(python -c "import fjsp2 as F;M=F.meta();print(','.join([n for n,d in M.items() if d['path'].startswith('brandimarte')]+['r-la%02d'%i for i in range(16,31)]))") || return 1
  python moea_fjsp2.py $enc 5 $P v3_qk.csv $I 20000 >> v3_qk.log 2>&1
}

# T4：排班测试集验证 20 次
t4() {
  cd $G || return 1
  python ga_rule.py dec5,K0.25:default,K0.25:out/full/best_rule.py,K0.25:out/score_best_rule.py 20 $P out/val20.csv test >> out/val20.log 2>&1 || return 1
  python analyze_val.py out/val20.csv out/val20.md >> out/val20.log 2>&1
}

# T5：FJSP MOEA/D 对照
t5() {
  cd $B || return 1
  python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 $P v3_moead.csv big 5000 moead >> v3_moead.log 2>&1 || return 1
  python analyze_fjsp2.py v3_moead.csv report_v3_moead.md >> v3_moead.log 2>&1
}

# T6a：FJSP 主实验最终版（main，20 次，5000 次评价）
t6a() {
  cd $B || return 1
  python moea_fjsp2.py pd,rk,sp0.1,sp0.25,sp0.5 20 $P v3_main.csv main 5000 >> v3_main.log 2>&1 || return 1
  python analyze_fjsp2.py v3_main.csv report_v3_main.md >> v3_main.log 2>&1
}

# T6b：FJSP 大预算（big，10 次，20000 次评价）
t6b() {
  cd $B || return 1
  python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 $P v3_big.csv big 20000 >> v3_big.log 2>&1 || return 1
  python analyze_fjsp2.py v3_big.csv report_v3_big.md >> v3_big.log 2>&1
}

# T7：FJSP Behnke 60 个大实例
t7() {
  cd $B || return 1
  python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 $P v3_behnke.csv behnke 5000 >> v3_behnke.log 2>&1 || return 1
  python analyze_fjsp2.py v3_behnke.csv report_v3_behnke.md >> v3_behnke.log 2>&1
}

log "===== 调度启动 ====="
run_task T3 t3
run_task T4 t4
run_task T5 t5
run_task T6a t6a
run_task T6b t6b
run_task T7 t7
log "===== T3～T7 全部完成 ====="
