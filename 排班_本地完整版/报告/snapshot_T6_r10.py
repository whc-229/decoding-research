"""T6 中期快照：等 v3_main.csv 中第 0～9 次全部齐了，把表头 + run<10 的行另存为 v3_main_r10.csv。
只读 v3_main.csv、另写新文件，不影响正在写入的主进程。每 5 分钟检查一次；完成后写标记文件并退出。
用法：python snapshot_T6_r10.py（在后台 / tmux 中运行）"""
import collections, csv, io, os, sys, time

BENCH = "/home/hk/解码研究/排班_本地完整版/实验0_表示分析/bench"
SRC, DST = f"{BENCH}/v3_main.csv", f"{BENCH}/v3_main_r10.csv"
MARK = "/home/hk/解码研究/排班_本地完整版/报告/T3_T7_标记/T6_r10快照.done"
N_INST, N_ENC, N_RUN = 276, 5, 10


def complete_lines():
    """读取 v3_main.csv 中已完整写入的行（丢弃末尾可能写了一半、没有换行符的行）。"""
    with open(SRC, encoding="utf-8") as f:
        text = f.read()
    return text[:text.rfind("\n") + 1].splitlines(keepends=True)


def check(lines):
    """按 TASKS.md 的判据检查第 0～9 次是否齐全，并额外要求每个 (实例, 编码, 次) 恰有 465/2000/5000 三行。
    返回 (是否齐全, 说明文字, 表头, 要抽取的行)。"""
    header, body = lines[0], lines[1:]
    rows = [(ln, r) for ln in body for r in csv.reader(io.StringIO(ln)) if r and int(r[2]) < N_RUN]
    c5000 = collections.Counter((r[0], r[1]) for _, r in rows if r[3] == "5000")
    trip = collections.Counter((r[0], r[1], r[2]) for _, r in rows)
    evs = collections.defaultdict(set)
    for _, r in rows:
        evs[(r[0], r[1], r[2])].add(r[3])
    need = N_INST * N_ENC
    ok = (len(c5000) == need and sum(v == N_RUN for v in c5000.values()) == need
          and len(trip) == need * N_RUN and all(v == 3 for v in trip.values())
          and all(s == {"465", "2000", "5000"} for s in evs.values()))
    msg = f"(实例,编码)组合 {len(c5000)}，其中 10 次齐全 {sum(v == N_RUN for v in c5000.values())}；(实例,编码,次) {len(trip)}，行数 {len(rows)}"
    return ok, msg, header, [ln for ln, _ in rows]


def main():
    """循环检查，齐全后写出快照文件和标记文件。"""
    while True:
        ok, msg, header, out = check(complete_lines())
        print(time.strftime("%F %T"), msg, flush=True)
        if ok:
            tmp = DST + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(header)
                f.writelines(out)
            os.replace(tmp, DST)
            with open(MARK, "w", encoding="utf-8") as f:
                f.write(f"快照时间 {time.strftime('%F %T')}，{msg}\n")
            print("快照完成", DST, flush=True)
            return
        time.sleep(300)


if __name__ == "__main__":
    sys.exit(main())
