#!/usr/bin/env python3
"""Presentation renders of the 11 coil types: smooth passage surfaces coloured cold (inlet) -> warm (outlet),
metallic copper body cut away in front, IN / OUT arrows.   python coil_renders.py [names...] -> figs/coils/<name>.png"""
import os
import sys

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import pyvista as pv
from scipy import ndimage

import layouts

pv.OFF_SCREEN = True
CMAP = LinearSegmentedColormap.from_list("flow", ["#1F4FBF", "#7E57C2", "#E0301E"])
CAM_AZ = np.arctan2(-250, 150)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figs", "coils")
os.makedirs(OUT, exist_ok=True)


def faces(c, f0):
    f = [f0]
    for x in c:
        f.append(2 * x - f[-1])
    return np.array(f)


def grid(d):
    rf = faces(d["rc"], 13.5)
    tf = np.linspace(0, 2 * np.pi, len(d["tc"]) + 1)
    zc = d["zc"]; zf = faces(zc, zc[0] - (zc[1] - zc[0]) / 2)
    R, T, Z = np.meshgrid(rf, tf, zf, indexing="ij")
    return pv.StructuredGrid(R * np.cos(T), R * np.sin(T), Z)


def clusters(mask, d, n_max=2):
    lab, n = ndimage.label(mask)
    out = []
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    for k in np.argsort(sizes)[::-1][:n_max]:
        if sizes[k] < 0.15 * sizes.max():
            continue
        i, j, kk = np.nonzero(lab == k + 1)
        r = d["rc"][i].mean(); th = np.angle(np.exp(1j * d["tc"][j]).mean()); z = d["zc"][kk].mean()
        out.append((r, th, z))
    merged = []
    for c in out:
        xy = np.array([c[0] * np.cos(c[1]), c[0] * np.sin(c[1]), c[2]])
        if all(np.linalg.norm(xy - np.array([m[0] * np.cos(m[1]), m[0] * np.sin(m[1]), m[2]])) > 12 for m in merged):
            merged.append(c)
    return merged


def render(name, flow=17.5):
    d = np.load(os.path.join(HERE, "results", f"field_base_{name}_{flow:g}.npz"))
    mat = d["mat"]
    g = grid(d)
    T = np.where(mat == 3, d["Tnode"][np.clip(d["node"], 0, None)], np.nan)
    t0, t1 = np.nanpercentile(T, 2), np.nanpercentile(T, 98)
    frac = np.where(mat == 3, np.clip((T - t0) / max(t1 - t0, 1e-9), 0, 1), 0.0)
    _, mdl = layouts.build(name, flow / 1000.0)
    assert (mdl.node == d["node"]).all()
    in_mask = np.isin(d["node"], list(mdl.inlets)) & (mat == 3)
    out_mask = np.isin(d["node"], [n for n, _ in mdl.outlets]) & (mat == 3)
    ports = [(c, "#1F5FBF", "IN") for c in clusters(in_mask, d, n_max=4)] + [(c, "#C0392B", "OUT") for c in clusters(out_mask, d, n_max=4)]
    rot = CAM_AZ - np.angle(np.mean([np.exp(1j * c[1]) for c, _, _ in ports]))
    g = g.rotate_z(np.degrees(rot), inplace=False)
    g.cell_data["fluid"] = (mat == 3).astype(float).ravel(order="F")
    R = d["rc"][:, None, None] * np.ones(mat.shape)
    Z = d["zc"][None, None, :] * np.ones(mat.shape)
    solid = (mat == 1) & ((R < 15.05) | (Z < 0) | (Z > 96))          # inner copper wall + the two end plates
    ghost = (mat == 1) & ~solid                                        # buffer / carrier / tube walls: see-through
    g.cell_data["solid"] = solid.astype(float).ravel(order="F")
    g.cell_data["ghost"] = ghost.astype(float).ravel(order="F")
    g.cell_data["frac"] = frac.ravel(order="F")
    gp = g.cell_data_to_point_data()
    p = pv.Plotter(off_screen=True, window_size=(1000, 1150), lighting="three lights")
    p.set_background("white")
    cu = gp.contour([0.5], scalars="solid").smooth_taubin(n_iter=30, pass_band=0.1)
    p.add_mesh(cu, color="#C7834A", pbr=True, metallic=0.45, roughness=0.5, smooth_shading=True)
    gh = gp.contour([0.5], scalars="ghost").smooth_taubin(n_iter=30, pass_band=0.1)
    if gh.n_points:
        p.add_mesh(gh, color="#D9A066", opacity=0.13, smooth_shading=True)
    fl = gp.contour([0.5], scalars="fluid").smooth_taubin(n_iter=40, pass_band=0.08)
    fp = g.threshold(0.5, scalars="fluid").cell_centers()
    from scipy.spatial import cKDTree
    _, idx = cKDTree(fp.points).query(fl.points)
    fl.point_data["frac"] = np.asarray(fp.point_data["frac"])[idx]
    p.add_mesh(fl, scalars="frac", cmap=CMAP, clim=(0, 1), smooth_shading=True, show_scalar_bar=False, specular=0.35, specular_power=30)
    # IN / OUT arrows at the coldest and warmest passage cells
    for (r, th, z), col, lab in ports:
            th = th + rot
            ux, uy = np.cos(th), np.sin(th)
            tip = np.array([(r + 3) * ux, (r + 3) * uy, z]); tail = np.array([(r + 24) * ux, (r + 24) * uy, z])
            vec = (tip - tail) if lab == "IN" else (tail - tip)
            start = tail if lab == "IN" else tip
            p.add_mesh(pv.Arrow(start=start, direction=vec, scale=np.linalg.norm(vec), tip_length=0.3, tip_radius=0.17, shaft_radius=0.075), color=col)
            lp = tail + np.array([ux, uy, 0]) * 6
            p.add_point_labels(pv.PolyData(lp[None, :]), [lab], font_size=52, text_color=col, bold=True, shape=None, show_points=False, always_visible=True)
    p.camera_position = [(150, -250, 150), (0, 0, 44), (0, 0, 1)]
    p.camera.zoom(1.0)
    p.enable_anti_aliasing("ssaa")
    f = os.path.join(OUT, f"{name}.png")
    p.screenshot(f)
    p.close()
    from PIL import Image, ImageChops
    im = Image.open(f).convert("RGB")
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if bb:
        m = 12
        im = im.crop((max(bb[0] - m, 0), max(bb[1] - m, 0), min(bb[2] + m, im.width), min(bb[3] + m, im.height)))
    im.save(f)


if __name__ == "__main__":
    names = sys.argv[1:] or ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"]
    for n in names:
        render(n); print(n, flush=True)
