"""Draw the paper's figures (vector PDF) into draft/figs/ from results/ files.
Usage (from Paper5/): python -I src/paper/make_figures.py
Palette: dataviz reference categorical slots 1-5 (validated: CVD and normal-vision separation pass; low surface contrast
for slots 3-5 is relieved by a legend, direct labels, and distinct markers/line styles/hatching).
"""
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src", "scoping"))
FIG = "draft/figs"
os.makedirs(FIG, exist_ok=True)

C = {"DIRECT": "#2a78d6", "LEACH": "#eb6834", "KMRE": "#1baf7a", "PSOC": "#eda100", "LP": "#e87ba4"}
LBL = {"DIRECT": "DIRECT", "LEACH": "LEACH", "KMRE": "KMRE", "PSOC": "PSO-C", "LP": "LP schedule"}
LS = {"DIRECT": "-", "LEACH": "--", "KMRE": "-.", "PSOC": ":", "LP": "-"}
MK = {"DIRECT": "o", "LEACH": "s", "KMRE": "^", "PSOC": "D", "LP": "v"}
HATCH = {"DIRECT": "", "LEACH": "", "KMRE": "", "PSOC": "", "LP": "////"}
INK, MUTED, GRID = "#222222", "#666666", "#dddddd"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9, "legend.fontsize": 8, "xtick.labelsize": 8,
    "ytick.labelsize": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.axisbelow": True, "lines.linewidth": 1.4, "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
})
W = 6.3  # text width in inches (elsarticle preprint)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


def fig_deployment():
    import e8_model_v2 as v2
    pos = np.random.default_rng(100).uniform(0, 100, (100, 2))
    fig, ax = plt.subplots(figsize=(3.2, 4.4))
    ax.add_patch(plt.Rectangle((0, 0), 100, 100, fill=False, ec=MUTED, lw=0.8))
    ax.scatter(pos[:, 0], pos[:, 1], s=9, c=INK, lw=0, zorder=3, label="Sensor node")
    r = v2.Model("CC2420").rmax
    th = np.linspace(0, 2 * np.pi, 400)
    for i, (name, (x, y)) in enumerate(v2.SINKS.items()):
        ax.plot(x + r * np.cos(th), y + r * np.sin(th), color=C["DIRECT"], lw=0.9, ls="--",
                label=f"CC2420 range ({r:.0f} m)" if i == 0 else None, zorder=2)
        ax.scatter([x], [y], marker="^", s=60, c="white", ec=INK, lw=1.0, zorder=4)
        ax.annotate(f"{name} sink", (x, y), xytext=(7, 4), textcoords="offset points", fontsize=8, color=INK, zorder=5,
                    bbox={"boxstyle": "square,pad=0.15", "fc": "white", "ec": "none"})
    ax.set_xlim(-5, 105); ax.set_ylim(-5, 226)
    ax.set_aspect("equal"); ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.grid(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False, handlelength=1.6)
    fig.savefig(f"{FIG}/fig_deployment.pdf"); plt.close(fig)


def fig_audit():
    rows = list(csv.DictReader(open("papers/audit/coding.csv", encoding="utf-8")))
    stated = [r for r in rows if r["energy_model"] != "NONE"]
    items = [("First-order energy model", sum(r["energy_model"] == "FO" for r in stated), len(stated)),
             ("Datasheet radio in simulation", sum(r["datasheet_sim"] == "1" for r in rows), len(rows)),
             ("Comparison with optimum or bound", sum(r["bound_or_optimum"] == "1" for r in rows), len(rows)),
             ("Idle listening modelled", sum(r["idle_listening_modelled"] == "1" for r in rows), len(rows)),
             ("Direct transmission as baseline", sum(r["direct_baseline"] == "1" for r in rows), len(rows))]
    located = [r for r in rows if r["sink"] != "unstated"]
    sinks = [("Centre or inside", sum(r["sink"] == "centre" for r in located), len(located)),
             ("Edge or border", sum(r["sink"] == "edge" for r in located), len(located)),
             ("Outside the field", sum(r["sink"] == "outside" for r in located), len(located))]
    fig, axs = plt.subplots(2, 1, figsize=(W * 0.8, 3.1), gridspec_kw={"height_ratios": [5, 3]})
    for ax, data, title in [(axs[0], items, "(a) Evaluation practice"), (axs[1], sinks, "(b) Sink position")]:
        y = np.arange(len(data))[::-1]
        p = [wilson(k, n) for _, k, n in data]
        ax.barh(y, [q[0] for q in p], height=0.55, color=C["DIRECT"], ec="white", lw=1)
        ax.errorbar([q[0] for q in p], y, xerr=[[q[0] - q[1] for q in p], [q[2] - q[0] for q in p]], fmt="none",
                    ecolor=INK, elinewidth=0.8, capsize=2)
        for yi, (lab, k, n), q in zip(y, data, p):
            ax.text(q[2] + 0.015, yi, f"{k}/{n}", va="center", fontsize=8, color=INK)
        ax.set_yticks(y, [d[0] for d in data]); ax.set_xlim(0, 1.08); ax.grid(axis="y", visible=False)
        ax.set_title(title, loc="left", color=INK)
    axs[1].set_xlabel("Share of coded papers (95% Wilson interval)")
    fig.tight_layout(); fig.savefig(f"{FIG}/fig_audit.pdf"); plt.close(fig)


def load_e8():
    d = {}
    for l in open("results/e8_v2.txt", encoding="utf-8"):
        m = re.match(r"V2 (\S+) (\S+) seed (\d) rmax \S+: DIRECT=(\d+) LEACH=(\d+) KMRE=(\d+) PSOC=(\d+) LP=\[([\d.]+),([\d.]+)\]", l)
        if m:
            d[(m[1], m[2], int(m[3]))] = (dict(zip(["DIRECT", "LEACH", "KMRE", "PSOC"], map(int, m.groups()[3:7]))),
                                          float(m[8]), float(m[9]))
    return d


def load_lp():
    d = {}
    for l in open("results/e10_lp_protocol.txt", encoding="utf-8"):
        m = re.match(r"LPSCHED (\S+) (\S+) seed (\d) replan 50 noise 0.0: FND (\d+)", l)
        if m:
            d[(m[1], m[2], int(m[3]))] = int(m[4])
    return d


def fig_gap():
    e8, lp = load_e8(), load_lp()
    radios = [("FO", "First-order model"), ("CC2420", "CC2420 (2.4 GHz)"), ("nRF52840v3", "nRF52840 (2.4 GHz)"),
              ("CC1101-868", "CC1101 (868 MHz)")]
    sinks = ["far", "edge", "centre"]
    strat = ["DIRECT", "LEACH", "KMRE", "PSOC", "LP"]
    fig, axs = plt.subplots(1, 4, figsize=(W, 2.5), sharey=True)
    bw = 0.15
    for ax, (rad, title) in zip(axs, radios):
        for gi, s in enumerate(sinks):
            keys = [(rad, s, i) for i in range(3) if (rad, s, i) in e8]
            if not keys:
                ax.text(gi, 0.04, "not\nreachable", ha="center", va="bottom", fontsize=7, color=MUTED)
                continue
            for si, st in enumerate(strat):
                if st == "LP":
                    vals = [lp[k] / e8[k][2] for k in keys if k in lp]
                else:
                    vals = [e8[k][0][st] / e8[k][2] for k in keys]
                if not vals:
                    continue
                x = gi + (si - 2) * bw
                ax.bar(x, np.mean(vals), width=bw, color=C[st], ec="white", lw=0.8, hatch=HATCH[st],
                       label=LBL[st] if gi == 0 or (rad == "FO" and gi == 0) else None)
            lbub = np.mean([e8[k][1] / e8[k][2] for k in keys])
            ax.plot([gi - 2.6 * bw, gi + 2.6 * bw], [lbub, lbub], color=INK, lw=0.9, ls="--")
        ax.set_xticks(range(3), sinks); ax.set_title(title, color=INK); ax.set_ylim(0, 1.05)
        ax.grid(axis="x", visible=False)
    axs[0].set_ylabel("FND / UB (mean of layouts)")
    h, lab = axs[0].get_legend_handles_labels()
    h.append(plt.Line2D([], [], color=INK, lw=0.9, ls="--")); lab.append("LB / UB")
    fig.legend(h, lab, loc="upper center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 1.08))
    fig.tight_layout(); fig.savefig(f"{FIG}/fig_gap.pdf"); plt.close(fig)


def fig_alive():
    p = "results/fig_data/alive.json"
    if not os.path.exists(p):
        print("skip alive"); return
    d = json.load(open(p))
    e8, lp = load_e8(), load_lp()
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.6))
    for ax, (rad, s, title) in zip(axs, [("FO", "centre", "(a) First-order model, centre sink"),
                                         ("CC2420", "edge", "(b) CC2420, edge sink")]):
        xmax = 0
        for st in ("DIRECT", "LEACH", "KMRE", "PSOC"):
            tr = np.array(d[f"{rad} {s} {st}"])
            x = np.r_[tr[:, 0], tr[-1, 0]]
            ax.step(tr[:, 0], tr[:, 1], where="post", color=C[st], ls=LS[st], label=LBL[st])
            xmax = max(xmax, tr[-1, 0])
        k = (rad, s, 0)
        ax.axvline(e8[k][1], color=INK, lw=0.9, ls="--")
        ax.annotate("LB on FND", (e8[k][1], 50), xytext=(3, 0), textcoords="offset points", fontsize=7, color=INK)
        if k in lp:
            ax.plot([lp[k]], [99.5], marker=MK["LP"], ms=7, color=C["LP"], mec=INK, mew=0.6, ls="none",
                    label="LP schedule (FND)")
        ax.set_xlim(0, max(xmax, e8[k][1]) * 1.06); ax.set_ylim(0, 104)
        ax.set_xlabel("Round"); ax.set_title(title, loc="left", color=INK)
    axs[0].set_ylabel("Alive and connected nodes")
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.08))
    fig.tight_layout(); fig.savefig(f"{FIG}/fig_alive.pdf"); plt.close(fig)


def fig_residual():
    p = "results/fig_data/residual.json"
    if not os.path.exists(p):
        print("skip residual"); return
    d = json.load(open(p))
    order = ["DIRECT", "LEACH", "KMRE", "PSOC", "LP"]
    fig, ax = plt.subplots(figsize=(W * 0.75, 2.5))
    data = [np.array(d[s][1]) * 1e3 for s in order]
    bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=False, medianprops={"color": INK, "lw": 1})
    for patch, s in zip(bp["boxes"], order):
        patch.set_facecolor(C[s]); patch.set_alpha(0.35); patch.set_edgecolor(INK); patch.set_linewidth(0.7)
    rng = np.random.default_rng(0)
    for i, (s, v) in enumerate(zip(order, data), 1):
        ax.scatter(i + rng.uniform(-0.17, 0.17, len(v)), v, s=6, color=C[s], ec=INK, lw=0.2, zorder=3, marker=MK[s])
    ax.set_xticks(range(1, 6), [f"{LBL[s]}\nFND {d[s][0]}" for s in order])
    ax.set_ylabel("Residual energy at FND (mJ)"); ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(f"{FIG}/fig_residual.pdf"); plt.close(fig)


def fig_cg():
    p = "results/fig_data/cg.json"
    if not os.path.exists(p):
        print("skip cg"); return
    d = json.load(open(p))
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.3))
    for ax, (key, title) in zip(axs, [("FO centre", "(a) First-order model, centre sink"),
                                      ("CC2420 centre", "(b) CC2420, centre sink")]):
        tr = np.array(d[key])
        ax.plot(tr[:, 0], tr[:, 2], color=C["LEACH"], ls="--", label="Upper bound (UB)")
        ax.plot(tr[:, 0], tr[:, 1], color=C["DIRECT"], label="Lower bound (LB)")
        ax.set_xlabel("Column-generation iteration"); ax.set_title(title, loc="left", color=INK)
        ax.set_ylim(tr[:, 1].min() * 0.95, tr[:, 2].max() * 1.05)
        ax.annotate(f"final LB/UB = {tr[-1, 1] / tr[-1, 2]:.3f}", (tr[-1, 0], tr[-1, 1]), xytext=(-5, -16),
                    textcoords="offset points", ha="right", fontsize=7, color=INK)
    axs[0].set_ylabel("Rounds to FND")
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.07))
    fig.tight_layout(); fig.savefig(f"{FIG}/fig_cg.pdf"); plt.close(fig)


if __name__ == "__main__":
    for f in (fig_deployment, fig_audit, fig_gap, fig_alive, fig_residual, fig_cg):
        f(); print("ok", f.__name__)
