#!/usr/bin/env python3
"""Horizontal cross-sections of the vapour column at five heights: one instant (t = 120 s) and the time mean (85-120 s).
Row 1: T about the section mean + in-plane velocity arrows (instant); row 2: vertical velocity (instant);
row 3: vertical velocity (time mean).      python sections.py <run dir> <out png>"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

run, out = sys.argv[1], sys.argv[2]
c = np.load(os.path.join(run, "checkpoint.npz"))
m = np.load(os.path.join(run, "mean_2.npz"))
xc, zc, sec = m["xc"] * 1e3, m["zc"] * 1e3, m["sec"]
uc = 0.5 * (c["u"][1:] + c["u"][:-1]); vc = 0.5 * (c["v"][:, 1:] + c["v"][:, :-1]); wc = 0.5 * (c["w"][:, :, 1:] + c["w"][:, :, :-1])
Z = [(29, "lower connector", "#7FA6CC"), (119, "Zone 2", "#B87333"), (217, "middle connector", "#7FA6CC"), (300, "Zone 1", "#B87333"), (396, "top", "#7FA6CC")]
fig, ax = plt.subplots(3, 5, figsize=(15, 9.2))
X, Y = np.meshgrid(xc, xc, indexing="ij")
for j, (z, nm, col) in enumerate(Z):
    k = int(np.argmin(abs(zc - z)))
    T = np.where(sec, c["T"][:, :, k], np.nan); Tm = np.nanmean(T)
    a = ax[0, j]
    im0 = a.pcolormesh(xc, xc, (T - Tm).T, cmap="coolwarm", vmin=-4, vmax=4, shading="nearest")
    s = 2
    U = np.where(sec, uc[:, :, k], np.nan); V = np.where(sec, vc[:, :, k], np.nan)
    a.quiver(X[::s, ::s], Y[::s, ::s], U[::s, ::s], V[::s, ::s], scale=0.6, width=0.006, color="k")
    a.set_title(f"z = {z} mm · {nm}\nmean {Tm:.1f} °C", fontsize=10)
    W = np.where(sec, wc[:, :, k], np.nan)
    im1 = ax[1, j].pcolormesh(xc, xc, W.T, cmap="RdBu_r", vmin=-0.1, vmax=0.1, shading="nearest")
    Wm = np.where(sec, m["w"][:, :, k], np.nan)
    im2 = ax[2, j].pcolormesh(xc, xc, Wm.T, cmap="RdBu_r", vmin=-0.05, vmax=0.05, shading="nearest")
    for i in range(3):
        b = ax[i, j]
        b.add_patch(Circle((0, 0), 13.5, fill=False, ec=col, lw=2.5))
        b.set_aspect("equal"); b.set_xlim(-14.5, 14.5); b.set_ylim(-14.5, 14.5); b.set_xticks([]); b.set_yticks([])
        for sp in b.spines.values(): sp.set_visible(False)
for i, (im, lab) in enumerate(((im0, "T − section mean (K)"), (im1, "w (m/s), up +"), (im2, "w (m/s), up +"))):
    fig.colorbar(im, ax=ax[i, :].tolist(), fraction=0.015, pad=0.01, label=lab)
fig.text(0.01, 0.84, f"t = {float(c['t']):.0f} s\ntemperature\n+ in-plane\nvelocity", fontsize=11, weight="bold", color="#13294B", va="center")
fig.text(0.01, 0.53, f"t = {float(c['t']):.0f} s\nvertical\nvelocity", fontsize=11, weight="bold", color="#13294B", va="center")
fig.text(0.01, 0.21, "time mean\n" + os.environ.get("MEAN_LABEL", "85–120 s") + "\nvertical\nvelocity", fontsize=11, weight="bold", color="#13294B", va="center")
fig.subplots_adjust(left=0.09, right=0.9, top=0.93, bottom=0.03, wspace=0.08, hspace=0.18)
fig.savefig(out, dpi=150)
print(out)
