#!/usr/bin/env python3
"""Independent axisymmetric conduction model of the SAHA upper chamber -> heat gain of each copper zone.

Geometry (mm, z = 0 at the ice tray), taken from SAHA_cold_zone_simulations.pptx slide 25 and FLUENT_SETUP.md section 2:
  vapour r < 13.5, z 0-423.5 ; Perspex wall r 13.5-15 (connectors) and cap r < 15, z 423.5-425
  Zone 2 copper z 60-187, Zone 1 copper z 247-365: wall r 13.5-15, band r 15-R_band, plates r 13.5-43 x 11 mm at each end
  foam everything else out to r = 13.5+... = 93 and up to z = 475 (50 mm beyond the 43 mm plates / 425 mm top)
BCs: z = 0 at 0 C (ice tray + opening), outer foam surfaces Robin h to T_lab, copper held at its set point.
Copper is a Dirichlet region; the heat gain is the conductive flux into it. Also returns the flux distribution
on the Zone 1 copper surfaces for the 3-D layout model.
"""
import json
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K = dict(vap=0.0096, pmma=0.19, foam=0.035, cu=390.0)


def axis(breaks, dmax):
    pts = [breaks[0]]
    for a, b in zip(breaks[:-1], breaks[1:]):
        n = max(1, int(np.ceil((b - a) / dmax - 1e-9)))
        pts += list(np.linspace(a, b, n + 1)[1:])
    return np.array(pts)


def solve(R_band=25.1, h=8.0, T_lab=35.0, k_foam=0.035, r_out=93.0, z_out=475.0, k_vap=0.0096,
          d=0.5, Tz=(-15.0, -30.0), k_vap_eff=None):
    rb = sorted({0, 13.5, 15, R_band, 43, r_out})
    zb = sorted({0, 60, 71, 176, 187, 247, 258, 354, 365, 423.5, 425, z_out})
    rf = axis(rb, d) * 1e-3
    zf = axis(zb, d) * 1e-3
    rc, zc = 0.5 * (rf[1:] + rf[:-1]), 0.5 * (zf[1:] + zf[:-1])
    nr, nz = len(rc), len(zc)
    R, Z = np.meshgrid(rc * 1e3, zc * 1e3, indexing="ij")
    k = np.full((nr, nz), k_foam)
    mat = np.full((nr, nz), 3)                                       # 0 vap 1 pmma 2 cu 3 foam
    vap = (R < 13.5) & (Z < 423.5)
    k[vap] = k_vap; mat[vap] = 0
    pm = ((R > 13.5) & (R < 15) & (Z < 425)) | ((R < 15) & (Z > 423.5) & (Z < 425))
    k[pm] = K["pmma"]; mat[pm] = 1
    if k_vap_eff is not None:                                        # optional effective conductivity per z-band
        for (z0, z1), kk in k_vap_eff.items():
            m = vap & (Z > z0) & (Z < z1); k[m] = kk
    zone = np.zeros((nr, nz), int)
    for iz, (z0, z1) in enumerate([(60, 187), (247, 365)], start=1):
        cu = (Z > z0) & (Z < z1) & (R > 13.5) & ((R < R_band) | (R < 43) & ((Z < z0 + 11) | (Z > z1 - 11)))
        k[cu] = K["cu"]; mat[cu] = 2; zone[cu] = iz
    Tfix = {1: Tz[0], 2: Tz[1]}
    N = nr * nz
    idx = np.arange(N).reshape(nr, nz)
    dr, dz = np.diff(rf), np.diff(zf)
    rows, cols, vals = [], [], []
    b = np.zeros(N)
    diag = np.zeros(N)
    # radial faces between i and i+1
    rface = rf[1:-1]
    Gr = 2 * np.pi * rface[:, None] * dz[None, :] / (0.5 * dr[:-1, None] / k[:-1] + 0.5 * dr[1:, None] / k[1:])
    # axial faces
    Az = np.pi * (rf[1:] ** 2 - rf[:-1] ** 2)
    Gz = Az[:, None] / (0.5 * dz[None, :-1] / k[:, :-1] + 0.5 * dz[None, 1:] / k[:, 1:])
    def link(a, bb, G):
        rows.extend([a, bb, a, bb]); cols.extend([bb, a, a, bb]); vals.extend([-G, -G, G, G])
    for a, bb, G in ((idx[:-1].ravel(), idx[1:].ravel(), Gr.ravel()), (idx[:, :-1].ravel(), idx[:, 1:].ravel(), Gz.ravel())):
        rows += [a, bb, a, bb]; cols += [bb, a, a, bb]; vals += [-G, -G, G, G]
    # z = 0: Dirichlet 0 C through half cell
    G0 = Az / (0.5 * dz[0] / k[:, 0]); diag[idx[:, 0]] += G0; b[idx[:, 0]] += G0 * 0.0
    # outer side and top: Robin
    Gs = 2 * np.pi * rf[-1] * dz / (0.5 * dr[-1] / k[-1] + 1 / h); diag[idx[-1]] += Gs; b[idx[-1]] += Gs * T_lab
    Gt = Az / (0.5 * dz[-1] / k[:, -1] + 1 / h); diag[idx[:, -1]] += Gt; b[idx[:, -1]] += Gt * T_lab
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N))
    A = A + sp.diags(diag)
    # Dirichlet copper
    fixed = (mat == 2).ravel()
    Tf = np.zeros(N); Tf[fixed] = np.vectorize(Tfix.get)(zone.ravel()[fixed])
    free = ~fixed
    Aff = A[free][:, free]
    rhs = b[free] - A[free][:, fixed] @ Tf[fixed]
    T = Tf.copy(); T[free] = spla.spsolve(Aff.tocsc(), rhs)
    T = T.reshape(nr, nz)
    # heat into each zone = flux across faces copper <-> non-copper
    Q = {1: 0.0, 2: 0.0}
    surf = []                                                        # (zone, kind, r, z, Q) for distribution
    Gr2, Gz2 = Gr, Gz
    for i in range(nr - 1):
        for j in np.nonzero((mat[i] == 2) ^ (mat[i + 1] == 2))[0]:
            if mat[i, j] == 2:
                q = Gr2[i, j] * (T[i + 1, j] - T[i, j]); zn = zone[i, j]; kind = "r_out"
            else:
                q = Gr2[i, j] * (T[i, j] - T[i + 1, j]); zn = zone[i + 1, j]; kind = "r_in"
            Q[zn] += q; surf.append((zn, kind, rface[i] * 1e3, zc[j] * 1e3, q))
    for j in range(nz - 1):
        for i in np.nonzero((mat[:, j] == 2) ^ (mat[:, j + 1] == 2))[0]:
            if mat[i, j] == 2:
                q = Gz2[i, j] * (T[i, j + 1] - T[i, j]); zn = zone[i, j]; kind = "z_top"
            else:
                q = Gz2[i, j] * (T[i, j] - T[i, j + 1]); zn = zone[i, j + 1]; kind = "z_bot"
            Q[zn] += q; surf.append((zn, kind, rc[i] * 1e3, zf[j + 1] * 1e3, q))
    # energy balance
    Qlab = float((Gs * (T_lab - T[-1])).sum() + (Gt * (T_lab - T[:, -1])).sum())
    Qice = float((G0 * T[:, 0]).sum())
    return dict(Q1=Q[2], Q2=Q[1], Qlab=Qlab, Qice=Qice, bal=Qlab - Qice - Q[1] - Q[2], surf=surf, T=T, rc=rc, zc=zc, mat=mat)


def split_z1(res, R_band):
    """classify the Zone 1 surface flux into the patches used by the 3-D model"""
    out = {}
    for zn, kind, r, z, q in res["surf"]:
        if zn != 2:
            continue
        if kind == "r_in" and abs(r - 13.5) < 1e-6: key = "bore"
        elif kind in ("r_out",) and abs(r - 43) < 1e-6: key = "plate_rim"
        elif kind == "r_out": key = "band_outer"
        elif kind == "z_bot" and abs(z - 247) < 1e-6: key = "lower_plate_bottom"
        elif kind == "z_top" and abs(z - 365) < 1e-6: key = "upper_plate_top"
        elif kind == "z_top": key = "lower_plate_inner"
        else: key = "upper_plate_inner"
        out[key] = out.get(key, 0) + q
    return out


if __name__ == "__main__":
    rows = []
    for name, kw in [("base: band 25.1, h 8, 35C lab, 50 mm foam", dict()),
                     ("band to 27 (layout-sheet carrier)", dict(R_band=27.0)),
                     ("band to 20 (buffer only)", dict(R_band=20.0)),
                     ("h 8.5 (2.50 conv + 6.01 rad)", dict(h=8.51)),
                     ("lab 30 C", dict(T_lab=30.0)),
                     ("grid 0.25 mm", dict(d=0.25)),
                     ("grid 1.0 mm", dict(d=1.0)),
                     ("vapour k 0.009788", dict(k_vap=0.009788)),
                     ("foam k 0.025 (PU)", dict(k_foam=0.025)),
                     ("foam k 0.015 (aerogel)", dict(k_foam=0.015))]:
        r = solve(**kw)
        s = split_z1(r, kw.get("R_band", 25.1))
        rows.append(dict(case=name, Q1=r["Q1"], Q2=r["Q2"], balance=r["bal"], z1_split=s))
        tot = sum(s.values())
        plates = sum(v for k_, v in s.items() if "plate" in k_)
        print(f"{name:45s} Z1 {r['Q1']:.3f} W  Z2 {r['Q2']:.3f} W  bal {r['bal']:.1e}  Z1 via plates {plates / tot * 100:.0f}%")
    json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "results/heatload_axi.json", "w"), indent=1)
