#!/usr/bin/env python3
"""2-D figures of the vapour run, laid out like SAHA_vapour_coupled_radiation.pptx (radiation left out)."""
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
CU, GL = "#c47a45", "#86a9c9"
REG = [("conn_lo", "lower connector wall", "#c0392b"), ("ice", "ice tray (bottom)", "#8b7a2b"),
       ("conn_mid", "middle connector wall", "#e08a2c"), ("top", "top wall + cap", "#7b4f9d")]


def bands(ax, horizontal=False):
    for z0, z1 in ((60, 187), (247, 365)):
        (ax.axhspan if not horizontal else ax.axvspan)(z0, z1, color="#f3e6dc", zorder=0)


def bc_model(room, fname):
    import matplotlib.patches as mp
    fig = plt.figure(figsize=(13, 6.8))
    ax0 = fig.add_axes([0.03, 0.06, 0.30, 0.86]); ax1 = fig.add_axes([0.42, 0.1, 0.25, 0.8]); ax2 = fig.add_axes([0.72, 0.1, 0.25, 0.8])
    R3 = 13.5 * 3
    ax0.add_patch(mp.Rectangle((-R3, 0), 2 * R3, 423.5, color="#eef3f8"))
    for z0, z1, c in ((0, 60, GL), (60, 187, CU), (187, 247, GL), (247, 365, CU), (365, 423.5, GL)):
        for s in (-1, 1):
            ax0.add_patch(mp.Rectangle((s * R3 - (6 if s > 0 else 0) + (0 if s > 0 else 0), z0), 6 * s if s < 0 else 6, z1 - z0, color=c))
    ax0.add_patch(mp.Rectangle((-R3 - 6, 423.5), 2 * R3 + 12, 6, color=GL))
    ax0.add_patch(mp.Rectangle((-R3 - 10, -5), 2 * R3 + 20, 5, color="#2a6db3"))
    lab = [(440, "cap: Robin"), (395, "Perspex wall: Robin"), (306, "copper inner wall\nfixed −30 °C"), (217, "Perspex wall: Robin"),
           (124, "copper inner wall\nfixed −15 °C"), (30, "Perspex wall: Robin\nq = G_out (T_ext − T_w)")]
    for z, t in lab:
        ax0.annotate(t, (R3 + 6, z if z < 430 else 426), xytext=(R3 + 30, z), fontsize=9, va="center",
                     arrowprops=dict(arrowstyle="-", color="#999", lw=0.6))
    for z in (0, 60, 187, 247, 365, 423.5):
        ax0.text(-R3 - 14, z, f"{z:g}", ha="right", va="center", fontsize=8, color="#666")
    ax0.text(0, 212, "R134a vapour\n84.4 kPa\nρ = const\n(Boussinesq)", ha="center", va="center", fontsize=9)
    ax0.text(0, -22, "ice tray 0 °C (fixed)", ha="center", color="#2a6db3", fontsize=10, weight="bold")
    ax0.annotate("", (-R3 - 40, 140), (-R3 - 40, 190), arrowprops=dict(arrowstyle="->"))
    ax0.text(-R3 - 46, 165, "g", ha="right", fontsize=11)
    ax0.set_xlim(-R3 - 70, R3 + 150); ax0.set_ylim(-30, 450); ax0.axis("off")
    ax0.set_title("Vapour column Ø27 × 423.5 mm (radius drawn ×3), z in mm", fontsize=10, loc="left")
    w = room.vf_kind == "wall"
    z = room.vf_pos[w]
    for seg in ((0, 60), (187, 247), (365, 424)):
        m = (z > seg[0]) & (z < seg[1])
        ax1.plot(room.T_ext0[w][m], z[m], color="#a52a2a", lw=1.6, label="T_ext (environment seen by the wall)" if seg[0] == 0 else None)
        ax2.plot(room.G_out[w][m], z[m], color="#1f5fa8", lw=1.6)
    bands(ax1); bands(ax2)
    ax1.set_xlabel("°C"); ax1.set_ylabel("z (mm)"); ax1.set_title("Perspex walls: outside temperature", loc="left", fontsize=10)
    ax1.legend(fontsize=8, frameon=False, loc="upper left")
    ax2.set_xscale("log"); ax2.set_xlabel("G_out (W/m²K), log scale"); ax2.set_title("Perspex walls: outside conductance", loc="left", fontsize=10)
    ax2.text(0.97, 0.05, "both from this room / insulation model\n(collective response to the vapour +1 K)", transform=ax2.transAxes,
             ha="right", fontsize=8, color="#666")
    for a in (ax1, ax2):
        a.set_ylim(0, 424); a.grid(color="#eee")
    fig.savefig(fname, dpi=170); plt.close(fig)


def midplane(run, fname):
    c = np.load(os.path.join(run, "conduction.npz"))
    m = np.load(os.path.join(run, "mean_2.npz"))
    last = np.load(sorted(glob.glob(os.path.join(run, "snap_*.npz")))[-1])
    xc, zc, sec = c["xc"] * 1e3, c["zc"] * 1e3, c["sec"]
    jm = len(xc) // 2
    panels = [(c["T"][:, jm, :], "T, conduction only\n(vapour still)", "T"),
              (m["T"][:, jm, :], "T, time mean\n(convecting, 85–120 s)", "T"),
              (last["Tmid"], f"T, one instant\n(t = {float(last['t']):.0f} s)", "T"),
              (m["w"][:, jm, :], "w, time mean", "w"), (last["wmid"], "w, one instant", "w")]
    fig, axes = plt.subplots(1, 5, figsize=(16, 8.4), sharey=True)
    for ax, (F, title, kind) in zip(axes, panels):
        F = np.where(sec[:, jm][:, None], F, np.nan)
        if kind == "T":
            im = ax.pcolormesh(xc, zc, F.T, cmap="coolwarm", vmin=-30, vmax=5, shading="nearest")
            ax.contour(xc, zc, F.T, levels=np.arange(-30, 5, 2.5), colors="k", linewidths=0.3, linestyles="--")
            imT = im
        else:
            im = ax.pcolormesh(xc, zc, F.T, cmap="RdBu_r", vmin=-0.1, vmax=0.1, shading="nearest"); imW = im
        for z0, z1, col in ((0, 60, GL), (60, 187, CU), (187, 247, GL), (247, 365, CU), (365, 423.5, GL)):
            for s in (-1, 1):
                ax.add_patch(plt.Rectangle((s * 13.5 + (0 if s > 0 else -1.5), z0), 1.5, z1 - z0, color=col))
        ax.set_xlim(-15.5, 15.5); ax.set_ylim(0, 423.5); ax.set_title(title, fontsize=10)
        ax.set_xticks([-13.5, 0, 13.5]); ax.set_xlabel("x (mm)")
    axes[0].set_ylabel("z (mm)")
    fig.colorbar(imT, ax=axes[:3], shrink=0.8, label="T (°C)", pad=0.01)
    fig.colorbar(imW, ax=axes[3:], shrink=0.8, label="vertical velocity w (m/s)", pad=0.01)
    fig.suptitle("Mid-plane through the vapour column (width drawn ~7× true scale); copper bands = Zones 2 and 1", fontsize=10, x=0.02, ha="left", color="#555")
    fig.savefig(fname, dpi=150, bbox_inches="tight"); plt.close(fig)


def smooth(y, n=5):
    k = np.ones(n) / n
    return np.convolve(y, k, mode="same")


def history(run, fname, t0=0.0, t1=120.0, win=(85, 120)):
    H = json.load(open(os.path.join(run, "history.json")))["hist"]
    t = np.array([h["t"] for h in H])
    sel = (t >= t0) & (t <= t1)
    get = lambda k: np.array([h[k] for h in H])
    top = get("top_wall") + get("cap")
    fig, (a, b) = plt.subplots(1, 2, figsize=(15, 5))
    for key, lab, col in REG:
        y = top if key == "top" else get(key)
        a.plot(t[sel], smooth(y)[sel], color=col, lw=0.9, label=lab)
        mw = (t >= win[0]) & (t <= win[1])
        mean = y[mw].mean()
        a.plot(win, [mean, mean], color=col, lw=3); a.text(win[1] + 0.8, mean, f"{mean:.0f}", color=col, weight="bold", va="center")
    for key, lab, col, sgn in (("z2", "Zone 2 inner wall", "#2aa198", -1), ("z1", "Zone 1 inner wall", "#2a6db3", -1)):
        y = sgn * get(key)
        b.plot(t[sel], smooth(y)[sel], color=col, lw=0.9, label=lab)
        mw = (t >= win[0]) & (t <= win[1]); mean = y[mw].mean()
        b.plot(win, [mean, mean], color=col, lw=3); b.text(win[1] + 0.8, mean, f"{mean:.0f}", color=col, weight="bold", va="center")
    st = get("storage")
    b.plot(t[sel], smooth(-st)[sel], color="#888", lw=0.8, label="net out of the vapour (storage change)")
    for ax, tt in ((a, "Heat INTO the vapour (sources), mW"), (b, "Heat from the vapour INTO the copper, mW")):
        ax.axvspan(*win, color="#f0f0f0", zorder=0); ax.axhline(0, color="#aaa", lw=0.6)
        ax.text(np.mean(win), ax.get_ylim()[0] if False else 0, "", fontsize=8)
        ax.set_title(tt, loc="left", fontsize=11); ax.set_xlabel("time (s)"); ax.legend(fontsize=8, ncol=2, frameon=False, loc="upper left")
        ax.set_xlim(t0, t1 + 6); ax.grid(color="#eee")
    fig.tight_layout(); fig.savefig(fname, dpi=150); plt.close(fig)


def coupling(run, room, fname):
    H = json.load(open(os.path.join(run, "history.json")))
    cp = H["coupling"]
    import vapour3d as v3
    m = np.load(os.path.join(run, "mean_2.npz"))
    col = v3.Column(1.0)
    # Perspex inner-wall temperature: one-way (no vapour heat) vs coupled (room solved with the 85-120 s vapour heat)
    T_ext = None
    w = room.vf_kind == "wall"
    T = m["T"].astype(float)
    Tw_one = room.T_ext0
    # vapour heat into each layer from the time-mean field with the final T_ext
    last_cp = cp[-1]
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(15, 6.2), gridspec_kw=dict(width_ratios=[1, 1, 1.15]))
    zr = room.vf_pos[w]
    # coupled wall temperature: the time-mean vapour field drawn through the room model with the same band
    # exchange as the run (vapour/bands.py), iterated to its fixed point
    import bands as bandmod
    band, nb = bandmod.make_bands(room)
    T_ext = room.T_ext0.copy()
    for it in range(40):
        col.set_bc(*v3.room_bc(col, room, T_ext))
        _, lat, capq = col.wall_heat(T)
        qv = v3.layer_heat_to_faces(col, room, lat, capq)
        T_ext, Tsol, Tw_room, qf = bandmod.exchange(room, band, nb, T_ext, qv, 0.5)
    Tw_cpl = Tw_room[w]
    coupling.result = dict(zone_room=room.zone_heat(Tsol), q_pmma_mW=float(qf.sum() * 1e3),
                           dT_lo=float((Tw_room - Tw_one)[w & (room.vf_pos < 60)].mean()),
                           dT_mid=float((Tw_room - Tw_one)[w & (room.vf_pos > 187) & (room.vf_pos < 247)].mean()),
                           dT_top=float((Tw_room - Tw_one)[w & (room.vf_pos > 365)].mean()),
                           T_cap_one=float(np.average(room.T_ext0[~w], weights=room.vf_A[~w])),
                           T_cap_cpl=float(np.average(Tw_room[~w], weights=room.vf_A[~w])))
    for seg in ((0, 60), (187, 247), (365, 424)):
        mm = (zr > seg[0]) & (zr < seg[1])
        a.plot(Tw_one[w][mm], zr[mm], "--", color="#666", label="one-way (vapour still)" if seg[0] == 0 else None)
        if Tw_cpl is not None:
            a.plot(Tw_cpl[mm], zr[mm], color="#b03a2e", lw=2, label="two-way coupled (no radiation)" if seg[0] == 0 else None)
            b.plot(Tw_cpl[mm] - Tw_one[w][mm], zr[mm], ".", color="#b03a2e", ms=3)
    bands(a); bands(b); a.set_ylim(0, 424); b.set_ylim(0, 424)
    a.set_xlabel("Perspex inner-wall temperature (°C)"); a.set_ylabel("z (mm)"); a.legend(fontsize=8, frameon=False)
    a.set_title("Perspex walls facing the vapour", loc="left", fontsize=10)
    b.axvline(0, color="#999", lw=0.6); b.set_xlabel("change from one-way (K)"); b.set_title("Change of the wall temperature", loc="left", fontsize=10)
    tt = [x["t"] for x in cp]
    c.plot(tt, [x["q_pmma_mW"] for x in cp], color="#e08a2c", label="heat drawn from the Perspex walls (mW)")
    c2 = c.twinx()
    c2.plot(tt, [x["T_ext_conn_mean"] for x in cp], color="#b03a2e", label="mean T_ext of the connector walls (°C)")
    c2.plot(tt, [x["T_cap"] for x in cp], color="#7fa7cf", label="cap T_ext (°C)")
    c.set_xlabel("time (s)"); c.set_ylabel("mW"); c2.set_ylabel("°C")
    c.set_title("Exchanges (every 1 s, smoothed 5 s)", loc="left", fontsize=10)
    h1, l1 = c.get_legend_handles_labels(); h2, l2 = c2.get_legend_handles_labels()
    c.legend(h1 + h2, l1 + l2, fontsize=8, frameon=False, loc="center right")
    for ax in (a, b, c): ax.grid(color="#eee")
    fig.tight_layout(); fig.savefig(fname, dpi=150); plt.close(fig)


if __name__ == "__main__":
    import room as roommod
    run = sys.argv[1]; out = sys.argv[2]
    rm = roommod.Room()
    which = sys.argv[3] if len(sys.argv) > 3 else "all"
    if which in ("all", "bc"): bc_model(rm, os.path.join(out, "v_bc_model.png"))
    if which in ("coupling",):
        coupling(run, rm, os.path.join(out, "v_coupling.png"))
        json.dump(coupling.result, open(os.path.join(run, "coupling_result.json"), "w"), indent=1)
    if which in ("all",):
        midplane(run, os.path.join(out, "v_midplane.png"))
        history(run, os.path.join(out, "v_history_0_60.png"), 0, 60, (25, 60))
        history(run, os.path.join(out, "v_history_60_120.png"), 60, 120, (85, 120))
        coupling(run, rm, os.path.join(out, "v_coupling.png"))
        json.dump(coupling.result, open(os.path.join(run, "coupling_result.json"), "w"), indent=1)
    print("done")
