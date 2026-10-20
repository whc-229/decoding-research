"""重放好解的排班，得到"决策时刻状态 → 好解选的动作"样本。

对每个好解：按派班序列 sim.seq 逐班前推（第 i 班用基因里的工具基因 x[i+h]，与解码相同），
每班先按当时的可用机器人和可新开类型构造候选集合与特征（features.featurize），再标出该解实际派的机器人 / 新开的类型。
重放结束后核对目标值与原解相同，不同则丢弃该解并计数。
"""
import glob, os, pickle, sys, time
import numpy as np
import common as C
import features as F

R, M = C.R, C.M


def _avail(sc, s):
    av = [r for r in s.robots if ((r.ready <= 0) if s.E == 0 else (r.ready <= s.E - sc["R"][r.type]["out_travel_time"] + 1e-9))
          and r.remain >= sc["R"][r.type]["single_work_time"]]
    av.sort(key=lambda r: (r.count, -r.remain))
    return av


def replay(sc, x, seq, obj=None, kfrac=0.25):
    """→ (样本列表[(特征矩阵, 标签下标)], 是否核对通过)"""
    x = np.asarray(x, np.float32).astype(np.float64)
    h = len(x) // 2
    K, nmax = R.n_slots(sc, kfrac)
    nty = len(sc["R"])
    tdef = min(int(x[2 * K] * nty), nty - 1)
    rc = M.rep_ceil_factory(sc)
    s = M.Sim(sc, False)
    out = []
    for i, rid in enumerate(seq):
        _, ty, ser = rid.split("_")
        ty, ser = int(ty), int(ser)
        av = _avail(sc, s)
        ctx = R.Ctx(sc, s, i, nmax, av, tdef, rc)
        acts, X = F.featurize(ctx)
        hit = [r for r in s.robots if r.type == ty and r.serial == ser]
        lab = None
        if hit:
            for j, (k, v) in enumerate(acts):
                if k == "reuse" and v._r is hit[0]:
                    lab = j; break
            if lab is None:
                return out, False
            ok = s.dispatch_reuse(hit[0], x[i + h])
        else:
            for j, (k, v) in enumerate(acts):
                if k == "new" and v == ty:
                    lab = j; break
            if lab is None:
                return out, False
            ok = s.dispatch_new(ty, x[i + h])
            ok = ok and s.robots[-1].serial == ser
        if not ok:
            return out, False
        out.append((X, lab))
    o = s.objectives()
    good = o is not None and (obj is None or (abs(o[0] - obj[0]) < 1e-9 and abs(o[1] - obj[1]) < 1e-6))
    return out, good


def build(tdir, outp):
    """把 teacher/*.pkl 全部重放，存成一个数据集 .npz：
    X[候选总数, NF]、gs[状态数+1]（每个状态的候选在 X 中的起止）、y[状态数]（标签在组内的下标）、
    meta 各列：实例编号、来源臂、运行号、解编号、非支配层、资源数、均衡度、班次号。"""
    files = sorted(glob.glob(os.path.join(tdir, "*.pkl")))
    tr, _ = C.I.split()
    Xs, gs, ys, meta = [], [0], [], []
    nsol = nbad = 0
    t = time.time()
    for fi, f in enumerate(files):
        d = pickle.load(open(f, "rb"))
        sc = C.I.load(d["inst"])
        for si, sol in enumerate(d["sols"]):
            smp, good = replay(sc, sol["x"], sol["seq"], sol["obj"])
            nsol += 1
            if not good:
                nbad += 1; continue
            for i, (X, lab) in enumerate(smp):
                if len(X) < 2:          # 只有一个候选，没有可学的
                    continue
                Xs.append(X); gs.append(gs[-1] + len(X)); ys.append(lab)
                meta.append((tr.index(d["inst"]), 0 if d["arm"] == "dec5" else 1, d["run"], fi * 1000 + si, sol["rank"],
                             sol["obj"][0], sol["obj"][1], i))
    X = np.concatenate(Xs) if Xs else np.zeros((0, F.NF))
    np.savez_compressed(outp, X=X, gs=np.array(gs), y=np.array(ys), meta=np.array(meta, np.float64),
                        names=np.array(F.NAMES), insts=np.array(tr))
    print(f"{len(files)} 个文件，{nsol} 个解（重放核对失败 {nbad}），{len(ys)} 个决策样本，{len(X)} 个候选，{time.time() - t:.0f}s")
    return nbad


if __name__ == "__main__":
    tdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(C.OUT, "teacher")
    outp = sys.argv[2] if len(sys.argv) > 2 else os.path.join(C.OUT, "il_data.npz")
    build(tdir, outp)
