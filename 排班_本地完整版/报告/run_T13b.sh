#!/usr/bin/env bash
# T13b（T13 第 5 步）调度：把落在网格边界的参数各往外扩一次。顺序 5b（FJSP pilot）→ 5a（排班训练集），
# 选中值变了才补跑对应的大实验（FJSP big / 排班测试集），没变就跳过。统计重算与报告由 Claude Code 补做。
# 可续跑：已完成的步骤有标记 报告/T13_标记/sN.done；未完成的步骤重跑同一命令，脚本会跳过 CSV 中已有的行。
# 环境同 run_T13.sh：FJSP 用 ana，排班 MOEA 用 LLM-CP，判定脚本用 ana。用法：在 tmux 里 bash 报告/run_T13b.sh；日志写到 报告/T13_调度.log。
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

# 决定进程数 P：其他占用 ≤2 用 6，≤10 用 4，否则每 5 分钟重查，最多等 2 小时后用 4（与 run_T13.sh 相同）
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
  if [ -f $MARK/$name.done ]; then log "T13b $name 已完成，跳过"; return; fi
  pick_procs
  log "T13b $name 开始（进程数 $P）"
  local t0=$(date +%s)
  if $fn; then
    echo "进程数 $P，开始 $(date -d @$t0 '+%F %T')，结束 $(date '+%F %T')，用时 $(( ($(date +%s) - t0) / 60 )) 分钟" > $MARK/$name.done
    log "T13b $name 完成：$(cat $MARK/$name.done)"
  else
    log "T13b $name 失败（退出码 $?），调度停止，等待排查"; exit 1
  fi
}

# 排班的 8 条规则臂（与 run_T13.sh 的 rules() 相同）。$1 = 臂名前缀（D0.1 / P8），$2 = 规则写法前缀（D0.1 / P8:X1.0）
rules() {
  local L=$1 S=$2 out=""
  for s in 0 1 2; do out="$out,$L:ES16(s$s)=$S:nn:out/es/il_h16$([ $s = 0 ] || echo _s$s)/best.npz"; done
  for r in 1 2 3 4 5; do out="$out,$L:GP(run$r)=$S:../neural/out/gp/run$r/best_rule.py"; done
  echo "${out#,}"
}

# 读 json 文件里 pick 的某一项：$1 = 文件，$2 = 键
pick_of() { $ANA -c "import json,sys;print(json.load(open(sys.argv[1]))['pick'][sys.argv[2]])" "$1" "$2"; }

# 开跑前把现有判定结果另存（已存在则不覆盖）
s5save() {
  [ -f $N/out/choose_t13_v1.json ] || cp $N/out/choose_t13.json $N/out/choose_t13_v1.json
  [ -f $B/choose_t13_v2.json ] || cp $B/choose_t13.json $B/choose_t13_v2.json
}

# 5b：FJSP pilot 补 spr3.0、spr4.0，然后用四个 pilot 文件重新判定
s5b() {
  cd $B || return 1
  $ANA moea_fjsp3.py spr3.0,spr4.0 5 $P pilot_t13d.csv pilot 5000 >> pilot_t13d.log 2>&1 || return 1
  $ANA choose_t13.py pilot_t13.csv,pilot_t13b.csv,pilot_t13c.csv,pilot_t13d.csv 5000 >> pilot_t13d.log 2>&1
}

# 5b 后续：spr 选中值变了才在 big 集上补跑新 spr（78 个实例 × 10 次 × 20000 次评价）→ v3_big_t13c.csv
s5b_big() {
  cd $B || return 1
  local old new
  old=$(pick_of choose_t13_v2.json spr) && new=$(pick_of choose_t13.json spr) || return 1
  if [ "$old" = "$new" ]; then log "T13b 5b：spr 选中值未变（$new），不补跑 big"; return 0; fi
  log "T13b 5b：spr 选中值由 $old 变为 $new，补跑 big"
  $ANA moea_fjsp3.py $new 10 $P v3_big_t13c.csv big 20000 >> v3_big_t13c.log 2>&1
}

# 5a：排班训练集补 D0.1、P8、P16（各 8 条规则 × 5 次，种子 5000 + 次号），然后两个 CSV 合并重新判定
s5a() {
  cd $N || return 1
  $LCP base3.py "$(rules D0.1 D0.1),$(rules P8 P8:X1.0),$(rules P16 P16:X1.0)" 5 $P out/train_t13b.csv train --seed-base 5000 >> out/train_t13b.log 2>&1 || return 1
  $ANA choose_t13.py out/train_t13.csv,out/train_t13b.csv >> out/train_t13b.log 2>&1
}

# 5a 后续：D 或 P 的选中值变了才补跑测试集（只跑变了的那个，8 条规则 × 5 次，种子 1000 + 次号）→ out/val_t13b.csv
s5a_val() {
  cd $N || return 1
  local A="" od nd op np
  od=$(pick_of out/choose_t13_v1.json D) && nd=$(pick_of out/choose_t13.json D) || return 1
  op=$(pick_of out/choose_t13_v1.json P) && np=$(pick_of out/choose_t13.json P) || return 1
  [ "$od" != "$nd" ] && A="$A,$(rules $nd $nd)"
  [ "$op" != "$np" ] && A="$A,$(rules $np $np:X1.0)"
  log "T13b 5a：D $od → $nd，P $op → $np"
  if [ -z "$A" ]; then log "T13b 5a：D、P 选中值都未变，不补跑测试集"; return 0; fi
  $LCP base3.py "${A#,}" 5 $P out/val_t13b.csv test >> out/val_t13b.log 2>&1
}

log "===== T13b 调度启动（顺序 5b → 5b 后续 → 5a → 5a 后续）====="
run_step s5save s5save
run_step s5b s5b
run_step s5b_big s5b_big
run_step s5a s5a
run_step s5a_val s5a_val
log "===== T13b 运行全部完成（统计重算与报告由 Claude Code 补做）====="
