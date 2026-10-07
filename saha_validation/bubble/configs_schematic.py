#!/usr/bin/env python3
"""Schematics of the four ways the SAHA chamber can be filled / pressurised.   -> figs/chamber_configs.png"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

NAVY, CU, CU_D, PMMA = "#13294B", "#C8803F", "#8A5226", "#9EC3E0"
LIQ, VAP, GAS, FILM = "#3E7CC7", "#EAF2FA", "#E9E4F3", "#1F4FBF"
W = 13.5                                            # bore radius, mm (drawn x2)
SX = 2.0


def chamber(ax, liquid_top, vap_fill=VAP, pressure="", title="", notes=(), condense=("z1",), gas=False, bellows=False, top_liquid=None):
    # cone / reservoir below z=0 (generic), bore above
    cone = Polygon([(-W * SX, 0), (-55, -55), (-55, -120), (55, -120), (55, -55), (W * SX, 0)], closed=True, fc="none", ec=PMMA, lw=3)
    # fluids
    ax.add_patch(Polygon([(-W * SX, 0), (-55, -55), (-55, -120), (55, -120), (55, -55), (W * SX, 0)], closed=True, fc=vap_fill, ec="none"))
    ax.add_patch(Rectangle((-W * SX, 0), 2 * W * SX, 425, fc=vap_fill, ec="none"))
    # liquid up to liquid_top (z, mm); below 0 fill cone
    if liquid_top is not None:
        if liquid_top <= 0:
            zt = liquid_top
            xw = W * SX + (55 - W * SX) * min(1.0, -zt / 55.0)
            ax.add_patch(Polygon([(-xw, zt), (-55, -55), (-55, -120), (55, -120), (55, -55), (xw, zt)], closed=True, fc=LIQ, ec="none", alpha=0.85))
            ax.plot([-xw, xw], [zt, zt], color="#0B2545", lw=1.2, ls="--")
        else:
            ax.add_patch(Polygon([(-W * SX, 0), (-55, -55), (-55, -120), (55, -120), (55, -55), (W * SX, 0)], closed=True, fc=LIQ, ec="none", alpha=0.85))
            ax.add_patch(Rectangle((-W * SX, 0), 2 * W * SX, liquid_top, fc=LIQ, ec="none", alpha=0.85))
            ax.plot([-W * SX, W * SX], [liquid_top, liquid_top], color="#0B2545", lw=1.2, ls="--")
    if gas:
        ax.add_patch(Rectangle((-W * SX, 300), 2 * W * SX, 125, fc=GAS, ec="none"))
    if top_liquid is not None:
        pass
    ax.add_patch(cone)
    # walls: Perspex and copper zones
    for z0, z1 in ((0, 60), (187, 247), (365, 425)):
        for s in (-1, 1):
            ax.add_patch(Rectangle((s * W * SX - (3 if s < 0 else 0), z0), 3, z1 - z0, fc=PMMA, ec="none"))
    for (z0, z1, lab) in ((60, 187, "Zone 2\n−15 °C"), (247, 365, "Zone 1\n−30 °C")):
        for s in (-1, 1):
            ax.add_patch(Rectangle((s * W * SX - (8 if s < 0 else 0), z0), 8, z1 - z0, fc=CU, ec=CU_D, lw=0.6))
            ax.add_patch(Rectangle((s * W * SX - (24 if s < 0 else 0), z0), 24, 8, fc=CU, ec=CU_D, lw=0.6))
            ax.add_patch(Rectangle((s * W * SX - (24 if s < 0 else 0), z1 - 8), 24, 8, fc=CU, ec=CU_D, lw=0.6))
        ax.text(W * SX + 28, (z0 + z1) / 2, lab, fontsize=8.5, color=CU_D, va="center", weight="bold")
    ax.add_patch(Rectangle((-W * SX - 3, 425), 2 * W * SX + 6, 4, fc=PMMA, ec="none"))
    # condensate films
    for c in condense:
        z0, z1 = {"z1": (247, 365), "z2": (60, 187)}[c]
        for s in (-1, 1):
            ax.add_patch(Rectangle((s * W * SX - (2 if s > 0 else -0.5) - (0 if s > 0 else 2), z0 + 5), 2, z1 - z0 - 10, fc=FILM, ec="none"))
    # ice bath / thermostat
    ax.add_patch(Rectangle((-70, -128), 140, 75, fc="none", ec="#7FB3D5", lw=1.5, ls=":"))
    ax.text(0, -136, "liquid thermostat (bath)", fontsize=7.5, ha="center", color="#2E6F9E")
    if bellows:
        for k in range(6):
            ax.plot([30 + k * 6, 33 + k * 6], [-100 - (k % 2) * 4, -100 - ((k + 1) % 2) * 4], color="k", lw=1)
        ax.add_patch(FancyArrowPatch((75, -95), (60, -95), arrowstyle="-|>", mutation_scale=10, color="k"))
        ax.text(58, -80, "bellows /\npiston sets p", fontsize=7.5)
    ax.text(-62, 455, title, fontsize=10.5, weight="bold", color=NAVY, va="bottom")
    ax.text(-62, 440, pressure, fontsize=8.5, color="#B4471A", va="bottom")
    y = -165
    for n in notes:
        ax.text(-62, y, n, fontsize=8, va="top", color="#1A1F2B"); y -= 14
    ax.set_xlim(-65, 85); ax.set_ylim(-235, 470); ax.set_aspect("equal"); ax.axis("off")


fig, axs = plt.subplots(1, 4, figsize=(17, 11))
chamber(axs[0], -20, title="A · Condenser-set (geyser)", pressure="p = p_sat(−30 °C) = 84.4 kPa",
        notes=["• Liquid in the cone, vapour above", "• Zone 1 = coldest = condenser", "• Bubbles: vapour rises, condenses", "  on Zone 1, drips back", "• Superheat = T_liq + 30 K"])
chamber(axs[1], 120, title="B · High fill", pressure="p = 84.4 kPa (set by Zone 1)",
        notes=["• Liquid up into Zone 2 (−15 °C)", "• Liquid in Zone 2 is 15 K superheated", "• Zone 2 boils it, Zone 1 condenses:", "  a heat pipe between the zones", "  (large extra load on both coils)"])
chamber(axs[2], 425, title="C · Pressurised, liquid-filled", pressure="p set by bellows, e.g. 300–600 kPa", condense=(), bellows=True,
        notes=["• Bore full of liquid; no vapour", "• Superheat by dropping p", "  (expansion), recompress after", "  each bubble (PICO style)", "• Cold zones cool subcooled liquid"])
chamber(axs[3], -20, vap_fill=GAS, title="D · Gas-buffered", pressure="p = p_R134a + p_gas (N₂ / Ar)", gas=True,
        notes=["• Inert gas sets the total pressure", "• R134a vapour still condenses", "  on Zone 1, slowed by the gas", "• Superheat set by the gas", "  pressure, not only by Zone 1"])
# legend
ax = axs[3]
for i, (c, lab) in enumerate(((LIQ, "liquid R134a (superheated in the cone)"), (VAP, "R134a vapour"), (GAS, "R134a vapour + inert gas"),
                              (FILM, "condensing liquid film"), (CU, "copper zone"), (PMMA, "Perspex / glass"))):
    fig.patches.append(Rectangle((0.08 + (i % 3) * 0.29, 0.925 - (i // 3) * 0.02), 0.012, 0.011, transform=fig.transFigure, fc=c, ec="0.5", lw=0.5))
    fig.text(0.096 + (i % 3) * 0.29, 0.926 - (i // 3) * 0.02, lab, fontsize=9)
fig.suptitle("SAHA chamber: four ways to fill and pressurise it (geometry below z = 0 is generic until the lower-chamber drawing is available)",
             x=0.01, ha="left", fontsize=12.5, weight="bold", color=NAVY)
fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig("figs/chamber_configs.png", dpi=150)
print("ok")
