#!/bin/bash
cd "$(dirname "$0")"
ls ../requests_family/*.json | xargs -n1 basename | sed 's/.json$//' | while read s; do [ -f out8/$s.json ] || echo $s; done | xargs -P 2 -I{} python3 features8.py {} 100 out8 > out8/feat.log 2>&1
echo done > out8/FEAT_DONE
