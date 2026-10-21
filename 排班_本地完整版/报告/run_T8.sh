#!/usr/bin/env bash
# T8：等 T3～T7 调度结束（T7 完成标记出现）后，运行 T3 扫描补点（q=0.2，槽数 1.5/2.0/3.0）。
# 进程数规则与 run_T3_T7.sh 相同；可续跑（moea_fjsp2.py 会跳过 CSV 中已有的行）。日志追加到 报告/T3_T7_调度.log。
R=/home/hk/解码研究/排班_本地完整版; B=$R/实验0_表示分析/bench
MARK=$R/报告/T3_T7_标记; LOG=$R/报告/T3_T7_调度.log
PY=/home/hk/miniconda3/envs/ana/bin/python   # 固定用 conda 环境 ana（与 T3～T7 相同）
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=$R

# 写一行带时间戳的调度日志
log() { echo "$(date '+%F %T') $*" | tee -a $LOG; }

# 估计其他程序占用的核数（30 秒内每秒采样 /proc/loadavg 的运行进程数，取平均）
others_busy() {
  local s=0
  for i in $(seq 30); do s=$((s + $(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1) - 1)); sleep 1; done
  echo $((s / 30))
}

# 决定进程数 P：其他占用 ≤2 用 6，≤10 用 4，否则每 5 分钟重查，最多等 2 小时后用 4
pick_procs() {
  local waited=0 busy
  while true; do
    busy=$(others_busy)
    if [ $busy -le 2 ]; then P=6; break; fi
    if [ $busy -le 10 ]; then P=4; break; fi
    if [ $waited -ge 120 ]; then P=4; log "已等 ${waited} 分钟，其他占用仍为 $busy，改用 4 个进程"; break; fi
    log "T8 等待：其他程序占用约 $busy 个核（已等 ${waited} 分钟）"
    sleep 270; waited=$((waited + 5))
  done
  log "其他占用约 $busy 个核 → 进程数 $P"
}

[ -f $MARK/T8.done ] && { log "T8 已完成，跳过"; exit 0; }
until [ -f $MARK/T7.done ]; do
  grep -q '调度停止' $LOG && { log "T3～T7 调度已停止，T8 不启动"; exit 1; }
  sleep 300
done
pick_procs
log "T8 开始（进程数 $P）"
t0=$(date +%s)
cd $B || exit 1
I=$($PY -c "import fjsp2 as F;M=F.meta();print(','.join([n for n,d in M.items() if d['path'].startswith('brandimarte')]+['r-la%02d'%i for i in range(16,31)]))") || exit 1
if $PY moea_fjsp2.py sp1.5q0.2,sp2.0q0.2,sp3.0q0.2 5 $P v3_qk2.csv $I 20000 >> v3_qk2.log 2>&1; then
  echo "进程数 $P，开始 $(date -d @$t0 '+%F %T')，结束 $(date '+%F %T')，用时 $(( ($(date +%s) - t0) / 60 )) 分钟" > $MARK/T8.done
  log "T8 完成：$(cat $MARK/T8.done)"
else
  log "T8 失败（退出码 $?），等待排查"; exit 1
fi
