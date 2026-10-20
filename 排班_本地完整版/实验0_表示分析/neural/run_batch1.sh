#!/usr/bin/env bash
# 第 1 批（服务器上，在 tmux 里运行）：环境检查 → 一致性检查 → 老师数据采集 + 重放 → 测试集基线臂（本机重跑）
# 用法: bash run_batch1.sh [进程数|auto]      断了重跑同一条命令即可，已完成的部分会跳过
set -e
cd "$(dirname "$0")"
P=${1:-auto}
mkdir -p out
python envcheck.py | tee out/envcheck.txt
python check_platform.py "$P" | tee out/check_platform.txt
python collect.py dec5,K0.25:default 10 "$P" 2>&1 | tee -a out/collect.log
python replay.py out/teacher out/il_data.npz 2>&1 | tee -a out/collect.log
python ga_any.py "dec5,K0.25:default,K0.25:LLM(r47)=K0.25:out/full/best_rule.py,K0.25:LLM(r35)=K0.25:out/score/best_rule.py" \
    5 "$P" out/val_server.csv test 2>&1 | tee -a out/val.log
echo "第 1 批完成。把 neural/out/ 下的 envcheck.txt check_platform.txt il_data.npz val_server.csv collect.log 拷回 Windows。"
