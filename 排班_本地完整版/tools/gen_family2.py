"""实验3 扩充：再生成 48 个实例（E/H/M 各 16 个，名字编号从 11 起，不与原实例族冲突）。
生成规则与 tools/gen_family.py 相同，只换随机种子；为控制计算量，1440 h 的时域改为 1080 h。
用法: python tools/gen_family2.py [输出目录，默认 requests_family2]
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_family as F

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "requests_family2")
    os.makedirs(out, exist_ok=True)
    rng = random.Random(20261015)
    meta = {}
    for group in ("E", "H", "M"):
        for j in range(11, 27):
            robots, tools, T = F.gen(rng, group)
            T = min(T, 1080)
            name = f"{group}{j:02d}_{T}h"
            json.dump(F.make(robots, tools, T), open(os.path.join(out, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            meta[name] = dict(T=T, robots=robots, tools=tools)
    json.dump(meta, open(os.path.join(HERE, "tools", "family2_参数.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(meta), "个实例 →", out)
