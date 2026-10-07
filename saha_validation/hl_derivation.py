#!/usr/bin/env python3
"""Typeset derivation of the heat-loss equation -> figs/hl_derivation.png (matplotlib mathtext)."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NAVY, CU, GREY = "#13294B", "#B87333", "#4B5563"
nb = json.load(open("results/heatload_noinsulation.json"))
k, L, h, ri, ro, dT = 0.035, 0.118, 8.0, 0.043, 0.093, 65.0
Rf = np.log(ro / ri) / (2 * np.pi * k * L); Rh = 1 / (h * 2 * np.pi * ro * L); Q = dT / (Rf + Rh)
plt.rcParams.update({"mathtext.fontset": "dejavuserif", "font.family": "DejaVu Sans"})
steps = [
    ("1  Flat layer (Fourier's law)", r"$Q = \dfrac{k\,A\,\Delta T}{t}\quad\Rightarrow\quad R = \dfrac{t}{k\,A}$"),
    ("2  Cylindrical layer (side wall)", r"$Q = \dfrac{2\pi k L\,\Delta T}{\ln(r_o/r_i)}\quad\Rightarrow\quad R_{foam} = \dfrac{\ln(r_o/r_i)}{2\pi k L}$"),
    ("3  Outer surface film (convection + radiation)", r"$Q = h\,A_o\,\Delta T\quad\Rightarrow\quad R_{film} = \dfrac{1}{h\,2\pi r_o L}$"),
    ("4  Layers in series, paths in parallel", r"$R_{total} = R_{foam} + R_{film},\qquad \dfrac{1}{R_{chamber}} = \sum_i \dfrac{1}{R_i},\qquad Q = \dfrac{\Delta T}{R_{total}}$"),
    ("5  Zone 1 side wall, 50 mm foam", r"$Q = \dfrac{\Delta T}{\dfrac{\ln(r_o/r_i)}{2\pi k L} + \dfrac{1}{2\pi r_o L h}} = \dfrac{65\ \mathrm{K}}{%.1f + %.2f\ \mathrm{K/W}} = %.2f\ \mathrm{W}$" % (Rf, Rh, Q)),
    ("6  No insulation at all (bare copper in 35 °C air)", r"$Q = h\,A_{Cu}\,\Delta T = 8 \times %.4f\ \mathrm{m^2} \times 65\ \mathrm{K} \approx %.0f\ \mathrm{W}$" % (nb["bare"]["A1"], nb["bare"]["Q1"])),
]
fig = plt.figure(figsize=(7.4, 8.4))
y = 0.975
for i, (t, eq) in enumerate(steps):
    fig.text(0.02, y, t, fontsize=12, weight="bold", color=NAVY, va="top")
    fig.text(0.05, y - 0.045, eq, fontsize=15 if i < 4 else 14, color=CU if i in (4, 5) else "#1A1F2B", va="top")
    y -= 0.143 if i != 4 else 0.175
fig.text(0.02, 0.015, r"$\Delta T = T_{lab} - T_{copper}$;  $r_i$ = 43 mm (plate rim), $r_o = r_i + t$, $L$ = 118 mm, $k$ = 0.035 W/m·K, $h$ = 8 W/m²K." "\n"
         "Full chamber model (side + plates + ends + Perspex/vapour paths): 2.58 W.", fontsize=9.5, color=GREY, va="bottom")
fig.savefig("figs/hl_derivation.png", dpi=200)
print(Rf, Rh, Q)
