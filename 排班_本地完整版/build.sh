#!/usr/bin/env bash
# 编译：原解码 paiban_dec0、阈值解码 paiban_dec1、阈值+按出勤排序解码 paiban_dec2、排序+容量预判 paiban_dec3（及 ρ 固定为 1 的 paiban_dec3f）
# θ 用环境变量 THETA 改（默认 0.85）；DECODERS="3" 只编译指定版本
# 依赖：g++（C++17）。头文件都在 include/ 下（含 nlohmann/json.hpp），无需额外安装。
set -e
cd "$(dirname "$0")"
THETA=${THETA:-0.85}
SRC="src/main_cli.cpp src/problem.cpp src/workflow.cpp src/Properties.cpp src/Entity.cpp src/MOEA_solver.cpp src/Population_moea.cpp"
for D in ${DECODERS:-0 1 2 3}; do
  [ "$D" = "4" ] || [ "$D" = "5" ] || [ "$D" = "5r" ] || [ "$D" = "6" ] || [ "$D" = "6b" ] || [ "$D" = "7" ] || [ "$D" = "8" ] || [ "$D" = "9" ] && continue
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=$D -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec$D -lstdc++fs
  echo "已编译 paiban_dec$D"
done
# 维修相位排序 + 容量预判（ρ ≡ 1）：paiban_dec4
if [ -z "$DECODERS" ] || [[ " $DECODERS " == *" 4 "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=4 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec4 -lstdc++fs
  echo "已编译 paiban_dec4（维修相位排序 + 容量预判）"
fi
# 排序 + 容量预判 + 回溯修复（ρ ≡ 1，回溯窗口 BT_WINDOW=12 班）：paiban_dec5
if [ -z "$DECODERS" ] || [[ " $DECODERS " == *" 5 "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=5 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec5 -lstdc++fs
  echo "已编译 paiban_dec5（排序 + 容量预判 + 回溯修复）"
fi
# 实验0：dec5 + 强制新开带（新开区间内每个类型子区间的上 30% 不受容量预判改写）：paiban_dec5r
if [[ " $DECODERS " == *" 5r "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=5 -DFORCE_NEW_BAND -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec5r -lstdc++fs
  echo "已编译 paiban_dec5r（dec5 + 强制新开带）"
fi
# 实验1：规则 + 稀疏偏离编码：paiban_dec6
if [[ " $DECODERS " == *" 6 "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=6 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec6 -lstdc++fs
  echo "已编译 paiban_dec6（规则 + 稀疏偏离）"
fi
# 实验1：dec6 的变体——新开偏离不受容量预判约束、偏离中 30% 为新开：paiban_dec6b
if [[ " $DECODERS " == *" 6b "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=6 -DSDE_NEW_CAP=0 -DSDE_REUSE_SHARE=0.7 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec6b -lstdc++fs
  echo "已编译 paiban_dec6b"
fi
# 实验2：解码方式基因（末位选 dec5 或 dec6b）：paiban_dec7
if [[ " $DECODERS " == *" 7 "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=7 -DSDE_NEW_CAP=0 -DSDE_REUSE_SHARE=0.7 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec7 -lstdc++fs
  echo "已编译 paiban_dec7（解码方式基因：dec5 / dec6b）"
fi
# 实验3：偏离密度编码（--dev-density d 固定；不给则由末位基因自适应）：paiban_dec8
if [[ " $DECODERS " == *" 8 "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=8 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec8 -lstdc++fs
  echo "已编译 paiban_dec8（偏离密度）"
fi
# 实验3：dec6b + 可调偏离槽数（--slot-frac f，K = ⌈f·Nmax⌉；--slot-adapt 由末位基因决定启用几个槽）：paiban_dec9
if [[ " $DECODERS " == *" 9 "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=6 -DSDE_NEW_CAP=0 -DSDE_REUSE_SHARE=0.7 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec9 -lstdc++fs
  echo "已编译 paiban_dec9（dec6b + 可调偏离槽数）"
fi
# 容量预判解码的固定裕度版本（ρ ≡ 1，不用裕度基因），用于消融
if [ -z "$DECODERS" ] || [[ " $DECODERS " == *" 3 "* ]]; then
  g++ -std=c++17 -O2 -w -Iinclude -DROBOT_DECODER=3 -DCAP_RHO_SPAN=0 -DROBOT_DECODER_THETA=$THETA $SRC -o paiban_dec3f -lstdc++fs
  echo "已编译 paiban_dec3f（ρ 固定为 1）"
fi
