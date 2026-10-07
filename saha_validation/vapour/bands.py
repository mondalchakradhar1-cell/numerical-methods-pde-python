"""Smooth (band-level) two-way coupling between the vapour model and the room model.

The deck's exchange  T_ext = T_wall(room, q drawn) + q / G_out  is applied on bands of ~10 mm (walls) and three
rings (cap) instead of on individual 0.5 mm room faces: the heat the vapour draws is spread uniformly over each band
before it goes into the room model, and the room wall temperature is band-averaged before it comes back.
Face-level exchange is unstable (the room's response to a single thin strip is far stiffer than G_out says)."""
import numpy as np


def make_bands(room, dz_wall=10.0, n_cap=3):
    w = room.vf_kind == "wall"
    z = room.vf_pos
    band = -np.ones(len(z), int)
    nb = 0
    for (a, b) in ((0, 60), (187, 247), (365, 424)):
        n = max(1, int(round((b - a) / dz_wall)))
        e = np.linspace(a, b, n + 1)
        for i in range(n):
            m = w & (z >= e[i]) & (z < e[i + 1] + (1e-9 if i == n - 1 else 0))
            if m.any():
                band[m] = nb; nb += 1
    rc = np.linspace(0, 13.5, n_cap + 1)
    for i in range(n_cap):
        m = (~w) & (z >= rc[i]) & (z < rc[i + 1] + 1e-9)
        if m.any():
            band[m] = nb; nb += 1
    return band, nb


def exchange(room, band, nb, T_ext, q_vap, relax=0.3):
    A = room.vf_A
    Ab = np.bincount(band, weights=A, minlength=nb)
    Qb = np.bincount(band, weights=q_vap, minlength=nb)
    q_s = Qb[band] / Ab[band] * A                        # band-uniform flux density
    Tsol, Tw = room.solve(q_s)
    Twb = np.bincount(band, weights=Tw * A, minlength=nb) / Ab
    GAb = np.bincount(band, weights=room.G_out * A, minlength=nb)
    Text_b = Twb + Qb / GAb
    # back to faces: keep the one-way within-band shape, shift by the band change
    T0b = np.bincount(band, weights=room.T_ext0 * A, minlength=nb) / Ab
    T_new = np.clip(room.T_ext0 + (Text_b - T0b)[band], -30.0, 35.0)
    return T_ext + relax * (T_new - T_ext), Tsol, Tw, q_s
