#!/usr/bin/env python3
"""True-scale section of the SAHA cold stage (axisymmetric, both halves) -> figs/chamber_schematic.png"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch

NAVY, CU, CU_D, PMMA, FOAM, VAP, ICE = "#13294B", "#C8803F", "#8A5226", "#9EC3E0", "#F3EEE4", "#EAF2FA", "#3D4A5C"
fig, ax = plt.subplots(figsize=(7.6, 9.6))
ax.set_aspect("equal"); ax.axis("off")
R_FOAM, Z_TOP = 93.0, 475.0


def box(r0, r1, z0, z1, fc, ec="none", lw=0.0, hatch=None, z=1, both=True):
    for s in ((1, -1) if both else (1,)):
        x0, x1 = sorted((s * r0, s * r1))
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=fc, ec=ec, lw=lw, hatch=hatch, zorder=z))


# foam block and lab
box(0, R_FOAM, 0, Z_TOP, FOAM, ec="#CBBFA8", lw=0.8, both=True)
ax.add_patch(Rectangle((-R_FOAM, 0), 2 * R_FOAM, Z_TOP, fc="none", ec="#B9AD95", lw=1.2, zorder=6))
# vapour bore
ax.add_patch(Rectangle((-13.5, 0), 27, 423.5, fc=VAP, ec="none", zorder=2))
# Perspex: connectors, top section, cap
for z0, z1 in ((0, 60), (187, 247), (365, 425)):
    box(13.5, 15, z0, z1, PMMA, z=3)
ax.add_patch(Rectangle((-15, 423.5), 30, 1.5, fc=PMMA, ec="none", zorder=3))
# copper zones: wall, buffer, plates; coil tubes
for (z0, z1) in ((60, 187), (247, 365)):
    box(13.5, 20, z0, z1, CU, z=3)
    box(13.5, 43, z0, z0 + 11, CU, ec=CU_D, lw=0.6, z=4)
    box(13.5, 43, z1 - 11, z1, CU, ec=CU_D, lw=0.6, z=4)
    zc = z0 + 11 + 4.0
    while zc < z1 - 11 - 3:
        for s in (1, -1):
            ax.add_patch(Circle((s * 22.0, zc), 2.0, fc=CU, ec=CU_D, lw=0.6, zorder=5))
            ax.add_patch(Circle((s * 22.0, zc), 1.3, fc="#2A78D6", ec="none", zorder=6))
        zc += 6.9
# coolant in / out (generic)
for (z0, z1) in ((60, 187), (247, 365)):
    zi = z0 + 15.0; zo = z1 - 15.0
    ax.add_patch(FancyArrowPatch((60, zi - 2), (25, zi), arrowstyle="-|>", mutation_scale=9, lw=1.2, color="#2A78D6", zorder=9))
    ax.text(62, zi - 2, "coolant in", fontsize=7.5, color="#2A78D6", va="center", zorder=9)
    ax.add_patch(FancyArrowPatch((25, zo), (60, zo + 2), arrowstyle="-|>", mutation_scale=9, lw=1.2, color="#C0392B", zorder=9))
    ax.text(62, zo + 2, "coolant out", fontsize=7.5, color="#C0392B", va="center", zorder=9)
# radial dimensions under the ice tray
for (r, lab, y) in ((13.5, "bore Ø27", -24), (43, "plates Ø86", -38), (R_FOAM, "outside Ø186 mm", -52)):
    ax.add_patch(FancyArrowPatch((-r, y), (r, y), arrowstyle="<|-|>", mutation_scale=6, lw=0.7, color=NAVY, zorder=8))
    ax.text(r + 3, y, lab, fontsize=8, color=NAVY, va="center")
# foam thickness
ax.add_patch(FancyArrowPatch((43, 470), (R_FOAM, 470), arrowstyle="<|-|>", mutation_scale=6, lw=0.7, color="#8A7A5C", zorder=8))
ax.text(68, 463, "50 mm foam", fontsize=7.5, color="#8A7A5C", ha="center", va="top")
# ice tray
ax.add_patch(Rectangle((-R_FOAM - 6, -10), 2 * R_FOAM + 12, 10, fc=ICE, ec="none", zorder=5))
ax.text(0, -5, "ice tray, 0 °C", color="white", ha="center", va="center", fontsize=9.5, weight="bold", zorder=7)
# axis
ax.plot([0, 0], [-12, Z_TOP + 8], color="#6B7280", lw=0.7, ls=(0, (8, 3, 2, 3)), zorder=7)
ax.text(0, 212, "R134a\nvapour\nØ27 mm\nbore", ha="center", va="center", fontsize=8, color=NAVY, zorder=8,
        bbox=dict(fc=VAP, ec="none", pad=0.5))
# dimension ladder on the left
X = -R_FOAM - 18
lv = [0, 60, 187, 247, 365, 425]
for z in lv + [Z_TOP]:
    ax.plot([X - 3, -R_FOAM], [z, z], color="#9CA3AF", lw=0.5, zorder=1)
    ax.text(X - 5, z, f"{z:g}", ha="right", va="center", fontsize=8.5, color="#4B5563")
ax.text(X - 5, Z_TOP + 14, "z, mm", ha="right", va="center", fontsize=8.5, color="#4B5563")
for (a, b, lab) in ((0, 60, "60 lower\nconnector"), (60, 187, "127\nZone 2"), (187, 247, "60 middle\nconnector"), (247, 365, "118\nZone 1"), (365, 425, "60 top")):
    ax.add_patch(FancyArrowPatch((X, a), (X, b), arrowstyle="<|-|>", mutation_scale=7, lw=0.8, color=NAVY, zorder=8))
    ax.text(X + 3, (a + b) / 2, lab, ha="left", va="center", fontsize=8.2, color=NAVY, zorder=8,
            bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.85))
# right-hand labels with leaders
def lab(xy, xt, zt, text, col=NAVY, w="normal"):
    ax.annotate(text, xy=xy, xytext=(xt, zt), fontsize=9, color=col, weight=w, va="center", ha="left",
                arrowprops=dict(arrowstyle="-", color="#6B7280", lw=0.6), zorder=9)
XT = R_FOAM + 10
lab((40, 365 - 5.5), XT, 405, "end plate, 86 mm OD × 11 mm")
lab((19, 320), XT, 322, "ZONE 1 copper\nset point −30 °C", CU_D, "bold")
lab((24, 290), XT, 288, "coil tubes Ø4 mm on r 22 mm\n(layout-dependent)")
lab((14.2, 215), XT, 222, "Perspex connector")
lab((19, 140), XT, 136, "ZONE 2 copper\nset point −15 °C", CU_D, "bold")
lab((17, 100), XT, 98, "buffer, r 15–20 mm")
lab((14.2, 430), XT, 452, "Perspex top + cap")
lab((70, 30), XT, 40, "foam insulation, 50 mm\nbeyond the plates and cap")
ax.text(R_FOAM + 4, Z_TOP + 10, "lab 35 °C, h = 8 W/m²K", fontsize=9, color="#B4471A", weight="bold", ha="left")
ax.set_xlim(-R_FOAM - 50, R_FOAM + 92); ax.set_ylim(-58, Z_TOP + 22)
fig.savefig("figs/chamber_schematic.png", dpi=220, bbox_inches="tight", pad_inches=0.05)
print("ok")
