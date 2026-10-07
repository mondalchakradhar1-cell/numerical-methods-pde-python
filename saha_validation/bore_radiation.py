#!/usr/bin/env python3
"""Gray diffuse radiation inside the vapour bore (r = 13.5 mm, z 0-423.5) with exact cylinder view factors.
Surface temperatures come from the axisymmetric conduction model (one-way: radiation does not feed back).
Checks the decks' 'radiation into Zone 1 ~ +34-40 mW, Zone 2 ~ +4-6 mW' (FLUENT_SETUP.md section 9)."""
import json
import sys

import numpy as np

import heatload_axi

SIG = 5.670374e-8
R = 13.5e-3


def F_dd(h):
    h = np.maximum(np.abs(h), 1e-12)
    rho = R / h
    S = 2 + 1 / rho ** 2
    return 0.5 * (S - np.sqrt(S * S - 4))


def run(eps_cu=0.3, eps_pmma=0.9, dz=1.0):
    res = heatload_axi.solve()
    T, rc, zc, mat = res["T"], res["rc"] * 1e3, res["zc"] * 1e3, res["mat"]
    zf = np.arange(0, 423.5 + 1e-9, dz); zf[-1] = 423.5
    zb = 0.5 * (zf[1:] + zf[:-1]); n = len(zb)
    i_s = np.argmin(np.abs(rc - 13.75))                       # first solid cell outside the bore
    Tw = np.interp(zb, zc, T[i_s]) + 273.15
    cu1 = (zb > 247) & (zb < 365); cu2 = (zb > 60) & (zb < 187)
    Tw[cu1] = 243.15; Tw[cu2] = 258.15
    eps = np.where(cu1 | cu2, eps_cu, eps_pmma)
    j_cap = np.argmin(np.abs(zc - 424.25))
    Tcap = np.interp(6.0, rc, T[:, j_cap]) + 273.15
    # surfaces: bands 0..n-1, bottom disk n, top disk n+1
    Ad = np.pi * R ** 2
    Ab = 2 * np.pi * R * np.diff(zf) * 1e-3
    zz = zf * 1e-3
    N = n + 2
    F = np.zeros((N, N))
    a, b = zz[:-1], zz[1:]
    for i in range(n):
        c, d = zz[:-1], zz[1:]
        Fij = Ad / Ab[i] * (F_dd(c - b[i]) - F_dd(d - b[i]) - F_dd(c - a[i]) + F_dd(d - a[i]))
        Fij = np.where(np.arange(n) > i, Fij, 0)
        F[i, :n] += Fij
    F[:n, :n] = F[:n, :n] + (F[:n, :n].T * Ab[None, :].T / Ab[None, :]).T * 0  # placeholder (filled below by reciprocity)
    for i in range(n):
        for j in range(i):
            F[i, j] = F[j, i] * Ab[j] / Ab[i]
    for i in range(n):
        F[i, i] = 1 - 2 * Ad / Ab[i] * (1 - F_dd(b[i] - a[i]))
    # disks
    H = zz[-1]
    F[n, :n] = F_dd(a) - F_dd(b); F[n + 1, :n] = F_dd(H - b) - F_dd(H - a)
    F[n, n + 1] = F[n + 1, n] = F_dd(H)
    F[:n, n] = F[n, :n] * Ad / Ab; F[:n, n + 1] = F[n + 1, :n] * Ad / Ab
    A = np.r_[Ab, Ad, Ad]
    Ts = np.r_[Tw, 273.15, Tcap]
    e = np.r_[eps, 1.0, eps_pmma]
    Eb = SIG * Ts ** 4
    # radiosity: J_i - (1-e_i) sum F_ij J_j = e_i Eb_i
    M = np.eye(N) - (1 - e)[:, None] * F
    J = np.linalg.solve(M, e * Eb)
    q_net = A * (J - F @ J)                                  # net emitted (W)
    out = dict(eps_cu=eps_cu, closure_max=float(np.abs(F.sum(1) - 1).max()),
               Z1_absorbed_mW=float(-q_net[:n][cu1].sum() * 1e3), Z2_absorbed_mW=float(-q_net[:n][cu2].sum() * 1e3),
               cap_emitted_mW=float(q_net[n + 1] * 1e3), bottom_emitted_mW=float(q_net[n] * 1e3),
               pmma_emitted_mW=float(q_net[:n][~(cu1 | cu2)].sum() * 1e3), sum_mW=float(q_net.sum() * 1e3))
    return out


if __name__ == "__main__":
    rows = [run(e) for e in (0.05, 0.3, 0.9)]
    for r in rows:
        print(json.dumps(r))
    json.dump(rows, open("results/bore_radiation.json", "w"), indent=1)
