"""一致性检查（只报告，不阻止）：
  1. 本机确定性：同一次运行跑两遍，必须完全相同（不同则代码有问题，先别跑）；
  2. 与 rulegen/out/val_full.csv 是否逐位相同：不同系统 / numpy 版本下浮点末位可能不同，NSGA-II 轨迹会分叉，
     所以不一致是正常的，只说明新旧两台机器的结果不能混在一张表里比——基线臂要在本机重跑。
用法: python check_platform.py [进程数|auto]     （约 12 次运行，几分钟）"""
import csv, multiprocessing as mp, os, sys
import common as C
import ga_any

NAME2SPEC = {"dec5": "dec5", "K0.25:default": "K0.25:default", "K0.25:LLM(r47)": "K0.25:out/full/best_rule.py"}
PICK = ["H04_480h", "M01_480h", "E20_480h"]


def main():
    mp.freeze_support()
    rows = {}
    for r in csv.DictReader(open(os.path.join(C.RULEGEN, "out", "val_full.csv"), encoding="utf-8")):
        rows[(r["scenario"], r["variant"], int(r["run"]))] = r["front(资源数:均衡度;...)"]
    insts = [i for i in PICK if (i, "dec5", 0) in rows] or sorted({k[0] for k in rows})[:3]
    jobs = [(i, n, NAME2SPEC[n], 0) for i in insts for n in NAME2SPEC if (i, n, 0) in rows]
    with mp.Pool(C.nprocs(sys.argv[1] if len(sys.argv) > 1 else "auto")) as p:
        res = p.map(ga_any.job, jobs, chunksize=1)
    again = ga_any.job(jobs[0])
    print("本机确定性：", "通过" if again[6] == res[0][6] else "失败！同一次运行两遍结果不同，先别跑，把输出发给我")
    bad = 0
    for row in res:
        old = rows[(row[0], row[1], 0)]
        same = old == row[6]
        bad += not same
        print(("一致  " if same else "不一致"), row[0], row[1], row[6], "" if same else f"（原: {old}）")
    print("与 val_full.csv 全部逐位一致：旧结果可以直接和本机新结果合并" if bad == 0 else
          f"与 val_full.csv 有 {bad}/{len(res)} 次不逐位一致（正常）：基线臂 dec5 / 默认规则 / r47 / r35 在本机重跑，全部新旧对比都用本机结果")


if __name__ == "__main__":
    main()
