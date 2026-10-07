#!/usr/bin/env python3
"""3-D renders of the vapour column (radius drawn x2.5, as in the coupled deck) and the 0-120 s GIF."""
import glob
import os
import sys

import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
SR = 2.5                       # radial exaggeration
R_MM, H_MM = 13.5, 423.5
CMAP = "coolwarm"
CLIM = (-30, 0)


def grid_from(T, xc, zc, sec):
    nx, ny, nz = T.shape
    dx = (xc[1] - xc[0]) * 1e3
    dz = (zc[1] - zc[0]) * 1e3
    g = pv.ImageData(dimensions=(nx + 1, ny + 1, nz + 1), spacing=(dx * SR, dx * SR, dz),
                     origin=((xc[0] * 1e3 - dx / 2) * SR, (xc[0] * 1e3 - dx / 2) * SR, 0.0))
    Tm = np.where(sec[:, :, None], T, np.nan).astype(float)
    g.cell_data["T"] = Tm.ravel(order="F")
    return g


def scenery(p, cut=True):
    """Perspex glass, copper bands, ice tray (back halves only when cut)"""
    r_in, r_cu = R_MM * SR, R_MM * SR + 6
    def shell(z0, z1, r0, r1, color, opacity, ang=(0, 180)):
        res = 60
        th = np.radians(np.linspace(ang[0], ang[1], res)) if cut else np.radians(np.linspace(0, 360, res))
        pts, faces = [], []
        for zz in (z0, z1):
            for rr in (r0, r1):
                for t in th:
                    pts.append((rr * np.cos(t), rr * np.sin(t), zz))
        pts = np.array(pts)
        n = len(th)
        def idx(zi, ri, ti): return zi * 2 * n + ri * n + ti
        for ti in range(n - 1):
            for zi, ri in ((0, 0), (0, 1)):
                pass
            for ri in (0, 1):                            # inner / outer surfaces
                faces.append([4, idx(0, ri, ti), idx(0, ri, ti + 1), idx(1, ri, ti + 1), idx(1, ri, ti)])
            for zi in (0, 1):                            # end rings
                faces.append([4, idx(zi, 0, ti), idx(zi, 0, ti + 1), idx(zi, 1, ti + 1), idx(zi, 1, ti)])
        mesh = pv.PolyData(pts, np.hstack(faces))
        p.add_mesh(mesh, color=color, opacity=opacity, smooth_shading=True, specular=0.4)
    glass = "#9fbfd9"
    for z0, z1 in ((0, 60), (187, 247), (365, 425)):
        shell(z0, z1, r_in, r_in + 3.5, glass, 0.35)
    for z0, z1 in ((60, 187), (247, 365)):
        shell(z0, z1, r_in, r_cu, "#c87533", 0.95)
    tray = pv.Cylinder(center=(0, 0, -3), direction=(0, 0, 1), radius=r_cu + 10, height=6, resolution=80)
    p.add_mesh(tray, color="#3d4a5c")


def particles_poly(P_hist, Tfield, xc, zc, sec, tail=10):
    """polylines of the last `tail` positions of every particle, coloured by local temperature"""
    P = P_hist[-tail:] * 1e3                       # (tail, n, 3) mm
    n = P.shape[1]
    pts = P.transpose(1, 0, 2).reshape(-1, 3).copy()
    pts[:, :2] *= SR
    lines = np.hstack([[tail] + list(range(i * tail, (i + 1) * tail)) for i in range(n)])
    poly = pv.PolyData(pts, lines=lines)
    dx = (xc[1] - xc[0]); dz = zc[1] - zc[0]
    Pl = P_hist[-tail:].transpose(1, 0, 2).reshape(-1, 3)
    i = np.clip(((Pl[:, 0] - xc[0] + dx / 2) / dx).astype(int), 0, len(xc) - 1)
    j = np.clip(((Pl[:, 1] - xc[0] + dx / 2) / dx).astype(int), 0, len(xc) - 1)
    k = np.clip((Pl[:, 2] / dz).astype(int), 0, len(zc) - 1)
    poly.point_data["T"] = Tfield[i, j, k].astype(float)
    return poly


def camera(p):
    p.camera_position = [(260, -900, 330), (0, 0, 212), (0, 0, 1)]
    p.camera.zoom(1.05)


def render_midplane(p, T, xc, zc, sec, bar=False):
    g = grid_from(T, xc, zc, sec)
    sl = g.slice(normal="y", origin=(0, 0.01, 0)).threshold(-1e9, scalars="T")
    p.add_mesh(sl, scalars="T", cmap=CMAP, clim=CLIM, lighting=False, show_scalar_bar=bar,
               scalar_bar_args=dict(title="vapour T (°C)", vertical=True, position_x=0.86, position_y=0.25, height=0.5,
                                    color="black", title_font_size=12, label_font_size=10, n_labels=7))


def midplane_mesh(F, xc, zc, sec, name):
    """mid-plane (y = 0) as a 2-D structured surface in 3-D, radius drawn x SR; F has shape (nx, nz)"""
    dx = (xc[1] - xc[0]) * 1e3
    dz = (zc[1] - zc[0]) * 1e3
    xe = (np.r_[xc - (xc[1] - xc[0]) / 2, xc[-1] + (xc[1] - xc[0]) / 2]) * 1e3 * SR
    ze = np.r_[zc - (zc[1] - zc[0]) / 2, zc[-1] + (zc[1] - zc[0]) / 2] * 1e3
    X, Z = np.meshgrid(xe, ze, indexing="ij")
    g = pv.StructuredGrid(X, np.zeros_like(X) + 0.01, Z)
    jm = sec.shape[1] // 2
    vals = np.where(sec[:, jm][:, None], F, np.nan)
    g.cell_data[name] = vals.ravel(order="F")
    return g.threshold(-1e9, scalars=name)


def frame(snap, P_hist, xc, zc, sec, fname, title):
    """two 3-D panels of one instant: mid-plane temperature and mid-plane vertical velocity"""
    p = pv.Plotter(off_screen=True, window_size=(1100, 1200), shape=(1, 2), border=False)
    p.set_background("white")
    p.subplot(0, 0)
    scenery(p, cut=True)
    p.add_mesh(midplane_mesh(snap["Tmid"].astype(float), xc, zc, sec, "T"), scalars="T", cmap=CMAP, clim=CLIM, lighting=False,
               scalar_bar_args=dict(title="vapour T (°C)", vertical=True, position_x=0.86, position_y=0.25, height=0.5,
                                    color="black", title_font_size=12, label_font_size=10, n_labels=7))
    camera(p)
    p.add_text("temperature, mid-plane", position="upper_edge", font_size=11, color="black")
    p.subplot(0, 1)
    scenery(p, cut=True)
    p.add_mesh(midplane_mesh(snap["wmid"].astype(float), xc, zc, sec, "w"), scalars="w", cmap="RdBu_r", clim=(-0.1, 0.1), lighting=False,
               scalar_bar_args=dict(title="w (m/s)", vertical=True, position_x=0.86, position_y=0.25, height=0.5,
                                    color="black", title_font_size=12, label_font_size=10, n_labels=5))
    camera(p)
    p.add_text("vertical velocity, mid-plane", position="upper_edge", font_size=11, color="black")
    p.add_text(title, position="lower_edge", font_size=12, color="black")
    p.screenshot(fname)
    p.close()


def four_panel(run, fname, win=2):
    m = np.load(os.path.join(run, f"mean_{win}.npz"))
    xc, zc, sec = m["xc"], m["zc"], m["sec"]
    snaps = sorted(glob.glob(os.path.join(run, "snap_*.npz")))
    last = np.load(snaps[-1])
    part = np.load(os.path.join(run, "particles.npz"))
    p = pv.Plotter(off_screen=True, window_size=(2200, 1250), shape=(1, 4), border=False)
    p.set_background("white")
    # 1 mean T mid-plane
    p.subplot(0, 0); scenery(p); render_midplane(p, m["T"].astype(float), xc, zc, sec); camera(p)
    p.add_text("time-mean temperature\non the mid-plane", position="upper_edge", font_size=10, color="black")
    # 2 mean flow paths: streamlines of the time-mean velocity
    p.subplot(0, 1); scenery(p)
    g = grid_from(m["T"].astype(float), xc, zc, sec)
    vel = np.stack([m["u"], m["v"], m["w"]], axis=-1).astype(float)
    vel[:, :, :, :2] *= SR
    vel[~sec] = 0
    g.cell_data["vel"] = vel.reshape(-1, 3, order="F")
    gp = g.cell_data_to_point_data()
    src = pv.PointSet(np.c_[np.random.default_rng(2).uniform(-1, 1, (900, 2)) * R_MM * SR * 0.65, np.random.default_rng(3).uniform(2, 421, 900)])
    try:
        st = gp.streamlines_from_source(src, vectors="vel", integration_direction="both", max_steps=3000,
                                        initial_step_length=0.5, max_length=400)
        p.add_mesh(st, scalars="T", cmap=CMAP, clim=CLIM, line_width=1.3, show_scalar_bar=False)
    except Exception as e:
        print("streamlines failed", e)
    camera(p)
    p.add_text("time-mean flow paths", position="upper_edge", font_size=10, color="black")
    # 3 one instant T
    p.subplot(0, 2); scenery(p); render_midplane(p, last["T"].astype(float), xc, zc, sec, bar=True); camera(p)
    p.add_text(f"one instant:\ntemperature (t = {float(last['t']):.0f} s)", position="upper_edge", font_size=10, color="black")
    # 4 one instant flow paths: tracer tails over the last 2 s
    p.subplot(0, 3); scenery(p)
    poly = particles_poly(part["P"], last["T"].astype(float), xc, zc, sec, tail=20)
    p.add_mesh(poly, scalars="T", cmap=CMAP, clim=CLIM, line_width=1.4, show_scalar_bar=False)
    camera(p)
    p.add_text("one instant:\nflow paths (tracers, last 2 s)", position="upper_edge", font_size=10, color="black")
    p.screenshot(fname); p.close()


def gif(run, fname, every=1, fps=8):
    import imageio.v2 as imageio
    from PIL import Image
    c = np.load(os.path.join(run, "conduction.npz"))
    xc, zc, sec = c["xc"], c["zc"], c["sec"]
    part = np.load(os.path.join(run, "particles.npz")) if os.path.exists(os.path.join(run, "particles.npz")) else None
    snaps = sorted(glob.glob(os.path.join(run, "snap_*.npz")))[::every]
    frames = []
    tmp = os.path.join(run, "_frame.png")
    for s in snaps:
        d = np.load(s)
        t = float(d["t"])
        Ph = None
        if part is not None:
            idx = np.nonzero(part["t"] <= t + 1e-6)[0]
            if len(idx):
                Ph = part["P"][max(0, idx[-1] - 9): idx[-1] + 1]
        phase = "one-way walls" if t < 60 else "two-way coupled walls"
        frame(d, Ph, xc, zc, sec, tmp, f"t = {t:6.1f} s   ({phase})")
        im = Image.open(tmp).convert("RGB")
        im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        frames.append(np.asarray(im))
        print("frame", t, flush=True)
    imageio.mimsave(fname, frames, duration=1 / fps, loop=0)


if __name__ == "__main__":
    run = sys.argv[1]
    what = sys.argv[2] if len(sys.argv) > 2 else "all"
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(run, "..", "..", "figs")
    if what in ("frame",):
        c = np.load(os.path.join(run, "conduction.npz"))
        s = sorted(glob.glob(os.path.join(run, "snap_*.npz")))[-1]
        frame(np.load(s), None, c["xc"], c["zc"], c["sec"], os.path.join(out, "test_frame.png"), "test")
    if what in ("all", "four"):
        four_panel(run, os.path.join(out, "vapour_3d_four.png"))
    if what in ("all", "gif"):
        gif(run, os.path.join(out, "vapour_0_120s.gif"))
