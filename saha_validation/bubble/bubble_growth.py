#!/usr/bin/env python3
"""Growth and rise of a vapour bubble in superheated liquid R134a after nucleation.

Growth: Mikic-Rohsenow-Griffith (1970) solution, valid from inertia-controlled (R = A t) to
heat-diffusion-controlled growth (R = B sqrt(t)):
    A = sqrt(2/3 * h_fg rho_v dT / (rho_l T_sat)),   B = sqrt(12/pi) Ja sqrt(alpha_l),   Ja = rho_l c_l dT / (rho_v h_fg)
    t+ = t A^2/B^2,  R+ = R A/B^2,  R+ = 2/3 [ (t+ + 1)^1.5 - t+^1.5 - 1 ]
Rise: quasi-steady terminal velocity of the current bubble (Mendelson): U = sqrt(2.14 sigma/(rho_l d) + 0.505 g d).
Properties: CoolProp.   -> figs/bubble_growth.png, results/bubble_growth.json, figs/bubble_rise.gif
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

F = "R134a"
NAVY, CU = "#13294B", "#B87333"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left"})


def case(T_liq, p):
    Ts = PropsSI("T", "P", p, "Q", 0, F)
    TL = T_liq + 273.15
    rl = PropsSI("D", "T", TL, "Q", 0, F); cl = PropsSI("C", "T", TL, "Q", 0, F); kl = PropsSI("L", "T", TL, "Q", 0, F)
    sig = PropsSI("I", "T", TL, "Q", 0, F)
    rv = PropsSI("D", "P", p, "Q", 1, F)
    hfg = PropsSI("H", "P", p, "Q", 1, F) - PropsSI("H", "P", p, "Q", 0, F)
    dT = TL - Ts
    A = np.sqrt(2 / 3 * hfg * rv * dT / (rl * Ts))
    Ja = rl * cl * dT / (rv * hfg)
    B = np.sqrt(12 / np.pi) * Ja * np.sqrt(kl / (rl * cl))
    return dict(T_liq=T_liq, p=p, Tsat=Ts - 273.15, dT=dT, rho_l=rl, rho_v=rv, h_fg=hfg, sigma=sig, A=A, B=B, Ja=Ja)


def radius(c, t):
    tp = t * c["A"] ** 2 / c["B"] ** 2
    Rp = 2 / 3 * ((tp + 1) ** 1.5 - tp ** 1.5 - 1)
    return Rp * c["B"] ** 2 / c["A"]


def rise(c, depth, dt=1e-5, tmax=5.0):
    t, z, out = 0.0, 0.0, []
    while z < depth and t < tmax:
        R = radius(c, t)
        d = 2 * R
        U = np.sqrt(2.14 * c["sigma"] / (c["rho_l"] * max(d, 1e-6)) + 0.505 * 9.81 * d) if d > 1e-4 else 0.0
        out.append((t, z, R, U))
        z += U * dt; t += dt
        dt = min(dt * 1.002, 2e-4)
    return np.array(out)


P84 = PropsSI("P", "T", 243.15, "Q", 0, F)
CASES = [(0, P84, "A: liquid 0 °C, 84.4 kPa (30 K superheat)", "#2A78D6"), (20, P84, "A: liquid 20 °C, 84.4 kPa (50 K)", "#E08A2E"),
         (30, P84, "A: liquid 30 °C, 84.4 kPa (60 K)", "#C0392B"), (30, 400e3, "C: liquid 30 °C, 400 kPa (21 K)", "#7E57C2")]
t = np.logspace(-8, 0, 400)
fig, ax = plt.subplots(1, 3, figsize=(17, 5.2))
res = []
for Tl, p, lab, col in CASES:
    c = case(Tl, p)
    R = radius(c, t)
    ax[0].loglog(t * 1e3, R * 1e3, color=col, lw=2.2, label=lab)
    rr = {}
    for depth in (0.03, 0.06, 0.10):
        tr = rise(c, depth)
        if depth == 0.06:
            ax[1].plot(tr[:, 0] * 1e3, tr[:, 1] * 1e3, color=col, lw=2.2, label=lab)
        Rs = tr[-1, 2]
        V = 4 / 3 * np.pi * Rs ** 3
        rr[f"{depth * 1e3:.0f}mm"] = dict(t_ms=tr[-1, 0] * 1e3, R_mm=Rs * 1e3, V_ml=V * 1e6, energy_J=V * c["rho_v"] * c["h_fg"], U_ms=tr[-1, 3])
    res.append(dict(label=lab, **{k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in c.items()}, R_1ms_mm=float(radius(c, 1e-3) * 1e3),
                    R_10ms_mm=float(radius(c, 1e-2) * 1e3), at_surface=rr))
    ax[2].bar([f"{d}" for d in ("30", "60", "100")], [rr[k]["energy_J"] for k in rr], alpha=0.0)
ax[0].set_title("Bubble radius after nucleation"); ax[0].set_xlabel("time after nucleation, ms"); ax[0].set_ylabel("bubble radius, mm")
ax[0].set_xlim(1e-5, 1e3); ax[0].set_ylim(1e-4, 200); ax[0].grid(color="#e5e9ef", which="both"); ax[0].legend(frameon=False, fontsize=9)
ax[0].text(2e-5, 3e-4, "inertia-limited: R ∝ t", fontsize=9, color="0.4"); ax[0].text(3, 0.3, "heat-limited: R ∝ √t", fontsize=9, color="0.4")
ax[1].set_title("Bubble rising through 60 mm of liquid"); ax[1].set_xlabel("time, ms"); ax[1].set_ylabel("height risen, mm"); ax[1].grid(color="#e5e9ef"); ax[1].legend(frameon=False, fontsize=9)
# bar chart of radius and energy at the surface
ax[2].cla()
x = np.arange(3); wbar = 0.2
for i, (r, col) in enumerate(zip(res, [c[3] for c in CASES])):
    ax[2].bar(x + (i - 1.5) * wbar, [r["at_surface"][k]["R_mm"] for k in ("30mm", "60mm", "100mm")], wbar, color=col, label=r["label"])
ax[2].set_xticks(x); ax[2].set_xticklabels(["30 mm", "60 mm", "100 mm"]); ax[2].set_xlabel("liquid depth above the nucleation point"); ax[2].set_yscale("log")
ax[2].set_ylabel("bubble radius on reaching the surface, mm"); ax[2].set_title("Size when the bubble reaches the liquid surface"); ax[2].grid(color="#e5e9ef", axis="y", which="both")
ax[2].legend(frameon=False, fontsize=8.5)
fig.tight_layout(); fig.savefig("figs/bubble_growth.png", dpi=160); plt.close(fig)
for r in res:
    print(r["label"], f"Ja {r['Ja']:.0f}  A {r['A']:.2f} m/s  B {r['B'] * 1e3:.2f} mm/sqrt(s)  R(1 ms) {r['R_1ms_mm']:.2f} mm  R(10 ms) {r['R_10ms_mm']:.2f} mm")
    for k, v in r["at_surface"].items():
        print(f"   depth {k}: t {v['t_ms']:.0f} ms  R {v['R_mm']:.1f} mm  V {v['V_ml']:.2f} ml  energy {v['energy_J']:.3f} J  U {v['U_ms']:.2f} m/s")
json.dump(res, open("results/bubble_growth.json", "w"), indent=1)
