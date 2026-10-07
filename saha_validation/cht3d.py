"""Independent 3-D conjugate model of one SAHA copper zone (Zone 1) with a 1-D coolant network.

Finite-volume conduction on a cylindrical (r, theta, z) grid: copper wall r 13.5-15, carrier / buffer, end plates
r 13.5-43 x 11 mm.  Coolant passages are voxelised; every copper face that touches a passage cell is coupled to the
coolant node of that passage segment through 1/(d/2k + 1/h).  h comes from developed-flow correlations and is scaled
so that h * (voxel wetted area) = h * (true wetted area).  The coolant network is an upwind energy balance per node
(m cp T_i = sum_j m_ji cp T_j + sum G (T_cu - T_i)).  The external heat is a Neumann flux on the copper boundary,
taken from the axisymmetric chamber model (heatload_axi.py) and scaled to the requested total.
Everything is linear, so one solve gives the field for any inlet: the inlet that centres the inner wall is
T_in = -30 - (Tmax + Tmin)/2 when the solve uses T_in = -30 and the set point is -30.
"""
import time

import numpy as np
import pyamg
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import props

K_CU, K_FOAM, K_SOLDER = 390.0, 0.035, 50.0


def axis(breaks, dmax):
    pts = [breaks[0]]
    for a, b in zip(breaks[:-1], breaks[1:]):
        dm = dmax(a, b) if callable(dmax) else dmax
        n = max(1, int(np.ceil((b - a) / dm - 1e-9)))
        pts += list(np.linspace(a, b, n + 1)[1:])
    return np.array(pts)


class Grid:
    def __init__(self, r_breaks, z_breaks, ntheta=180, dr_fine=0.5, dz_fine=0.5, r_fine_max=36.0):
        self.rf = axis(sorted(set(r_breaks)), lambda a, b: dr_fine if b <= r_fine_max + 1e-9 else 2.0)
        self.zf = axis(sorted(set(z_breaks)), lambda a, b: dz_fine if (a >= -1e-9 and b <= 96 + 1e-9) else 1.0)
        self.nt = ntheta
        self.tf = np.linspace(0, 2 * np.pi, ntheta + 1)
        self.rc = 0.5 * (self.rf[1:] + self.rf[:-1]); self.zc = 0.5 * (self.zf[1:] + self.zf[:-1])
        self.tc = 0.5 * (self.tf[1:] + self.tf[:-1])
        self.dr, self.dz, self.dt = np.diff(self.rf), np.diff(self.zf), 2 * np.pi / ntheta
        self.shape = (len(self.rc), ntheta, len(self.zc))
        self.R, self.T, self.Z = np.meshgrid(self.rc, self.tc, self.zc, indexing="ij")
        self.N = int(np.prod(self.shape))


class Model:
    """material: 0 = outside (inactive), 1 = copper, 2 = foam, 3 = fluid (passage)"""

    def __init__(self, g):
        self.g = g
        self.mat = np.zeros(g.shape, np.int8)
        self.k = np.zeros(g.shape)
        self.node = -np.ones(g.shape, np.int64)        # coolant node of a fluid cell
        self.pid = -np.ones(g.shape, np.int64)         # passage id of a fluid cell
        self.contact = {}                               # extra interface resistance on r-faces: mask over r-face array
        self.passages = []
        self.nodes_m, self.nodes_up, self.nodes_pid, self.nodes_s = [], [], [], []
        self.inlets = []                                # node ids fed from the inlet at T_in
        self.outlets = []                               # (node id, mass flow)

    # ---------------- materials
    def set_copper(self, mask):
        self.mat[mask] = 1; self.k[mask] = K_CU

    def set_foam(self, mask):
        self.mat[mask] = 2; self.k[mask] = K_FOAM

    # ---------------- passages
    def add_passage(self, name, mask, s, L, shape, m, coil_D=None, ds=2.0, nu_override=None, turbulent=False):
        """mask: cells of the passage (not yet fluid), s: progress along it (mm) for those cells"""
        mask = mask & (self.mat != 3)
        pid = len(self.passages)
        nseg = max(1, int(np.ceil(L / ds)))
        seg = np.clip((s[mask] / L * nseg).astype(int), 0, nseg - 1)
        n0 = len(self.nodes_m)
        for i in range(nseg):
            self.nodes_m.append(m); self.nodes_up.append([(n0 + i - 1, m)] if i else []); self.nodes_pid.append(pid)
            self.nodes_s.append((i + 0.5) * L / nseg)
        self.mat[mask] = 3; self.k[mask] = 0; self.node[mask] = n0 + seg; self.pid[mask] = pid
        h, Re, f = props.passage_htc(shape, m, coil_D, nu_override, turbulent)
        P = props.section(shape)[2]
        self.passages.append(dict(name=name, first=n0, last=n0 + nseg - 1, L=L, shape=shape, m=m, h=h, Re=Re, f=f,
                                  A_true=P * L * 1e-3, coil_D=coil_D, dp=props.dp(shape, m, L, f), ncell=int(mask.sum())))
        return pid

    def connect(self, pid_down, upstream):
        """upstream: list of (node id, mass flow) feeding the first node of passage pid_down; 'in' for the inlet"""
        n = self.passages[pid_down]["first"]
        if upstream == "in":
            self.nodes_up[n] = []; self.inlets.append(n)
        else:
            self.nodes_up[n] = list(upstream)

    def first(self, pid):
        return self.passages[pid]["first"]

    def last(self, pid):
        return self.passages[pid]["last"]

    def node_at(self, pid, s):
        p = self.passages[pid]; nseg = p["last"] - p["first"] + 1
        return p["first"] + int(np.clip(s / p["L"] * nseg, 0, nseg - 1))

    # ---------------- solve
    def assemble(self, flux):
        """flux: dict of boundary patches -> array of W per boundary face, built by apply_flux()"""
        g = self.g
        nr, nt, nz = g.shape
        idx = np.arange(g.N).reshape(g.shape)
        act = (self.mat == 1) | (self.mat == 2)
        cell_id = -np.ones(g.N, np.int64)
        cell_id[act.ravel()] = np.arange(act.sum())
        nc = int(act.sum()); nn = len(self.nodes_m)
        # face lists in each direction: (a, b, area, da, db)
        faces = []
        Ar = (g.rf[1:-1][:, None, None] * g.dt * g.dz[None, None, :]) * np.ones((1, nt, 1))
        da = 0.5 * g.dr[:-1][:, None, None] * np.ones((1, nt, nz)); db = 0.5 * g.dr[1:][:, None, None] * np.ones((1, nt, nz))
        extra = self.contact.get("r", np.zeros_like(Ar))
        faces.append((idx[:-1], idx[1:], Ar, da, db, extra))
        At = (g.dr[:, None, None] * g.dz[None, None, :]) * np.ones((1, nt, 1))
        dd = 0.5 * g.rc[:, None, None] * g.dt * np.ones((1, nt, nz))
        faces.append((idx, np.roll(idx, -1, axis=1), At, dd, dd, np.zeros_like(At)))
        Az = (0.5 * (g.rf[1:] ** 2 - g.rf[:-1] ** 2) * g.dt)[:, None, None] * np.ones((1, nt, nz - 1))
        da = 0.5 * g.dz[:-1][None, None, :] * np.ones((nr, nt, 1)); db = 0.5 * g.dz[1:][None, None, :] * np.ones((nr, nt, 1))
        faces.append((idx[:, :, :-1], idx[:, :, 1:], Az, da, db, np.zeros_like(Az)))
        k = self.k.ravel(); mat = self.mat.ravel(); node = self.node.ravel(); pid = self.pid.ravel()
        hp = np.array([p["h"] for p in self.passages])
        rows, cols, vals = [], [], []
        cf_c, cf_n, cf_G, cf_A = [], [], [], []           # cell-coolant couplings
        for a, b, A, d1, d2, ex in faces:
            a = a.ravel(); b = b.ravel(); A = A.ravel() * 1e-6; d1 = d1.ravel() * 1e-3; d2 = d2.ravel() * 1e-3; ex = ex.ravel()
            ma, mb = mat[a], mat[b]
            both = ((ma == 1) | (ma == 2)) & ((mb == 1) | (mb == 2))
            G = A[both] / (d1[both] / k[a[both]] + d2[both] / k[b[both]] + ex[both])
            ia, ib = cell_id[a[both]], cell_id[b[both]]
            rows += [ia, ib, ia, ib]; cols += [ib, ia, ia, ib]; vals += [-G, -G, G, G]
            for (s1, s2, dd_) in ((a, b, d1), (b, a, d2)):
                m1 = ((mat[s1] == 1) | (mat[s1] == 2)) & (mat[s2] == 3)
                cf_c.append(cell_id[s1[m1]]); cf_n.append(node[s2[m1]]); cf_A.append(A[m1])
                cf_G.append(dd_[m1] / k[s1[m1]])          # conduction part, combined with h below
        cf_c = np.concatenate(cf_c); cf_n = np.concatenate(cf_n); cf_A = np.concatenate(cf_A); cf_R = np.concatenate(cf_G)
        npid = np.array(self.nodes_pid)[cf_n]
        # scale h so that h_eff * voxel area = h * true area, per passage
        A_vox = np.bincount(npid, weights=cf_A, minlength=len(self.passages))
        for i, p in enumerate(self.passages):
            p["A_vox"] = A_vox[i]; p["h_eff"] = p["h"] * p["A_true"] / A_vox[i] if A_vox[i] > 0 else 0
        heff = np.array([p["h_eff"] for p in self.passages])[npid]
        Gc = cf_A / (cf_R + 1 / heff)
        self.Gc = Gc; self.cf_c = cf_c; self.cf_n = cf_n
        for i, p in enumerate(self.passages):
            p["UA"] = float(Gc[npid == i].sum())
        # coolant rows (index nc + node)
        cp = props.CP
        m = np.array(self.nodes_m)
        r_ = [cf_c, nc + cf_n, cf_c, nc + cf_n]; c_ = [nc + cf_n, cf_c, cf_c, nc + cf_n]; v_ = [-Gc, -Gc, Gc, Gc]
        rows += r_; cols += c_; vals += v_
        un, uj, um = [], [], []
        for i, ups in enumerate(self.nodes_up):
            for j, mj in ups:
                un.append(nc + i); uj.append(nc + j); um.append(-cp * mj)
        rows += [np.array(un), np.arange(nc, nc + nn)]; cols += [np.array(uj), np.arange(nc, nc + nn)]
        vals += [np.array(um), cp * m]
        Atot = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nc + nn, nc + nn))
        b = np.zeros(nc + nn)
        for fl in flux.values():
            ids, q = fl
            okc = cell_id[ids] >= 0
            np.add.at(b, cell_id[ids[okc]], q[okc])
            okf = mat[ids] == 3
            np.add.at(b, nc + node[ids[okf]], q[okf])
        self.cell_id, self.nc, self.nn, self.A, self.b = cell_id, nc, nn, Atot, b

    def solve(self, T_in=0.0, q_fric=None, tol=1e-11):
        nc, nn = self.nc, self.nn
        b = self.b.copy()
        for n in self.inlets:
            b[nc + n] += props.CP * self.nodes_m[n] * T_in
        if q_fric is not None:
            b[nc:] += q_fric
        A = self.A
        Acc = A[:nc, :nc].tocsr(); Aff = A[nc:, nc:].tocsc(); Afc = A[nc:, :nc].tocsr()
        t0 = time.time()
        ml = pyamg.smoothed_aggregation_solver(Acc, max_coarse=2000)
        luf = spla.splu(Aff)
        def prec(v):
            xc = ml.solve(v[:nc], tol=1e-3, maxiter=2, cycle="V")
            xf = luf.solve(v[nc:] - Afc @ xc)
            return np.r_[xc, xf]
        M = spla.LinearOperator(A.shape, prec)
        it = [0]
        x, info = spla.gmres(A, b, M=M, rtol=tol, restart=200, maxiter=2000, callback=lambda r: it.__setitem__(0, it[0] + 1),
                             callback_type="pr_norm")
        res = np.linalg.norm(A @ x - b) / np.linalg.norm(b)
        self.solve_info = dict(info=info, iters=it[0], rel_res=float(res), seconds=time.time() - t0)
        T = np.full(self.g.N, np.nan)
        act = self.cell_id >= 0
        T[act] = x[self.cell_id[act]]
        self.Tcell = T.reshape(self.g.shape); self.Tnode = x[nc:]
        return self.Tcell, self.Tnode


def boundary_faces(model, side):
    """returns flat cell ids and face areas (m2) of copper/active boundary faces on a side"""
    g = model.g
    nr, nt, nz = g.shape
    idx = np.arange(g.N).reshape(g.shape)
    act = model.mat > 0
    out_ids, out_A, out_pos = [], [], []
    if side in ("r_in", "r_out"):
        # faces in r direction between active and inactive (or domain edge)
        pad = np.zeros((nr + 2, nt, nz), bool); pad[1:-1] = act
        if side == "r_out":
            m = pad[1:-1] & ~pad[2:]
            i, j, kk = np.nonzero(m); rface = g.rf[i + 1]
        else:
            m = pad[1:-1] & ~pad[:-2]
            i, j, kk = np.nonzero(m); rface = g.rf[i]
        A = rface * g.dt * g.dz[kk] * 1e-6
        return idx[i, j, kk], A, rface, g.zc[kk]
    pad = np.zeros((nr, nt, nz + 2), bool); pad[:, :, 1:-1] = act
    if side == "z_top":
        m = pad[:, :, 1:-1] & ~pad[:, :, 2:]; i, j, kk = np.nonzero(m); zface = g.zf[kk + 1]
    else:
        m = pad[:, :, 1:-1] & ~pad[:, :, :-2]; i, j, kk = np.nonzero(m); zface = g.zf[kk]
    A = 0.5 * (g.rf[i + 1] ** 2 - g.rf[i] ** 2) * g.dt * 1e-6
    return idx[i, j, kk], A, g.rc[i], zface


def apply_flux(model, split, Q_total, zoff=258.0):
    """distribute the axisymmetric Zone-1 surface heat onto the 3-D boundary.
    split: list of (kind, r, z, q) for zone 1 from heatload_axi (z absolute; local z = z - 258).
    Each axisymmetric face's heat is spread over the 3-D faces of the same patch by area at matching position."""
    import collections
    pat = collections.defaultdict(list)
    for zn, kind, r, z, q in split:
        if zn != 2:
            continue
        zl = z - zoff
        if kind == "r_in" and abs(r - 13.5) < 1e-6: pat["bore"].append((zl, q))
        elif kind == "r_out" and abs(r - 43) < 1e-6: pat["rim"].append((zl, q))
        elif kind == "r_out": pat["band"].append((zl, q))
        elif kind == "z_bot" and abs(zl + 11) < 1e-6: pat["bottom"].append((r, q))
        elif kind == "z_top" and abs(zl - 107) < 1e-6: pat["top"].append((r, q))
        elif kind == "z_top": pat["lower_inner"].append((r, q))
        else: pat["upper_inner"].append((r, q))
    tot = sum(q for v in pat.values() for _, q in v)
    scale = Q_total / tot
    flux = {}
    # flux density as function of position: q per unit length (z) or per unit radius
    def density(lst):
        x = np.array([a for a, _ in lst]); q = np.array([b for _, b in lst]); o = np.argsort(x)
        x, q = x[o], q[o]
        # cell widths from midpoints
        e = np.r_[x[0] - (x[1] - x[0]) / 2, 0.5 * (x[1:] + x[:-1]), x[-1] + (x[-1] - x[-2]) / 2]
        return x, q / np.diff(e), (e[0], e[-1])
    g = model.g
    ids, A, rr, zz = boundary_faces(model, "r_in")
    x, qd, _ = density(pat["bore"])
    w = np.interp(zz, x, qd) * A / (2 * np.pi * rr * 1e-3) * 1e3        # W per face = q'(z)[W/mm] * dz[mm] / ntheta
    flux["bore"] = (ids, w * scale)
    ids, A, rr, zz = boundary_faces(model, "r_out")
    rim = rr > 42.9
    x, qd, _ = density(pat["rim"]); w_rim = np.interp(zz, x, qd) * A / (2 * np.pi * rr * 1e-3) * 1e3
    x, qd, _ = density(pat["band"]); w_band = np.interp(zz, x, qd) * A / (2 * np.pi * rr * 1e-3) * 1e3
    w_rim *= sum(q for _, q in pat["rim"]) / w_rim[rim].sum()
    w_band *= sum(q for _, q in pat["band"]) / w_band[~rim].sum()
    flux["r_out"] = (ids, np.where(rim, w_rim, w_band) * scale)
    for side, key_out, key_in in (("z_bot", "bottom", "upper_inner"), ("z_top", "top", "lower_inner")):
        ids, A, rr, zz = boundary_faces(model, side)
        outer = (zz < -10.9) if side == "z_bot" else (zz > 106.9)
        res = np.zeros(len(ids))
        for key, sel in ((key_out, outer), (key_in, ~outer)):
            if not pat[key] or not sel.any():
                continue
            x, qd, _ = density(pat[key])
            Qkey = sum(q for _, q in pat[key])
            # spread over the selected faces in proportion to the radial density, normalised to the patch heat
            wv = np.interp(rr[sel], x, qd, left=0, right=0) * A[sel] / (2 * np.pi * rr[sel] * 1e-3 * 1e-3) / 1e3
            wv *= Qkey / wv.sum() if wv.sum() > 0 else 0
            res[sel] = wv
        flux[side] = (ids, res * scale)
    model.flux_total = sum(v[1].sum() for v in flux.values())
    return flux


def inner_wall(model, flux):
    """inner copper surface temperature T(theta, z) at r = 13.5 (first cell + half-cell flux correction)"""
    g = model.g
    T0 = model.Tcell[0]                      # (nt, nz)
    ids, w = flux["bore"]
    q = np.zeros(g.N); np.add.at(q, ids, w)
    q = q.reshape(g.shape)[0]
    A = g.rf[0] * g.dt * g.dz[None, :] * 1e-6
    return T0 + q / A * (0.5 * g.dr[0] * 1e-3) / K_CU
