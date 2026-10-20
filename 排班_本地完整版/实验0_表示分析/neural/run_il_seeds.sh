#!/usr/bin/env bash
# 模仿学习的种子重复（结构 32-16 与 16，种子 1～4），然后打代理分
set -e
cd "$(dirname "$0")"
P=${1:-auto}
L=""
for s in 1 2 3 4; do
    [ -f out/nn_il_s$s.npz ] || python train_il.py out/il_data.npz out/nn_il_s$s.npz --hidden 32,16 --seed $s > out/nn_il_s$s.log 2>&1
    [ -f out/nn_il_h16_s$s.npz ] || python train_il.py out/il_data.npz out/nn_il_h16_s$s.npz --hidden 16 --seed $s > out/nn_il_h16_s$s.log 2>&1
    L="$L,IL(32-16;s$s)=K0.25:nn:out/nn_il_s$s.npz,IL(16;s$s)=K0.25:nn:out/nn_il_h16_s$s.npz"
done
python score_rules.py "IL(32-16)=K0.25:nn:out/nn_il.npz,IL(16)=K0.25:nn:out/nn_il_h16.npz$L" "$P" 2>&1 | tee out/il_seeds_proxy.md
