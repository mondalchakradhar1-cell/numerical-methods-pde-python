#!/usr/bin/env python3
"""3-D pictures of the coarse coolant CFD (pyvista, off-screen) and 2-D path plots.

    python viz_coolant.py <tag> <layout> <flow>  -> figs/coolant/<layout>_<flow>_{3d.png, paths.png, flow.gif}
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
OUT = os.path.join(HERE, "figs", "coolant")
os.makedirs(OUT, exist_ok=True)


def grid(d):
    rf, zf = d["rf"], None
    tc = d["tc"]; nt = len(tc)
    tf = np.linspace(0, 2 * np.pi, nt + 1)
    zc = d["zc"]
    dz = np.diff(zc)
    zf = np.r_[zc[0] - dz[0] / 2, 0.5 * (zc[1:] + zc[:-1]), zc[-1] + dz[-1] / 2]
    R, Tt, Z = np.meshgrid(rf, tf, zf, indexing="ij")
    X, Y = R * np.cos(Tt), R * np.sin(Tt)
    g = pv.StructuredGrid(X, Y, Z)
    return g


def cell_array(d, values_fluid, fill=np.nan):
    mat = d["mat"]
    A = np.full(mat.shape, fill, dtype=float)
    A[d["I"], d["J"], d["K"]] = values_fluid
    return A.ravel(order="F")


def build(d):
    g = grid(d)
    g.cell_data["mat"] = d["mat"].ravel(order="F").astype(float)
    g.cell_data["T"] = cell_array(d, d["Tf"])
    g.cell_data["p"] = cell_array(d, d["p"] / 1e3)
    vel = d["vel"]                                                    # (u_r, u_t, u_z) at fluid cells
    th = d["tc"][d["J"]]
    vx = vel[:, 0] * np.cos(th) - vel[:, 1] * np.sin(th)
    vy = vel[:, 0] * np.sin(th) + vel[:, 1] * np.cos(th)
    V = np.zeros(d["mat"].shape + (3,))
    V[d["I"], d["J"], d["K"]] = np.c_[vx, vy, vel[:, 2]]
    g.cell_data["vel"] = V.reshape(-1, 3, order="F")
    g.cell_data["speed"] = cell_array(d, np.linalg.norm(vel, axis=1), 0.0)
    Tcu = np.where(d["mat"] == 1, d["Tcu"], np.nan)
    g.cell_data["Tcu"] = Tcu.ravel(order="F")
    return g


def camera(p):
    p.camera_position = [(115, -150, 120), (0, 0, 45), (0, 0, 1)]


def copper(p, g, opacity=0.18):
    cu = g.threshold((0.5, 1.5), scalars="mat")
    surf = cu.extract_surface()
    clipped = surf.clip(normal=(0, -1, 0), origin=(0, 0, 0), invert=False)
    p.add_mesh(clipped, color="#c87533", opacity=opacity, smooth_shading=True)


def render(tag, name, flow):
    f = os.path.join(HERE, "results", f"coolant_{tag}_{name}_{flow:g}.npz")
    d = np.load(f)
    res = [r for r in json.load(open(os.path.join(HERE, "results", f"coolant_{tag}.json"))) if r["layout"] == name and r["m_gs"] == flow][0]
    g = build(d)
    fluid = g.threshold((2.5, 3.5), scalars="mat")
    Tlim = (float(res["inlet_C"]), float(res["inlet_C"] + 1.25 * max(res["rise_mK"], 1.0) / 1e3))
    lbl = "A*" if name == "A_built" else name
    # ----------------------------------------------------------------- 4-panel still
    p = pv.Plotter(off_screen=True, window_size=(2400, 900), shape=(1, 3), border=False)
    p.set_background("white")
    p.subplot(0, 0)
    copper(p, g)
    p.add_mesh(fluid.extract_surface(algorithm="dataset_surface"), scalars="T", cmap="coolwarm", clim=Tlim, show_scalar_bar=True,
               scalar_bar_args=dict(title="methanol T (°C)", color="black", vertical=True, position_x=0.85, position_y=0.2, height=0.6, fmt="%.3f"))
    camera(p); p.add_text(f"{lbl}: methanol temperature in the passages", font_size=11, color="black")
    p.subplot(0, 1)
    copper(p, g, 0.10)
    gp = fluid.cell_data_to_point_data()
    src_xyz = np.c_[d["rc"][d["I"][d["src_cells"]]] * np.cos(d["tc"][d["J"][d["src_cells"]]]),
                    d["rc"][d["I"][d["src_cells"]]] * np.sin(d["tc"][d["J"][d["src_cells"]]]),
                    d["zc"][d["K"][d["src_cells"]]]]
    rng = np.random.default_rng(0)
    seeds = pv.PointSet(src_xyz[rng.choice(len(src_xyz), min(150, len(src_xyz)), replace=False)])
    st = gp.streamlines_from_source(seeds, vectors="vel", integration_direction="forward", max_steps=40000,
                                    initial_step_length=0.3, step_unit="l", max_length=6000.0, terminal_speed=1e-5)
    if st.n_points:
        p.add_mesh(st, scalars="T", cmap="coolwarm", clim=Tlim, line_width=2, show_scalar_bar=False)
    camera(p); p.add_text("streamlines from the inlet (coloured by T)", font_size=11, color="black")
    p.subplot(0, 2)
    copper(p, g, 0.10)
    p.add_mesh(fluid.extract_surface(algorithm="dataset_surface"), scalars="p", cmap="viridis", show_scalar_bar=True,
               scalar_bar_args=dict(title="p (kPa)", color="black", vertical=True, position_x=0.85, position_y=0.2, height=0.6, fmt="%.1f"))
    camera(p); p.add_text("static pressure", font_size=11, color="black")
    p.screenshot(os.path.join(OUT, f"{name}_{flow:g}_3d.png")); p.close()
    # ----------------------------------------------------------------- animation: tracers along the streamlines
    if st.n_points:
        tint = st.point_data["IntegrationTime"] if "IntegrationTime" in st.point_data else None
        lines = []
        conn = st.lines
        i = 0
        while i < len(conn):
            n = conn[i]; ids = conn[i + 1:i + 1 + n]; i += 1 + n
            lines.append(ids)
        # IntegrationTime is in mm / (m/s) units of the grid -> treat as relative time
        tmax = max(float(tint[ids].max()) for ids in lines) if tint is not None else 1.0
        import imageio.v2 as imageio
        from PIL import Image
        frames = []
        nfr = 48
        tmp = os.path.join(OUT, "_f.png")
        for fr in range(nfr):
            t = tmax * fr / (nfr - 1)
            pts, cols = [], []
            for ids in lines:
                for lag in np.arange(0, 1.0, 0.1) * tmax:        # a train of tracers per streamline
                    tt = t - lag
                    if tt < 0: continue
                    k = int(np.searchsorted(tint[ids], tt))
                    if k >= len(ids): continue
                    pts.append(st.points[ids[k]]); cols.append(st.point_data["T"][ids[k]])
            pa = pv.Plotter(off_screen=True, window_size=(900, 760)); pa.set_background("white")
            copper(pa, g, 0.12)
            pa.add_mesh(st, color="#bbbbbb", opacity=0.25, line_width=1)
            if pts:
                cloud = pv.PolyData(np.array(pts)); cloud.point_data["T"] = np.array(cols)
                pa.add_mesh(cloud, scalars="T", cmap="coolwarm", clim=Tlim, point_size=9, render_points_as_spheres=True,
                            scalar_bar_args=dict(title="methanol T (°C)", color="black", fmt="%.3f"))
            camera(pa)
            pa.add_text(f"{lbl}, {flow:g} g/s: methanol tracers (inlet → outlet)", font_size=10, color="black")
            pa.screenshot(tmp); pa.close()
            frames.append(np.asarray(Image.open(tmp).convert("RGB")))
        imageio.mimsave(os.path.join(OUT, f"{name}_{flow:g}_flow.gif"), frames, duration=0.12, loop=0)
    # ----------------------------------------------------------------- 2-D path plots
    s = d["s"]; pid = d["pid"]
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(16, 4.6))
    for k in np.unique(pid):
        m = pid == k
        o = np.argsort(s[m])
        ss, TT, pp = s[m][o], d["Tf"][m][o], d["p"][m][o] / 1e3
        bins = np.linspace(ss.min(), ss.max(), max(2, int((ss.max() - ss.min()) / 4)))
        idx = np.digitize(ss, bins)
        sb = [ss[idx == i].mean() for i in np.unique(idx)]
        a.plot(sb, [TT[idx == i].mean() for i in np.unique(idx)], lw=1.2)
        b.plot(sb, [pp[idx == i].mean() for i in np.unique(idx)], lw=1.2)
    a.set_xlabel("distance along the passage, mm"); a.set_ylabel("methanol T (cross-section mean), °C"); a.set_title("Coolant warming along the path (CFD)", loc="left")
    b.set_xlabel("distance along the passage, mm"); b.set_ylabel("static pressure, kPa"); b.set_title("Pressure along the path (CFD)", loc="left")
    Tw = (d["Tw"] + 30) * 1e3
    im = c.pcolormesh(np.degrees(d["tc"]), d["zc"], Tw.T, cmap="RdBu_r", vmin=-150, vmax=150, shading="nearest")
    c.set_title(f"Inner wall from the CFD: spread {res['spread_mK']:.0f} mK", loc="left"); c.set_xlabel("θ, deg"); c.set_ylabel("z, mm")
    fig.colorbar(im, ax=c, label="T − T_set, mK")
    for ax in (a, b): ax.grid(color="#eee")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"{name}_{flow:g}_paths.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], float(sys.argv[3]))
