#!/usr/bin/env bash
# 把算法库 MOEA_serial_full_cpp/Multi_serial_v3（247 个多目标算法）接到排班目标函数上
# 用法：LIBDIR=算法库源码目录 bash build_lib.sh        → paiban_lib_dec2、paiban_lib_dec3
#   LIBDIR 默认 ../../../MOEA_serial_full_cpp/Multi_serial_v3/Multi_serial_v3（即本文件夹在 算法库/目标函数/排班/ 下时的相对位置）
set -e
cd "$(dirname "$0")"
LIBDIR=${LIBDIR:-../../../MOEA_serial_full_cpp/Multi_serial_v3/Multi_serial_v3}
THETA=${THETA:-0.85}
mkdir -p build_lib/obj
# 1) 算法库：除 main.cpp 外全部编译成静态库（只需一次）
if [ ! -f build_lib/libmoea.a ]; then
  ls "$LIBDIR"/*.cpp | grep -v -e '/main.cpp$' -e '/Problems_bk.cpp$' > build_lib/srcs.txt
  cat build_lib/srcs.txt | xargs -P ${JOBS:-2} -I{} sh -c 'g++ -std=c++17 -O2 -w -include algorithm -include numeric -include cstring -I"'"$LIBDIR"'" -c "{}" -o build_lib/obj/$(basename "{}" .cpp).o'
  ar rcs build_lib/libmoea.a build_lib/obj/*.o
  echo "算法库已编译：$(ls build_lib/obj/*.o | wc -l) 个目标文件"
fi
g++ -std=c++17 -O2 -w -I"$LIBDIR" -c libbridge/paiban_lib_main.cpp -o build_lib/paiban_lib_main.o
g++ -std=c++17 -O2 -w -I"$LIBDIR" -c libbridge/paiban_algs.cpp -o build_lib/paiban_algs.o
# 2) 排班模型 + 桥接层（按解码方式各编一份）
MODEL="src/problem.cpp src/workflow.cpp src/Properties.cpp src/Entity.cpp libbridge/paiban_bridge.cpp"
# 2 = 排序解码；3 = 排序+容量预判（裕度基因）；3f = 排序+容量预判（ρ 固定为 1，当前最好的编码）
for D in ${DECODERS:-2 3 3f}; do
  FLAGS="-DROBOT_DECODER=${D%f}"
  [ "$D" = "3f" ] && FLAGS="$FLAGS -DCAP_RHO_SPAN=0"
  g++ -std=c++17 -O2 -w -Iinclude $FLAGS -DROBOT_DECODER_THETA=$THETA $MODEL build_lib/paiban_lib_main.o build_lib/paiban_algs.o build_lib/libmoea.a -o paiban_lib_dec$D -lstdc++fs
  echo "已编译 paiban_lib_dec$D"
done
