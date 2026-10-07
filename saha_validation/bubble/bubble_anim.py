#!/usr/bin/env python3
"""Animation of one bubble event (configuration A, liquid 20 C, 84.4 kPa, 60 mm of liquid above the nucleation point):
nucleation, growth while rising, arrival at the surface, vapour rising to Zone 1 and condensing.  -> figs/bubble_event.gif"""
import json
import os
import sys

import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Polygon, Circle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bubble_growth import case, radius, rise, P84

NAVY, CU, CU_D, PMMA, LIQ, VAP = "#13294B", "#C8803F", "#8A5226", "#9EC3E0", "#3E7CC7", "#EAF2FA"
c = case(20.0, P84)
DEPTH = 0.06
tr = rise(c, DEPTH)
t_s = tr[-1, 0]
z_nuc = -100.0                                  # mm (in the reservoir), surface at -40 mm
z_surf = z_nuc + DEPTH * 1e3
W = 27.0                                        # bore half-width drawn x2
frames = []
T_end = t_s + 0.9                               # then vapour rises to Zone 1 (~0.3 m/s mixed) and condenses
times = np.r_[np.linspace(0, 0.004, 8), np.linspace(0.005, t_s, 46), np.linspace(t_s + 0.02, T_end, 26)]
tmp = "/tmp/_bub.png"
E_tot = 4 / 3 * np.pi * tr[-1, 2] ** 3 * c["rho_v"] * c["h_fg"]
for tt in times:
    fig = plt.figure(figsize=(11, 7.2))
    ax = fig.add_axes([0.02, 0.04, 0.42, 0.9]); ax2 = fig.add_axes([0.53, 0.55, 0.43, 0.36]); ax3 = fig.add_axes([0.53, 0.1, 0.43, 0.3])
    # chamber (generic lower part)
    ax.add_patch(Polygon([(-W, 0), (-55, -55), (-55, -120), (55, -120), (55, -55), (W, 0)], closed=True, fc=VAP, ec="none"))
    ax.add_patch(Rectangle((-W, 0), 2 * W, 425, fc=VAP, ec="none"))
    xw = W + (55 - W) * min(1, -z_surf / 55)
    ax.add_patch(Polygon([(-xw, z_surf), (-55, -55), (-55, -120), (55, -120), (55, -55), (xw, z_surf)], closed=True, fc=LIQ, ec="none", alpha=0.85))
    ax.add_patch(Polygon([(-W, 0), (-55, -55), (-55, -120), (55, -120), (55, -55), (W, 0)], closed=True, fc="none", ec=PMMA, lw=3))
    for (z0, z1) in ((60, 187), (247, 365)):
        for s in (-1, 1):
            ax.add_patch(Rectangle((s * W - (8 if s < 0 else 0), z0), 8, z1 - z0, fc=CU, ec=CU_D, lw=0.6))
    for z0, z1 in ((0, 60), (187, 247), (365, 425)):
        for s in (-1, 1):
            ax.add_patch(Rectangle((s * W - (3 if s < 0 else 0), z0), 3, z1 - z0, fc=PMMA, ec="none"))
    ax.text(W + 12, 306, "Zone 1  −30 °C\n(condenser)", fontsize=9, color=CU_D, weight="bold", va="center")
    ax.text(W + 12, 123, "Zone 2  −15 °C", fontsize=9, color=CU_D, weight="bold", va="center")
    ax.text(58, -80, "superheated\nliquid 20 °C\n(50 K)", fontsize=8.5, color="#0B2545")
    if tt <= t_s:
        k = min(np.searchsorted(tr[:, 0], tt), len(tr) - 1)
        R = radius(c, tt) * 1e3; z = z_nuc + tr[k, 1] * 1e3
        ax.add_patch(Circle((0, z), max(R, 0.6), fc="white", ec="#0B2545", lw=1.2, zorder=5))
        if tt < 0.002:
            ax.plot(0, z_nuc, marker="*", ms=14, color="#E0301E", zorder=6)
            ax.text(8, z_nuc - 4, "WIMP / neutron recoil", fontsize=8.5, color="#E0301E")
        phase = "bubble grows while rising"
        film = 0.0
    else:
        f = (tt - t_s) / (T_end - t_s)
        zc = z_surf + f * (306 - z_surf)
        ax.add_patch(Rectangle((-W + 3, max(z_surf, zc - 60)), 2 * W - 6, 60, fc="#F4D35E", alpha=0.55 * (1 - 0.6 * f), ec="none", zorder=4))
        phase = "vapour rises up the bore and condenses on Zone 1"
        film = min(1.0, max(0, (zc - 247) / 120))
        if film > 0:
            for s in (-1, 1):
                ax.add_patch(Rectangle((s * W - (3 if s > 0 else -0), 247 + 5), 3 * s if False else 3, 108 * film, fc="#1F4FBF", ec="none", zorder=6) if s > 0 else
                             Rectangle((-W, 247 + 5), 3, 108 * film, fc="#1F4FBF", ec="none", zorder=6))
    ax.set_xlim(-60, 115); ax.set_ylim(-135, 430); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"t = {tt * 1e3:6.1f} ms", fontsize=13, color=NAVY, loc="left", weight="bold")
    ax.text(-58, -122, phase, fontsize=9.5, color="#B4471A", va="top")
    # radius curve
    tl = np.logspace(-6, np.log10(t_s), 200)
    ax2.loglog(tl * 1e3, radius(c, tl) * 1e3, color=CU, lw=2)
    if 0 < tt <= t_s:
        ax2.plot(tt * 1e3, radius(c, tt) * 1e3, "o", color="#E0301E", ms=8)
    ax2.set_xlabel("time after nucleation, ms"); ax2.set_ylabel("bubble radius, mm"); ax2.set_title("Bubble radius (Mikić–Rohsenow–Griffith)", loc="left", fontsize=11, color=NAVY, weight="bold")
    ax2.grid(color="#e5e9ef", which="both"); ax2.spines[["top", "right"]].set_visible(False)
    # energy delivered
    tt2 = np.linspace(0, T_end, 200)
    Ec = np.where(tt2 < t_s, 4 / 3 * np.pi * radius(c, np.minimum(tt2, t_s)) ** 3 * c["rho_v"] * c["h_fg"], E_tot)
    ax3.plot(tt2 * 1e3, Ec, color=NAVY, lw=2); ax3.axvline(tt * 1e3, color="#E0301E", lw=1)
    ax3.set_xlabel("time, ms"); ax3.set_ylabel("latent heat in the bubble, J"); ax3.grid(color="#e5e9ef"); ax3.spines[["top", "right"]].set_visible(False)
    ax3.set_title(f"Heat carried to Zone 1: {E_tot:.1f} J  (Zone 1 copper +{E_tot / 634 * 1e3:.0f} mK)", loc="left", fontsize=11, color=NAVY, weight="bold")
    fig.text(0.53, 0.955, "One bubble event · configuration A (84.4 kPa, set by Zone 1)\nliquid 20 °C · 60 mm of liquid above the nucleation point", fontsize=9.5, color="0.3", va="bottom")
    fig.savefig(tmp, dpi=100); plt.close(fig)
    frames.append(imageio.imread(tmp))
imageio.mimsave("figs/bubble_event.gif", frames, duration=[0.25] * (len(frames) - 1) + [2.0], loop=0)
print("frames", len(frames), "t_surface ms", t_s * 1e3, "E", E_tot)
