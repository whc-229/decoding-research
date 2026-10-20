#!/usr/bin/env bash
# 第 2 批：新臂测试集验证（47 实例 × 5 次），追加到 out/val_server.csv；先主臂（IL16 ×5、ES16 ×3、GP ×5），再结构对照 IL32-16 ×5。
# 用法: bash run_batch2.sh [进程数|auto]      断了重跑同一条命令即可，已完成的 (实例, 臂, 次) 会跳过
set -e
cd "$(dirname "$0")"
P=${1:-auto}
A=""
for s in 0 1 2 3 4; do f=out/nn_il_h16$([ $s = 0 ] || echo _s$s).npz; A="$A,K0.25:IL16(s$s)=K0.25:nn:$f"; done
for s in 0 1 2; do f=out/es/il_h16$([ $s = 0 ] || echo _s$s)/best.npz; A="$A,K0.25:ES16(s$s)=K0.25:nn:$f"; done
for r in 1 2 3 4 5; do A="$A,K0.25:GP(run$r)=K0.25:../neural/out/gp/run$r/best_rule.py"; done
python ga_any.py "${A#,}" 5 "$P" out/val_server.csv test 2>&1 | tee -a out/val2.log
B=""
for s in 0 1 2 3 4; do f=out/nn_il$([ $s = 0 ] || echo _s$s).npz; B="$B,K0.25:IL32-16(s$s)=K0.25:nn:$f"; done
python ga_any.py "${B#,}" 5 "$P" out/val_server.csv test 2>&1 | tee -a out/val2.log
echo "第 2 批完成"
