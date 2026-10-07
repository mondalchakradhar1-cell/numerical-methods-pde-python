"""Coolant properties and developed-flow correlations (same inputs as the SAHA decks).

Methanol at -30 C: rho 840, cp 2286, mu 1.43e-3 (SAHA_new_cooling_design_exploration.pdf p7) and Pr 15.5
(cold-zone deck slide 25) -> k = mu cp / Pr = 0.211 W/m K.
"""
import numpy as np

RHO, CP, MU, PR = 840.0, 2286.0, 1.43e-3, 15.5
KF = MU * CP / PR


def re(m, dh, area):
    return m * dh / (area * MU)


def nu_straight_round(Re):
    return 4.364                      # fully developed laminar, H1


def nu_gnielinski(Re, Pr=PR):
    f = (0.790 * np.log(Re) - 1.64) ** -2
    return (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * np.sqrt(f / 8) * (Pr ** (2 / 3) - 1))


def nu_helical(Re, d, D, Pr=PR):
    """Manlapaz & Churchill (1981), laminar helical coil, constant heat flux"""
    De = Re * np.sqrt(d / D)
    x3 = (1 + 1342 / (De ** 2 * Pr)) ** 2
    x4 = 1 + 1.15 / Pr
    return ((4.364 + 4.636 / x3) ** 3 + 1.816 * (De / x4) ** 1.5) ** (1 / 3)


def f_helical(Re, d, D):
    """Darcy friction, laminar helical coil, Mishra & Gupta (1979)"""
    De = Re * np.sqrt(d / D)
    return 64 / Re * (1 + 0.033 * np.log10(De) ** 4)


def re_crit_helical(d, D):
    """Ito / Schmidt critical Reynolds number for a helical coil"""
    return 2300 * (1 + 8.6 * (d / D) ** 0.45)


def rect_alpha(w, h):
    return min(w, h) / max(w, h)


def nu_rect_H1(w, h):
    a = rect_alpha(w, h)              # Shah & London, four walls heated
    return 8.235 * (1 - 2.0421 * a + 3.0853 * a ** 2 - 2.4765 * a ** 3 + 1.0578 * a ** 4 - 0.1861 * a ** 5)


def fre_rect(w, h):
    a = rect_alpha(w, h)              # Shah & London, Darcy f*Re
    return 96 * (1 - 1.3553 * a + 1.9467 * a ** 2 - 1.7012 * a ** 3 + 0.9564 * a ** 4 - 0.2537 * a ** 5)


def section(shape):
    """returns hydraulic diameter, flow area, wetted perimeter (m) for a shape dict in mm"""
    if shape["kind"] == "round":
        d = shape["d"] * 1e-3
        return d, np.pi * d ** 2 / 4, np.pi * d
    w, h = shape["w"] * 1e-3, shape["h"] * 1e-3
    return 4 * w * h / (2 * (w + h)), w * h, 2 * (w + h)


H_SCALE = 1.0          # sensitivity multiplier on every film coefficient
TURB_STRAIGHT = False  # True: straight round passages above Re 2300 use Gnielinski instead of laminar Nu 4.36


def passage_htc(shape, m, coil_D=None, nu_override=None, turbulent=False):
    """returns (h, Re, Darcy f) for developed flow"""
    h, Re, f = _passage_htc(shape, m, coil_D, nu_override, turbulent or TURB_STRAIGHT)
    return h * H_SCALE, Re, f


def _passage_htc(shape, m, coil_D=None, nu_override=None, turbulent=False):
    dh, A, P = section(shape)
    Re = re(m, dh, A)
    if isinstance(nu_override, tuple):            # (Nu, Dh_mm): film coefficient on a given hydraulic diameter
        return nu_override[0] * KF / (nu_override[1] * 1e-3), Re, fre_rect(shape["w"], shape["h"]) / Re if shape["kind"] == "rect" else 64 / Re
    if nu_override is not None:
        Nu = nu_override
        f = fre_rect(shape["w"], shape["h"]) / Re if shape["kind"] == "rect" else 64 / Re
    elif shape["kind"] == "round" and coil_D:
        Nu, f = nu_helical(Re, dh, coil_D * 1e-3), f_helical(Re, dh, coil_D * 1e-3)
    elif shape["kind"] == "round":
        if turbulent and Re > 2300:
            Nu = nu_gnielinski(Re); f = (0.790 * np.log(Re) - 1.64) ** -2
        else:
            Nu, f = nu_straight_round(Re), 64 / Re
    else:
        Nu, f = nu_rect_H1(shape["w"], shape["h"]), fre_rect(shape["w"], shape["h"]) / Re
    return Nu * KF / dh, Re, f


def dp(shape, m, L_mm, f):
    dh, A, P = section(shape)
    v = m / (RHO * A)
    return f * (L_mm * 1e-3) / dh * RHO * v ** 2 / 2
