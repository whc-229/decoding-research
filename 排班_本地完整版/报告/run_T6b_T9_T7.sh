#!/usr/bin/env bash
# 顺序调整（TASKS.md 2026-10-22：T6 big 完成后先跑 T9，再跑 T7、T8）后的调度，接替 run_T3_T7.sh 的 T6b、T7 和 run_T9.sh。
#   1. 等 run_T3_T7.sh 留下的 T6b 计算进程（moea_fjsp2.py … v3_big.csv）结束；
#   2. T6b 收尾：同一条命令续跑一遍（moea_fjsp2.py 跳过已有的行，正常应 0 次待做），再做分析，写 T6b.done；
#   3. T9：核对（check_seed.py 规则解不一致 0、check_v2.py 不一致 0）→ 运行 → 与 v3_big 合并分析，写 T9.done；
#   4. T7：Behnke，写 T7.done。run_T8.sh 一直在等 T7.done，之后自动跑 T8。
# 进程数规则、标记文件、日志与 run_T3_T7.sh 相同；可续跑（已有 .done 的步骤跳过）。用法：nohup bash 报告/run_T6b_T9_T7.sh &
R=/home/hk/解码研究/排班_本地完整版; B=$R/实验0_表示分析/bench
MARK=$R/报告/T3_T7_标记; LOG=$R/报告/T3_T7_调度.log
export PATH=/home/hk/miniconda3/envs/ana/bin:$PATH     # 与 T3～T6a 相同的 conda 环境 ana（python 即 ana 的 python）
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=$R

# 写一行带时间戳的调度日志
log() { echo "$(date '+%F %T') $*" | tee -a $LOG; }

# 估计其他程序占用的核数（30 秒内每秒采样 /proc/loadavg 的运行进程数，取平均）
others_busy() {
  local s=0
  for i in $(seq 30); do s=$((s + $(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1) - 1)); sleep 1; done
  echo $((s / 30))
}

# 决定进程数 P：其他占用 ≤2 用 6，≤10 用 4，否则每 5 分钟重查，最多等 2 小时后用 4（同 run_T3_T7.sh）
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

# 运行一个任务（同 run_T3_T7.sh 的 run_task）：成功后写标记文件，失败则停止调度
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

# T6b 收尾：续跑同一条命令（补齐可能缺的行）并分析
t6b() {
  cd $B || return 1
  python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 $P v3_big.csv big 20000 >> v3_big.log 2>&1 || return 1
  python analyze_fjsp2.py v3_big.csv report_v3_big.md >> v3_big.log 2>&1
}

# T9：核对后运行，与 v3_big 合并分析
t9() {
  cd $B || return 1
  if pgrep -f "moea_fjsp2.py .*v3_big_seed.csv" > /dev/null; then log "T9：已有进程在写 v3_big_seed.csv"; return 1; fi
  local c1 c2
  c1=$(python check_seed.py 2>&1 | tail -1); c2=$(python check_v2.py 2>&1 | tail -1)
  log "T9 开跑前核对：$c1；$c2"
  echo "$c1" | grep -q "规则解不一致 0$" && echo "$c2" | grep -q "不一致 0$" || { log "T9 核对未通过"; return 1; }
  python moea_fjsp2.py rk+seed,rk+glr,rk+glr+seed 10 $P v3_big_seed.csv big 20000 >> v3_big_seed.log 2>&1 || return 1
  { cat v3_big.csv; tail -n +2 v3_big_seed.csv; } > v3_big_all.csv
  python analyze_fjsp2.py v3_big_all.csv report_v3_big_all.md >> v3_big_seed.log 2>&1
}

# T7：FJSP Behnke 60 个大实例（同 run_T3_T7.sh）
t7() {
  cd $B || return 1
  python moea_fjsp2.py rk,sp0.1,sp0.25,sp0.5 10 $P v3_behnke.csv behnke 5000 >> v3_behnke.log 2>&1 || return 1
  python analyze_fjsp2.py v3_behnke.csv report_v3_behnke.md >> v3_behnke.log 2>&1
}

log "===== 调度（新顺序 T6b → T9 → T7；T8 由 run_T8.sh 在 T7 后接上）启动 ====="
while pgrep -f "moea_fjsp2.py .*v3_big.csv" > /dev/null; do sleep 60; done
log "T6b 计算进程已结束，收尾"
run_task T6b t6b
run_task T9 t9
run_task T7 t7
log "===== T6b、T9、T7 全部完成 ====="
