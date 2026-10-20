#!/usr/bin/env bash
# 第 5 步：rulegen 消融重复（full / score 反馈各再跑 2 次，种子 2、3），每次 2 个进程评价规则。
# 走 rulegen_run.py 外壳（评价超时固定 600 秒，见其说明），输出在 rulegen/out/<tag>/（新目录，不动已有的 full/、score/）。
# 2026-10-20 实际是 4 次同时跑的（各在 tmux 窗口 abl / full_s3 / score_s2 / score_s3）；这个脚本是依次跑的版本，
# 断了重跑会从各自的 state.json 继续，已完成的跳过。**不要和正在跑的同 tag 进程同时启动。**
set -e
cd "$(dirname "$0")"
for t in full_s2:full:2 full_s3:full:3 score_s2:score:2 score_s3:score:3; do
    IFS=: read tag fb seed <<< "$t"
    [ -f "../rulegen/out/$tag/best_rule.py" ] && { echo "$tag 已完成，跳过"; continue; }
    python rulegen_run.py --feedback "$fb" --tag "$tag" --seed "$seed" --procs 2 2>&1 | tee -a "out/rulegen_$tag.log"
done
echo "消融重复完成"
