"""The eleven Zone-1 cooling layouts of SAHA_layout_result_sheets.pdf, rebuilt from the sheets' own geometry notes:

  A_built : bifilar Ø5/4 tube on r 22.6 soldered (3 x 0.3 mm strip, k 50) to the 5 mm buffer r 15-20, foam round it
  P..H    : the common copper carrier r 15-27 with passages wetted at r = 20 (B: carrier to r 32 for the outer layer;
            E_PDF: the paired-sleeve PDF dimensions, lanes at r 23.75-24.25, headers to r 36)
Passage sizes are inferred from the Reynolds numbers printed on the sheets (round 4 mm tubes give Re 3907 at 17.5 g/s,
the 6 x 0.5 mm lanes give 472, 5 mm spines 3126).  Local z: 0 = top of the lower plate, 96 = underside of the upper.
"""
import numpy as np

import cht3d

TAU = 2 * np.pi


def wrap(a):
    return (a + np.pi) % TAU - np.pi


def helix_mask(g, rc, d, z0, pitch, th0, phi_tot, sense=1):
    """round tube on a helix: centre (rc, th0 + sense*phi, z0 + pitch*phi/2pi), phi in [0, phi_tot].
    pitch may be negative (descending).  Returns mask and progress s (mm)."""
    R, T, Z = g.R, g.T, g.Z
    near = np.abs(R - rc) <= d / 2 + 1e-9
    mask = np.zeros(g.shape, bool); s = np.zeros(g.shape)
    ell = np.hypot(rc * 1.0, pitch / TAU)                 # mm per radian along the helix
    base = ((T - th0) * sense) % TAU
    nturn = int(np.ceil(phi_tot / TAU)) + 1
    for n in range(-1, nturn + 1):
        phi = base + TAU * n
        ok = near & (phi >= 0) & (phi <= phi_tot)
        zc = z0 + pitch * phi / TAU
        cosA = TAU * rc / np.hypot(TAU * rc, pitch)
        inside = ok & ((R - rc) ** 2 + ((Z - zc) * cosA) ** 2 <= (d / 2) ** 2) & ~mask
        mask |= inside; s[inside] = phi[inside] * ell
    return mask, s, phi_tot * ell


def leg_mask(g, rc, d, th, z0, z1, up=True):
    R, T, Z = g.R, g.T, g.Z
    m = ((R - rc) ** 2 + (rc * wrap(T - th)) ** 2 <= (d / 2) ** 2) & (Z >= z0) & (Z <= z1)
    s = (Z - z0) if up else (z1 - Z)
    return m, s, z1 - z0


def arc_mask(g, rc, d, z, th_a, th_b):
    """horizontal round arc at height z from th_a to th_b (th_b > th_a, radians, may exceed 2pi)"""
    R, T, Z = g.R, g.T, g.Z
    rel = (T - th_a) % TAU
    m = ((R - rc) ** 2 + (Z - z) ** 2 <= (d / 2) ** 2) & (rel <= th_b - th_a)
    return m, rel * rc, (th_b - th_a) * rc


def rect_arc(g, r0, r1, z0, z1, th_a, th_b, s_from="a"):
    R, T, Z = g.R, g.T, g.Z
    rel = (T - th_a) % TAU
    span = th_b - th_a
    m = (R > r0) & (R < r1) & (Z > z0) & (Z < z1) & (rel <= span)
    s = rel if s_from == "a" else span - rel
    return m, s * 0.5 * (r0 + r1), span * 0.5 * (r0 + r1)


def rect_lane(g, r0, r1, th_c, width, z0, z1, up=True):
    R, T, Z = g.R, g.T, g.Z
    rm = 0.5 * (r0 + r1)
    m = (R > r0) & (R < r1) & (np.abs(wrap(T - th_c)) * rm <= width / 2) & (Z > z0) & (Z < z1)
    return m, (Z - z0) if up else (z1 - Z), z1 - z0


# ------------------------------------------------------------------------------------------------ builders
def base_carrier(g, mdl, r_carrier=27.0):
    R, Z = g.R, g.Z
    cu = (R < 15) | ((Z < 0) | (Z > 96)) & (R < 43) | (R < r_carrier) & (Z >= 0) & (Z <= 96)
    mdl.set_copper(cu)


def grid_for(name, dr=0.5, dz=0.5, nt=180):
    rb = [13.5, 15, 20, 20.5, 21, 22, 24, 27, 43]
    if name == "A_built": rb = [13.5, 15, 20, 25.1, 43]
    if name == "B": rb = [13.5, 15, 20, 32, 43]
    if name == "E_PDF": rb = [13.5, 15, 23.75, 24.25, 27, 29, 36, 43]
    zb = [-11, 0, 96, 107]
    return cht3d.Grid(rb, zb, ntheta=nt, dr_fine=dr, dz_fine=dz, r_fine_max=36, r_refine=R_REFINE.get(name) if REFINE[0] else None)


def coil_pair(mdl, g, rc, d, zlo, zhi, pitch_strand, th0, m, D, name, z_shift=None):
    """folded bifilar: strand A rises from zlo to ~zhi, hairpin, strand B descends interleaved half a pitch above"""
    turns = (zhi - zlo) / pitch_strand
    phi = turns * TAU
    mA, sA, LA = helix_mask(g, rc, d, zlo, pitch_strand, th0, phi)
    a = mdl.add_passage(f"{name} strand A (up)", mA, sA, LA, dict(kind="round", d=d), m, coil_D=D)
    off = pitch_strand / 2 if z_shift is None else z_shift
    zb_top = zlo + off + pitch_strand * turns
    mB, sB, LB = helix_mask(g, rc, d, zb_top, -pitch_strand, th0 + phi, phi, sense=-1)
    b = mdl.add_passage(f"{name} strand B (down)", mB, sB, LB, dict(kind="round", d=d), m, coil_D=D)
    mdl.connect(b, [(mdl.last(a), m)])
    return a, b


def build(name, m_tot, dr=0.5, dz=0.5, nt=180):
    g = grid_for(name, dr, dz, nt)
    mdl = cht3d.Model(g)
    R, T, Z = g.R, g.T, g.Z
    D_coil = 44.0                        # coil diameter on the r = 22 passage circle
    if name == "A_built":
        # wall + buffer copper, foam round the tube, plates
        cu = (R < 20) | ((Z < 0) | (Z > 96)) & (R < 43)
        mdl.set_copper(cu)
        mdl.set_foam((R > 20) & (R < 25.1) & (Z >= 0) & (Z <= 96))
        rc, d_o, d_i, p = 22.6, 5.0, 4.0, 13.83
        turns = 84.0 / p
        phi = turns * TAU
        for strand, (z0, pitch, th0, sense) in enumerate(((4.0, p, 0.0, 1), (4.0 + p / 2 + p * turns, -p, phi, -1))):
            mo, _, _ = helix_mask(g, rc, d_o, z0, pitch, th0, phi, sense)
            mdl.set_copper(mo)                                   # tube wall copper (the bore is overwritten below)
        mA, sA, LA = helix_mask(g, rc, d_i, 4.0, p, 0.0, phi)
        a = mdl.add_passage("strand A (up)", mA, sA, LA, dict(kind="round", d=d_i), m_tot, coil_D=2 * rc)
        mB, sB, LB = helix_mask(g, rc, d_i, 4.0 + p / 2 + p * turns, -p, phi, phi, sense=-1)
        b = mdl.add_passage("strand B (down)", mB, sB, LB, dict(kind="round", d=d_i), m_tot, coil_D=2 * rc)
        mdl.connect(a, "in"); mdl.connect(b, [(mdl.last(a), m_tot)])
        mdl.outlets.append((mdl.last(b), m_tot))
        # contact on the r = 20 face: solder strip (3 x 0.3 mm, k 50) under the tube centreline, 0.1 mm foam gap elsewhere
        nr = g.shape[0]
        i20 = int(np.argmin(np.abs(g.rf[1:-1] - 20.0)))
        ex = np.zeros((nr - 1, g.shape[1], g.shape[2]))
        tube_out = (mdl.mat[i20 + 1] == 1) & (g.zc[None, :] >= 0) & (g.zc[None, :] <= 96)   # tube region only, not the plates
        # distance in z from the nearest tube centreline at r = 22.6
        zc_dist = np.full(tube_out.shape, 1e9)
        for z0, pitch, th0, sense in ((4.0, p, 0.0, 1), (4.0 + p / 2 + p * turns, -p, phi, -1)):
            base = ((g.tc - th0) * sense) % TAU
            for n in range(-1, int(turns) + 3):
                ph = base + TAU * n
                ok = (ph >= 0) & (ph <= phi)
                zc = z0 + pitch * ph / TAU
                dist = np.abs(g.zc[None, :] - zc[:, None])
                dist[~ok] = 1e9
                zc_dist = np.minimum(zc_dist, dist)
        solder = tube_out & (zc_dist <= 1.5)
        gap = tube_out & ~solder
        A = g.rf[i20 + 1] * 1e-3 * g.dt * g.dz[None, :] * 1e-3
        if CONTACT[0] == "solder_gap":                       # optional: 3 x 0.3 mm solder strip, 0.1 mm foam gap elsewhere
            ex[i20][solder] = 0.3e-3 / K_SOLDER_AREA(1.0)
            ex[i20][gap] = 0.1e-3 / cht3d.K_FOAM
        # default ("ideal"): perfect thermal contact wherever the tube wall touches the buffer
        mdl.contact["r"] = ex / 1.0                              # resistance per unit area (m2K/W); divided by A below
        mdl.contact_is_specific = True
        mdl.Q_sheet = 2.55
        return g, mdl
    base_carrier(g, mdl, 32.0 if name == "B" else 27.0)
    if name == "E_PDF":
        mdl.set_copper((R < 36) & (Z >= 0) & (Z < 14) | (R < 29) & (Z > 90) & (Z <= 96))
    rc, d = 22.0, 4.0
    if name == "P":
        turns = 80.0 / 6.9
        mm, s, L = helix_mask(g, rc, d, 5.0, 6.9, 0.0, turns * TAU)
        a = mdl.add_passage("helix", mm, s, L, dict(kind="round", d=d), m_tot, coil_D=D_coil)
        mdl.connect(a, "in"); mdl.outlets.append((mdl.last(a), m_tot))
    elif name == "A":
        a, b = coil_pair(mdl, g, rc, d, 5.0, 82.0, 13.8, 0.0, m_tot, D_coil, "coil")
        mdl.connect(a, "in"); mdl.outlets.append((mdl.last(b), m_tot))
    elif name == "B":
        turns_i = 80.0 / 6.6
        mi, si, Li = helix_mask(g, 21.0, d, 5.0, 6.6, 0.0, turns_i * TAU)
        a = mdl.add_passage("inner_up", mi, si, Li, dict(kind="round", d=d), m_tot, coil_D=42.0)
        turns_o = 80.0 / 7.4
        th_top = turns_i * TAU
        mo, so, Lo = helix_mask(g, 27.0, d, 85.0, -7.4, th_top, turns_o * TAU, sense=-1)
        b = mdl.add_passage("outer_down", mo, so, Lo, dict(kind="round", d=d), m_tot, coil_D=54.0)
        mdl.connect(a, "in"); mdl.connect(b, [(mdl.last(a), m_tot)]); mdl.outlets.append((mdl.last(b), m_tot))
    elif name == "C":
        m = m_tot / 2
        turns = 77.0 / 13.8
        mu_, su, Lu = helix_mask(g, rc, d, 5.0, 13.8, 0.0, turns * TAU)
        a = mdl.add_passage("up", mu_, su, Lu, dict(kind="round", d=d), m, coil_D=D_coil)
        md, sd, Ld = helix_mask(g, rc, d, 5.0 + 6.9 + 77.0, -13.8, turns * TAU, turns * TAU, sense=-1)
        b = mdl.add_passage("down", md, sd, Ld, dict(kind="round", d=d), m, coil_D=D_coil)
        mdl.connect(a, "in"); mdl.connect(b, "in")
        mdl.outlets += [(mdl.last(a), m), (mdl.last(b), m)]
    elif name == "D":
        nleg, z0, z1 = 16, 8.0, 88.0
        prev = None
        for i in range(nleg):
            th = i * TAU / nleg
            up = i % 2 == 0
            ml, sl, Ll = leg_mask(g, rc, d, th, z0, z1, up)
            p = mdl.add_passage(f"leg{i}", ml, sl, Ll, dict(kind="round", d=d), m_tot)
            mdl.connect(p, "in" if prev is None else [(mdl.last(prev), m_tot)])
            prev = p
            if i < nleg - 1:
                zt = z1 if up else z0
                ma, sa, La = arc_mask(g, rc, d, zt, th, th + TAU / nleg)
                q = mdl.add_passage(f"turn{i}", ma, sa, La, dict(kind="round", d=d), m_tot)
                mdl.connect(q, [(mdl.last(prev), m_tot)]); prev = q
        mdl.outlets.append((mdl.last(prev), m_tot))
    elif name in ("E", "E_PDF"):
        if name == "E":
            lr0, lr1, z_lo, z_hi = 20.0, 20.5, 6.0, 91.0
            sup = (20.5, 23.5, 1.0, 6.0); ret = (22.0, 27.0, 9.0, 12.0)
            pocket = (20.0, 20.5, 91.0, 94.0)
        else:
            lr0, lr1, z_lo, z_hi = 23.75, 24.25, 5.0, 91.0
            sup = (24.25, 29.25, 1.0, 4.0); ret = (29.5, 34.5, 8.0, 11.0)
            pocket = (23.75, 24.25, 91.0, 94.0)
        w = 6.0; npair_half = 4; mb = m_tot / 8
        lane_pitch = TAU / 16
        for half in range(2):
            th_h0 = half * np.pi
            centre = th_h0 + np.pi / 2 - lane_pitch / 2 + lane_pitch / 2   # feed in the middle of the half
            # supply gallery: two arms from the feed point
            ups = [lane_pitch * (2 * k + 0.5) + th_h0 for k in range(npair_half)]
            dns = [lane_pitch * (2 * k + 1.5) + th_h0 for k in range(npair_half)]
            arms_s, arms_r = [], []
            for sgn, ths in ((-1, [t for t in ups if t < centre][::-1]), (1, [t for t in ups if t > centre])):
                if not ths: continue
                end = ths[-1] + sgn * lane_pitch * 0.3
                a0, a1 = (end, centre) if sgn < 0 else (centre, end)
                gm, gs, gL = rect_arc(g, sup[0], sup[1], sup[2], sup[3], a0, a1, s_from="b" if sgn < 0 else "a")
                m_arm = mb * len(ths)
                gp = mdl.add_passage(f"h{half}_supply_{'L' if sgn < 0 else 'R'}", gm, gs, gL,
                                     dict(kind="rect", w=sup[3] - sup[2], h=sup[1] - sup[0]), m_arm, ds=1.0)
                mdl.connect(gp, "in")
                # flow decreases after each tap
                taps = [(abs(t - centre) * 0.5 * (sup[0] + sup[1]), t) for t in ths]
                p = mdl.passages[gp]
                for nd in range(p["first"], p["last"] + 1):
                    s_nd = mdl.nodes_s[nd]
                    mdl.nodes_m[nd] = mb * sum(1 for st, _ in taps if st >= s_nd - 0.5)
                for nd in range(p["first"] + 1, p["last"] + 1):
                    mdl.nodes_up[nd] = [(nd - 1, mdl.nodes_m[nd])]
                arms_s.append((gp, taps))
            # return gallery arms (collect) - one gallery for the half, flowing towards the outlet in the middle
            ret_nodes = {}
            for sgn, ths in ((-1, [t for t in dns if t < centre][::-1]), (1, [t for t in dns if t > centre])):
                if not ths: continue
                end = ths[-1] + sgn * lane_pitch * 0.3
                a0, a1 = (end, centre) if sgn < 0 else (centre, end)
                # progress measured from the far end towards the outlet
                gm, gs, gL = rect_arc(g, ret[0], ret[1], ret[2], ret[3], a0, a1, s_from="a" if sgn < 0 else "b")
                gp = mdl.add_passage(f"h{half}_return_{'L' if sgn < 0 else 'R'}", gm, gs, gL,
                                     dict(kind="rect", w=ret[3] - ret[2], h=ret[1] - ret[0]), mb * len(ths), ds=1.0)
                ret_nodes[sgn] = (gp, ths, gL)
            for k in range(npair_half):
                tu, td = ups[k], dns[k]
                mu_, su, Lu = rect_lane(g, lr0, lr1, tu, w, z_lo, z_hi, up=True)
                if True:   # riser from the supply gallery into the lane
                    mu_ |= (np.abs(wrap(g.T - tu)) * 0.5 * (lr0 + lr1) <= w / 2) & (g.R > lr0) & (g.R < sup[1]) & (g.Z > sup[2]) & (g.Z <= z_lo)
                lu = mdl.add_passage(f"h{half}_pair{k}_up", mu_, su, Lu, dict(kind="rect", w=w, h=lr1 - lr0), mb)
                gp, taps = [a for a in arms_s if any(abs(t - tu) < 1e-9 for _, t in a[1])][0]
                st = [s for s, t in taps if abs(t - tu) < 1e-9][0]
                mdl.connect(lu, [(mdl.node_at(gp, st), mb)])
                pm, ps, pL = rect_arc(g, pocket[0], pocket[1], pocket[2], pocket[3], tu - w / 2 / lr0, td + w / 2 / lr0)
                pk = mdl.add_passage(f"h{half}_pair{k}_pocket", pm, ps, pL, dict(kind="rect", w=pocket[3] - pocket[2], h=6.0), mb, ds=1.0)
                mdl.connect(pk, [(mdl.last(lu), mb)])
                md, sd, Ld = rect_lane(g, lr0, lr1, td, w, ret[2], z_hi, up=False)
                md |= (np.abs(wrap(g.T - td)) * 0.5 * (lr0 + lr1) <= w / 2) & (g.R > lr0) & (g.R < ret[1]) & (g.Z > ret[2]) & (g.Z < ret[3])
                ld = mdl.add_passage(f"h{half}_pair{k}_down", md, sd, Ld, dict(kind="rect", w=w, h=lr1 - lr0), mb)
                mdl.connect(ld, [(mdl.last(pk), mb)])
                sgn = -1 if td < centre else 1
                gp_r, ths, gL = ret_nodes[sgn]
                s_tap = gL - abs(td - centre) * 0.5 * (ret[0] + ret[1])
                nd = mdl.node_at(gp_r, s_tap)
                mdl.nodes_up[nd] = mdl.nodes_up[nd] + [(mdl.last(ld), mb)]
            for sgn, (gp_r, ths, gL) in ret_nodes.items():
                p = mdl.passages[gp_r]
                taps = [gL - abs(t - centre) * 0.5 * (ret[0] + ret[1]) for t in ths]
                for nd in range(p["first"], p["last"] + 1):
                    mdl.nodes_m[nd] = mb * sum(1 for st in taps if st <= mdl.nodes_s[nd] + 0.5)
                for nd in range(p["first"] + 1, p["last"] + 1):
                    ups_ = [u for u in mdl.nodes_up[nd] if u[0] != nd - 1]
                    mdl.nodes_up[nd] = [(nd - 1, mdl.nodes_m[nd - 1])] + ups_
                # the first node has only lane inflows
                mdl.nodes_up[p["first"]] = [u for u in mdl.nodes_up[p["first"]] if u[0] != p["first"] - 1 and mdl.nodes_pid[u[0]] != gp_r]
                mdl.outlets.append((p["last"], mdl.nodes_m[p["last"]]))
        # make every node's mass flow consistent with its inflows (galleries)
        for nd in range(len(mdl.nodes_m)):
            if mdl.nodes_up[nd]:
                mdl.nodes_m[nd] = sum(mm for _, mm in mdl.nodes_up[nd]) if nd not in mdl.inlets else mdl.nodes_m[nd]
    elif name == "F":
        th_s, th_r = 0.0, np.radians(340.0)
        ms, ss, Ls = leg_mask(g, rc, 5.0, th_s, 3.0, 85.0)
        sp_ = mdl.add_passage("supply_spine", ms, ss, Ls, dict(kind="round", d=5.0), m_tot)
        mdl.connect(sp_, "in")
        mr, sr, Lr = leg_mask(g, rc, 5.0, th_r, 3.0, 85.0, up=True)
        rp = mdl.add_passage("return_spine", mr, sr, Lr, dict(kind="round", d=5.0), m_tot)
        zr = [13.0 + 9.6 * k for k in range(8)]
        mb = m_tot / 8
        th_a, th_b = th_s + np.radians(5.5), th_r - np.radians(5.5)
        for k, z in enumerate(zr):
            ma, sa, La = arc_mask(g, rc, d, z, th_a, th_b)
            p = mdl.add_passage(f"ring{k}", ma, sa, La, dict(kind="round", d=d), mb, coil_D=2 * rc)
            mdl.connect(p, [(mdl.node_at(sp_, z - 3.0), mb)])
            nd = mdl.node_at(rp, z - 3.0)
            mdl.nodes_up[nd] = mdl.nodes_up[nd] + [(mdl.last(p), mb)]
        # spine flows: supply decreases above each ring, return increases
        for pid, inc in ((sp_, False), (rp, True)):
            p = mdl.passages[pid]
            for nd in range(p["first"], p["last"] + 1):
                zs = mdl.nodes_s[nd] + 3.0
                n_below = sum(1 for z in zr if z < zs)
                mdl.nodes_m[nd] = mb * (n_below if inc else 8 - n_below)
                mdl.nodes_m[nd] = max(mdl.nodes_m[nd], 1e-9)
            for nd in range(p["first"] + 1, p["last"] + 1):
                extra = [u for u in mdl.nodes_up[nd] if mdl.nodes_pid[u[0]] != pid]
                mdl.nodes_up[nd] = [(nd - 1, mdl.nodes_m[nd - 1] if inc else mdl.nodes_m[nd])] + extra
            if inc:
                mdl.nodes_up[p["first"]] = [u for u in mdl.nodes_up[p["first"]] if mdl.nodes_pid[u[0]] != pid]
        for nd in range(len(mdl.nodes_m)):
            if mdl.nodes_up[nd] and nd not in mdl.inlets:
                mdl.nodes_m[nd] = sum(mm for _, mm in mdl.nodes_up[nd])
        mdl.outlets.append((mdl.last(rp), m_tot))
    elif name == "G":
        m = m_tot / 2
        # lower coil: in near the middle, strand down, hairpin at the bottom, strand back up
        p = 13.8; turns = 32.5 / p; phi = turns * TAU
        m1, s1, L1 = helix_mask(g, rc, d, 44.0, -p, 0.0, phi)
        a = mdl.add_passage("lower_coil down", m1, s1, L1, dict(kind="round", d=d), m, coil_D=D_coil)
        m2, s2, L2 = helix_mask(g, rc, d, 44.0 - 32.5 - 6.9, p, phi, phi, sense=-1)
        b = mdl.add_passage("lower_coil up", m2, s2, L2, dict(kind="round", d=d), m, coil_D=D_coil)
        mdl.connect(a, "in"); mdl.connect(b, [(mdl.last(a), m)])
        m3, s3, L3 = helix_mask(g, rc, d, 52.0, p, 0.0, phi)
        c = mdl.add_passage("upper_coil up", m3, s3, L3, dict(kind="round", d=d), m, coil_D=D_coil)
        m4, s4, L4 = helix_mask(g, rc, d, 52.0 + 32.5 + 6.9, -p, phi, phi, sense=-1)
        e = mdl.add_passage("upper_coil down", m4, s4, L4, dict(kind="round", d=d), m, coil_D=D_coil)
        mdl.connect(c, "in"); mdl.connect(e, [(mdl.last(c), m)])
        mdl.outlets += [(mdl.last(b), m), (mdl.last(e), m)]
    elif name == "H":
        # inlet ring (fed at theta 0, flowing both ways), 1 mm annular gap r 20-21 with axial flow, outlet ring
        nt_ = g.shape[1]
        ring_in = (20.0, 22.0, 2.0, 6.0); ring_out = (20.0, 22.0, 91.0, 95.0)
        arms = []
        for sgn in (1, -1):
            a0, a1 = (0.0, np.pi) if sgn > 0 else (np.pi, TAU)
            mi, si, Li = rect_arc(g, *ring_in, a0, a1, s_from="a" if sgn > 0 else "b")
            pi_ = mdl.add_passage(f"inlet_ring_{'+' if sgn > 0 else '-'}", mi, si, Li, dict(kind="rect", w=4.0, h=2.0), m_tot / 2, ds=1.0)
            mdl.connect(pi_, "in"); arms.append(pi_)
        ncol = nt_
        mcol = m_tot / ncol
        cols = []
        for j in range(ncol):
            th = g.tc[j]
            mc = (g.R > 20.0) & (g.R < 21.0) & (g.Z > 6.0) & (g.Z < 91.0) & (np.abs(wrap(g.T - th)) < g.dt / 2)
            w_col = TAU * 20.5 / ncol
            pc = mdl.add_passage(f"jacket_col{j}", mc, g.Z - 6.0, 85.0, dict(kind="rect", w=w_col, h=1.0), mcol, ds=1.0,
                                 nu_override=(JACKET_NU[0], 2.0))
            # which inlet arm and where
            if th <= np.pi:
                mdl.connect(pc, [(mdl.node_at(arms[0], th * 21.0), mcol)])
            else:
                mdl.connect(pc, [(mdl.node_at(arms[1], (TAU - th) * 21.0), mcol)])
            cols.append((pc, th))
        for pi_, sgn in ((arms[0], 1), (arms[1], -1)):
            p = mdl.passages[pi_]
            for nd in range(p["first"], p["last"] + 1):
                s_nd = mdl.nodes_s[nd]
                mdl.nodes_m[nd] = max(m_tot / 2 * (1 - s_nd / p["L"]), mcol)
            for nd in range(p["first"] + 1, p["last"] + 1):
                mdl.nodes_up[nd] = [(nd - 1, mdl.nodes_m[nd])]
        # outlet ring: collects towards theta = pi from both sides
        outs = []
        for sgn in (1, -1):
            a0, a1 = (0.0, np.pi) if sgn > 0 else (np.pi, TAU)
            mo, so, Lo = rect_arc(g, *ring_out, a0, a1, s_from="a" if sgn > 0 else "b")
            po = mdl.add_passage(f"outlet_ring_{'+' if sgn > 0 else '-'}", mo, so, Lo, dict(kind="rect", w=4.0, h=2.0), m_tot / 2, ds=1.0)
            outs.append(po)
        for pc, th in cols:
            po = outs[0] if th <= np.pi else outs[1]
            s_ = th * 21.0 if th <= np.pi else (TAU - th) * 21.0
            nd = mdl.node_at(po, s_)
            mdl.nodes_up[nd] = mdl.nodes_up[nd] + [(mdl.last(pc), mcol)]
        for po in outs:
            p = mdl.passages[po]
            for nd in range(p["first"] + 1, p["last"] + 1):
                mdl.nodes_up[nd] = [(nd - 1, None)] + [u for u in mdl.nodes_up[nd] if mdl.nodes_pid[u[0]] != po]
            # mass flows cumulative
            for nd in range(p["first"], p["last"] + 1):
                tot = 0.0
                for j_, mm in mdl.nodes_up[nd]:
                    tot += mdl.nodes_m[j_] if mm is None else mm
                mdl.nodes_m[nd] = max(tot, 1e-12)
                mdl.nodes_up[nd] = [(j_, mdl.nodes_m[j_] if mm is None else mm) for j_, mm in mdl.nodes_up[nd]]
            mdl.outlets.append((p["last"], mdl.nodes_m[p["last"]]))
    else:
        raise KeyError(name)
    mdl.Q_sheet = 2.58
    return g, mdl


REFINE = [False]         # CFD: refine r so the thin channels get several cells
R_REFINE = {"E": [(20.0, 20.5, 0.125)], "E_PDF": [(23.75, 24.25, 0.125)], "H": [(20.0, 21.0, 0.25)]}
CONTACT = ["ideal"]      # tube-buffer joint of A*: "ideal" (no gap, no resistance) or "solder_gap"
JACKET_NU = [5.385]          # one wall heated, other adiabatic (parallel plates, based on Dh = 2 x gap)


def K_SOLDER_AREA(_):
    return cht3d.K_SOLDER


LAYOUTS = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"]
