"""Room / insulation side of the vapour-column coupling (axisymmetric conduction, no radiation).

The solid chamber (Perspex, foam, copper held at set point, lab Robin h to 35 C, ice tray 0 C) is solved with the vapour
column cut out.  On every face where the vapour touches Perspex (connector walls r = 13.5 and the cap underside
z = 423.5) a heat flow q (W, positive = from the solid INTO the vapour) is prescribed.  The matrix is factorised once.

Outputs used by the 3-D vapour model (the same quantities as the coupled deck, slide 3):
  G_out  outside conductance of each Perspex face (W/m2K), from a +1 K perturbation of the vapour
  T_ext  environment temperature seen by the face:  q = G_out (T_ext - T_wall)
and room_solve(q) -> wall temperatures + zone heat gains through the solids for the two-way exchange.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

KV, KP, KF, KC = 0.009788, 0.19, 0.035, 390.0
H_LAB, T_LAB = 8.0, 35.0
R_IN, R_VES, R_BAND, R_PL, R_OUT = 13.5, 15.0, 25.1, 43.0, 93.0
Z_CAP, Z_TOP, Z_OUT = 423.5, 425.0, 475.0


def axis(breaks, d):
    pts = [breaks[0]]
    for a, b in zip(breaks[:-1], breaks[1:]):
        n = max(1, int(np.ceil((b - a) / d - 1e-9)))
        pts += list(np.linspace(a, b, n + 1)[1:])
    return np.array(pts)


class Room:
    def __init__(self, d=0.5, h=H_LAB, T_lab=T_LAB):
        rf = axis(sorted({0, R_IN, R_VES, R_BAND, R_PL, R_OUT}), d)
        zf = axis(sorted({0, 60, 71, 176, 187, 247, 258, 354, 365, Z_CAP, Z_TOP, Z_OUT}), d)
        self.rf, self.zf = rf, zf
        rc, zc = 0.5 * (rf[1:] + rf[:-1]), 0.5 * (zf[1:] + zf[:-1])
        self.rc, self.zc = rc, zc
        nr, nz = len(rc), len(zc)
        R, Z = np.meshgrid(rc, zc, indexing="ij")
        mat = np.full((nr, nz), 3)
        vap = (R < R_IN) & (Z < Z_CAP); mat[vap] = 0
        pm = ((R > R_IN) & (R < R_VES) & (Z < Z_TOP)) | ((R < R_VES) & (Z > Z_CAP) & (Z < Z_TOP)); mat[pm] = 1
        zone = np.zeros((nr, nz), int)
        for iz, (z0, z1) in enumerate([(60, 187), (247, 365)], start=1):
            cu = (Z > z0) & (Z < z1) & (R > R_IN) & ((R < R_BAND) | (R < R_PL) & ((Z < z0 + 11) | (Z > z1 - 11)))
            mat[cu] = 2; zone[cu] = iz
        k = np.choose(mat, [KV, KP, KC, KF]).astype(float)
        self.mat, self.zone = mat, zone
        rfm, zfm = rf * 1e-3, zf * 1e-3
        dr, dz = np.diff(rfm), np.diff(zfm)
        Ar = 2 * np.pi * rfm[1:-1][:, None] * dz[None, :]
        Az = (np.pi * (rfm[1:] ** 2 - rfm[:-1] ** 2))[:, None] * np.ones((1, nz - 1))
        Gr = Ar / (0.5 * dr[:-1, None] / k[:-1] + 0.5 * dr[1:, None] / k[1:])
        Gz = Az / (0.5 * dz[None, :-1] / k[:, :-1] + 0.5 * dz[None, 1:] / k[:, 1:])
        idx = np.arange(nr * nz).reshape(nr, nz)
        solid_free = (mat == 1) | (mat == 3)                       # unknowns
        self.uid = -np.ones(nr * nz, int); self.uid[solid_free.ravel()] = np.arange(solid_free.sum())
        nu = int(solid_free.sum())
        rows, cols, vals = [], [], []
        b = np.zeros(nu)
        Tcu = np.where(zone == 1, -15.0, -30.0)
        uid = self.uid.reshape(nr, nz)
        def add_pairs(a_, b_, G):
            a_, b_, G = a_.ravel(), b_.ravel(), G.ravel()
            ma, mb = mat.ravel()[a_], mat.ravel()[b_]
            fa, fb = (ma == 1) | (ma == 3), (mb == 1) | (mb == 3)
            both = fa & fb
            ia, ib = self.uid[a_[both]], self.uid[b_[both]]
            rows.extend([ia, ib, ia, ib]); cols.extend([ib, ia, ia, ib]); vals.extend([-G[both], -G[both], G[both], G[both]])
            for s1, s2, m1 in ((a_, b_, fa & (mb == 2)), (b_, a_, fb & (ma == 2))):
                i1 = self.uid[s1[m1]]
                rows.append(i1); cols.append(i1); vals.append(G[m1])
                np.add.at(b, i1, G[m1] * Tcu.ravel()[s2[m1]])
        add_pairs(idx[:-1], idx[1:], Gr)
        add_pairs(idx[:, :-1], idx[:, 1:], Gz)
        # vapour faces: r faces between vapour (i) and Perspex (i+1); z faces between vapour (j) and cap (j+1)
        vf = []                                                   # (unknown id of solid cell, area, half-dist/k, z or r, kind)
        for i in range(nr - 1):
            for j in np.nonzero((mat[i] == 0) & (mat[i + 1] == 1))[0]:
                vf.append((uid[i + 1, j], Ar[i, j], 0.5 * dr[i + 1] / k[i + 1, j], zc[j], "wall"))
        for j in range(nz - 1):
            for i in np.nonzero((mat[:, j] == 0) & (mat[:, j + 1] == 1))[0]:
                vf.append((uid[i, j + 1], Az[i, j], 0.5 * dz[j + 1] / k[i, j + 1], rc[i], "cap"))
        self.vf_uid = np.array([v[0] for v in vf]); self.vf_A = np.array([v[1] for v in vf])
        self.vf_Rh = np.array([v[2] for v in vf]); self.vf_pos = np.array([v[3] for v in vf])
        self.vf_kind = np.array([v[4] for v in vf])
        # outer boundaries
        dGs = 2 * np.pi * rfm[-1] * dz / (0.5 * dr[-1] / k[-1] + 1 / h)
        np.add.at(b, uid[-1], dGs * T_lab); rows.append(uid[-1]); cols.append(uid[-1]); vals.append(dGs)
        Atop = np.pi * (rfm[1:] ** 2 - rfm[:-1] ** 2)
        dGt = Atop / (0.5 * dz[-1] / k[:, -1] + 1 / h)
        np.add.at(b, uid[:, -1], dGt * T_lab); rows.append(uid[:, -1]); cols.append(uid[:, -1]); vals.append(dGt)
        bot = (mat[:, 0] == 1) | (mat[:, 0] == 3)
        dG0 = Atop / (0.5 * dz[0] / k[:, 0])
        rows.append(uid[bot, 0]); cols.append(uid[bot, 0]); vals.append(dG0[bot])  # 0 C
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nu, nu))
        self.A, self.b0, self.lu = A, b, spla.splu(A.tocsc())
        self.k, self.idx, self.nu = k, idx, nu
        self.Gr, self.Gz = Gr, Gz
        self._calib()

    def solve(self, q_into_vapour):
        """q: W per vapour face (positive = heat leaves the solid into the vapour)"""
        b = self.b0.copy()
        np.add.at(b, self.vf_uid, -q_into_vapour)
        T = self.lu.solve(b)
        Tw = T[self.vf_uid] - q_into_vapour * self.vf_Rh / self.vf_A
        return T, Tw

    def zone_heat(self, T):
        """heat into each copper zone through the solids (W)"""
        mat, zone = self.mat, self.zone
        nr, nz = mat.shape
        Tfull = np.full(nr * nz, np.nan); ok = self.uid >= 0; Tfull[ok] = T[self.uid[ok]]
        Tfull = Tfull.reshape(nr, nz)
        Tcu = np.where(zone == 1, -15.0, -30.0)
        Q = {1: 0.0, 2: 0.0}
        for (a, b_, G) in ((np.s_[:-1, :], np.s_[1:, :], self.Gr), (np.s_[:, :-1], np.s_[:, 1:], self.Gz)):
            ma, mb = mat[a], mat[b_]
            m1 = ((ma == 1) | (ma == 3)) & (mb == 2)
            m2 = ((mb == 1) | (mb == 3)) & (ma == 2)
            for zz in (1, 2):
                Q[zz] += float((G[m1 & (self.zone[b_] == zz)] * (Tfull[a][m1 & (self.zone[b_] == zz)] - Tcu[b_][m1 & (self.zone[b_] == zz)])).sum())
                Q[zz] += float((G[m2 & (self.zone[a] == zz)] * (Tfull[b_][m2 & (self.zone[a] == zz)] - Tcu[a][m2 & (self.zone[a] == zz)])).sum())
        return Q[1], Q[2]

    def _calib(self):
        """T_ext = wall temperature with no vapour heat; G_out = row sum of the face admittance matrix
        (the collective response to raising every vapour face by 1 K, as in the coupled deck)."""
        n = len(self.vf_uid)
        q0 = np.zeros(n)
        _, Tw0 = self.solve(q0)
        Z = np.zeros((n, n))
        B = np.zeros((self.nu, n))
        for i in range(n):
            B[self.vf_uid[i], i] -= 1.0
        X = self.lu.solve(B)                                   # all unit-flux responses at once
        Z = X[self.vf_uid, :] - np.diag(self.vf_Rh / self.vf_A)
        Z = Z - Tw0[:, None] * 0                              # response of Tw to unit q (linear part)
        self.Z = Z
        Y = np.linalg.inv(-Z)                                  # q = Y (T_ext - Tw)
        self.Y = Y
        self.G_out = Y.sum(axis=1) / self.vf_A
        self.T_ext0 = Tw0
        self.T_ext = Tw0.copy()
