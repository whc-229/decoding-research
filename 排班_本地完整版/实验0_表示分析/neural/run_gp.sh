#!/usr/bin/env bash
# 第 2 步：GP 规则 5 次独立运行（依次跑，每次可续跑）。用法: bash run_gp.sh [进程数|auto] [起始运行号] [结束运行号]
set -e
cd "$(dirname "$0")"
P=${1:-auto}; A=${2:-1}; B=${3:-5}
mkdir -p out/gp
for r in $(seq "$A" "$B"); do
    python gp.py "$r" "$P" 2>&1 | tee -a "out/gp/run$r.log"
done
