#!/usr/bin/env python3
"""Bubble nucleation energy in superheated liquid R134a (Seitz hot-spike threshold) and the energy to grow a bubble
to a given size.  Properties: CoolProp.   -> figs/r134a_bubble_energy.png, results/r134a_bubble_energy.json

Critical radius   r_c = 2 sigma / (p_v - p_l)                         (p_v ~ p_sat(T) inside the critical bubble)
Threshold energy  E_c = 4 pi r_c^2 (sigma - T dsigma/dT) + 4/3 pi r_c^3 rho_v h_fg - 4/3 pi r_c^3 (p_v - p_l)
Grown bubble      E(r) = 4/3 pi r^3 rho_v(p_l) h_fg + 4 pi r^2 (sigma - T dsigma/dT)      (vapour at the chamber pressure)
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

F = "R134a"
KEV = 1.602176634e-16


def props(Tc):
    T = Tc + 273.15
    s = PropsSI("I", "T", T, "Q", 0, F)
    ds = (PropsSI("I", "T", T + 0.05, "Q", 0, F) - PropsSI("I", "T", T - 0.05, "Q", 0, F)) / 0.1
    pv = PropsSI("P", "T", T, "Q", 0, F)
    rv = PropsSI("D", "T", T, "Q", 1, F)
    hfg = PropsSI("H", "T", T, "Q", 1, F) - PropsSI("H", "T", T, "Q", 0, F)
    return T, s, ds, pv, rv, hfg


def threshold(Tc, pl):
    T, s, ds, pv, rv, hfg = props(Tc)
    dp = pv - pl
    if dp <= 0:
        return np.nan, np.nan
    rc = 2 * s / dp
    E = 4 * np.pi * rc ** 2 * (s - T * ds) + 4 / 3 * np.pi * rc ** 3 * rv * hfg - 4 / 3 * np.pi * rc ** 3 * dp
    return rc, E


Ts = np.linspace(25, 35, 41)
PL = [200, 300, 400, 500, 600]                       # kPa
res = {}
for p in PL:
    rr, EE = zip(*[threshold(t, p * 1e3) for t in Ts])
    res[p] = (np.array(rr), np.array(EE))
NAVY = "#13294B"
cols = ["#C0392B", "#E08A2E", "#1B9E8A", "#2A78D6", "#7E57C2"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left"})
fig, ax = plt.subplots(1, 3, figsize=(17, 5.2))
for (p, c) in zip(PL, cols):
    rc, E = res[p]
    ax[0].semilogy(Ts, E / KEV, color=c, lw=2.2, label=f"{p} kPa")
    ax[1].semilogy(Ts, rc * 1e9, color=c, lw=2.2, label=f"{p} kPa")
ax[0].set_title("Energy to nucleate a bubble (threshold)"); ax[0].set_ylabel("threshold energy E_c, keV"); ax[0].set_xlabel("liquid temperature, °C")
ax[1].set_title("Size of the critical bubble"); ax[1].set_ylabel("critical radius r_c, nm"); ax[1].set_xlabel("liquid temperature, °C")
for a in ax[:2]:
    a.grid(color="#e5e9ef", which="both"); a.legend(frameon=False, title="chamber pressure", fontsize=9.5)
# energy vs size for a grown bubble at 30 C, chamber 400 kPa, starting from the critical bubble
Tc, p = 30.0, 400e3
T, s, ds, pv, rv, hfg = props(Tc)
rv_p = PropsSI("D", "P", p, "T", T, F) if PropsSI("T", "P", p, "Q", 1, F) < T else rv
r = np.logspace(np.log10(threshold(Tc, p)[0]), -2.3, 200)
E_r = 4 / 3 * np.pi * r ** 3 * rv_p * hfg + 4 * np.pi * r ** 2 * (s - T * ds)
a = ax[2]
a.loglog(r * 1e3, E_r, color="#B87333", lw=2.5)
rc0, Ec0 = threshold(Tc, p)
a.plot(rc0 * 1e3, Ec0, "o", color=NAVY); a.annotate(f"critical bubble\nr_c = {rc0 * 1e9:.0f} nm, E_c = {Ec0 / KEV:.1f} keV", (rc0 * 1e3, Ec0), (12, 4), textcoords="offset points", fontsize=9.5)
for rmm in (0.01, 0.1, 1.0):
    e = 4 / 3 * np.pi * (rmm * 1e-3) ** 3 * rv_p * hfg + 4 * np.pi * (rmm * 1e-3) ** 2 * (s - T * ds)
    a.plot(rmm, e, "o", color="#C0392B"); a.annotate(f"r = {rmm:g} mm: {e:.2g} J", (rmm, e), (8, -12), textcoords="offset points", fontsize=9.5)
a.set_title("Energy to grow a bubble to radius r (30 °C, 400 kPa)"); a.set_xlabel("bubble radius r, mm"); a.set_ylabel("energy, J")
a.grid(color="#e5e9ef", which="both")
fig.tight_layout(); fig.savefig("figs/r134a_bubble_energy.png", dpi=160)
out = dict(model="Seitz hot-spike threshold", rows=[])
for t in (25, 30, 35):
    for pk in PL:
        rc, E = threshold(t, pk * 1e3)
        out["rows"].append(dict(T_C=t, p_kPa=pk, r_c_nm=rc * 1e9, E_c_keV=E / KEV, superheat_K=t - (PropsSI("T", "P", pk * 1e3, "Q", 0, F) - 273.15)))
        print(f"T {t} C  p {pk} kPa  superheat {out['rows'][-1]['superheat_K']:5.1f} K  r_c {rc * 1e9:7.1f} nm  E_c {E / KEV:9.2f} keV")
grow = []
for rmm in (0.001, 0.01, 0.1, 0.5, 1.0, 2.0):
    e = 4 / 3 * np.pi * (rmm * 1e-3) ** 3 * rv_p * hfg + 4 * np.pi * (rmm * 1e-3) ** 2 * (s - T * ds)
    grow.append(dict(r_mm=rmm, E_J=e, E_keV=e / KEV)); print(f"grow r {rmm} mm: {e:.3e} J")
out["grow_30C_400kPa"] = grow; out["rho_v_400kPa"] = rv_p; out["h_fg_30C"] = hfg; out["sigma_30C"] = s
json.dump(out, open("results/r134a_bubble_energy.json", "w"), indent=1)
