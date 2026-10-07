#!/usr/bin/env python3
"""Figures for the validation deck."""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reference import SHEETS, NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figs")
BLUE, ORANGE, GREY, INK = "#2a6fdb", "#e8743b", "#9aa3ad", "#1f2933"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans",
                     "axes.edgecolor": "#555", "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})
ORDER = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"]
LBL = {k: ("A*" if k == "A_built" else k) for k in ORDER}


def load(tag):
    r = json.load(open(os.path.join(HERE, "results", f"layouts_{tag}.json")))
    return {(x["layout"], x["m_gs"]): x for x in r}


def compare_bars(res, key_idx, key, fname, xlabel, log=False, title=""):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, flow in zip(axes, (17.5, 5.0)):
        y = np.arange(len(ORDER))[::-1]
        sheet = [SHEETS[k][flow if flow != 5.0 else 5][key_idx] for k in ORDER]
        mine = [res.get((k, flow), {}).get(key, np.nan) for k in ORDER]
        ax.barh(y + 0.2, sheet, 0.38, color=GREY, label="result sheets (deck)")
        ax.barh(y - 0.2, mine, 0.38, color=BLUE if flow == 17.5 else ORANGE, label="this re-validation")
        for yi, s, m in zip(y, sheet, mine):
            ax.text(max(s, m if np.isfinite(m) else 0) * (1.05 if not log else 1.15), yi, f"{s:g} / {m:.3g}" if np.isfinite(m) else f"{s:g}",
                    va="center", fontsize=8, color=INK)
        ax.set_yticks(y); ax.set_yticklabels([LBL[k] for k in ORDER])
        ax.set_title(f"{flow:g} g/s", loc="left", fontsize=11, color=INK)
        ax.set_xlabel(xlabel)
        if log: ax.set_xscale("log")
        ax.grid(axis="x", color="#e5e7eb"); ax.set_axisbelow(True)
        ax.set_xlim(right=ax.get_xlim()[1] * (1.25 if not log else 3))
    axes[0].legend(loc="lower right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, fname), dpi=170); plt.close(fig)


def parity(res, fname):
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
    for ax, (idx, key, lab, lim) in zip(axes, ((0, "spread_mK", "inner-wall spread, mK", (0, 140)),
                                                (1, "inlet_C", "inlet that centres the wall, °C", (-30.85, -30.0)),
                                                (3, "UA_WK", "coolant-copper UA, W/K", (0, 100)))):
        for flow, c in ((17.5, BLUE), (5.0, ORANGE)):
            xs, ys, ls = [], [], []
            for k in ORDER:
                if (k, flow) in res:
                    xs.append(SHEETS[k][flow if flow != 5.0 else 5][idx]); ys.append(res[(k, flow)][key]); ls.append(LBL[k])
            ax.scatter(xs, ys, s=28, color=c, label=f"{flow:g} g/s", zorder=3)
            for x, y, l in zip(xs, ys, ls):
                ax.annotate(l, (x, y), xytext=(3, 3), textcoords="offset points", fontsize=7, color=c)
        ax.plot(lim, lim, color="#888", lw=1)
        if key == "spread_mK":
            ax.fill_between(lim, [lim[0] - 10, lim[1] - 10], [lim[0] + 10, lim[1] + 10], color="#e5e7eb", zorder=0, label="±10 mK")
        if key == "inlet_C":
            ax.fill_between(lim, [lim[0] - .02, lim[1] - .02], [lim[0] + .02, lim[1] + .02], color="#e5e7eb", zorder=0, label="±20 mK")
        ax.set_xlim(lim); ax.set_ylim(lim)
        ax.set_xlabel("result sheet (deck)"); ax.set_ylabel("this re-validation"); ax.set_title(lab, loc="left", fontsize=10)
        ax.grid(color="#f0f0f0")
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=170); plt.close(fig)


def wall_maps(tag, flow, fname):
    fig, axes = plt.subplots(3, 4, figsize=(13, 8.2))
    vmax = 0.08
    for ax, k in zip(axes.ravel(), ORDER + [None]):
        if k is None:
            ax.axis("off"); continue
        f = os.path.join(HERE, "results", f"field_{tag}_{k}_{flow:g}.npz")
        if not os.path.exists(f):
            ax.axis("off"); continue
        d = np.load(f)
        Tw = d["Tw"] + 30.0
        im = ax.pcolormesh(np.degrees(d["tc"]), d["zc"], Tw.T * 1e3, cmap="RdBu_r", vmin=-vmax * 1e3, vmax=vmax * 1e3, shading="auto")
        sp = (Tw.max() - Tw.min()) * 1e3
        ax.set_title(f"{LBL[k]}  spread {sp:.0f} mK", fontsize=9, loc="left")
        ax.set_xticks([0, 90, 180, 270, 360]); ax.tick_params(labelsize=7)
        ax.axhline(0, color="k", lw=0.5, ls="--"); ax.axhline(96, color="k", lw=0.5, ls="--")
    fig.colorbar(im, ax=axes, shrink=0.6, label="inner wall T − T_set, mK (band ±150)")
    fig.supxlabel("angle round the zone θ, deg (unrolled)"); fig.supylabel("height z, mm (0 = top of lower plate)")
    fig.savefig(os.path.join(FIG, fname), dpi=150, bbox_inches="tight"); plt.close(fig)


def profiles(res, flow, fname):
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    cmap = plt.get_cmap("tab20")
    for i, k in enumerate(ORDER):
        x = res.get((k, flow))
        if not x: continue
        ax.plot((np.array(x["wall_avg"]) + 30) * 1e3, x["wall_profile_z"], color=cmap(i), lw=1.6, label=LBL[k])
    ax.axvspan(-150, 150, color="#f3f4f6", zorder=0)
    ax.axhline(0, color="k", lw=0.5, ls="--"); ax.axhline(96, color="k", lw=0.5, ls="--")
    ax.set_xlim(-80, 80); ax.set_xlabel("inner wall T − T_set (average round the zone), mK"); ax.set_ylabel("height z, mm")
    ax.legend(fontsize=7, ncol=2, frameon=False, loc="lower left")
    ax.set_title(f"Inner wall along the height, {flow:g} g/s", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=170); plt.close(fig)


def heatload(fname):
    rows = json.load(open(os.path.join(HERE, "results", "heatload_axi.json")))
    base = rows[0]
    labels = ["early design\nassumption", "cold-zone deck\n(conduction)", "room CFD\n(still vapour)", "grand deck\n(+vapour +rad)", "this check\n(conduction)"]
    z1 = [10, 2.58, 2.575, 2.776, base["Q1"]]; z2 = [7.5, 1.9, 1.800, 1.747, base["Q2"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    x = np.arange(len(labels))
    ax.bar(x - 0.18, z1, 0.36, color=BLUE, label="Zone 1 (−30 °C)"); ax.bar(x + 0.18, z2, 0.36, color=ORANGE, label="Zone 2 (−15 °C)")
    for xi, a, b in zip(x, z1, z2):
        ax.text(xi - 0.18, a + 0.15, f"{a:.3g}", ha="center", fontsize=8); ax.text(xi + 0.18, b + 0.15, f"{b:.3g}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8); ax.set_ylabel("heat gain, W"); ax.legend(frameon=False)
    ax.set_yscale("log"); ax.set_ylim(0.8, 15)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=170); plt.close(fig)


def chamber_field(fname):
    import heatload_axi
    r = heatload_axi.solve()
    T, rc, zc, mat = r["T"], r["rc"] * 1e3, r["zc"] * 1e3, r["mat"]
    fig, ax = plt.subplots(figsize=(4.4, 7.4))
    Tm = np.where(mat == 2, np.nan, T)
    im = ax.pcolormesh(rc, zc, Tm.T, cmap="coolwarm", shading="auto", vmin=-30, vmax=35)
    cu = np.ma.masked_where(mat != 2, np.ones_like(T))
    ax.pcolormesh(rc, zc, cu.T, cmap=matplotlib.colors.ListedColormap(["#b87333"]), shading="auto")
    ax.contour(rc, zc, T.T, levels=np.arange(-30, 36, 5), colors="k", linewidths=0.4)
    ax.set_xlabel("r, mm"); ax.set_ylabel("z, mm (0 = ice tray)"); ax.set_aspect("equal")
    fig.colorbar(im, ax=ax, label="T, °C", shrink=0.7)
    ax.set_title("Axisymmetric chamber conduction\n(copper = brown, held at set point)", fontsize=9, loc="left")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=170); plt.close(fig)


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "base"
    res = load(tag)
    compare_bars(res, 0, "spread_mK", "cmp_spread.png", "inner-wall spread, mK  (sheet / mine)")
    compare_bars(res, 2, "dp_kPa", "cmp_dp.png", "pressure drop, kPa  (sheet / mine, log)", log=True)
    parity(res, "parity.png")
    for fl in (17.5, 5.0):
        wall_maps(tag, fl, f"wallmaps_{fl:g}.png"); profiles(res, fl, f"profiles_{fl:g}.png")
    heatload("heatload.png")
    chamber_field("chamber_field.png")
    print("figures written")
