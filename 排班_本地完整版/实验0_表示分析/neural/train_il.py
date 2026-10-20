"""模仿学习：共享 MLP 给候选打分，每个决策状态在自己的候选集合上做 softmax，最小化加权交叉熵（标签 = 好解选的动作）。
权重：非支配层 rank 的解权重 1/(rank+1)；每个实例总权重相同（避免长时域实例主导）。
早停：从 15 个训练实例中留出 3 个（E/H/M 各 1）做验证；测试实例完全不参与。
用法: python train_il.py 数据.npz 输出.npz [--src dec5|all] [--hidden 32,16] [--epochs 60] [--seed 0]
"""
import argparse, json, time
import numpy as np
import nnrule as N
import features as F

VAL_INSTS = ["E21_720h", "H20_480h", "M20_1080h"]


def seg_softmax(s, gs):
    m = np.maximum.reduceat(s, gs[:-1])
    rep = np.repeat(m, np.diff(gs))
    e = np.exp(s - rep)
    z = np.add.reduceat(e, gs[:-1])
    return e / np.repeat(z, np.diff(gs)), z, m


def fwd(p, X):
    nl = int(p["nl"]); H = [(X - p["mu"]) / p["sd"]]
    for li in range(nl):
        a = H[-1] @ p[f"W{li}"] + p[f"b{li}"]
        H.append(np.tanh(a) if li < nl - 1 else a)
    return H


def loss_grad(p, X, gs, y, w):
    H = fwd(p, X)
    s = H[-1][:, 0]
    P, _, _ = seg_softmax(s, gs)
    idx = gs[:-1] + y
    loss = -np.sum(w * np.log(P[idx] + 1e-12)) / w.sum()
    ds = P * np.repeat(w, np.diff(gs))
    ds[idx] -= w
    ds /= w.sum()
    g, d = {}, ds[:, None]
    for li in range(int(p["nl"]) - 1, -1, -1):
        g[f"W{li}"] = H[li].T @ d
        g[f"b{li}"] = d.sum(0)
        if li > 0:
            d = (d @ p[f"W{li}"].T) * (1 - H[li] ** 2)
    acc = np.mean(np.array([np.argmax(s[a:b]) for a, b in zip(gs[:-1], gs[1:])]) == y)
    return loss, g, acc


def subset(gs, X, y, w, sel):
    """取出若干状态（sel 为状态下标）组成新的分组数据"""
    a, b = gs[sel], gs[sel + 1]
    if len(sel) == 0:
        return X[:0], np.array([0]), y[:0], w[:0]
    idx = np.concatenate([np.arange(i, j) for i, j in zip(a, b)])
    ngs = np.concatenate([[0], np.cumsum(b - a)])
    return X[idx], ngs, y[sel], w[sel]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out")
    ap.add_argument("--src", default="dec5", choices=["dec5", "all"])
    ap.add_argument("--hidden", default="32,16")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--l2", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    d = np.load(a.data)
    X, gs, y, meta, insts = d["X"], d["gs"], d["y"], d["meta"], list(d["insts"])
    keep = np.arange(len(y)) if a.src == "all" else np.where(meta[:, 1] == 0)[0]
    w = 1.0 / (meta[:, 4] + 1.0)
    inst = meta[:, 0].astype(int)
    for k in np.unique(inst):                      # 每个实例总权重相同
        m = inst == k
        w[m] *= 1.0 / w[m].sum()
    vid = [insts.index(v) for v in VAL_INSTS if v in insts]
    isval = np.isin(inst, vid)
    tr_s, va_s = keep[~isval[keep]], keep[isval[keep]]
    Xtr, gtr, ytr, wtr = subset(gs, X, y, w, tr_s)
    Xva, gva, yva, wva = subset(gs, X, y, w, va_s)
    hidden = tuple(int(h) for h in a.hidden.split(",")) if a.hidden else ()
    p = N.init_params(hidden, a.seed)
    p["mu"], p["sd"] = Xtr.mean(0), np.where(Xtr.std(0) > 1e-6, Xtr.std(0), 1.0)
    keys = [k for k in p if k[0] in "Wb"]
    mom = {k: np.zeros_like(p[k]) for k in keys}; vel = {k: np.zeros_like(p[k]) for k in keys}
    rng = np.random.default_rng(a.seed)
    best, best_p, t0, step, hist = 1e9, None, time.time(), 0, []
    base_va = np.mean(yva == 0) if len(yva) else 0
    for ep in range(a.epochs):
        order = rng.permutation(len(ytr))
        for bi in range(0, len(order), a.batch):
            sel = order[bi:bi + a.batch]
            Xb, gb, yb, wb = subset(gtr, Xtr, ytr, wtr, sel)
            _, g, _ = loss_grad(p, Xb, gb, yb, wb)
            step += 1
            for k in keys:
                g[k] = g[k] + a.l2 * p[k] if k[0] == "W" else g[k]
                mom[k] = 0.9 * mom[k] + 0.1 * g[k]; vel[k] = 0.999 * vel[k] + 0.001 * g[k] ** 2
                p[k] = p[k] - a.lr * (mom[k] / (1 - 0.9 ** step)) / (np.sqrt(vel[k] / (1 - 0.999 ** step)) + 1e-8)
        ltr, _, atr = loss_grad(p, Xtr, gtr, ytr, wtr)
        lva, _, ava = loss_grad(p, Xva, gva, yva, wva) if len(yva) else (ltr, None, atr)
        hist.append((ep, ltr, atr, lva, ava))
        if lva < best:
            best, best_p = lva, {k: v.copy() for k, v in p.items()}
        if ep % 10 == 0 or ep == a.epochs - 1:
            print(f"ep {ep:3d}  训练 CE {ltr:.4f} 准确率 {atr:.3f} | 验证 CE {lva:.4f} 准确率 {ava:.3f}", flush=True)
    N.NNRule(best_p).save(a.out)
    info = {"data": a.data, "src": a.src, "hidden": hidden, "n_weights": N.n_weights(best_p), "train_states": int(len(ytr)),
            "val_states": int(len(yva)), "val_insts": VAL_INSTS, "best_val_ce": float(best), "val_acc_if_default": float(base_va),
            "seconds": time.time() - t0, "epochs": a.epochs, "history": hist}
    json.dump(info, open(a.out.replace(".npz", ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"保存 {a.out}；{N.n_weights(best_p)} 个权重，训练 {len(ytr)} 个状态，{info['seconds']:.0f}s；"
          f"验证集上\"总选默认首选\"的准确率 {base_va:.3f}")


if __name__ == "__main__":
    main()
