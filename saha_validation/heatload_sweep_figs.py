#!/usr/bin/env python3
"""Figures of the heat-load sweeps -> figs/hl_thickness.png, hl_kfoam.png, hl_height.png, hl_lab.png"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

S = json.load(open("results/heatload_sweeps.json"))
B1, B2 = "#2A78D6", "#EB6834"
NAVY = "#13294B"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left"})
lab = {0.035: "k 0.035 (EPS / PS foam)", 0.025: "k 0.025 (PU foam)", 0.015: "k 0.015 (aerogel)"}
ls = {0.035: "-", 0.025: "--", 0.015: ":"}

# 1 thickness
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), sharey=False)
for k in (0.035, 0.025, 0.015):
    r = [x for x in S["thickness"] if x["k"] == k]
    t = [x["t"] for x in r]
    ax[0].plot(t, [x["Q1"] for x in r], ls[k], color=B1, lw=2, marker="o", ms=4, label=lab[k])
    ax[1].plot(t, [x["Q2"] for x in r], ls[k], color=B2, lw=2, marker="o", ms=4, label=lab[k])
for a, z, q in ((ax[0], "Zone 1 (−30 °C)", S["base"]["Q1"]), (ax[1], "Zone 2 (−15 °C)", S["base"]["Q2"])):
    a.plot([50], [q], "o", ms=11, mfc="none", mec="k", mew=1.5)
    a.annotate(f"design: 50 mm,\nk 0.035 → {q:.2f} W", (50, q), (58, q + 0.7), fontsize=10, arrowprops=dict(arrowstyle="-", color="0.4"))
    a.set_title(f"{z}: heat vs insulation thickness"); a.set_xlabel("foam thickness beyond the plates and cap, mm"); a.set_ylabel("heat reaching the copper, W")
    a.grid(color="#e5e9ef"); a.legend(frameon=False, fontsize=9.5); a.set_xlim(0, 105); a.set_ylim(0, None)
fig.tight_layout(); fig.savefig("figs/hl_thickness.png", dpi=160); plt.close(fig)

# 2 conductivity
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
lst = {25: ":", 50: "-", 75: "--"}
for t in (25, 50, 75):
    r = [x for x in S["k_foam"] if x["t"] == t]
    kk = [x["k"] * 1e3 for x in r]
    ax[0].plot(kk, [x["Q1"] for x in r], lst[t], color=B1, lw=2, marker="o", ms=4, label=f"{t} mm foam")
    ax[1].plot(kk, [x["Q2"] for x in r], lst[t], color=B2, lw=2, marker="o", ms=4, label=f"{t} mm foam")
for a, z, q in ((ax[0], "Zone 1 (−30 °C)", S["base"]["Q1"]), (ax[1], "Zone 2 (−15 °C)", S["base"]["Q2"])):
    a.plot([35], [q], "o", ms=11, mfc="none", mec="k", mew=1.5)
    for kx, nm in ((15, "aerogel"), (25, "PU"), (35, "EPS")):
        a.axvline(kx, color="0.85", lw=1, zorder=0); a.text(kx, a.get_ylim()[1] if False else 0.05, nm, rotation=90, va="bottom", ha="right", fontsize=9, color="0.45")
    a.set_title(f"{z}: heat vs foam conductivity"); a.set_xlabel("foam thermal conductivity, mW/m·K"); a.set_ylabel("heat reaching the copper, W")
    a.grid(color="#e5e9ef"); a.legend(frameon=False, fontsize=9.5); a.set_ylim(0, None)
fig.tight_layout(); fig.savefig("figs/hl_kfoam.png", dpi=160); plt.close(fig)

# 3 along the height
fig, ax = plt.subplots(1, 2, figsize=(12, 5.0))
for a, zn, (z0, z1), col in ((ax[0], "Z1", (247, 365), B1), (ax[1], "Z2", (60, 187), B2)):
    P = S["profile"][zn]
    tot = 0
    for part, c2, lw in (("bore (inner wall)", col, 2.2), ("band outer", "0.35", 1.6)):
        if part not in P:
            continue
        z = np.array([p[0] for p in P[part]]); q = np.array([p[1] for p in P[part]])
        zb = np.arange(z0, z1 + 1, 1.0)
        qb = np.array([q[(z >= zb[i]) & (z < zb[i + 1])].sum() for i in range(len(zb) - 1)])        # W per mm
        a.plot(qb * 1e3, 0.5 * (zb[1:] + zb[:-1]), color=c2, lw=lw, label=f"{part}: {q.sum():.2f} W")
        tot += q.sum()
    pl = P.get("plates", [])
    zp = np.array([p[0] for p in pl]); qp = np.array([p[1] for p in pl])
    mid = 0.5 * (z0 + z1)
    lo, hi = qp[zp < mid].sum(), qp[zp >= mid].sum()
    tot += lo + hi
    for zz, qq, nm in ((z0 + 5.5, lo, "lower plate"), (z1 - 5.5, hi, "upper plate")):
        a.barh(zz, qq * 1e3 / 11, height=11, color=col, alpha=0.25, edgecolor=col)
        a.text(qq * 1e3 / 11 * 0.02 + 0.5, zz, f"{nm} (11 mm thick): {qq:.2f} W", va="center", fontsize=9.5)
    a.set_title(f"{'Zone 1 (−30 °C)' if zn == 'Z1' else 'Zone 2 (−15 °C)'}: where the heat enters, total {tot:.2f} W")
    a.set_xlabel("heat into the copper per mm of height, mW/mm"); a.set_ylabel("height z above the ice tray, mm")
    a.grid(color="#e5e9ef"); a.legend(frameon=False, fontsize=9.5, loc="center right"); a.set_xlim(0, None)
fig.tight_layout(); fig.savefig("figs/hl_height.png", dpi=160); plt.close(fig)

# 4 lab temperature and outer film coefficient
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
r = S["T_lab"]
ax[0].plot([x["T_lab"] for x in r], [x["Q1"] for x in r], "-o", color=B1, lw=2, label="Zone 1")
ax[0].plot([x["T_lab"] for x in r], [x["Q2"] for x in r], "-o", color=B2, lw=2, label="Zone 2")
ax[0].set_title("Heat vs lab temperature (50 mm, k 0.035)"); ax[0].set_xlabel("lab air temperature, °C"); ax[0].set_ylabel("heat, W")
r = S["h"]
ax[1].plot([x["h"] for x in r], [x["Q1"] for x in r], "-o", color=B1, lw=2, label="Zone 1")
ax[1].plot([x["h"] for x in r], [x["Q2"] for x in r], "-o", color=B2, lw=2, label="Zone 2")
ax[1].set_title("Heat vs outer-surface film coefficient"); ax[1].set_xlabel("h on the foam outside, W/m²K"); ax[1].set_ylabel("heat, W")
for a in ax:
    a.grid(color="#e5e9ef"); a.legend(frameon=False); a.set_ylim(0, None)
fig.tight_layout(); fig.savefig("figs/hl_lab.png", dpi=160); plt.close(fig)
print("ok")

# 5 proportionality checks
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
r = S["T_lab"]
dT = np.array([x["T_lab"] for x in r]) + 30.0
for key, col, nm in (("Q1", B1, "Zone 1"), ("Q2", B2, "Zone 2")):
    q = np.array([x[key] for x in r]); p = np.polyfit(dT, q, 1)
    ax[0].plot(dT, q, "o", color=col); ax[0].plot(dT, np.polyval(p, dT), "-", color=col, lw=1.5, label=f"{nm}: {p[0] * 1e3:.1f} mW per K (exactly linear)")
ax[0].set_title("Q ∝ ΔT"); ax[0].set_xlabel("ΔT = T_lab − T_Zone1, K"); ax[0].set_ylabel("heat, W")
r = [x for x in S["k_foam"] if x["t"] == 50]
k = np.array([x["k"] for x in r])
for key, col, nm in (("Q1", B1, "Zone 1"), ("Q2", B2, "Zone 2")):
    q = np.array([x[key] for x in r])
    ax[1].plot(k * 1e3, q, "o-", color=col, lw=1.5, label=nm)
    ax[1].plot([0, 50], [0, q[k == 0.035][0] / 0.035 * 0.05], ":", color=col, lw=1)
ax[1].set_title("Q ≈ ∝ k  (dotted: exact proportionality)"); ax[1].set_xlabel("foam k, mW/m·K"); ax[1].set_ylabel("heat, W"); ax[1].set_xlim(0, 52)
r = [x for x in S["thickness"] if x["k"] == 0.035]
t = np.array([x["t"] for x in r]); q = np.array([x["Q1"] for x in r])
tt = np.linspace(8, 100, 100)
def ana(t, k=0.035, L=0.118, h=8, dT=65):
    ri = 0.043; ro = ri + t / 1000
    return dT / (np.log(ro / ri) / (2 * np.pi * k * L) + 1 / (h * 2 * np.pi * ro * L))
ax[2].plot(t, q, "o-", color=B1, lw=2, label="Zone 1, full chamber model")
ax[2].plot(tt, ana(tt), "--", color="0.3", lw=1.5, label="side wall only, Q = ΔT / (R_foam + R_film)")
ax[2].plot(tt, q[t == 50][0] * 50 / tt, ":", color="0.6", lw=1.5, label="if Q were ∝ 1/t")
ax[2].set_title("Q falls with thickness, but slower than 1/t"); ax[2].set_xlabel("foam thickness t, mm"); ax[2].set_ylabel("heat, W"); ax[2].set_ylim(0, 7)
for a in ax:
    a.grid(color="#e5e9ef"); a.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig("figs/hl_proportional.png", dpi=160); plt.close(fig)
print("ok5")
