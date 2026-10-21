#!/usr/bin/env bash
# 任务 C：等 A2 结束 → C1 训练实例 MOEA → C2 按事先固定的规则选 K（候选 0.25、0.5）→ （K = 0.5 时）C4 MOEA/D 补臂。
# K0.75 在现有编码里表示不出来，2026-10-21 决定不比。
# 每步可续跑。用法（在 neural/ 下，tmux 里）: bash run_C.sh [进程数]
set -e
cd "$(dirname "$0")"
P=${1:-9}
PY=$HOME/miniconda3/envs/LLM-CP/bin/python
ANA=$HOME/miniconda3/envs/ana/bin/python
until grep -q "A2 完成" out/valA2.log 2>/dev/null; do sleep 300; done
rules() {   # $1 = K → 8 个臂（ES16 s0～s2、GP run1～5）
    local K=$1 out=""
    for s in 0 1 2; do out="$out,K$K:ES16(s$s)=K$K:nn:out/es/il_h16$([ $s = 0 ] || echo _s$s)/best.npz"; done
    for r in 1 2 3 4 5; do out="$out,K$K:GP(run$r)=K$K:../neural/out/gp/run$r/best_rule.py"; done
    echo "${out#,}"
}
# C1：15 个训练实例，K ∈ {0.25, 0.5} × 8 条规则 + dec5，每臂 5 次，种子 5000+次号
$PY moea_any.py "dec5,$(rules 0.25),$(rules 0.5)" 5 "$P" out/train_K.csv train --seed-base 5000 2>&1 | tee -a out/trainK.log
echo "C1 完成" | tee -a out/trainK.log
# C2：选 K
$ANA c2_choose.py | tee out/c2_choose.log
K=$($ANA -c "import json; print(json.load(open('out/c2_choose.json'))['K'])")
echo "选出 K = $K" | tee -a out/trainK.log
if [ "$K" != "0.25" ]; then  # C4：MOEA/D 下补 最终K + 8 条规则
    $PY moea_any.py "$(rules $K)" 5 "$P" out/val_moead.csv test --algo moead 2>&1 | tee -a out/trainK.log
fi
echo "任务 C 运行部分完成（K = $K）" | tee -a out/trainK.log
