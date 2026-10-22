#!/usr/bin/env bash
# 【已停用 2026-10-23】顺序改为 T6b → T9 → T7 → T8，由 run_T6b_T9_T7.sh 接替；本文件仅保留备查。
# T9：等 T8 完成标记出现后，跑启发式初始化对照（rk+seed / rk+glr / rk+glr+seed，big 实例，10 次，20000 次评价），
# 然后与 v3_big 合并分析。命令照 TASKS.md 的 T9 一节；进程数规则与 run_T8.sh 相同；可续跑（moea_fjsp2.py 跳过 CSV 中已有的行）。
# 开跑前必须：check_seed.py "规则解不一致 0"、check_v2.py "不一致 0"，否则停下等排查。日志追加到 报告/T3_T7_调度.log。
# 报告（报告/T9_启发式初始化.md）不由本脚本写，由负责 FJSP 的会话在完成后写。
R=/home/hk/解码研究/排班_本地完整版; B=$R/实验0_表示分析/bench
MARK=$R/报告/T3_T7_标记; LOG=$R/报告/T3_T7_调度.log
PY=/home/hk/miniconda3/envs/ana/bin/python   # 与 T3～T8 相同的 conda 环境
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=$R

# 写一行带时间戳的调度日志
log() { echo "$(date '+%F %T') $*" | tee -a $LOG; }

# 估计其他程序占用的核数（30 秒内每秒采样 /proc/loadavg 的运行进程数，取平均）
others_busy() {
  local s=0
  for i in $(seq 30); do s=$((s + $(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1) - 1)); sleep 1; done
  echo $((s / 30))
}

# 决定进程数 P：其他占用 ≤2 用 6，≤10 用 4，否则每 5 分钟重查，最多等 2 小时后用 4（同 run_T8.sh）
pick_procs() {
  local waited=0 busy
  while true; do
    busy=$(others_busy)
    if [ $busy -le 2 ]; then P=6; break; fi
    if [ $busy -le 10 ]; then P=4; break; fi
    if [ $waited -ge 120 ]; then P=4; log "已等 ${waited} 分钟，其他占用仍为 $busy，改用 4 个进程"; break; fi
    log "T9 等待：其他程序占用约 $busy 个核（已等 ${waited} 分钟）"
    sleep 270; waited=$((waited + 5))
  done
  log "其他占用约 $busy 个核 → 进程数 $P"
}

[ -f $MARK/T9.done ] && { log "T9 已完成，跳过"; exit 0; }
until [ -f $MARK/T8.done ]; do
  grep -q 'T8 失败\|调度停止' $LOG && { log "T8 或 T3～T7 调度失败，T9 不启动"; exit 1; }
  sleep 300
done
# 一个 CSV 只能有一个写入进程：已有别的进程在写 v3_big_seed.csv 就不启动
if pgrep -f "moea_fjsp2.py .*v3_big_seed.csv" > /dev/null; then
  log "T9：已有进程在写 v3_big_seed.csv，本脚本不启动"; exit 1
fi
cd $B || exit 1
c1=$($PY check_seed.py 2>&1 | tail -1); c2=$($PY check_v2.py 2>&1 | tail -1)
log "T9 开跑前核对：$c1；$c2"
echo "$c1" | grep -q "规则解不一致 0$" && echo "$c2" | grep -q "不一致 0$" || { log "T9 核对未通过，调度停止，等待排查"; exit 1; }
pick_procs
log "T9 开始（进程数 $P）"
t0=$(date +%s)
if $PY moea_fjsp2.py rk+seed,rk+glr,rk+glr+seed 10 $P v3_big_seed.csv big 20000 >> v3_big_seed.log 2>&1; then
  { cat v3_big.csv; tail -n +2 v3_big_seed.csv; } > v3_big_all.csv
  $PY analyze_fjsp2.py v3_big_all.csv report_v3_big_all.md >> v3_big_seed.log 2>&1
  echo "进程数 $P，开始 $(date -d @$t0 '+%F %T')，结束 $(date '+%F %T')，用时 $(( ($(date +%s) - t0) / 60 )) 分钟" > $MARK/T9.done
  log "T9 完成：$(cat $MARK/T9.done)；合并分析 report_v3_big_all.md"
else
  log "T9 失败（退出码 $?），等待排查"; exit 1
fi
