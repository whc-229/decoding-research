"""生成重排班场景：每个实例 3 类机器人扰动，各在原计划进行到 30% / 60% 时发生，共 6 个场景。
  breakdown    原计划下一班的机器人故障停用 48 h（修好后预算恢复满额）
  early_maint  原计划下一班的机器人必须先去维修（维修提前，子任务顺序改变）
  delay        原计划下一班的机器人延误 8 h
（超时 overrun、工具报废 tool_loss 在自检中照原计划就能吸收、几乎不需要改派，不放进主实验。）
用法: python gen_scenarios.py   输出 scenarios.json"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C  # noqa: E402

EVENTS = [("breakdown", {"type": "breakdown", "D": 48}), ("early_maint", {"type": "early_maint"}), ("delay", {"type": "delay", "d": 8})]
FRACS = [0.3, 0.6]

if __name__ == "__main__":
    out = {}
    for p in sorted(glob.glob(os.path.join(HERE, "plans", "*.npy"))):
        inst = os.path.basename(p)[:-4]
        x = np.load(p)
        pl = C.Plan(C.I.load(inst), x)
        for name, ev in EVENTS:
            for fr in FRACS:
                k = int(fr * len(pl.duties))
                scn = C.Scenario(inst, x, k, ev)
                kk = k
                while not scn.valid and kk < len(pl.duties) - 1:      # 下一班原计划新开机器人时，顺延到下一班
                    kk += 1; scn = C.Scenario(inst, x, kk, ev)
                if scn.valid:
                    out[f"{inst}|{name}|{fr}"] = dict(inst=inst, k=kk, ev=ev, desc=scn.desc, t0=scn.t0, n_left=scn.n_left,
                                                    plan_obj=pl.obj, split="train" if inst in C.I.split()[0] else "test")
    json.dump(out, open(os.path.join(HERE, "scenarios.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "个场景")
