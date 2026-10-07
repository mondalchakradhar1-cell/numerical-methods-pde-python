#!/usr/bin/env python3
"""Heat into the vapour (sources) and from the vapour into the copper, 0-120 s, smoothed over 1 s;
time means over 85-120 s drawn as bars.     python heatflow_fig.py <history.json> <out png>"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

H = json.load(open(sys.argv[1]))["hist"]
t = np.array([h["t"] for h in H])
g = lambda k: np.array([h[k] for h in H], float)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": "#13294B", "axes.titlelocation": "left"})


def smooth(y, w=1.0):
    out = np.empty_like(y)
    for i, ti in enumerate(t):
        m = (t > ti - w / 2) & (t <= ti + w / 2)
        out[i] = np.nanmean(y[m])
    return out


w0, w1 = float(os.environ.get("W0", 85.0)), float(os.environ.get("W1", 120.5))
win = (t >= w0) & (t <= w1)
fig, ax = plt.subplots(1, 2, figsize=(14, 5.4))
labs = {0: [], 1: []}
src = [("ice", "ice tray (bottom)", "#8C6D1F"), ("conn_lo", "lower connector wall", "#C0392B"), ("conn_mid", "middle connector wall", "#E08A2E"), (None, "top wall + cap", "#7B4F9E")]
for k, lab, col in src:
    y = g("top_wall") + g("cap") if k is None else g(k)
    ys = smooth(y)
    ax[0].plot(t, ys, color=col, lw=0.9, label=lab)
    mv = y[win].mean()
    ax[0].plot([w0, w1], [mv, mv], color=col, lw=3); labs[0].append((mv, col))
snk = [("z1", "Zone 1 inner wall", "#2A78D6", -1), ("z2", "Zone 2 inner wall", "#1B9E8A", -1)]
for k, lab, col, sgn in snk:
    y = sgn * g(k); ys = smooth(y)
    ax[1].plot(t, ys, color=col, lw=0.9, label=lab)
    mv = y[win].mean()
    ax[1].plot([w0, w1], [mv, mv], color=col, lw=3); labs[1].append((mv, col))
for i, a in enumerate(ax):
    ys_ = []
    for mv, col in sorted(labs[i]):
        y = mv if not ys_ or mv - ys_[-1] > 5 else ys_[-1] + 5
        ys_.append(y); a.text(w1 + 1, y, f"{mv:.0f}", color=col, va="center", fontsize=10, weight="bold")
for a, ttl in zip(ax, (f"Heat INTO the {os.environ.get('FLUID_LABEL', 'vapour')} (sources), mW", f"Heat from the {os.environ.get('FLUID_LABEL', 'vapour')} INTO the copper, mW")):
    a.axvspan(w0, w1, color="#f0f0f0", zorder=0); a.axvline(60, color="0.5", ls="--", lw=0.8)
    a.text(59, a.get_ylim()[0] + 0.1 * (a.get_ylim()[1] - a.get_ylim()[0]), "walls coupled\nto the room →", fontsize=8.5, color="0.4", ha="right")
    a.text((w0 + w1) / 2, a.get_ylim()[0] + 0.03 * (a.get_ylim()[1] - a.get_ylim()[0]), "time-mean window", fontsize=8.5, color="0.4", ha="center")
    a.axhline(0, color="0.6", lw=0.6); a.set_xlim(0, w1 * 1.05); a.set_xlabel("time (s)"); a.set_title(ttl); a.legend(frameon=False, fontsize=9.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    a.grid(color="#eceff3")
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=150)
print({k: round(float(g(k)[win].mean()), 1) for k in ("ice", "conn_lo", "conn_mid", "z1", "z2")})
