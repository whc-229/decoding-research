#!/usr/bin/env bash
# T1：两次小样例运行（依次执行，避免互相争用 CPU 影响耗时）
R=~/解码研究/排班_本地完整版; E=$R/实验0_表示分析; LOG=$R/报告/T1_日志
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=$R
( cd $E/bench && /usr/bin/time -f "耗时 %e s，峰值内存 %M KB" python moea_fjsp2.py rk,sp0.25 1 2 /tmp/t.csv k1 2000 ) > $LOG/sample_moea_fjsp2.log 2>&1; echo "退出码 $?" >> $LOG/sample_moea_fjsp2.log
( cd $E/rulegen && /usr/bin/time -f "耗时 %e s，峰值内存 %M KB" python ga_rule.py dec5 1 2 /tmp/g.csv E11_480h ) > $LOG/sample_ga_rule.log 2>&1; echo "退出码 $?" >> $LOG/sample_ga_rule.log
echo ALL_DONE > $LOG/samples.done
