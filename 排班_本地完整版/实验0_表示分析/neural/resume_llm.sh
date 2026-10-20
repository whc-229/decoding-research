#!/usr/bin/env bash
# DeepSeek 充值后续跑因 402 停下的 LLM 运行（各自从 state.json 继续）：rulegen 消融 full_s3 / score_s2 / score_s3、EoH run1。
# 同时把测试集验证（tmux 窗口 val2）降到 6 个进程给 LLM 评价让出 CPU，LLM 运行全部结束后自动换回 15 个进程。
# 用法（在 neural/ 下）: bash resume_llm.sh
cd "$(dirname "$0")"
T=$HOME/bin/tmux
ENV="export PATH=\$HOME/bin:\$HOME/miniconda3/envs/LLM-CP/bin:\$PATH OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; cd $(pwd)"
$T send-keys -t nn:val2 C-c; sleep 10; $T send-keys -t nn:val2 "bash run_batch2.sh 6" Enter
for t in full_s3:full:3 score_s2:score:2 score_s3:score:3; do
    IFS=: read tag fb seed <<< "$t"
    $T send-keys -t "nn:$tag" "$ENV && python rulegen_run.py --feedback $fb --tag $tag --seed $seed --procs 2 2>&1 | tee -a out/rulegen_$tag.log" Enter
done
$T send-keys -t nn:eoh1 "$ENV && python eoh.py 1 --procs 2 2>&1 | tee -a out/eoh_run1.log" Enter
sleep 60
$T send-keys -t nn:watch "while pgrep -f 'python (rulegen_run|eoh)[.]py' >/dev/null; do sleep 120; done; date; tmux send-keys -t nn:val2 C-c; sleep 10; tmux send-keys -t nn:val2 'bash run_batch2.sh 15' Enter; echo 已切换到 15 个进程" Enter
echo "已续跑 4 个 LLM 运行；测试集验证暂用 6 个进程"
