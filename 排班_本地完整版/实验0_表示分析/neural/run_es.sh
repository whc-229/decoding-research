#!/usr/bin/env bash
# 第 1b 步：ES 微调，网络主臂结构 16，从 IL 种子 0、1、2 各跑一次（依次跑，可续跑）。用法: bash run_es.sh [进程数|auto]
set -e
cd "$(dirname "$0")"
P=${1:-auto}
mkdir -p out/es
python es.py out/nn_il_h16.npz il_h16 "$P" --seed 0 2>&1 | tee -a out/es/il_h16.log
python es.py out/nn_il_h16_s1.npz il_h16_s1 "$P" --seed 1 2>&1 | tee -a out/es/il_h16_s1.log
python es.py out/nn_il_h16_s2.npz il_h16_s2 "$P" --seed 2 2>&1 | tee -a out/es/il_h16_s2.log
