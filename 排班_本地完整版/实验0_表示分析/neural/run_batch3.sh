#!/usr/bin/env bash
# 第 3 批：rulegen 消融重复（full_s2/s3、score_s2/s3）与 EoH（run1～3）的 7 条规则做测试集验证（47 实例 × 5 次），追加到 out/val_server.csv。
# 必须在第 2 批结束后再跑（同一个 CSV 只能有一个写入进程）。用法: bash run_batch3.sh [进程数|auto]；可续跑。
set -e
cd "$(dirname "$0")"
P=${1:-auto}
A="K0.25:LLM-full(s2)=K0.25:out/full_s2/best_rule.py,K0.25:LLM-full(s3)=K0.25:out/full_s3/best_rule.py"
A="$A,K0.25:LLM-score(s2)=K0.25:out/score_s2/best_rule.py,K0.25:LLM-score(s3)=K0.25:out/score_s3/best_rule.py"
for r in 1 2 3; do A="$A,K0.25:EoH(run$r)=K0.25:../neural/out/eoh/run$r/best_rule.py"; done
python ga_any.py "$A" 5 "$P" out/val_server.csv test 2>&1 | tee -a out/val3.log
echo "第 3 批完成"
