#!/usr/bin/env python3
"""Typeset: how the coolant inlet temperature follows from the heat load -> figs/inlet_derivation.png"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAVY, CU, GREY = "#13294B", "#B87333", "#4B5563"
plt.rcParams.update({"mathtext.fontset": "dejavuserif", "font.family": "DejaVu Sans"})
steps = [
    ("1  Coolant energy balance: the methanol warms along the coil",
     r"$\Delta T_{cool} = \dfrac{Q}{\dot m\,c_p} = \dfrac{2.58\ \mathrm{W}}{0.0175\ \mathrm{kg/s}\times 2286\ \mathrm{J/kgK}} = 64\ \mathrm{mK}\quad(226\ \mathrm{mK\ at\ 5\ g/s})$"),
    ("2  The wall sits above the coolant by the film + copper resistance",
     r"$T_{wall} - T_{cool} \approx \dfrac{Q}{UA}\qquad UA = \sum h\,A_{wet}\ \ (\mathrm{A^*}:\ 46\ \mathrm{W/K} \Rightarrow 56\ \mathrm{mK})$"),
    ("3  Mean wall temperature for a given inlet",
     r"$\bar T_{wall} \approx T_{in} + \dfrac{\Delta T_{cool}}{2} + \dfrac{Q}{UA}$"),
    ("4  Hand estimate: put the mean wall on the set point",
     r"$T_{in} \approx T_{set} - \dfrac{\Delta T_{cool}}{2} - \dfrac{Q}{UA} = -30 - 0.032 - 0.056 = -30.09\ ^\circ\mathrm{C}\ \ (\mathrm{A^*})$"),
    ("5  3-D model: centre the warmest and coldest wall points (linear problem)",
     r"$T_{in} = T_{in,0} + T_{set} - \dfrac{T_{wall,max} + T_{wall,min}}{2} = -30.149\ ^\circ\mathrm{C}\ \ (\mathrm{A^*},\ 17.5\ \mathrm{g/s})$"),
    ("6  Allowed inlet window: the whole wall stays within ±0.15 K",
     r"$T_{in} \pm \left(0.150 - \dfrac{\mathrm{spread}}{2}\right) = -30.149 \pm 0.099 \Rightarrow -30.25\ \mathrm{to}\ -30.05\ ^\circ\mathrm{C}$"),
]
fig = plt.figure(figsize=(7.6, 8.4))
y = 0.975
for i, (t, eq) in enumerate(steps):
    fig.text(0.02, y, t, fontsize=11.5, weight="bold", color=NAVY, va="top")
    fig.text(0.04, y - 0.045, eq, fontsize=13.5 if i != 0 else 12, color=CU if i in (4, 5) else "#1A1F2B", va="top")
    y -= 0.155
fig.text(0.02, 0.015, "The hand estimate (step 4) uses the mean wall; the end plates bring 74 % of the heat in far from the coolant,\n"
         "so the warmest wall point sits at the plates and the 3-D centring inlet (step 5) is 20–90 mK colder.", fontsize=9.3, color=GREY, va="bottom")
fig.savefig("figs/inlet_derivation.png", dpi=200)
