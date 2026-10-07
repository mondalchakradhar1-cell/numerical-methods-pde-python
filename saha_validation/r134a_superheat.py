#!/usr/bin/env python3
"""R134a liquid between 25 and 35 C: saturation (vapour) pressure and degree of superheat at several system pressures.
Properties: CoolProp (reference equation of state).   -> figs/r134a_superheat_25_35.png, results/r134a_superheat_25_35.json"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI

F = "R134a"
T = np.linspace(25, 35, 101)
Psat = np.array([PropsSI("P", "T", t + 273.15, "Q", 0, F) for t in T]) / 1e3            # kPa
rhoL = np.array([PropsSI("D", "T", t + 273.15, "Q", 0, F) for t in T])
P_SYS = [(84.4, "84.4 kPa (set by Zone 1)"), (101.325, "1 atm"), (200, "200 kPa"), (400, "400 kPa"), (600, "600 kPa")]
Tsat = {p: PropsSI("T", "P", p * 1e3, "Q", 0, F) - 273.15 for p, _ in P_SYS}
NAVY, CU = "#13294B", "#B87333"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left"})
fig, ax = plt.subplots(1, 2, figsize=(13.5, 5.2))
a = ax[0]
a.plot(T, Psat, color=CU, lw=2.5)
for t in (25, 30, 35):
    p = PropsSI("P", "T", t + 273.15, "Q", 0, F) / 1e3
    a.plot(t, p, "o", color=NAVY); a.annotate(f"{p:.0f} kPa", (t, p), (6, -14), textcoords="offset points", fontsize=10, color=NAVY)
a.set_title("R134a saturation (vapour) pressure, 25–35 °C"); a.set_xlabel("liquid temperature, °C"); a.set_ylabel("saturation pressure, kPa (abs)")
a.text(0.03, 0.95, "Liquid below this pressure is superheated\n(metastable); above it, subcooled.", transform=a.transAxes, va="top", fontsize=10, color="0.35")
a.grid(color="#e5e9ef")
a = ax[1]
cols = ["#C0392B", "#E08A2E", "#1B9E8A", "#2A78D6", "#7E57C2"]
for (p, lab), c in zip(P_SYS, cols):
    a.plot(T, T - Tsat[p], color=c, lw=2.2, label=f"{lab}: T_sat {Tsat[p]:.1f} °C")
a.set_title("Degree of superheat of the liquid: ΔT = T − T_sat(p)"); a.set_xlabel("liquid temperature, °C"); a.set_ylabel("superheat, K")
a.legend(frameon=False, fontsize=9.2, loc="upper left", bbox_to_anchor=(0, 1.0)); a.grid(color="#e5e9ef")
a.set_ylim(-0, 70)
fig.tight_layout(); fig.savefig("figs/r134a_superheat_25_35.png", dpi=170)
rows = []
for t in (25, 27.5, 30, 32.5, 35):
    ps = PropsSI("P", "T", t + 273.15, "Q", 0, F) / 1e3
    rows.append(dict(T_C=t, Psat_kPa=ps, rho_liq=PropsSI("D", "T", t + 273.15, "Q", 0, F), h_fg_kJkg=(PropsSI("H", "T", t + 273.15, "Q", 1, F) - PropsSI("H", "T", t + 273.15, "Q", 0, F)) / 1e3,
                     superheat_K={f"{p:g}": t - Tsat[p] for p, _ in P_SYS}))
    print(f"T {t:5.1f} C  Psat {ps:7.1f} kPa  rho_L {rows[-1]['rho_liq']:.0f}  h_fg {rows[-1]['h_fg_kJkg']:.1f} kJ/kg  superheat: " + ", ".join(f"{p:g} kPa {t - Tsat[p]:.1f} K" for p, _ in P_SYS))
json.dump(dict(fluid=F, source="CoolProp (reference EOS)", Tsat_C={f"{p:g}": Tsat[p] for p, _ in P_SYS}, rows=rows), open("results/r134a_superheat_25_35.json", "w"), indent=1)
