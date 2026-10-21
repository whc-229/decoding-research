#!/usr/bin/env bash
# 任务 B1 → A1 → A2（依次跑；每步可续跑：断了重跑同一条命令，已完成的 (实例, 臂, 次) 跳过）。用法: bash run_AB.sh [进程数|auto]
set -e
cd "$(dirname "$0")"
P=${1:-auto}
ES=""; for s in 0 1 2; do ES="$ES,ES16(s$s)=nn:out/es/il_h16$([ $s = 0 ] || echo _s$s)/best.npz"; done
GP=""; for r in 1 2 3 4 5; do GP="$GP,GP(run$r)=../neural/out/gp/run$r/best_rule.py"; done
arm() { local K=$1 L=$2 out=""; IFS=,; for x in $L; do [ -n "$x" ] && out="$out,K$K:${x%%=*}=K$K:${x#*=}"; done; unset IFS; echo "${out#,}"; }
LLM="K0.25:LLM(r35)=K0.25:out/score/best_rule.py,K0.25:LLM-score(s2)=K0.25:out/score_s2/best_rule.py,K0.25:LLM-score(s3)=K0.25:out/score_s3/best_rule.py"
# B1：K0.5 + ES16 / GP，465 次；dec5 的 765 次同总预算对照 → val_server.csv
python moea_any.py "$(arm 0.5 "$ES"),$(arm 0.5 "$GP")" 5 "$P" out/val_server.csv test 2>&1 | tee -a out/valB.log
python moea_any.py "dec5-765=dec5" 5 "$P" out/val_server.csv test --checks 765 2>&1 | tee -a out/valB.log
echo "B1 完成" | tee -a out/valB.log
# A1：MOEA/D 465 次，13 个臂 → val_moead.csv
A13="dec5,K0.25:default,$(arm 0.25 "$ES"),$(arm 0.25 "$GP"),$LLM"
python moea_any.py "$A13" 5 "$P" out/val_moead.csv test --algo moead 2>&1 | tee -a out/valA1.log
echo "A1 完成" | tee -a out/valA1.log
# A2：NSGA-II 2000 次，13 个臂 + K0.5 + ES16，检查点 465 / 2000 → val_big.csv
python moea_any.py "$A13,$(arm 0.5 "$ES")" 5 "$P" out/val_big.csv test --checks 465,2000 2>&1 | tee -a out/valA2.log
echo "A2 完成" | tee -a out/valA2.log
