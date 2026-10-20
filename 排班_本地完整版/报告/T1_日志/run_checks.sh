#!/usr/bin/env bash
# T1：并行运行全部核对脚本，每个脚本单独记录日志、耗时与退出码
R=~/解码研究/排班_本地完整版; E=$R/实验0_表示分析; LOG=$R/报告/T1_日志
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=$R
run() { local name=$1 dir=$2; shift 2
  ( cd "$dir" && /usr/bin/time -f "耗时 %e s，峰值内存 %M KB" python "$@" ) > "$LOG/$name.log" 2>&1
  echo "退出码 $?" >> "$LOG/$name.log"; }
run check_lib     $E          check_lib.py &
run check6        $E          check6.py "$R" &
run check9        $E          check9.py "$R" &
run check_ruledec $E/rulegen  check_ruledec.py &
run test_core     $E/reroster test_core.py 2 &
run check_v2      $E/bench    check_v2.py &
wait; echo ALL_DONE > $LOG/checks.done
