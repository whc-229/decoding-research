#!/usr/bin/env bash
# 第 1 步：模仿学习的几个变体（依次训练，已有输出的跳过），然后在训练实例上打代理分
set -e
cd "$(dirname "$0")"
P=${1:-auto}
t() { [ -f "out/$1.npz" ] || python train_il.py out/il_data.npz "out/$1.npz" "${@:2}" 2>&1 | tee "out/$1.log"; }
t nn_il --hidden 32,16
t nn_il_lin --hidden ""
t nn_il_h16 --hidden 16
t nn_il_all --hidden 32,16 --src all
python score_rules.py "IL(32-16)=K0.25:nn:out/nn_il.npz,IL(线性)=K0.25:nn:out/nn_il_lin.npz,IL(16)=K0.25:nn:out/nn_il_h16.npz,IL(32-16;全部老师)=K0.25:nn:out/nn_il_all.npz" "$P" 2>&1 | tee out/il_proxy.md
