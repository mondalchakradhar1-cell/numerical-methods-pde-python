#!/usr/bin/env python3
"""Coarse 3-D CFD of the methanol inside the passages of each Zone-1 layout, conjugate with the copper.

Flow: steady incompressible laminar Navier-Stokes on the fluid cells of the layout's cylindrical grid (staggered
velocities on cell faces, pressure at cells), solved by artificial compressibility with local pseudo-time steps.
First-order upwind advection, no-slip walls (ghost velocities), centrifugal and Coriolis terms of the cylindrical
frame (v_theta^2/r, -u_r v_theta/r).  Inflow ports are volume sources in the first 2 mm of a passage; outflow ports
hold p = 0.  Series links that the voxel geometry does not draw (hairpins, the radial link of B) are carried as
mass + mixed-enthalpy links.

Heat: one linear solve over copper + foam + methanol: conduction everywhere (methanol k 0.211), upwind advection in
the methanol with the converged face fluxes, external heat as the same Neumann flux as the layout model.  No film
correlation: the wall heat transfer is whatever the coarse grid resolves.

    python coolant_cfd.py <layout> [flow g/s] [--iters N]
"""
import argparse
import json
import os
import time

import numba as nb
import numpy as np
import pyamg
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import cht3d
import layouts
import props
import run_layouts

HERE = os.path.dirname(os.path.abspath(__file__))
RHO, NU, KF, CP = props.RHO, props.MU / props.RHO, props.KF, props.CP
SIDES = ((0, -1), (0, 1), (1, -1), (1, 1), (2, -1), (2, 1))       # (direction, sign): r-, r+, t-, t+, z-, z+


# ------------------------------------------------------------------------------------------------ topology
def build_topology(g, mdl):
    nr, nt, nz = g.shape
    fl = mdl.mat == 3
    fid = -np.ones(g.shape, np.int64)
    fid[fl] = np.arange(fl.sum())
    I, J, K = np.nonzero(fl)
    nc = len(I)
    rc, zc = g.rc, g.zc
    size = np.c_[g.dr[I], g.rc[I] * g.dt, g.dz[K]] * 1e-3                 # cell sizes (m) in r, t, z
    vol = (g.rc[I] * g.dr[I] * g.dt * g.dz[K]) * 1e-9
    # neighbour cells
    nbc = -np.ones((nc, 6), np.int64)
    for s_, (d, sg) in enumerate(SIDES):
        if d == 0:
            ii = I + sg; ok = (ii >= 0) & (ii < nr); nbc[ok, s_] = fid[ii[ok], J[ok], K[ok]]
        elif d == 1:
            jj = (J + sg) % nt; nbc[:, s_] = fid[I, jj, K]
        else:
            kk = K + sg; ok = (kk >= 0) & (kk < nz); nbc[ok, s_] = fid[I[ok], J[ok], kk[ok]]
    # faces: one per (cell, + side) with a fluid neighbour
    L, R, D, A, H, RF = [], [], [], [], [], []
    cface = -np.ones((nc, 6), np.int64)
    nf = 0
    for d in range(3):
        sp_ = 2 * d + 1
        c = np.nonzero(nbc[:, sp_] >= 0)[0]
        n = nbc[c, sp_]
        if d == 0:
            area = g.rf[I[c] + 1] * g.dt * g.dz[K[c]] * 1e-6; h = (g.rc[I[c] + 1] - g.rc[I[c]]) * 1e-3; rr = g.rf[I[c] + 1] * 1e-3
        elif d == 1:
            area = g.dr[I[c]] * g.dz[K[c]] * 1e-6; h = g.rc[I[c]] * g.dt * 1e-3; rr = g.rc[I[c]] * 1e-3
        else:
            area = 0.5 * (g.rf[I[c] + 1] ** 2 - g.rf[I[c]] ** 2) * g.dt * 1e-6; h = 0.5 * (g.dz[K[c]] + g.dz[K[c] + 1]) * 1e-3; rr = g.rc[I[c]] * 1e-3
        idx = np.arange(nf, nf + len(c))
        cface[c, sp_] = idx; cface[n, 2 * d] = idx
        L.append(c); R.append(n); D.append(np.full(len(c), d)); A.append(area); H.append(h); RF.append(rr)
        nf += len(c)
    L, R, D = np.concatenate(L), np.concatenate(R), np.concatenate(D)
    A, H, RF = np.concatenate(A), np.concatenate(H), np.concatenate(RF)
    # same-direction neighbour faces in the 6 directions (-1 = closed)
    nbf = -np.ones((nf, 6), np.int64)
    for s_, (k, sg) in enumerate(SIDES):
        own = D == k
        # along its own direction: far faces of L (minus side) and R (plus side)
        if sg < 0:
            nbf[own, s_] = cface[L[own], 2 * k]
        else:
            nbf[own, s_] = cface[R[own], 2 * k + 1]
        oth = ~own
        L2, R2 = nbc[L[oth], s_], nbc[R[oth], s_]
        ok = (L2 >= 0) & (R2 >= 0)
        f2 = np.full(oth.sum(), -1)
        f2[ok] = cface[L2[ok], 2 * D[oth][ok] + 1]
        good = f2 >= 0
        good[good] = R[f2[good]] == R2[good]
        f2[~good] = -1
        nbf[oth, s_] = f2
    # transverse velocity interpolation: for each other direction, the 4 faces of L and R
    tr = -np.ones((nf, 2, 4), np.int64)
    for d in range(3):
        m = D == d
        others = [k for k in range(3) if k != d]
        for o, k in enumerate(others):
            tr[m, o, 0] = cface[L[m], 2 * k]; tr[m, o, 1] = cface[L[m], 2 * k + 1]
            tr[m, o, 2] = cface[R[m], 2 * k]; tr[m, o, 3] = cface[R[m], 2 * k + 1]
    return dict(fid=fid, I=I, J=J, K=K, nc=nc, size=size, vol=vol, nbc=nbc, cface=cface,
                L=L, R=R, D=D, A=A, H=H, RF=RF, nbf=nbf, tr=tr, nf=nf)


# ------------------------------------------------------------------------------------------------ kernels
@nb.njit(parallel=True, cache=True)
def mom_step(U, Un, p, L, R, D, H, RF, nbf, tr, size, nu, beta, cfl, dts, active):
    nf = U.shape[0]
    for f in nb.prange(nf):
        if not active[f]:
            Un[f] = U[f]; continue
        d = D[f]; u = U[f]
        l, r = L[f], R[f]
        # transverse components
        o = 0
        vt = np.zeros(3)
        for k in range(3):
            if k == d:
                vt[k] = u; continue
            s = 0.0
            for q in range(4):
                g = tr[f, o, q]
                if g >= 0:
                    s += U[g]
            vt[k] = 0.25 * s
            o += 1
        adv = 0.0; lap = 0.0
        for k in range(3):
            fm = nbf[f, 2 * k]; fp = nbf[f, 2 * k + 1]
            if k == d:
                um = U[fm] if fm >= 0 else 0.0
                up = U[fp] if fp >= 0 else 0.0
                hm = size[l, k]; hp = size[r, k]
            else:
                um = U[fm] if fm >= 0 else -u
                up = U[fp] if fp >= 0 else -u
                hm = 0.5 * (size[l, k] + size[r, k]); hp = hm
            vel = vt[k]
            # second-order upwind where the second neighbour exists, first order next to walls
            if vel > 0:
                f2 = nbf[fm, 2 * k] if fm >= 0 else -1
                if f2 >= 0:
                    adv += vel * (3 * u - 4 * um + U[f2]) / (2 * hm)
                else:
                    adv += vel * (u - um) / hm
            else:
                f2 = nbf[fp, 2 * k + 1] if fp >= 0 else -1
                if f2 >= 0:
                    adv += vel * (-3 * u + 4 * up - U[f2]) / (2 * hp)
                else:
                    adv += vel * (up - u) / hp
            lap += ((up - u) / hp - (u - um) / hm) / (0.5 * (hp + hm))
        src = 0.0
        if d == 0:
            src = vt[1] * vt[1] / RF[f]
        elif d == 1:
            src = -vt[0] * u / RF[f]
        dpdx = (p[r] - p[l]) / H[f]
        hmin = min(H[f], min(size[l, 0], min(size[l, 1], size[l, 2])))
        dt = min(cfl * hmin / (abs(u) + beta), 0.1 * hmin * hmin / nu)   # 3-D explicit viscous limit is h^2/(6 nu)
        dts[f] = dt
        Un[f] = u + dt * (-adv + nu * lap + src - dpdx)


@nb.njit(parallel=True, cache=True)
def p_step(U, p, cface, A, vol, Sv, fixed, size, beta, cfl, div_out):
    nc = p.shape[0]
    for c in nb.prange(nc):
        flux = 0.0
        umax = 0.0
        for s in range(6):
            f = cface[c, s]
            if f >= 0:
                umax = max(umax, abs(U[f]))
                if s % 2 == 1:
                    flux += A[f] * U[f]
                else:
                    flux -= A[f] * U[f]
        dv = flux / vol[c] - Sv[c]
        div_out[c] = dv
        if fixed[c]:
            continue
        hmin = min(size[c, 0], min(size[c, 1], size[c, 2]))
        dt = cfl * hmin / (umax + beta)
        p[c] -= dt * beta * beta * dv


# ------------------------------------------------------------------------------------------------ ports
def ports(g, mdl, T):
    """inflow sources, outflow cells and enthalpy links from the 1-D network of the layout"""
    fid, nc = T["fid"], T["nc"]
    node_c = mdl.node[mdl.mat == 3]                                 # node of each fluid cell (fluid order)
    cells_of = {}
    for c, n in enumerate(node_c):
        cells_of.setdefault(int(n), []).append(c)
    nbc = T["nbc"]
    def adjacent(a, b):
        sb = set(b)
        return any(int(x) in sb for c in a for x in nbc[c] if x >= 0)
    src = []        # (cells, mass flow, link_from_cells or None)
    outs = []       # cells held at p = 0
    for n in mdl.inlets:
        src.append((cells_of.get(n, []), mdl.nodes_m[n], None))
    for n, m in mdl.outlets:
        outs.append(cells_of.get(n, []))
    links = 0
    for p in mdl.passages:
        n0 = p["first"]
        ups = mdl.nodes_up[n0]
        if n0 in mdl.inlets or not ups:
            continue
        if len(ups) != 1:
            continue                                   # manifolds / collectors are geometric, never links
        for (j, mj) in ups:
            cj = cells_of.get(j, []); c0 = cells_of.get(n0, [])
            if not cj or not c0:
                continue
            if not adjacent(cj, c0) and j == mdl.passages[mdl.nodes_pid[j]]["last"]:
                outs.append(cj); src.append((c0, mj, cj)); links += 1
    return src, outs, links


# ------------------------------------------------------------------------------------------------ flow
def solve_flow(g, mdl, T, iters=60000, cfl=0.5, check=1000, tol=2e-3, log=print):
    src, outs, nlinks = ports(g, mdl, T)
    nc, nf = T["nc"], T["nf"]
    Sv = np.zeros(nc)
    for cells, m, _ in src:
        cells = np.array(cells)
        V = T["vol"][cells].sum()
        Sv[cells] += (m / RHO) / V
    fixed = np.zeros(nc, np.bool_)
    for cells in outs:
        fixed[np.array(cells)] = True
    # initial guess: plug flow along the passage progress
    s_c = mdl.scell[mdl.mat == 3] * 1e-3
    pid_c = mdl.pid[mdl.mat == 3]
    Umean = np.array([p["m"] / (RHO * props.section(p["shape"])[1]) for p in mdl.passages])
    # near-developed start: velocity along the passage progress, parabolic in the distance to the wall,
    # scaled per passage to its mean velocity; pressure from the 1-D friction gradient
    from scipy import ndimage
    flm = mdl.mat == 3
    sampling = (float(np.median(g.dr)), float(np.median(g.rc) * g.dt), float(np.median(g.dz)))
    dist = ndimage.distance_transform_edt(np.pad(flm, ((0, 0), (1, 1), (0, 0)), mode="wrap"), sampling=sampling)[:, 1:-1, :][flm]
    hw = np.zeros(len(mdl.passages))
    np.maximum.at(hw, pid_c, dist)
    shape = dist * (2 * hw[pid_c] - dist) / np.maximum(hw[pid_c], 1e-9) ** 2
    norm = np.bincount(pid_c, weights=shape) / np.maximum(np.bincount(pid_c), 1)
    prof = shape / np.maximum(norm[pid_c], 1e-9)
    U = np.zeros(nf)
    same = pid_c[T["L"]] == pid_c[T["R"]]
    ds = s_c[T["R"]] - s_c[T["L"]]
    pf = 0.5 * (prof[T["L"]] + prof[T["R"]])
    U[same] = np.clip(ds[same] / T["H"][same], -1, 1) * Umean[pid_c[T["L"]][same]] * pf[same]
    # pressure: remaining 1-D friction drop to the passage end, plus everything downstream in series
    dp_p = np.array([p_["dp"] for p_ in mdl.passages]) / RHO
    down = np.zeros(len(mdl.passages))
    for i_, p_ in enumerate(mdl.passages):
        # passages fed by this one's last node
        nxt = [j for j, q in enumerate(mdl.passages) if any(u == p_["last"] for u, _ in mdl.nodes_up[q["first"]])]
        down[i_] = 0.0 if not nxt else max(dp_p[j] for j in nxt)
    Lp = np.array([p_["L"] for p_ in mdl.passages]) * 1e-3
    p = (dp_p[pid_c] * np.clip(1 - s_c / Lp[pid_c], 0, 1) + down[pid_c])
    p[np.array([c for cs in outs for c in cs], dtype=np.int64)] = 0.0
    taps = any(len(mdl.nodes_up[q["first"]]) == 1 and mdl.nodes_up[q["first"]][0][0] != mdl.passages[mdl.nodes_pid[mdl.nodes_up[q["first"]][0][0]]]["last"]
               for q in mdl.passages if mdl.nodes_up[q["first"]])
    if taps:
        p[:] = 0.0          # manifolds: per-passage 1-D pressures do not match at the taps; let the controller build p
    Un = U.copy(); U2 = U.copy(); dts = np.zeros(nf); div = np.zeros(nc)
    beta = max(2.5 * Umean.max(), 1.0)
    active = np.ones(nf, np.bool_)
    t0 = time.time()
    hist = []
    pin_cells = [np.array(c) for c, _, _ in src]
    prev = None
    for it in range(1, iters + 1):
        # Heun (RK2) for momentum: stable with the second-order upwind advection
        mom_step(U, Un, p, T["L"], T["R"], T["D"], T["H"], T["RF"], T["nbf"], T["tr"], T["size"], NU, beta, cfl, dts, active)
        mom_step(Un, U2, p, T["L"], T["R"], T["D"], T["H"], T["RF"], T["nbf"], T["tr"], T["size"], NU, beta, cfl, dts, active)
        U = 0.5 * (U + U2)
        p_step(U, p, T["cface"], T["A"], T["vol"], Sv, fixed, T["size"], beta, cfl, div)
        if it % check == 0:
            pin = max(float(p[c].mean()) for c in pin_cells) * RHO
            # outflow through the p = 0 cells (their net inflow) against the injected mass
            out_flow = float((div[fixed] + Sv[fixed]) @ T["vol"][fixed] * -RHO) if False else float(-(div[fixed] * T["vol"][fixed]).sum() * RHO)
            mass_res = abs(out_flow / sum(m for _, m, _ in src) - 1.0)
            if not np.isfinite(pin):
                raise FloatingPointError(f"flow solve diverged at iteration {it}")
            # flow-rate controller: rescale pressure (and velocity) toward the injected mass flow;
            # the steady state is unchanged, only the slow ACM pressure build-up is skipped
            ratio = out_flow / sum(m for _, m, _ in src)
            if 0.2 < ratio < 5 and abs(ratio - 1) > 0.01 and it <= iters - 3 * check:
                fac = float(np.clip((1 / ratio) ** 1.3, 0.8, 1.35))
                p *= fac
                U *= float(np.clip(1 / ratio, 0.85, 1.25))
            hist.append((it, pin, mass_res))
            log(f"    it {it:6d}  p_in {pin / 1e3:8.3f} kPa  mass residual {mass_res:.2e}  {time.time() - t0:.0f}s")
            if prev is not None and abs(pin - prev) < tol * abs(pin) and mass_res < 1e-2:
                break
            prev = pin
    return dict(U=U, p=p * RHO, Sv=Sv, fixed=fixed, src=src, outs=outs, links=nlinks, hist=hist, beta=beta,
                iters=it, seconds=time.time() - t0)


# ------------------------------------------------------------------------------------------------ heat
def solve_heat(g, mdl, T, F, flux):
    """steady conjugate energy: copper/foam/methanol cells, upwind advection with the CFD face fluxes"""
    nr, nt, nz = g.shape
    act = mdl.mat > 0
    gid = -np.ones(g.N, np.int64); gid[act.ravel()] = np.arange(act.sum()); N = int(act.sum())
    kcell = np.where(mdl.mat == 3, KF, mdl.k).ravel()
    idx = np.arange(g.N).reshape(g.shape)
    rows, cols, vals = [], [], []
    Ar = (g.rf[1:-1][:, None, None] * g.dt * g.dz[None, None, :]) * np.ones((1, nt, 1))
    da = 0.5 * g.dr[:-1][:, None, None] * np.ones((1, nt, nz)); db = 0.5 * g.dr[1:][:, None, None] * np.ones((1, nt, nz))
    ex = mdl.contact.get("r", np.zeros_like(Ar))
    faces = [(idx[:-1], idx[1:], Ar, da, db, ex)]
    At = (g.dr[:, None, None] * g.dz[None, None, :]) * np.ones((1, nt, 1)); dd = 0.5 * g.rc[:, None, None] * g.dt * np.ones((1, nt, nz))
    faces.append((idx, np.roll(idx, -1, axis=1), At, dd, dd, np.zeros_like(At)))
    Az = (0.5 * (g.rf[1:] ** 2 - g.rf[:-1] ** 2) * g.dt)[:, None, None] * np.ones((1, nt, nz - 1))
    da = 0.5 * g.dz[:-1][None, None, :] * np.ones((nr, nt, 1)); db = 0.5 * g.dz[1:][None, None, :] * np.ones((nr, nt, 1))
    faces.append((idx[:, :, :-1], idx[:, :, 1:], Az, da, db, np.zeros_like(Az)))
    for a, b, Af, d1, d2, e in faces:
        a = a.ravel(); b = b.ravel(); Af = Af.ravel() * 1e-6; d1 = d1.ravel() * 1e-3; d2 = d2.ravel() * 1e-3; e = e.ravel()
        ok = (gid[a] >= 0) & (gid[b] >= 0)
        Gc = Af[ok] / (d1[ok] / kcell[a[ok]] + d2[ok] / kcell[b[ok]] + e[ok])
        ia, ib = gid[a[ok]], gid[b[ok]]
        rows += [ia, ib, ia, ib]; cols += [ib, ia, ia, ib]; vals += [-Gc, -Gc, Gc, Gc]
    # advection on fluid-fluid faces (advective upwind form: inflow faces only)
    fl_flat = np.nonzero((mdl.mat == 3).ravel())[0]
    gL, gR = gid[fl_flat[T["L"]]], gid[fl_flat[T["R"]]]
    Fm = RHO * CP * F                                              # W/K, positive from L to R
    pos = Fm > 0
    # into R from L when F>0: rcp F (T_R - T_L) ; into L from R when F<0: rcp |F| (T_L - T_R)
    rows += [gR[pos], gR[pos], gL[~pos], gL[~pos]]
    cols += [gR[pos], gL[pos], gL[~pos], gR[~pos]]
    vals += [Fm[pos], -Fm[pos], -Fm[~pos], Fm[~pos]]
    b = np.zeros(N)
    for fl in flux.values():
        ids, q = fl
        ok = gid[ids] >= 0
        np.add.at(b, gid[ids[ok]], q[ok])
    # sources: inflow ports and links
    inlet_rows = []
    for cells, m, link in F_src(T):
        pass
    A = None
    return rows, cols, vals, b, gid, N, fl_flat


def F_src(T):
    return []


def assemble_and_solve_heat(g, mdl, T, flow, flux):
    rows, cols, vals, b, gid, N, fl_flat = solve_heat(g, mdl, T, flow["U"] * T["A"], flux)
    b_in = np.zeros(N)
    # outflow-port enthalpy: the advective form needs nothing extra; inflow sources:
    for cells, m, link in flow["src"]:
        cells = np.array(cells)
        V = T["vol"][cells]
        w = V / V.sum()
        gi = gid[fl_flat[cells]]
        G = RHO * 0 + CP * m * w                                     # W/K per source cell
        rows.append(gi); cols.append(gi); vals.append(G)
        if link is None:
            b_in[gi] += G                                           # times T_in (=1 for the unit inlet solve)
        else:
            lc = np.array(link)
            # mixed temperature of the upstream end cells, weighted by their volume (plug assumption)
            wl = T["vol"][lc] / T["vol"][lc].sum()
            gl = gid[fl_flat[lc]]
            rr = np.repeat(gi, len(gl)); cc = np.tile(gl, len(gi)); vv = -np.outer(G, wl).ravel()
            rows.append(rr); cols.append(cc); vals.append(vv)
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N))
    # solve twice: heat with T_in = 0, and the unit-inlet response (to centre the wall)
    isf = np.zeros(N, bool); isf[gid[fl_flat]] = True
    t0 = time.time()
    lu_f = spla.splu(A[isf][:, isf].tocsc())
    Acc = A[~isf][:, ~isf].tocsr()
    ml = pyamg.smoothed_aggregation_solver(Acc, max_coarse=2000)
    Acf = A[~isf][:, isf]; Afc = A[isf][:, ~isf]
    perm_c = np.nonzero(~isf)[0]; perm_f = np.nonzero(isf)[0]
    def prec(v):
        xc = ml.solve(v[perm_c], tol=1e-3, maxiter=2)
        xf = lu_f.solve(v[perm_f] - Afc @ xc)
        out = np.zeros(N); out[perm_c] = xc; out[perm_f] = xf
        return out
    M = spla.LinearOperator(A.shape, prec)
    sols = []
    for rhs in (b, b_in):
        x, info = spla.gmres(A, rhs, M=M, rtol=1e-10, restart=200, maxiter=500)
        sols.append((x, info, float(np.linalg.norm(A @ x - rhs) / max(np.linalg.norm(rhs), 1e-30))))
    return sols, gid, fl_flat, time.time() - t0


# ------------------------------------------------------------------------------------------------ driver
def run(name, m_gs, iters=60000, dr=0.4, dz=0.4, nt=180, out=None, log=print):
    layouts.REFINE[0] = True
    m = m_gs * 1e-3
    g, mdl = layouts.build(name, m, dr, dz, nt)
    R_band = {"A_built": 25.1, "B": 32.0}.get(name, 27.0)
    axi = run_layouts.axi_split(R_band)
    flux = cht3d.apply_flux(mdl, axi["surf"], mdl.Q_sheet)
    T = build_topology(g, mdl)
    log(f"  {name} {m_gs} g/s: {T['nc']:,} methanol cells, {T['nf']:,} faces, grid {g.shape}")
    try:
        flow = solve_flow(g, mdl, T, iters=iters, log=log)
    except FloatingPointError as e:
        log(f"  {e}; retrying with a smaller pseudo-time step (CFL 0.3)")
        flow = solve_flow(g, mdl, T, iters=int(iters * 1.5), cfl=0.3, log=log)
    sols, gid, fl_flat, tsec = assemble_and_solve_heat(g, mdl, T, flow, flux)
    (x0, i0, r0), (x1, i1, r1) = sols
    # x = x0 + T_in * x1 ; wall at r = 13.5 (first radial layer of copper)
    Tc0 = np.full(g.N, np.nan); Tc1 = np.full(g.N, np.nan)
    ok = gid >= 0
    Tc0[ok] = x0[gid[ok]]; Tc1[ok] = x1[gid[ok]]
    Tc0 = Tc0.reshape(g.shape); Tc1 = Tc1.reshape(g.shape)
    Tw0 = Tc0[0]; Tw1 = Tc1[0]
    # the inner wall responds to T_in with gain ~1 (all heat leaves through the coolant)
    gain = float(np.nanmean(Tw1))
    # choose T_in so that the wall is centred on -30: Tw = Tw0 + T_in * Tw1
    Tin = (-30.0 - 0.5 * (np.nanmax(Tw0) + np.nanmin(Tw0))) / gain
    Tw = Tw0 + Tin * Tw1
    spread = float(np.nanmax(Tw) - np.nanmin(Tw))
    Tfield = Tc0 + Tin * Tc1
    # pressure drop: inlet port mean pressure (sum over series links)
    pin = [float(flow["p"][np.array(c)].mean()) for c, _, l in flow["src"]]
    # worst series path: a link source adds the entry pressure of the passage that feeds it (recursively)
    pid_f = mdl.pid[mdl.mat == 3]
    node_f = mdl.node[mdl.mat == 3]
    src_of_pid = {}
    for i_, (c, _, l) in enumerate(flow["src"]):
        src_of_pid.setdefault(int(pid_f[np.array(c)][0]), i_)
    def entry(q, depth=0):
        if depth > 50:
            return 0.0
        i_ = src_of_pid.get(q)
        if i_ is not None:
            return total(i_, depth + 1)
        first = mdl.passages[q]["first"]
        cells = np.nonzero(node_f == first)[0]
        return float(flow["p"][cells].mean()) if len(cells) else 0.0
    def total(i_, depth=0):
        c, _, l = flow["src"][i_]
        if l is None:
            return pin[i_]
        return pin[i_] + entry(int(pid_f[np.array(l)][0]), depth + 1)
    dp_series = max(total(i_) for i_ in range(len(flow["src"])))
    # outlet temperature: mean over outlet cells
    Tf = Tfield[mdl.mat == 3]
    Tout = float(np.mean([Tf[np.array(c)].mean() for c in flow["outs"][: len(mdl.outlets)]]))
    # velocities at cell centres for visualisation
    U = flow["U"]
    vc = np.zeros((T["nc"], 3))
    cnt = np.zeros((T["nc"], 3))
    for side in range(6):
        f = T["cface"][:, side]; okf = f >= 0
        d = side // 2
        vc[okf, d] += U[f[okf]]; cnt[okf, d] += 1
    vc = np.where(cnt > 0, vc / np.maximum(cnt, 1), 0.0)
    speed = np.linalg.norm(vc, axis=1)
    Q = float(sum(v[1].sum() for v in flux.values()))
    res = dict(layout=name, m_gs=m_gs, cells_fluid=int(T["nc"]), faces=int(T["nf"]), grid=list(g.shape),
               iters=flow["iters"], flow_seconds=flow["seconds"], heat_seconds=tsec, links=flow["links"],
               dp_kPa=dp_series / 1e3, p_inlets_kPa=[x / 1e3 for x in pin], spread_mK=spread * 1e3, inlet_C=Tin,
               wall_gain=gain, rise_mK=(Tout - Tin) * 1e3, Q_W=Q, umax=float(speed.max()), umean=float(speed.mean()),
               heat_residuals=[r0, r1], mass_residual=flow["hist"][-1][2] if flow["hist"] else None,
               flow_hist=flow["hist"])
    if out:
        np.savez_compressed(out, rc=g.rc, tc=g.tc, zc=g.zc, rf=g.rf, mat=mdl.mat, I=T["I"], J=T["J"], K=T["K"],
                            vel=vc.astype(np.float32), p=flow["p"].astype(np.float32), Tf=Tf.astype(np.float32),
                            Tcu=np.where(mdl.mat > 0, Tfield, np.nan).astype(np.float32), Tw=Tw.astype(np.float32),
                            pid=mdl.pid[mdl.mat == 3], s=mdl.scell[mdl.mat == 3].astype(np.float32),
                            src_cells=np.concatenate([np.array(c) for c, _, _ in flow["src"]]),
                            out_cells=np.concatenate([np.array(c) for c in flow["outs"]]))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("layouts", nargs="*"); ap.add_argument("--flows", default="17.5")
    ap.add_argument("--iters", type=int, default=60000); ap.add_argument("--tag", default="cfd")
    a = ap.parse_args()
    outj = os.path.join(HERE, "results", f"coolant_{a.tag}.json")
    allr = json.load(open(outj)) if os.path.exists(outj) else []
    for nm in a.layouts or layouts.LAYOUTS:
        for fgs in [float(x) for x in a.flows.split(",")]:
            r = run(nm, fgs, a.iters, out=os.path.join(HERE, "results", f"coolant_{a.tag}_{nm}_{fgs:g}.npz"),
                    log=lambda s: print(s, flush=True))
            allr = [x for x in allr if not (x["layout"] == nm and x["m_gs"] == fgs)] + [r]
            json.dump(allr, open(outj, "w"), indent=1)
            print(f"{nm:8s} {fgs:5.1f} g/s  CFD spread {r['spread_mK']:.1f} mK  inlet {r['inlet_C']:.3f}  dp {r['dp_kPa']:.2f} kPa  "
                  f"rise {r['rise_mK']:.0f} mK  umax {r['umax']:.2f} m/s  it {r['iters']}  {r['flow_seconds']:.0f}+{r['heat_seconds']:.0f}s", flush=True)
