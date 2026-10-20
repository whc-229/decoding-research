#!/usr/bin/env bash
# 第 5 步：rulegen 消融重复（full / score 反馈各再跑 2 次，种子 2、3），依次跑，每次 2 个进程评价规则。
# 输出在 rulegen/out/<tag>/（新目录，不动已有的 full/、score/）。断了重跑同一条命令会从 state.json 继续。
set -e
cd "$(dirname "$0")/../rulegen"
for t in full_s2:full:2 full_s3:full:3 score_s2:score:2 score_s3:score:3; do
    IFS=: read tag fb seed <<< "$t"
    [ -f "out/$tag/best_rule.py" ] && { echo "$tag 已完成，跳过"; continue; }
    python rulegen.py --feedback "$fb" --tag "$tag" --seed "$seed" --procs 2 2>&1 | tee -a "../neural/out/rulegen_$tag.log"
done
echo "消融重复完成"
