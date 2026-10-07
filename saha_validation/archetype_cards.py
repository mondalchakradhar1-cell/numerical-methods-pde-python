#!/usr/bin/env python3
"""One figure per coil archetype for the presentation: 3-D view of the coil passages (coolant temperature),
r-z cross-section (schematic), inner-wall map and the wall along the height.  No comparison content.

    python archetype_cards.py [flow]   -> figs/cards/<layout>_<flow>_card.png, figs/cards/<layout>_3d.png
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figs", "cards")
os.makedirs(OUT, exist_ok=True)
NAVY = "#13294B"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 11.5, "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left"})


def faces(c, f0):
    f = [f0]
    for x in c:
        f.append(2 * x - f[-1])
    return np.array(f)


def render3d(d, fname, title):
    rc, tc, zc, mat = d["rc"], d["tc"], d["zc"], d["mat"]
    rf = faces(rc, 13.5)
    tf = np.linspace(0, 2 * np.pi, len(tc) + 1)
    zf = faces(zc, zc[0] - (zc[1] - zc[0]) / 2)
    R, T, Z = np.meshgrid(rf, tf, zf, indexing="ij")
    g = pv.StructuredGrid(R * np.cos(T), R * np.sin(T), Z)
    g.cell_data["mat"] = mat.ravel(order="F").astype(float)
    Tc = np.where(mat == 3, d["Tnode"][np.clip(d["node"], 0, None)], np.nan)
    g.cell_data["T"] = Tc.ravel(order="F")
    p = pv.Plotter(off_screen=True, window_size=(900, 1000))
    p.set_background("white")
    cu = g.threshold((0.5, 1.5), scalars="mat").extract_surface().clip(normal=(0, -1, 0), origin=(0, 0, 0), invert=False)
    p.add_mesh(cu, color="#c87533", opacity=0.16, smooth_shading=True)
    fl = g.threshold((2.5, 3.5), scalars="mat").extract_surface()
    v = fl.cell_data["T"]
    p.add_mesh(fl, scalars="T", cmap="coolwarm", clim=(np.nanmin(v), np.nanmax(v)), show_scalar_bar=True,
               scalar_bar_args=dict(title="methanol T (°C)", color="black", vertical=True, position_x=0.83, position_y=0.25, height=0.5, fmt="%.3f",
                                    title_font_size=16, label_font_size=14))
    p.camera_position = [(115, -150, 125), (0, 0, 45), (0, 0, 1)]
    p.screenshot(fname)
    p.close()


def card(name, flow, res):
    d = np.load(os.path.join(HERE, "results", f"field_base_{name}_{flow:g}.npz"))
    f3d = os.path.join(OUT, f"{name}_{flow:g}_3d.png")
    render3d(d, f3d, name)
    tc, zc, rc, mat = np.degrees(d["tc"]), d["zc"], d["rc"], d["mat"]
    fig = plt.figure(figsize=(17, 5.6))
    # (a) 3-D
    ax = fig.add_axes([0.0, 0.02, 0.24, 0.92]); ax.axis("off")
    ax.imshow(plt.imread(f3d)[60:-40, 40:-20]); ax.set_title("Coil passages in 3-D (methanol temperature)", loc="left")
    # (b) r-z section
    ax = fig.add_axes([0.28, 0.12, 0.2, 0.78])
    ms = mat[:, 0, :]
    Ts = (d["Tsec"] + 30.0) * 1e3
    Tp = np.where(ms == 1, Ts, np.nan)
    vm = np.nanmax(abs(Tp))
    im = ax.pcolormesh(rc, zc, Tp.T, cmap="RdBu_r", vmin=-vm, vmax=vm, shading="nearest")
    ax.pcolormesh(rc, zc, np.ma.masked_where(ms.T != 3, np.ones_like(Ts.T)), cmap=matplotlib.colors.ListedColormap([NAVY]), shading="nearest")
    ax.set_xlim(13.5, 43); ax.set_ylim(-11, 107)
    ax.set_xlabel("radius r, mm"); ax.set_ylabel("height z, mm (0 = top of lower plate)")
    ax.set_title("Cross-section (passages navy)", loc="left")
    fig.colorbar(im, ax=ax, label="copper T − (−30 °C), mK", pad=0.02, fraction=0.08)
    # (c) inner wall map
    ax = fig.add_axes([0.55, 0.12, 0.24, 0.78])
    Tw = (d["Tw"] + 30.0) * 1e3
    im = ax.pcolormesh(tc, zc, Tw.T, cmap="RdBu_r", vmin=-150, vmax=150, shading="nearest")
    cs = ax.contour(tc, zc, Tw.T, levels=np.arange(-60, 61, 20), colors="k", linewidths=0.6)
    ax.clabel(cs, fontsize=7.5, fmt="%d")
    ax.axhline(0, color="k", ls="--", lw=0.7); ax.axhline(96, color="k", ls="--", lw=0.7)
    ax.set_xticks(range(0, 361, 90)); ax.set_xlabel("angle round the zone θ, deg"); ax.set_ylabel("height z, mm")
    ax.set_title(f"Inner copper wall: spread {res['spread']:.0f} mK", loc="left")
    fig.colorbar(im, ax=ax, label="T − (−30 °C), mK (band ±150)", pad=0.02, fraction=0.08)
    # (d) along the height
    ax = fig.add_axes([0.86, 0.12, 0.13, 0.78])
    with np.errstate(all="ignore"):
        lo, hi, av = Tw.min(axis=0), Tw.max(axis=0), Tw.mean(axis=0)
    ax.axvspan(-150, 150, color="#f1f1ec")
    ax.fill_betweenx(zc, lo, hi, color="#e7b98f", alpha=0.75, label="min–max round")
    ax.plot(av, zc, color="#b3631b", lw=1.6, label="average")
    ax.axhline(0, color="k", ls="--", lw=0.7); ax.axhline(96, color="k", ls="--", lw=0.7)
    ax.set_xlim(-160, 160); ax.set_xlabel("wall T − (−30 °C), mK"); ax.set_title("Along the height", loc="left")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    fig.savefig(os.path.join(OUT, f"{name}_{flow:g}_card.png"), dpi=150); plt.close(fig)


if __name__ == "__main__":
    flow = float(sys.argv[1]) if len(sys.argv) > 1 else 17.5
    S = json.load(open(os.path.join(HERE, "results", "summary.json")))
    for name in ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"]:
        res = [r for r in S["layouts"] if r["layout"] == name and abs(r["flow"] - flow) < 1e-6][0]
        card(name, flow, res)
        print(name, flush=True)
