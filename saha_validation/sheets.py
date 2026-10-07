#!/usr/bin/env python3
"""One result sheet per layout and flow, laid out like SAHA_layout_result_sheets.pdf, from the re-validation model.
Panel (c) puts the original sheet's number next to the new one.  Writes figs/sheets/<layout>_<flow>.png and a PDF."""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

from reference import SHEETS, NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def sheet(res, fld, fname, title_extra=""):
    d = np.load(fld)
    name, flow = res["layout"], res["m_gs"]
    ref = SHEETS[name][5 if flow == 5.0 else 17.5]
    tc, zc, rc = np.degrees(d["tc"]), d["zc"], d["rc"]
    mat, node, Tn = d["mat"], d["node"], d["Tnode"]
    pnames, npid, ns = d["pnames"], d["nodes_pid"], d["nodes_s"]
    fig = plt.figure(figsize=(16.5, 10.4))
    fig.text(0.05, 0.965, f"Layout {('A*' if name == 'A_built' else name)} — {NAMES[name].split(' ', 1)[1]}", fontsize=18, weight="bold")
    fig.text(0.05, 0.94, f"Zone 1 · total coolant flow {flow:g} g/s · heat {res['Q_W']:.2f} W · inlet {res['inlet_C']:.3f} °C · "
             f"{res['cells']:,} cells · re-validation model {title_extra}", fontsize=11, color="#555")
    fig.text(0.95, 0.965, f"Sheet {('A*' if name == 'A_built' else name)}-{flow:g}", ha="right", fontsize=11, color="#555")
    # (a) passages unrolled: coolant temperature of the outermost-in-r fluid cell in each (theta, z) column
    ax = fig.add_axes([0.05, 0.53, 0.26, 0.36])
    fl = mat == 3
    Tcell = np.where(fl, Tn[np.clip(node, 0, None)], np.nan)
    with np.errstate(all="ignore"):
        A = np.nanmean(Tcell, axis=0)
    im = ax.pcolormesh(tc, zc, A.T, cmap="RdBu_r", shading="nearest")
    ax.set_facecolor("#f1f3f5")
    ax.axhline(0, color="k", ls="--", lw=0.8); ax.axhline(96, color="k", ls="--", lw=0.8)
    ax.text(2, 98, "upper end plate", fontsize=8, color="#555"); ax.text(2, -8, "lower end plate", fontsize=8, color="#555")
    ax.set_xlim(0, 360); ax.set_ylim(-11, 107); ax.set_xticks(range(0, 361, 45))
    ax.set_xlabel("angle round the zone θ, deg (unrolled)"); ax.set_ylabel("height z, mm (0 = top of lower plate)")
    ax.set_title("(a) Coolant passages as meshed — coolant temperature", loc="left", weight="bold")
    fig.colorbar(im, ax=ax, label="coolant, °C", pad=0.02)
    # (b) inner wall map
    ax = fig.add_axes([0.40, 0.53, 0.26, 0.36])
    Tw = (d["Tw"] + 30.0) * 1e3
    im = ax.pcolormesh(tc, zc, Tw.T, cmap="RdBu_r", vmin=-150, vmax=150, shading="nearest")
    cs = ax.contour(tc, zc, Tw.T, levels=np.arange(-60, 61, 20), colors="k", linewidths=0.6)
    ax.clabel(cs, fontsize=7, fmt="%d")
    i, j = np.unravel_index(np.argmax(Tw), Tw.shape); ax.plot(tc[i], zc[j], "k^", ms=8); ax.annotate(f"max {Tw.max():+.0f} mK", (tc[i], zc[j]), xytext=(6, 4), textcoords="offset points", fontsize=8, bbox=dict(fc="w", ec="none", alpha=0.7))
    i, j = np.unravel_index(np.argmin(Tw), Tw.shape); ax.plot(tc[i], zc[j], "kv", ms=8); ax.annotate(f"min {Tw.min():+.0f} mK", (tc[i], zc[j]), xytext=(6, 4), textcoords="offset points", fontsize=8, bbox=dict(fc="w", ec="none", alpha=0.7))
    ax.axhline(0, color="k", ls="--", lw=0.8); ax.axhline(96, color="k", ls="--", lw=0.8)
    ax.set_xticks(range(0, 361, 45)); ax.set_xlabel("angle round the zone θ, deg (unrolled)"); ax.set_ylabel("height z, mm")
    ax.set_title("(b) Inner copper surface r = 13.5 mm — deviation from −30 °C", loc="left", weight="bold")
    fig.colorbar(im, ax=ax, label="T − T_set, mK (band ±150)", pad=0.02)
    # (c) results table: sheet vs this model
    ax = fig.add_axes([0.73, 0.53, 0.25, 0.36]); ax.axis("off")
    win = res["window"]
    rows = [("Quantity", "Sheet", "This model"),
            ("Coolant inlet (centres the wall)", f"{ref[1]:.3f} °C", f"{res['inlet_C']:.3f} °C"),
            ("Allowed inlet window, °C", f"{ref[1] - ref[6] / 1e3:.2f}…{ref[1] + ref[6] / 1e3:.2f}", f"{win[0]:.2f}…{win[1]:.2f}"),
            ("Inner-wall spread", f"{ref[0]:.1f} mK", f"{res['spread_mK']:.1f} mK"),
            ("Margin inside ±0.15 K", f"{ref[6]:.1f} mK", f"{res['margin_mK']:.1f} mK"),
            ("Spread at 5 W (same pattern)", f"{ref[7]} mK" if ref[7] else "—", f"{res['spread_mK'] * 5 / res['Q_W']:.0f} mK"),
            ("Coolant rise, mixed outlet", f"{64 if flow > 6 else 225} mK", f"{res['rise_mK']:.0f} mK"),
            ("Pressure drop, worst path", f"{ref[2]:.2f} kPa", f"{res['dp_kPa']:.2f} kPa*"),
            ("Reynolds number, passages", f"{ref[4]} – {ref[5]}", f"{res['Re'][0]:.0f} – {res['Re'][1]:.0f}"),
            ("Coolant–copper UA", f"{ref[3]:.1f} W/K", f"{res['UA_WK']:.1f} W/K"),
            ("Energy balance error", "", f"{res['energy_balance_W']:.1e} W")]
    tb = ax.table(cellText=[r for r in rows[1:]], colLabels=rows[0], loc="upper center", cellLoc="left", colWidths=[0.52, 0.26, 0.26])
    tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.55)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor("#ccd3db")
        if r == 0: cell.set_facecolor("#eef2f6"); cell.set_text_props(weight="bold")
        if r in (3, 4) and c > 0: cell.set_text_props(color="#b3631b", weight="bold")
    ax.set_title("(c) Results — sheet against this model", loc="left", weight="bold")
    ax.text(0, 0.02, "* friction of developed flow only (no bends / fittings)", fontsize=7.5, color="#666", transform=ax.transAxes)
    dsp = res["spread_mK"] - ref[0]; din = (res["inlet_C"] - ref[1]) * 1e3
    verdict = "SAME" if abs(dsp) <= 5 and abs(din) <= 20 else ("CLOSE" if abs(dsp) <= 13 and abs(din) <= 120 else "DIFFERS")
    col = {"SAME": "#2e8b57", "CLOSE": "#a86a12", "DIFFERS": "#c0392b"}[verdict]
    ax.text(0, -0.08, f"Δ spread {dsp:+.1f} mK · Δ inlet {din:+.0f} mK → {verdict}", fontsize=11, weight="bold", color=col, transform=ax.transAxes)
    # (d) coolant temperature along each passage
    ax = fig.add_axes([0.05, 0.08, 0.26, 0.36])
    cmap = plt.get_cmap("tab10")
    named = {}
    for pid, pn in enumerate(pnames):
        base = str(pn).split("_col")[0]
        named.setdefault(base, []).append(pid)
    shown = 0
    for k, (base, pids) in enumerate(named.items()):
        if shown >= 12: break
        pid = pids[0]
        m = npid == pid
        if "supply" in base or "return" in base or "ring_" in base:
            continue                                   # manifold arms: dead-end stubs drift to the wall temperature
        ax.plot(ns[m], Tn[m], color=cmap(k % 10), lw=1.4, label=base)
        shown += 1
    ax.legend(fontsize=7, ncol=2, frameon=False, loc="upper left")
    ax.set_xlabel("distance along the passage from its inlet node, mm"); ax.set_ylabel("coolant temperature, °C")
    ax.set_title("(d) Coolant temperature along each named passage", loc="left", weight="bold"); ax.grid(color="#eee")
    # (e) r-z section at theta index 0 (copper T, passages navy, foam/outside white)
    ax = fig.add_axes([0.40, 0.08, 0.26, 0.36])
    Ts = (d["Tsec"] + 30.0) * 1e3
    ms = mat[:, 0, :]
    Tp = np.where(ms == 1, Ts, np.nan)
    im = ax.pcolormesh(zc, rc, Tp, cmap="RdBu_r", vmin=-np.nanmax(abs(Tp)), vmax=np.nanmax(abs(Tp)), shading="nearest")
    ax.pcolormesh(zc, rc, np.ma.masked_where(ms != 3, np.ones_like(Ts)), cmap=matplotlib.colors.ListedColormap(["#0b2545"]), shading="nearest")
    ax.axhline(13.5, color="k", lw=0.8)
    ax.set_ylim(13.5, 43); ax.set_xlim(-11, 107)
    ax.set_xlabel("height z, mm"); ax.set_ylabel("radius r, mm")
    ax.set_title(f"(e) Section at θ = {tc[0]:.0f}° — copper T (passages navy)", loc="left", weight="bold")
    fig.colorbar(im, ax=ax, label="T − T_set, mK", pad=0.02)
    # (f) inner wall along the height
    ax = fig.add_axes([0.73, 0.08, 0.22, 0.36])
    lo, hi, av = [(np.array(res[k]) + 30) * 1e3 for k in ("wall_min", "wall_max", "wall_avg")]
    z = np.array(res["wall_profile_z"])
    ax.axvspan(-150, 150, color="#efefea")
    ax.fill_betweenx(z, lo, hi, color="#e7b98f", alpha=0.7, label="min–max round the zone")
    ax.plot(av, z, color="#b3631b", lw=1.6, label="average round the zone")
    ax.axhline(0, color="k", ls="--", lw=0.8); ax.axhline(96, color="k", ls="--", lw=0.8)
    ax.set_xlim(-160, 160); ax.set_xlabel("inner wall T − T_set, mK (grey = ±150 band)"); ax.set_ylabel("height z, mm")
    ax.legend(fontsize=7.5, loc="lower right", frameon=False)
    ax.set_title("(f) Inner wall along the height", loc="left", weight="bold")
    fig.text(0.05, 0.015, "Model: 3-D finite-volume conduction (copper wall r 13.5–15, carrier / buffer, end plates) coupled to a 1-D coolant network (developed-flow h), "
             "AMG-preconditioned GMRES. Basis: Zone 1, set point −30 °C, heat from the axisymmetric chamber model scaled to the sheet's total, methanol at −30 °C.",
             fontsize=8, color="#555", wrap=True)
    fig.savefig(fname, dpi=110); plt.close(fig)
    return verdict


def inlet_chart(results, fname):
    order = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), sharey=True)
    for ax, flow in zip(axes, (17.5, 5.0)):
        for i, k in enumerate(order):
            r = [x for x in results if x["layout"] == k and x["m_gs"] == flow][0]
            ref = SHEETS[k][5 if flow == 5.0 else 17.5]
            y = len(order) - i
            ax.plot([ref[1] - ref[6] / 1e3, ref[1] + ref[6] / 1e3], [y + 0.15] * 2, color="#9aa3ad", lw=6, solid_capstyle="butt")
            ax.plot([r["window"][0], r["window"][1]], [y - 0.15] * 2, color="#2a6fdb" if flow > 6 else "#e8743b", lw=6, solid_capstyle="butt")
            ax.plot(ref[1], y + 0.15, "k|", ms=10); ax.plot(r["inlet_C"], y - 0.15, "k|", ms=10)
        ax.set_yticks(range(len(order), 0, -1)); ax.set_yticklabels(["A*" if k == "A_built" else k for k in order])
        ax.set_title(f"{flow:g} g/s: allowed inlet window (grey = sheet, colour = this model; tick = centre)", loc="left", fontsize=10)
        ax.set_xlabel("coolant inlet temperature, °C"); ax.grid(axis="x", color="#eee")
        ax.axvline(-31.5, color="#c0392b", lw=1, ls="--"); ax.text(-31.48, 0.5, "−31.5 °C (old setting)", color="#c0392b", fontsize=8)
        ax.set_xlim(-31.6, -29.9)
    fig.tight_layout(); fig.savefig(fname, dpi=150); plt.close(fig)


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "base"
    res = json.load(open(os.path.join(HERE, "results", f"layouts_{tag}.json")))
    out = os.path.join(HERE, "figs", "sheets"); os.makedirs(out, exist_ok=True)
    order = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"]
    pdf = PdfPages(os.path.join(HERE, "figs", "result_sheets_revalidated.pdf"))
    verdicts = {}
    for k in order:
        for flow in (17.5, 5.0):
            r = [x for x in res if x["layout"] == k and x["m_gs"] == flow][0]
            fld = os.path.join(HERE, "results", f"field_{tag}_{k}_{flow:g}.npz")
            png = os.path.join(out, f"{k}_{flow:g}.png")
            verdicts[f"{k}_{flow:g}"] = sheet(r, fld, png)
            img = plt.imread(png); f2 = plt.figure(figsize=(16.5, 10.4)); a2 = f2.add_axes([0, 0, 1, 1]); a2.imshow(img); a2.axis("off"); pdf.savefig(f2, dpi=110); plt.close(f2)
            print(k, flow, verdicts[f"{k}_{flow:g}"], flush=True)
    pdf.close()
    inlet_chart(res, os.path.join(HERE, "figs", "inlet_validation.png"))
    json.dump(verdicts, open(os.path.join(HERE, "results", "sheet_verdicts.json"), "w"), indent=1)
