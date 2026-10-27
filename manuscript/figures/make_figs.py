"""Data figures for the manuscript (drafts). Run from the repo root:
   python manuscript/figures/make_figs.py
Reads only result files in the repo; writes vector PDFs next to this script."""
import csv, os, re, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXP = os.path.join(ROOT, "排班_本地完整版", "实验0_表示分析")
OUT = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.family": "serif", "font.serif": ["TeX Gyre Termes", "Times New Roman", "DejaVu Serif"],
                     "mathtext.fontset": "stix", "font.size": 8, "axes.linewidth": 0.6, "axes.edgecolor": "#52514e",
                     "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.labelcolor": "#0b0b0b",
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
                     "grid.color": "#e4e3df", "grid.linewidth": 0.5, "lines.linewidth": 1.4, "lines.markersize": 4})
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"   # categorical slots 1-3, + violet
MK = ["o", "s", "^", "D"]
COL1, COL2 = 3.5, 7.16                                        # IEEE column / page width (in)


def hv(P, ref=1.1):
    P = sorted(set(P)); nd, b = [], float("inf")
    for p in P:
        if p[1] < b:
            nd.append(p); b = p[1]
    v, pb = 0.0, ref
    for a, c in nd:
        if a < ref and c < pb:
            v += (ref - a) * (pb - c); pb = c
    return v / ref ** 2


def nd(P):
    out, b = [], float("inf")
    for a, c in sorted(set(P)):
        if c < b:
            out.append((a, c)); b = c
    return out


# ---------------------------------------------------------------- Fig: FJSP rate collapse
def fig_rate():
    R = collections.defaultdict(list)
    for f in ("v3_qk.csv", "v3_qk2.csv"):
        for r in csv.DictReader(open(os.path.join(EXP, "bench", f))):
            s = r["front(makespan:workload;...)"]
            R[(r["instance"], r["encoding"], int(r["evals"]))].append([tuple(map(float, p.split(":"))) for p in s.split(";")] if s else [])
    insts = sorted({k[0] for k in R}); encs = sorted({k[1] for k in R})
    sp = [e for e in encs if e.startswith("sp")]
    fq = lambda e: tuple(float(v) for v in re.match(r"sp([\d.]+)q([\d.]+)", e).groups())
    fig, axs = plt.subplots(1, 2, figsize=(COL2, 2.1), sharey=True)
    for b, ls in ((465, "-"), (20000, "--")):
        M = collections.defaultdict(list)
        for n in insts:
            pts = np.array([p for e in encs for fr in R[(n, e, b)] for p in fr]); lo, hi = pts.min(0), pts.max(0)
            rg = np.where(hi - lo > 1e-9, hi - lo, 1)
            for e in sp:
                M[e].append(np.mean([hv([tuple((np.array(p) - lo) / rg) for p in fr]) for fr in R[(n, e, b)]]))
        for qi, (q, c) in enumerate(((0.2, C1), (0.4, C2), (0.6, C3))):
            es = sorted([e for e in sp if fq(e)[1] == q], key=lambda e: fq(e)[0])
            k = [fq(e)[0] for e in es]; y = [np.mean(M[e]) for e in es]
            lab = f"$q={q}$" if b == 465 else None
            axs[0].plot(k, y, ls, color=c, marker=MK[qi], label=lab, mfc="white" if b == 20000 else c)
            axs[1].plot([q * kk for kk in k], y, ls, color=c, marker=MK[qi], mfc="white" if b == 20000 else c)
    for ax, xl in zip(axs, (r"slot ratio $\kappa$", r"deviation rate $\rho=q\kappa$")):
        ax.set_xscale("log"); ax.set_xlabel(xl); ax.grid(True, which="major")
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axs[0].set_xticks([0.05, 0.1, 0.2, 0.5, 1, 2, 3]); axs[1].set_xticks([0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.6])
    axs[0].set_ylabel("mean HV")
    axs[0].legend(loc="lower right", fontsize=7)
    axs[1].plot([], [], "-", color="#52514e", label="465 evaluations"); axs[1].plot([], [], "--", color="#52514e", mfc="white", marker="o", label="20 000 evaluations")
    axs[1].legend(loc="lower right", fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fjsp_rate.pdf")); plt.close(fig)


# ---------------------------------------------------------------- Fig: FJSP gap vs budget (values from report_v3_big_all.md)
def fig_budget():
    B = [465, 2000, 5000, 10000, 20000]
    S = {"RK": [36.4, 30.7, 26.8, 24.4, 22.4], "RK+seed": [24.8, 22.3, 20.7, 19.7, 18.6],
         "RK+GLR+seed": [19.5, 17.9, 16.9, 16.1, 15.4], r"RDD, $\rho=0.2$": [14.6, 12.5, 11.5, 10.8, 10.2]}
    fig, ax = plt.subplots(figsize=(COL1, 2.2))
    for i, (k, v) in enumerate(S.items()):
        ax.plot(B, v, color=(C4, C2, C3, C1)[i], marker=MK[i], label=k)
        ax.annotate(k, (B[-1], v[-1]), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7, color="#0b0b0b")
    ax.set_xscale("log"); ax.set_xticks(B); ax.set_xticklabels(["465", "2k", "5k", "10k", "20k"])
    ax.set_xlim(380, 90000); ax.set_xlabel("evaluations"); ax.set_ylabel("mean gap to best-known (%)"); ax.grid(True)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fjsp_budget.pdf")); plt.close(fig)


# ---------------------------------------------------------------- Fig: rostering fronts (median-HV run per method)
def fig_fronts():
    R = collections.defaultdict(list)
    for f, arm in (("val_server.csv", "dec5"), ("val_Kext.csv", "X1.0:ES16(s0)")):
        for r in csv.DictReader(open(os.path.join(EXP, "neural", "out", f), encoding="utf-8")):
            if r["variant"] == arm and r["evaluations"] == "465":
                s = r["front(资源数:均衡度;...)"]
                R[(r["scenario"], arm)].append([tuple(map(float, p.split(":"))) for p in s.split(";")] if s else [])
    arms = ("dec5", "X1.0:ES16(s0)")
    insts = sorted({k[0] for k in R if all((k[0], a) in R for a in arms)})
    rows = {}
    for n in insts:
        pts = np.array([p for a in arms for fr in R[(n, a)] for p in fr]); lo, hi = pts.min(0), pts.max(0)
        rg = np.where(hi - lo > 1e-9, hi - lo, 1)
        H = {a: [hv([tuple((np.array(p) - lo) / rg) for p in fr]) if fr else 0 for fr in R[(n, a)]] for a in arms}
        rows[n] = H
    pick = []
    for g in "EHM":
        cand = [n for n in insts if n.startswith(g)]
        gain = sorted(cand, key=lambda n: np.mean(rows[n][arms[1]]) - np.mean(rows[n][arms[0]]))
        pick.append(gain[len(gain) // 2])
    fig, axs = plt.subplots(1, 3, figsize=(COL2, 2.0))
    for ax, n in zip(axs, pick):
        for i, (a, lab, c) in enumerate(((arms[0], "D5", C2), (arms[1], r"RDD + ES16, $\rho=0.4$", C1))):
            hs = rows[n][a]; k = int(np.argsort(hs)[len(hs) // 2])
            P = nd(R[(n, a)][k])
            xs = [p[0] for p in P]; ys = [p[1] for p in P]
            ax.step(xs, ys, where="post", color=c, lw=1.0); ax.plot(xs, ys, MK[i], color=c, label=lab, ms=4.5, mec="white", mew=0.6)
        ax.set_title(n.split("_")[0] + f" ({n.split('_')[1]})", fontsize=8); ax.set_xlabel("resource count $f_1$"); ax.grid(True)
        ax.xaxis.get_major_locator().set_params(integer=True)
    axs[0].set_ylabel("imbalance $f_2$"); axs[0].legend(fontsize=7, loc="upper right")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "roster_fronts.pdf")); plt.close(fig)
    print("fronts:", pick)


# ---------------------------------------------------------------- Fig: rostering HV vs deviation rate (values of Table kcurve, fact-checked 2026-10-23)
def fig_roster_rate():
    rho = [0.1, 0.2, 0.3, 0.4]
    T = {"Training (15)": {"All": ([0.622, 0.698, 0.732, 0.737], 0.491), "E": ([0.431, 0.579, 0.637, 0.656], 0.608),
                           "H": ([0.655, 0.708, 0.742, 0.734], 0.471), "M": ([0.778, 0.808, 0.817, 0.821], 0.393)},
         "Test (47)": {"All": ([0.719, 0.769, 0.783, 0.786], 0.570), "E": ([0.656, 0.758, 0.772, 0.781], 0.733),
                       "H": ([0.681, 0.722, 0.744, 0.744], 0.550), "M": ([0.777, 0.810, 0.806, 0.809], 0.463)}}
    col = {"All": "#0b0b0b", "E": C1, "H": C2, "M": C3}
    mk = {"All": "o", "E": "s", "H": "^", "M": "D"}
    fig, axs = plt.subplots(1, 2, figsize=(COL1, 1.9), sharey=True)
    for ax, (name, G) in zip(axs, T.items()):
        for g, (y, d5) in G.items():
            ax.plot(rho, y, color=col[g], marker=mk[g], label=g, lw=1.2, ms=3.5)
            ax.axhline(d5, color=col[g], lw=0.7, ls=":")
        ax.set_title(name, fontsize=8); ax.set_xticks(rho); ax.set_xlabel(r"deviation rate $\rho$"); ax.grid(True, axis="y")
    axs[0].set_ylabel("mean HV")
    axs[1].legend(fontsize=6.5, loc="lower right", ncol=2, handlelength=1.4)
    fig.tight_layout(pad=0.4); fig.savefig(os.path.join(OUT, "roster_rate.pdf")); plt.close(fig)


if __name__ == "__main__":
    fig_rate(); fig_budget(); fig_fronts(); fig_roster_rate()
