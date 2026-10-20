#!/bin/bash
cd "$(dirname "$0")"
export PAIBAN_SRC="$(cd .. && pwd)"
V=dec3f,dec3f+wb,dec3fr,dec5,dec5+wb,dec5r,dec5r+wb
python3 ga.py 原请求_paiban $V 20 out/ga_原请求_paiban.csv > out/ga_原请求.log 2>&1 &
python3 ga.py D_三类型资源紧 $V 20 out/ga_D_三类型资源紧.csv > out/ga_D.log 2>&1 &
wait
echo done > out/GA_DONE
