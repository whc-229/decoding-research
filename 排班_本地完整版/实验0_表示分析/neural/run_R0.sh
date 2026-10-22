#!/usr/bin/env bash
# R0：排班偏离率扫描（TASKS.md R0，2026-10-23）。每步可续跑。用法（neural/ 下）: nohup bash run_R0.sh [进程数] > out/r0.log 2>&1 &
#   R0-1 已做：check_q.py（720 个解码 0 不一致）、moea_q.py 在 E11_480h、H11_480h 上重跑 X1.0 与 train_Kext.csv 逐位相同（80/80）。
#   R0-2：15 个训练实例 × {X1.0q0.6, X1.0q0.8, X0.5q0.8} × 8 条规则 × 5 次 → out/train_q.csv（+ _dev.csv 偏离数）。
#   R0-4 用：其余 13 个训练实例重跑 X1.0（q = 0.4）只为记录偏离数 → out/train_q04.csv（HV 仍用 train_Kext.csv；顺带全部与之逐位比较）。
#   R0-3：r0_choose.py 判定；最终方法改变时才补跑测试集臂 → out/val_q.csv（NSGA-II 465，种子 1000+次号，5 次，同 val_Kext.csv）。
set -e
cd "$(dirname "$0")"
P=${1:-4}
PY=$HOME/miniconda3/envs/LLM-CP/bin/python      # 与 train_Kext.csv 相同的环境
ANA=$HOME/miniconda3/envs/ana/bin/python
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PAIBAN_SRC=/home/hk/解码研究/排班_本地完整版
rules() {   # $1 = 臂前缀（X1.0q0.6 之类）→ 8 个臂
    local K=$1 out=""
    for s in 0 1 2; do out="$out,$K:ES16(s$s)=$K:nn:out/es/il_h16$([ $s = 0 ] || echo _s$s)/best.npz"; done
    for r in 1 2 3 4 5; do out="$out,$K:GP(run$r)=$K:../neural/out/gp/run$r/best_rule.py"; done
    echo "${out#,}"
}
echo "$(date '+%F %T') R0-2 开始（$P 个进程）"
$PY moea_q.py "$(rules X1.0q0.6),$(rules X1.0q0.8),$(rules X0.5q0.8)" 5 "$P" out/train_q.csv train --seed-base 5000
echo "$(date '+%F %T') R0-2 完成；补跑 X1.0（q = 0.4）记录偏离数"
$PY moea_q.py "$(rules X1.0)" 5 "$P" out/train_q04.csv train --seed-base 5000
$PY check_q.py cmp out/train_q04.csv
echo "$(date '+%F %T') R0-3 判定"
$ANA r0_choose.py
CH=$($ANA -c "import json; print(json.load(open('out/r0_choose.json'))['changed'])")
if [ "$CH" = "True" ]; then
    Q=$($ANA -c "import json; print(json.load(open('out/r0_choose.json'))['final']['q'])")
    echo "$(date '+%F %T') 最终方法改为 κ = 1.0、q = $Q，补跑测试集臂"
    $PY moea_any.py "$(rules X1.0q$Q)" 5 "$P" out/val_q.csv test
fi
echo "$(date '+%F %T') R0 运行部分完成（changed = $CH）"
