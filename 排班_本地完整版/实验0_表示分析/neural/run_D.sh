#!/usr/bin/env bash
# 任务 D：D2 代理分 → D2 训练实例 MOEA（扩展布局 X0.5 / X0.75 / X1.0 × 8 条规则 × 5 次，种子 5000+次号）→ D3 判定 →
# D4 测试集 X0.75、X1.0 × 8 条规则 → out/val_Kext.csv（敏感性分析，不用于选 K；若选出 K ≠ 0.5，所需测试集臂也在其中）。每步可续跑。
# 用法（在 neural/ 下，tmux 里）: bash run_D.sh [进程数]
set -e
cd "$(dirname "$0")"
P=${1:-9}
PY=$HOME/miniconda3/envs/LLM-CP/bin/python
ANA=$HOME/miniconda3/envs/ana/bin/python
rules() {   # $1 = K → 扩展布局的 8 个臂
    local K=$1 out=""
    for s in 0 1 2; do out="$out,X$K:ES16(s$s)=X$K:nn:out/es/il_h16$([ $s = 0 ] || echo _s$s)/best.npz"; done
    for r in 1 2 3 4 5; do out="$out,X$K:GP(run$r)=X$K:../neural/out/gp/run$r/best_rule.py"; done
    echo "${out#,}"
}
$PY score_ext.py "$P" 2>&1 | tee out/score_ext.log
$PY moea_any.py "$(rules 0.5),$(rules 0.75),$(rules 1.0)" 5 "$P" out/train_Kext.csv train --seed-base 5000 2>&1 | tee -a out/trainKext.log
echo "D2 完成" | tee -a out/trainKext.log
$ANA d3_choose.py | tee out/d3_choose.log
K=$($ANA -c "import json; print(json.load(open('out/d3_choose.json'))['K'])")
echo "选出 K = $K" | tee -a out/trainKext.log
$PY moea_any.py "$(rules 0.75),$(rules 1.0)" 5 "$P" out/val_Kext.csv test 2>&1 | tee -a out/trainKext.log
echo "任务 D 运行部分完成（K = $K）" | tee -a out/trainKext.log
