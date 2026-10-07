#!/usr/bin/env python3
"""Run the 3-D layout model for every layout and flow; write results/layouts_<tag>.json and field files.

    python run_layouts.py [tag] [layout ...] [--dr 0.5 --dz 0.5 --nt 180 --fric --vapour]
"""
import argparse
import json
import os
import time

import numpy as np

import cht3d
import heatload_axi
import layouts
import props

HERE = os.path.dirname(os.path.abspath(__file__))
_axi_cache = {}
VAPOUR_LOW = [False]
VAPOUR_MAP = [None]       # npz with theta (rad), z (mm local), q (W/m2) and Q (W) from the vapour CFD     # True: put the vapour heat on the lowest 30 mm of the Zone-1 bore instead of spreading it


def axi_split(R_band):
    if R_band not in _axi_cache:
        _axi_cache[R_band] = heatload_axi.solve(R_band=R_band)
    return _axi_cache[R_band]


def node_dp(mdl):
    out = np.zeros(len(mdl.nodes_m))
    for p in mdl.passages:
        n = p["last"] - p["first"] + 1
        for nd in range(p["first"], p["last"] + 1):
            out[nd] = p["dp"] * (1.0 / n) * (mdl.nodes_m[nd] / p["m"])
    return out


def worst_path_dp(mdl, dpn):
    # longest path to each node through the upstream graph (nodes are created in topological order except galleries)
    best = np.full(len(dpn), -1.0)
    import sys
    sys.setrecursionlimit(100000)
    def get(i):
        if best[i] >= 0:
            return best[i]
        ups = [j for j, _ in mdl.nodes_up[i]]
        best[i] = dpn[i] + (max(get(j) for j in ups) if ups else 0.0)
        return best[i]
    return max(get(n) for n, _ in mdl.outlets)


def run(name, m_tot, dr=0.5, dz=0.5, nt=180, fric=False, vapour=0.0, Q=None, save=None):
    t0 = time.time()
    g, mdl = layouts.build(name, m_tot, dr, dz, nt)
    R_band = {"A_built": 25.1, "B": 32.0}.get(name, 27.0)
    axi = axi_split(R_band)
    Qt = Q if Q is not None else mdl.Q_sheet
    flux = cht3d.apply_flux(mdl, axi["surf"], Qt)
    if VAPOUR_MAP[0] is not None:
        # time-mean convective heat from the 3-D vapour run onto the Zone-1 bore, q(theta, z) in W/m2
        vm = np.load(VAPOUR_MAP[0])
        ids, w = flux["bore"]
        th = g.T.ravel()[ids]; zz = g.Z.ravel()[ids]
        from scipy.interpolate import RegularGridInterpolator
        f = RegularGridInterpolator((vm["theta"], vm["z"]), vm["q"], bounds_error=False, fill_value=None)
        A = g.R.ravel()[ids] * 1e-3 * g.dt * g.dz[np.unravel_index(ids, g.shape)[2]] * 1e-3
        add = f(np.c_[th, zz]) * A
        add *= float(vm["Q"]) / add.sum()
        flux["bore"] = (ids, w + add)
    if vapour:
        # extra heat from vapour convection + bore radiation, spread over the bore as the coupled model's 3-D result
        ids, w = flux["bore"]
        if VAPOUR_LOW[0]:
            zz = g.Z.ravel()[ids]
            sel = (zz < 19.0) & (zz > -11.0)
            add = np.where(sel, w, 0.0)
        else:
            add = w
        flux["bore"] = (ids, w + vapour * add / add.sum())
    mdl.assemble(flux)
    dpn = node_dp(mdl)
    qf = dpn * np.array(mdl.nodes_m) / props.RHO if fric else None
    Tc, Tn = mdl.solve(0.0, q_fric=qf)
    Tw = cht3d.inner_wall(mdl, flux)
    tmax, tmin = float(Tw.max()), float(Tw.min())
    spread = tmax - tmin
    shift = -30.0 - 0.5 * (tmax + tmin)
    mout = sum(m for _, m in mdl.outlets)
    Tout = sum(m * Tn[n] for n, m in mdl.outlets) / mout
    res = dict(layout=name, m_gs=m_tot * 1e3, Q_W=float(sum(v[1].sum() for v in flux.values())),
               spread_mK=spread * 1e3, inlet_C=shift, window=[shift - (0.15 - spread / 2), shift + (0.15 - spread / 2)],
               margin_mK=(0.15 - spread / 2) * 1e3, rise_mK=Tout * 1e3, dp_kPa=worst_path_dp(mdl, dpn) / 1e3,
               UA_WK=float(mdl.Gc.sum()), Re=[float(min(p["Re"] for p in mdl.passages)), float(max(p["Re"] for p in mdl.passages))],
               Q_fric_W=float(qf.sum()) if qf is not None else 0.0,
               cells=int(g.N), active=int(mdl.nc), nodes=int(mdl.nn), solve=mdl.solve_info, seconds=time.time() - t0,
               passages=[{k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in p.items()
                          if k in ("name", "L", "m", "h", "h_eff", "Re", "f", "dp", "UA", "ncell")} for p in mdl.passages],
               wall_profile_z=g.zc.tolist(), wall_avg=(Tw.mean(axis=0) + shift).tolist(),
               wall_min=(Tw.min(axis=0) + shift).tolist(), wall_max=(Tw.max(axis=0) + shift).tolist())
    # energy balance: heat in = coolant enthalpy rise (+ friction)
    res["energy_balance_W"] = float(props.CP * mout * Tout - res["Q_W"] - res["Q_fric_W"])
    if save:
        np.savez_compressed(save, Tw=Tw + shift, tc=g.tc, zc=g.zc, rc=g.rc, mat=mdl.mat, node=mdl.node,
                            Tnode=Tn + shift, Tsec=Tc[:, 0, :] + shift, Tsec_mid=Tc[:, g.shape[1] // 4, :] + shift,
                            nodes_pid=np.array(mdl.nodes_pid), nodes_s=np.array(mdl.nodes_s),
                            pnames=np.array([p["name"] for p in mdl.passages]))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("layouts", nargs="*")
    ap.add_argument("--dr", type=float, default=0.5); ap.add_argument("--dz", type=float, default=0.5)
    ap.add_argument("--nt", type=int, default=180); ap.add_argument("--fric", action="store_true")
    ap.add_argument("--vapour", type=float, default=0.0); ap.add_argument("--flows", default="17.5,5")
    ap.add_argument("--Q", type=float, default=None); ap.add_argument("--fields", action="store_true")
    ap.add_argument("--hscale", type=float, default=1.0); ap.add_argument("--turb", action="store_true")
    ap.add_argument("--jacket_nu", type=float, default=None); ap.add_argument("--vapour_map", default=None); ap.add_argument("--vapour_low", action="store_true")
    a = ap.parse_args()
    props.H_SCALE = a.hscale; props.TURB_STRAIGHT = a.turb
    if a.jacket_nu: layouts.JACKET_NU[0] = a.jacket_nu
    VAPOUR_LOW[0] = a.vapour_low
    VAPOUR_MAP[0] = a.vapour_map
    names = a.layouts or layouts.LAYOUTS
    out = os.path.join(HERE, "results", f"layouts_{a.tag}.json")
    allres = json.load(open(out)) if os.path.exists(out) else []
    for nm in names:
        for mf in [float(x) for x in a.flows.split(",")]:
            save = os.path.join(HERE, "results", f"field_{a.tag}_{nm}_{mf:g}.npz") if a.fields else None
            r = run(nm, mf * 1e-3, a.dr, a.dz, a.nt, a.fric, a.vapour, a.Q, save)
            allres = [x for x in allres if not (x["layout"] == nm and x["m_gs"] == r["m_gs"])] + [r]
            json.dump(allres, open(out, "w"), indent=1)
            print(f"{nm:8s} {mf:5.1f} g/s  spread {r['spread_mK']:6.1f} mK  inlet {r['inlet_C']:.3f}  dp {r['dp_kPa']:6.2f} kPa"
                  f"  UA {r['UA_WK']:5.1f}  Re {r['Re'][0]:.0f}-{r['Re'][1]:.0f}  rise {r['rise_mK']:.0f} mK"
                  f"  bal {r['energy_balance_W']:.1e}  it {r['solve']['iters']} res {r['solve']['rel_res']:.1e}"
                  f"  cells {r['cells']}  {r['seconds']:.0f}s", flush=True)
