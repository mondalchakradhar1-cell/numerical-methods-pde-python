#!/usr/bin/env python3
"""Transient 3-D natural convection of the R134a vapour column (independent re-implementation, no radiation).

Column: r < 13.5 mm, z 0-423.5 mm.  Boussinesq, laminar, incompressible projection method on a staggered Cartesian
(MAC) grid with a stepped cylindrical wall (wall area corrected to 2 pi R per layer).
  momentum : AB2, 2nd-order upwind advection, no-slip ghosts, explicit diffusion
  energy   : AB2, MUSCL / van Leer fluxes
  pressure : AMG-preconditioned CG (pyamg), warm started
Walls: copper bands z 60-187 (-15 C) and 247-365 (-30 C) fixed; bottom z = 0 at 0 C; Perspex connectors and cap:
Robin q = G_out (T_ext - T_w) from room.py.  0-60 s one-way (T_ext frozen), 60-120 s two-way: every 1 s the 5-s mean
heat drawn from each Perspex row is put on the room model and T_ext = T_wall(room) + q/G_out (coupled deck slide 3).
"""
import json
import os
import sys
import time

import numba as nb
import numpy as np
import pyamg
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RHO, CP, KV, MU, BETA = 4.2254, 786.6, 0.009788, 1.0041e-5, 3.874e-3
NU, ALPHA, G = MU / RHO, KV / (RHO * CP), 9.81
T_REF = -15.0
R, H = 13.5e-3, 423.5e-3
REGIONS = ["ice", "conn_lo", "z2", "conn_mid", "z1", "top_wall", "cap"]


# ------------------------------------------------------------------------------------------------ kernels
@nb.njit(cache=True, inline="always")
def gu(u, ou, i, j, k, di, dj, dk, uc):
    """neighbour of a u-face with no-slip ghost for tangential directions"""
    nx1, ny, nz = u.shape
    a, b, c = i + di, j + dj, k + dk
    if a < 0 or a >= nx1:
        return 0.0
    if b < 0 or b >= ny or c < 0 or c >= nz:
        return -uc
    if ou[a, b, c]:
        return u[a, b, c]
    if di != 0:
        return 0.0
    return -uc


@nb.njit(cache=True, inline="always")
def upw2(uc, um1, um2, up1, up2, vel, h):
    if vel > 0:
        return vel * (3 * uc - 4 * um1 + um2) / (2 * h)
    return vel * (-3 * uc + 4 * up1 - up2) / (2 * h)


@nb.njit(parallel=True, cache=True)
def mom_rhs(u, v, w, ou, ov, ow, T, dx, dz, nu, gb, tref, Ru, Rv, Rw):
    nx, ny, nz = T.shape
    for i in nb.prange(nx + 1):
        for j in range(ny):
            for k in range(nz):
                if not ou[i, j, k]:
                    Ru[i, j, k] = 0.0; continue
                uc = u[i, j, k]
                vv = 0.25 * (v[i - 1, j, k] + v[i - 1, j + 1, k] + v[i, j, k] + v[i, j + 1, k])
                ww = 0.25 * (w[i - 1, j, k] + w[i - 1, j, k + 1] + w[i, j, k] + w[i, j, k + 1])
                xm1 = gu(u, ou, i, j, k, -1, 0, 0, uc); xm2 = gu(u, ou, i, j, k, -2, 0, 0, uc)
                xp1 = gu(u, ou, i, j, k, 1, 0, 0, uc); xp2 = gu(u, ou, i, j, k, 2, 0, 0, uc)
                ym1 = gu(u, ou, i, j, k, 0, -1, 0, uc); ym2 = gu(u, ou, i, j, k, 0, -2, 0, uc)
                yp1 = gu(u, ou, i, j, k, 0, 1, 0, uc); yp2 = gu(u, ou, i, j, k, 0, 2, 0, uc)
                zm1 = gu(u, ou, i, j, k, 0, 0, -1, uc); zm2 = gu(u, ou, i, j, k, 0, 0, -2, uc)
                zp1 = gu(u, ou, i, j, k, 0, 0, 1, uc); zp2 = gu(u, ou, i, j, k, 0, 0, 2, uc)
                adv = upw2(uc, xm1, xm2, xp1, xp2, uc, dx) + upw2(uc, ym1, ym2, yp1, yp2, vv, dx) + upw2(uc, zm1, zm2, zp1, zp2, ww, dz)
                lap = (xm1 + xp1 - 2 * uc) / dx ** 2 + (ym1 + yp1 - 2 * uc) / dx ** 2 + (zm1 + zp1 - 2 * uc) / dz ** 2
                Ru[i, j, k] = -adv + nu * lap
    for i in nb.prange(nx):
        for j in range(ny + 1):
            for k in range(nz):
                if not ov[i, j, k]:
                    Rv[i, j, k] = 0.0; continue
                vc = v[i, j, k]
                uu = 0.25 * (u[i, j - 1, k] + u[i + 1, j - 1, k] + u[i, j, k] + u[i + 1, j, k])
                ww = 0.25 * (w[i, j - 1, k] + w[i, j - 1, k + 1] + w[i, j, k] + w[i, j, k + 1])
                # reuse gu with axes permuted: write explicit neighbours
                xm1 = gv(v, ov, i, j, k, -1, 0, 0, vc); xm2 = gv(v, ov, i, j, k, -2, 0, 0, vc)
                xp1 = gv(v, ov, i, j, k, 1, 0, 0, vc); xp2 = gv(v, ov, i, j, k, 2, 0, 0, vc)
                ym1 = gv(v, ov, i, j, k, 0, -1, 0, vc); ym2 = gv(v, ov, i, j, k, 0, -2, 0, vc)
                yp1 = gv(v, ov, i, j, k, 0, 1, 0, vc); yp2 = gv(v, ov, i, j, k, 0, 2, 0, vc)
                zm1 = gv(v, ov, i, j, k, 0, 0, -1, vc); zm2 = gv(v, ov, i, j, k, 0, 0, -2, vc)
                zp1 = gv(v, ov, i, j, k, 0, 0, 1, vc); zp2 = gv(v, ov, i, j, k, 0, 0, 2, vc)
                adv = upw2(vc, xm1, xm2, xp1, xp2, uu, dx) + upw2(vc, ym1, ym2, yp1, yp2, vc, dx) + upw2(vc, zm1, zm2, zp1, zp2, ww, dz)
                lap = (xm1 + xp1 - 2 * vc) / dx ** 2 + (ym1 + yp1 - 2 * vc) / dx ** 2 + (zm1 + zp1 - 2 * vc) / dz ** 2
                Rv[i, j, k] = -adv + nu * lap
    for i in nb.prange(nx):
        for j in range(ny):
            for k in range(nz + 1):
                if not ow[i, j, k]:
                    Rw[i, j, k] = 0.0; continue
                wc = w[i, j, k]
                uu = 0.25 * (u[i, j, k - 1] + u[i + 1, j, k - 1] + u[i, j, k] + u[i + 1, j, k])
                vv = 0.25 * (v[i, j, k - 1] + v[i, j + 1, k - 1] + v[i, j, k] + v[i, j + 1, k])
                xm1 = gw(w, ow, i, j, k, -1, 0, 0, wc); xm2 = gw(w, ow, i, j, k, -2, 0, 0, wc)
                xp1 = gw(w, ow, i, j, k, 1, 0, 0, wc); xp2 = gw(w, ow, i, j, k, 2, 0, 0, wc)
                ym1 = gw(w, ow, i, j, k, 0, -1, 0, wc); ym2 = gw(w, ow, i, j, k, 0, -2, 0, wc)
                yp1 = gw(w, ow, i, j, k, 0, 1, 0, wc); yp2 = gw(w, ow, i, j, k, 0, 2, 0, wc)
                zm1 = gw(w, ow, i, j, k, 0, 0, -1, wc); zm2 = gw(w, ow, i, j, k, 0, 0, -2, wc)
                zp1 = gw(w, ow, i, j, k, 0, 0, 1, wc); zp2 = gw(w, ow, i, j, k, 0, 0, 2, wc)
                adv = upw2(wc, xm1, xm2, xp1, xp2, uu, dx) + upw2(wc, ym1, ym2, yp1, yp2, vv, dx) + upw2(wc, zm1, zm2, zp1, zp2, wc, dz)
                lap = (xm1 + xp1 - 2 * wc) / dx ** 2 + (ym1 + yp1 - 2 * wc) / dx ** 2 + (zm1 + zp1 - 2 * wc) / dz ** 2
                Tf = 0.5 * (T[i, j, k - 1] + T[i, j, k])
                Rw[i, j, k] = -adv + nu * lap + gb * (Tf - tref)


@nb.njit(cache=True, inline="always")
def gv(v, ov, i, j, k, di, dj, dk, vc):
    nx, ny1, nz = v.shape
    a, b, c = i + di, j + dj, k + dk
    if b < 0 or b >= ny1:
        return 0.0
    if a < 0 or a >= nx or c < 0 or c >= nz:
        return -vc
    if ov[a, b, c]:
        return v[a, b, c]
    if dj != 0:
        return 0.0
    return -vc


@nb.njit(cache=True, inline="always")
def gw(w, ow, i, j, k, di, dj, dk, wc):
    nx, ny, nz1 = w.shape
    a, b, c = i + di, j + dj, k + dk
    if c < 0 or c >= nz1:
        return 0.0
    if a < 0 or a >= nx or b < 0 or b >= ny:
        return -wc
    if ow[a, b, c]:
        return w[a, b, c]
    if dk != 0:
        return 0.0
    return -wc


@nb.njit(cache=True, inline="always")
def vl(a, b, c):
    """van Leer limited face value from upwind cell b, its upstream a and downstream c"""
    d1 = b - a; d2 = c - b
    if d1 * d2 <= 0:
        return b
    return b + d1 * d2 / (d1 + d2)


@nb.njit(parallel=True, cache=True)
def temp_rhs(T, u, v, w, fl, ou, ov, ow, dx, dz, alpha, wG, wTb, RT):
    """RT = dT/dt.  wG[i,j,k]: total wall conductance / (rho cp V) of the cell, wTb: conductance-weighted boundary T"""
    nx, ny, nz = T.shape
    for i in nb.prange(nx):
        for j in range(ny):
            for k in range(nz):
                if not fl[i, j, k]:
                    RT[i, j, k] = 0.0; continue
                Tc = T[i, j, k]
                s = 0.0
                # x faces
                for f in range(2):
                    fi = i + f
                    if ou[fi, j, k]:
                        uf = u[fi, j, k]
                        L = fi - 1; Rr = fi
                        if uf > 0:
                            a = T[L - 1, j, k] if (L - 1 >= 0 and fl[L - 1, j, k]) else T[L, j, k]
                            tf = vl(a, T[L, j, k], T[Rr, j, k])
                        else:
                            c = T[Rr + 1, j, k] if (Rr + 1 < nx and fl[Rr + 1, j, k]) else T[Rr, j, k]
                            tf = vl(c, T[Rr, j, k], T[L, j, k])
                        flux = uf * tf / dx - alpha * (T[Rr, j, k] - T[L, j, k]) / dx ** 2
                        s += -flux if f == 1 else flux
                for f in range(2):
                    fj = j + f
                    if ov[i, fj, k]:
                        vf = v[i, fj, k]
                        L = fj - 1; Rr = fj
                        if vf > 0:
                            a = T[i, L - 1, k] if (L - 1 >= 0 and fl[i, L - 1, k]) else T[i, L, k]
                            tf = vl(a, T[i, L, k], T[i, Rr, k])
                        else:
                            c = T[i, Rr + 1, k] if (Rr + 1 < ny and fl[i, Rr + 1, k]) else T[i, Rr, k]
                            tf = vl(c, T[i, Rr, k], T[i, L, k])
                        flux = vf * tf / dx - alpha * (T[i, Rr, k] - T[i, L, k]) / dx ** 2
                        s += -flux if f == 1 else flux
                for f in range(2):
                    fk = k + f
                    if ow[i, j, fk]:
                        wf = w[i, j, fk]
                        L = fk - 1; Rr = fk
                        if wf > 0:
                            a = T[i, j, L - 1] if (L - 1 >= 0) else T[i, j, L]
                            tf = vl(a, T[i, j, L], T[i, j, Rr])
                        else:
                            c = T[i, j, Rr + 1] if (Rr + 1 < nz) else T[i, j, Rr]
                            tf = vl(c, T[i, j, Rr], T[i, j, L])
                        flux = wf * tf / dz - alpha * (T[i, j, Rr] - T[i, j, L]) / dz ** 2
                        s += -flux if f == 1 else flux
                s += wG[i, j, k] * (wTb[i, j, k] - Tc)
                RT[i, j, k] = s


@nb.njit(parallel=True, cache=True)
def divergence(u, v, w, fl, dx, dz, out):
    nx, ny, nz = fl.shape
    for i in nb.prange(nx):
        for j in range(ny):
            for k in range(nz):
                if fl[i, j, k]:
                    out[i, j, k] = (u[i + 1, j, k] - u[i, j, k]) / dx + (v[i, j + 1, k] - v[i, j, k]) / dx + (w[i, j, k + 1] - w[i, j, k]) / dz
                else:
                    out[i, j, k] = 0.0


@nb.njit(parallel=True, cache=True)
def project(u, v, w, ou, ov, ow, phi, dt, dx, dz):
    nx, ny, nz = phi.shape
    for i in nb.prange(nx + 1):
        for j in range(ny):
            for k in range(nz):
                if ou[i, j, k]:
                    u[i, j, k] -= dt * (phi[i, j, k] - phi[i - 1, j, k]) / dx
    for i in nb.prange(nx):
        for j in range(ny + 1):
            for k in range(nz):
                if ov[i, j, k]:
                    v[i, j, k] -= dt * (phi[i, j, k] - phi[i, j - 1, k]) / dx
    for i in nb.prange(nx):
        for j in range(ny):
            for k in range(nz + 1):
                if ow[i, j, k]:
                    w[i, j, k] -= dt * (phi[i, j, k] - phi[i, j, k - 1]) / dz


@nb.njit(cache=True)
def interp_vel(u, v, w, x, y, z, dx, dz, x0):
    """trilinear interpolation of the staggered velocity at a point (m); x0 = left edge of the grid"""
    nx, ny, nz = u.shape[0] - 1, v.shape[1] - 1, w.shape[2] - 1
    fx = (x - x0) / dx; fy = (y - x0) / dx; fz = z / dz
    out = np.zeros(3)
    for comp in range(3):
        if comp == 0:
            gx, gy, gz, A = fx, fy - 0.5, fz - 0.5, u
        elif comp == 1:
            gx, gy, gz, A = fx - 0.5, fy, fz - 0.5, v
        else:
            gx, gy, gz, A = fx - 0.5, fy - 0.5, fz, w
        i0 = int(np.floor(gx)); j0 = int(np.floor(gy)); k0 = int(np.floor(gz))
        tx = gx - i0; ty = gy - j0; tz = gz - k0
        val = 0.0
        for a in range(2):
            for b in range(2):
                for c in range(2):
                    ii = min(max(i0 + a, 0), A.shape[0] - 1); jj = min(max(j0 + b, 0), A.shape[1] - 1); kk = min(max(k0 + c, 0), A.shape[2] - 1)
                    wt = (tx if a else 1 - tx) * (ty if b else 1 - ty) * (tz if c else 1 - tz)
                    val += wt * A[ii, jj, kk]
        out[comp] = val
    return out


@nb.njit(parallel=True, cache=True)
def advect_particles(P, u, v, w, dt, dx, dz, x0, Rmax, Hmax):
    for p in nb.prange(P.shape[0]):
        x, y, z = P[p, 0], P[p, 1], P[p, 2]
        k1 = interp_vel(u, v, w, x, y, z, dx, dz, x0)
        xm, ym, zm = x + 0.5 * dt * k1[0], y + 0.5 * dt * k1[1], z + 0.5 * dt * k1[2]
        k2 = interp_vel(u, v, w, xm, ym, zm, dx, dz, x0)
        x += dt * k2[0]; y += dt * k2[1]; z += dt * k2[2]
        r = np.sqrt(x * x + y * y)
        if r > Rmax:
            x *= Rmax / r; y *= Rmax / r
        z = min(max(z, 0.3e-3), Hmax - 0.3e-3)
        P[p, 0], P[p, 1], P[p, 2] = x, y, z


# ------------------------------------------------------------------------------------------------ set-up
class Column:
    def __init__(self, dx_mm=1.0, area_correct=True):
        self.dx = dx_mm * 1e-3
        n = int(round(2 * R / self.dx))
        self.nx = self.ny = n
        self.nz = int(round(H / self.dx))
        self.dz = H / self.nz
        self.x0 = -n * self.dx / 2
        xc = self.x0 + (np.arange(n) + 0.5) * self.dx
        X, Y = np.meshgrid(xc, xc, indexing="ij")
        self.xc = xc
        self.zc = (np.arange(self.nz) + 0.5) * self.dz
        sec = np.hypot(X, Y) < R
        self.sec = sec
        self.fl = np.repeat(sec[:, :, None], self.nz, axis=2)
        nx, ny, nz = self.nx, self.ny, self.nz
        self.ou = np.zeros((nx + 1, ny, nz), np.bool_); self.ou[1:-1] = self.fl[:-1] & self.fl[1:]
        self.ov = np.zeros((nx, ny + 1, nz), np.bool_); self.ov[:, 1:-1] = self.fl[:, :-1] & self.fl[:, 1:]
        self.ow = np.zeros((nx, ny, nz + 1), np.bool_); self.ow[:, :, 1:-1] = self.fl[:, :, :-1] & self.fl[:, :, 1:]
        # lateral wall faces per section cell
        pad = np.pad(sec, 1)
        nside = (~pad[:-2, 1:-1]).astype(int) + (~pad[2:, 1:-1]) + (~pad[1:-1, :-2]) + (~pad[1:-1, 2:])
        self.nside = np.where(sec, nside, 0)
        self.fA = (2 * np.pi * R / (self.nside.sum() * self.dx)) if area_correct else 1.0
        self.area_sec = sec.sum() * self.dx ** 2
        self.Vc = self.dx * self.dx * self.dz
        zmm = self.zc * 1e3
        self.kind = np.full(nz, "pmma", dtype=object)
        self.kind[(zmm > 60) & (zmm < 187)] = "z2"; self.kind[(zmm > 247) & (zmm < 365)] = "z1"
        self.region = np.select([zmm < 60, zmm < 187, zmm < 247, zmm < 365], [1, 2, 3, 4], 5)
        rr = np.hypot(X, Y)
        self.rsec = rr

    def set_bc(self, Gz, Tz, Gcap, Tcap):
        """Gz, Tz: outside conductance (W/m2K) and T_ext per layer for the Perspex rows; Gcap/Tcap per section cell"""
        dx, dz = self.dx, self.dz
        nx, ny, nz = self.nx, self.ny, self.nz
        Aside = dx * dz * self.fA
        hcell = KV / (0.5 * dx)
        G_lat = np.zeros(nz); T_lat = np.zeros(nz)
        for k in range(nz):
            if self.kind[k] == "z2":
                G_lat[k], T_lat[k] = hcell, -15.0
            elif self.kind[k] == "z1":
                G_lat[k], T_lat[k] = hcell, -30.0
            else:
                G_lat[k], T_lat[k] = 1 / (1 / Gz[k] + 1 / hcell), Tz[k]
        self.G_lat, self.T_lat = G_lat, T_lat
        wG = np.zeros((nx, ny, nz)); wGT = np.zeros((nx, ny, nz))
        cond_side = self.nside[:, :, None] * Aside * G_lat[None, None, :]
        wG += cond_side; wGT += cond_side * T_lat[None, None, :]
        Abot = dx * dx
        hz = KV / (0.5 * dz)
        gb = Abot * hz * self.sec
        wG[:, :, 0] += gb; wGT[:, :, 0] += gb * 0.0
        gc = Abot * self.sec / (1 / Gcap + 1 / hz)
        wG[:, :, -1] += gc; wGT[:, :, -1] += gc * Tcap
        self.wG_W = wG                                    # W/K
        self.wTb = np.where(wG > 0, wGT / np.where(wG > 0, wG, 1), 0.0)
        self.wG = wG / (RHO * CP * self.Vc)              # 1/s
        self.gbot, self.gcap, self.Tcap, self.cond_side = gb, gc, Tcap, cond_side

    def wall_heat(self, T):
        """heat INTO the vapour from each boundary group (W) and per Perspex layer"""
        lat = (self.cond_side * (self.T_lat[None, None, :] - T)).sum(axis=(0, 1))
        out = {"ice": float((self.gbot * (0.0 - T[:, :, 0])).sum()), "cap": float((self.gcap * (self.Tcap - T[:, :, -1])).sum())}
        names = {1: "conn_lo", 2: "z2", 3: "conn_mid", 4: "z1", 5: "top_wall"}
        for r_, nm in names.items():
            out[nm] = float(lat[self.region == r_].sum())
        return out, lat, self.gcap * (self.Tcap - T[:, :, -1])

    def poisson(self):
        nx, ny, nz = self.nx, self.ny, self.nz
        idx = -np.ones((nx, ny, nz), np.int64)
        idx[self.fl] = np.arange(self.fl.sum())
        rows, cols, vals = [], [], []
        for ax, h, op in ((0, self.dx, self.ou[1:-1]), (1, self.dx, self.ov[:, 1:-1]), (2, self.dz, self.ow[:, :, 1:-1])):
            a = np.take(idx, np.arange(idx.shape[ax] - 1), axis=ax)[op]
            b = np.take(idx, np.arange(1, idx.shape[ax]), axis=ax)[op]
            c = np.full(len(a), 1 / h ** 2)
            rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [c, c, -c, -c]
        n = int(self.fl.sum())
        L = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
        self.pidx = idx
        self.L = -L                                       # SPD (semi-definite)
        # exact fast solver: the column is the section extruded in z with closed ends ->
        # DCT-II in z (cell-centred Neumann) x eigen-decomposition of the 2-D section Laplacian
        sidx = -np.ones((nx, ny), np.int64); sidx[self.sec] = np.arange(self.sec.sum())
        m = int(self.sec.sum())
        L2 = np.zeros((m, m))
        for (a, b) in ((sidx[:-1, :], sidx[1:, :]), (sidx[:, :-1], sidx[:, 1:])):
            ok = (a >= 0) & (b >= 0)
            for p, q in zip(a[ok], b[ok]):
                L2[p, q] -= 1 / self.dx ** 2; L2[q, p] -= 1 / self.dx ** 2
                L2[p, p] += 1 / self.dx ** 2; L2[q, q] += 1 / self.dx ** 2
        lam2, V = np.linalg.eigh(L2)
        lamz = (2 / self.dz ** 2) * (1 - np.cos(np.pi * np.arange(nz) / nz))
        den = lam2[:, None] + lamz[None, :]
        den[np.abs(den) < 1e-9] = np.inf
        self.V, self.inv_den = V, 1.0 / den
        self.sidx_flat = np.nonzero(self.sec.ravel())[0]

    def solve_p(self, rhs):
        """solve Lap(phi) = rhs (rhs on the 3-D array, fluid cells); returns phi on fluid cells (flattened order)"""
        from scipy.fft import dct, idct
        B = rhs.reshape(self.nx * self.ny, self.nz)[self.sidx_flat]       # (m, nz)
        Bh = dct(B, type=2, axis=1, norm="ortho")
        Xh = -(self.V @ ((self.V.T @ Bh) * self.inv_den))
        X = idct(Xh, type=2, axis=1, norm="ortho")
        out = np.zeros((self.nx * self.ny, self.nz)); out[self.sidx_flat] = X
        return out.reshape(self.nx, self.ny, self.nz)[self.fl]

    def conduction(self):
        """steady conduction of the still vapour (initial state and the 'conduction only' panel)"""
        n = int(self.fl.sum()); idx = self.pidx
        rows, cols, vals = [], [], []
        for ax, h, op in ((0, self.dx, self.ou[1:-1]), (1, self.dx, self.ov[:, 1:-1]), (2, self.dz, self.ow[:, :, 1:-1])):
            a = np.take(idx, np.arange(idx.shape[ax] - 1), axis=ax)[op]
            b = np.take(idx, np.arange(1, idx.shape[ax]), axis=ax)[op]
            A = (self.Vc / h) * KV / h
            c = np.full(len(a), A)
            rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-c, -c, c, c]
        M = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
        M = M + sp.diags(self.wG_W[self.fl])
        b = (self.wG_W * self.wTb)[self.fl]
        import scipy.sparse.linalg as spla
        M = M.tocsr()
        ml = pyamg.smoothed_aggregation_solver(M, symmetry="symmetric")
        x, info = spla.cg(M, b, rtol=1e-12, maxiter=2000, M=ml.aspreconditioner())
        self.cond_res = float(np.linalg.norm(M @ x - b) / np.linalg.norm(b))
        T = np.zeros(self.fl.shape); T[self.fl] = x
        return T


def room_bc(col, room, T_ext_faces):
    """map room-face T_ext / G_out onto vapour layers (wall) and section cells (cap)"""
    w = room.vf_kind == "wall"
    zr = room.vf_pos[w]; G = room.G_out[w]; Te = T_ext_faces[w]; A = room.vf_A[w]
    zmm = col.zc * 1e3
    Gz = np.interp(zmm, zr, G); Tz = np.interp(zmm, zr, Te)
    c = ~w
    rr = room.vf_pos[c]; Gc = room.G_out[c]; Tc = T_ext_faces[c]
    rmm = col.rsec * 1e3
    Gcap = np.interp(rmm, rr, Gc); Tcap = np.interp(rmm, rr, Tc)
    return Gz, Tz, Gcap, Tcap


def layer_heat_to_faces(col, room, lat_mean, cap_mean):
    """distribute vapour-side heat (W, into vapour) per layer / cap cell onto the room faces"""
    q = np.zeros(len(room.vf_uid))
    w = np.nonzero(room.vf_kind == "wall")[0]
    zf = room.vf_pos[w]
    k = np.clip((zf * 1e-3 / col.dz).astype(int), 0, col.nz - 1)
    pm = col.kind[k] == "pmma"
    for kk in np.unique(k[pm]):
        sel = w[(k == kk) & pm]
        q[sel] = lat_mean[kk] * room.vf_A[sel] / room.vf_A[sel].sum()
    c = np.nonzero(room.vf_kind == "cap")[0]
    rf = room.rf[1:]
    rcell = col.rsec[col.sec] * 1e3; capq = cap_mean[col.sec]
    for ci in c:
        r = room.vf_pos[ci]
        # ring between neighbouring radial faces
        dr = 0.25
        m = (rcell >= r - dr) & (rcell < r + dr)
        q[ci] = capq[m].sum() if m.any() else 0.0
    # rescale cap so the total matches
    tot_cap = cap_mean[col.sec].sum()
    if q[c].sum() != 0:
        q[c] *= tot_cap / q[c].sum()
    return q


def run(t_end=120.0, t_couple=60.0, dx_mm=1.0, cfl=0.35, out=None, snap_dt=1.0, hist_dt=0.05, npart=2000, seed=1,
        win1=(25.0, 60.0), win2=(85.0, 120.0)):
    import room as roommod
    out = out or os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    t0w = time.time()
    room = roommod.Room()
    col = Column(dx_mm)
    T_ext = room.T_ext0.copy()
    col.set_bc(*room_bc(col, room, T_ext))
    col.poisson()
    T = col.conduction()
    np.savez_compressed(os.path.join(out, "conduction.npz"), T=T.astype(np.float32), xc=col.xc, zc=col.zc, sec=col.sec)
    q0, _, _ = col.wall_heat(T)
    rng = np.random.default_rng(seed)
    T = T + 1e-3 * rng.standard_normal(T.shape) * col.fl
    nx, ny, nz = col.nx, col.ny, col.nz
    u = np.zeros((nx + 1, ny, nz)); v = np.zeros((nx, ny + 1, nz)); w = np.zeros((nx, ny, nz + 1))
    Ru, Rv, Rw, RT = np.zeros_like(u), np.zeros_like(v), np.zeros_like(w), np.zeros_like(T)
    Ru0, Rv0, Rw0, RT0 = np.zeros_like(u), np.zeros_like(v), np.zeros_like(w), np.zeros_like(T)
    div = np.zeros_like(T); phi = np.zeros_like(T); phiv = np.zeros(int(col.fl.sum()))
    # particles: uniform in the column
    rr = R * 0.95 * np.sqrt(rng.random(npart)); th = 2 * np.pi * rng.random(npart)
    P = np.c_[rr * np.cos(th), rr * np.sin(th), H * rng.random(npart)]
    t, dt_prev, step = 0.0, None, 0
    hist = []; snaps_t = []
    next_hist, next_snap, next_ex = 0.0, 0.0, t_couple
    acc = {1: None, 2: None}
    lat_buf, cap_buf = [], []
    cpl_log = []
    Zheat_room = room.zone_heat(room.solve(np.zeros(len(room.vf_uid)))[0])
    dx, dz = col.dx, col.dz
    jm = ny // 2
    gb = G * BETA
    part_hist = []
    while t < t_end - 1e-12:
        if not np.isfinite(u).all():
            raise FloatingPointError(f'non-finite velocity at t = {t}')
        umax = max(np.abs(u).max(), np.abs(v).max(), np.abs(w).max(), 1e-4)
        dt = min(cfl * min(dx, dz) / umax, 0.02, 0.15 * dx ** 2 / max(NU, ALPHA))
        if dt_prev is not None:
            dt = min(dt, 1.2 * dt_prev)                  # keep the AB2 step ratio small
        dt = max(dt, 1e-4)
        mom_rhs(u, v, w, col.ou, col.ov, col.ow, T, dx, dz, NU, gb, T_REF, Ru, Rv, Rw)
        temp_rhs(T, u, v, w, col.fl, col.ou, col.ov, col.ow, dx, dz, ALPHA, col.wG, col.wTb, RT)
        if dt_prev is None:
            a1, a0 = 1.0, 0.0
        else:
            om = dt / dt_prev; a1, a0 = 1 + 0.5 * om, -0.5 * om
        u += dt * (a1 * Ru + a0 * Ru0); v += dt * (a1 * Rv + a0 * Rv0); w += dt * (a1 * Rw + a0 * Rw0)
        T += dt * (a1 * RT + a0 * RT0)
        Ru0[:] = Ru; Rv0[:] = Rv; Rw0[:] = Rw; RT0[:] = RT
        divergence(u, v, w, col.fl, dx, dz, div)
        phi[col.fl] = col.solve_p(div / dt)
        project(u, v, w, col.ou, col.ov, col.ow, phi, dt, dx, dz)
        advect_particles(P, u, v, w, dt, dx, dz, col.x0, R * 0.97, H)
        t += dt; dt_prev = dt; step += 1
        # statistics
        for wi, (a, b) in ((1, win1), (2, win2)):
            if a <= t <= b:
                if acc[wi] is None:
                    acc[wi] = dict(T=np.zeros_like(T), T2=np.zeros_like(T), u=np.zeros_like(T), v=np.zeros_like(T), w=np.zeros_like(T), w2=np.zeros_like(T), tt=0.0)
                A = acc[wi]
                uc = 0.5 * (u[1:] + u[:-1]); vc = 0.5 * (v[:, 1:] + v[:, :-1]); wc = 0.5 * (w[:, :, 1:] + w[:, :, :-1])
                A["T"] += dt * T; A["T2"] += dt * T * T; A["u"] += dt * uc; A["v"] += dt * vc; A["w"] += dt * wc; A["w2"] += dt * wc * wc
                A["tt"] += dt
        if t >= next_hist - 1e-9:
            qh, lat, capq = col.wall_heat(T)
            lat_buf.append((t, lat, capq))
            lat_buf = [x for x in lat_buf if x[0] > t - 5.0]
            wc = 0.5 * (w[:, :, 1:] + w[:, :, :-1])
            reg_T = {}
            for r_ in range(1, 6):
                m = col.fl & (col.region[None, None, :] == r_)
                reg_T[r_] = float(T[m].mean())
            stor = float((RT * col.fl).sum() * RHO * CP * col.Vc)
            hist.append(dict(t=t, **{k: v_ * 1e3 for k, v_ in qh.items()}, storage=stor * 1e3, wrms=float(np.sqrt((wc[col.fl] ** 2).mean())),
                             umax=float(umax), dt=dt, **{f"T{r_}": reg_T[r_] for r_ in reg_T}))
            next_hist += hist_dt
        if t >= next_snap - 1e-9:
            snaps_t.append(t)
            wc = 0.5 * (w[:, :, 1:] + w[:, :, :-1])
            np.savez_compressed(os.path.join(out, f"snap_{len(snaps_t) - 1:04d}.npz"), t=t, T=T.astype(np.float16),
                                Tmid=T[:, jm, :].astype(np.float32), wmid=wc[:, jm, :].astype(np.float32), P=P.astype(np.float32))
            next_snap += snap_dt
            el = time.time() - t0w
            print(f"t {t:7.2f} s  step {step}  dt {dt * 1e3:.2f} ms  umax {umax:.3f}  Z1 {hist[-1]['z1']:.0f} mW  ice {hist[-1]['ice']:.0f}  wall {el:.0f}s", flush=True)
        if len(part_hist) == 0 or t - part_hist[-1][0] >= 0.1 - 1e-9:
            part_hist.append((t, P.copy().astype(np.float32)))
        # two-way exchange
        if t >= t_couple and t >= next_ex - 1e-9:
            lat_m = np.mean([x[1] for x in lat_buf], axis=0); cap_m = np.mean([x[2] for x in lat_buf], axis=0)
            qf = layer_heat_to_faces(col, room, lat_m, cap_m)
            Tsol, Tw_room = room.solve(qf)
            T_ext = Tw_room + qf / (room.G_out * room.vf_A)
            col.set_bc(*room_bc(col, room, T_ext))
            Zheat_room = room.zone_heat(Tsol)
            cpl_log.append(dict(t=t, q_pmma_mW=float(qf.sum() * 1e3), T_ext_conn_mean=float(T_ext[room.vf_kind == "wall"].mean()),
                                T_cap=float(np.average(T_ext[room.vf_kind == 'cap'], weights=room.vf_A[room.vf_kind == 'cap'])),
                                Zroom_z2=Zheat_room[0], Zroom_z1=Zheat_room[1]))
            next_ex += 1.0
    means = {}
    for wi in (1, 2):
        A = acc[wi]
        if A is None: continue
        tt = A["tt"]
        means[wi] = {k: (A[k] / tt).astype(np.float32) for k in ("T", "T2", "u", "v", "w", "w2")}
        np.savez_compressed(os.path.join(out, f"mean_{wi}.npz"), **means[wi], xc=col.xc, zc=col.zc, sec=col.sec)
    np.savez_compressed(os.path.join(out, "particles.npz"), t=np.array([p[0] for p in part_hist]), P=np.array([p[1] for p in part_hist]))
    json.dump(dict(hist=hist, coupling=cpl_log, snaps=snaps_t, conduction_heat_mW={k: v_ * 1e3 for k, v_ in q0.items()},
                   grid=dict(dx_mm=dx_mm, nx=nx, nz=nz, cells=int(col.fl.sum()), fA=col.fA), seconds=time.time() - t0w,
                   room_zone_heat_final=Zheat_room, steps=step),
              open(os.path.join(out, "history.json"), "w"))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--t_end", type=float, default=120.0); ap.add_argument("--t_couple", type=float, default=60.0)
    ap.add_argument("--dx", type=float, default=1.0); ap.add_argument("--out", default=None)
    ap.add_argument("--w1", default="25,60"); ap.add_argument("--w2", default="85,120")
    a = ap.parse_args()
    run(a.t_end, a.t_couple, a.dx, out=a.out, win1=tuple(map(float, a.w1.split(","))), win2=tuple(map(float, a.w2.split(","))))
