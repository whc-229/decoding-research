#!/bin/bash
cd "$(dirname "$0")/.."
python3 run_mech.py 30 10 20 2 实验0_表示分析/out/wb_dev 原请求_paiban,D_三类型资源紧 "容量预判+回溯修复,dec5+写回,dec5+强制新开带,dec5+强制新开带+写回" > 实验0_表示分析/out/wb_dev.log 2>&1
echo done > 实验0_表示分析/out/WB_DEV_DONE
