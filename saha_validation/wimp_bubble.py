#!/usr/bin/env python3
"""SAHA as a superheated-liquid R134a (C2H2F4) bubble chamber for WIMP dark matter.

1. WIMP-nucleus recoil spectra in R134a (standard halo model), spin-dependent (proton) and spin-independent.
2. Seitz threshold E_c(T_liquid, p) and the gamma-blind window (electron dE/dx too low to nucleate).
3. Operating point when the pressure is set by the Zone 1 condenser: p = p_sat(T_zone1), threshold vs liquid T,
   and the sensitivity of the threshold to the Zone 1 temperature (+-0.15 K).
-> figs/wimp_*.png, results/wimp_bubble.json
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from CoolProp.CoolProp import PropsSI
from scipy.special import spherical_jn

F = "R134a"
KEV = 1.602176634e-16
C_LIGHT = 2.998e8
GEV = 1.78266192e-27            # kg per GeV/c^2
AMU = 0.9314941                 # GeV
NAVY, CU = "#13294B", "#B87333"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left"})

# ----------------------------------------------------------------------------- halo (standard halo model)
RHO_X, V0, VE, VESC = 0.3, 220e3, 232e3, 544e3          # GeV/cm3, m/s
vg = np.linspace(1, VESC + VE, 6000)


def f_speed(v):
    a = (v ** 2 + VE ** 2) / V0 ** 2; b = 2 * v * VE / V0 ** 2
    mumax = np.clip((VESC ** 2 - v ** 2 - VE ** 2) / (2 * v * VE), -1, 1)
    return v ** 2 * np.exp(-a) * (np.exp(b) - np.exp(-b * mumax)) / b


fv = f_speed(vg); fv /= np.trapezoid(fv, vg)
eta_cum = np.cumsum((fv / vg)[::-1])[::-1] * (vg[1] - vg[0])          # eta(vmin) = int_vmin f(v)/v dv  (s/m)


def eta(vmin):
    return np.interp(vmin, vg, eta_cum, right=0.0)


# ----------------------------------------------------------------------------- target
# R134a C2H2F4: per molecule 2 C, 2 H, 4 F; mass fractions
NUC = {"F": dict(A=19, n=4, J=0.5, Sp=0.441), "C": dict(A=12, n=2, J=0.0, Sp=0.0), "H": dict(A=1, n=2, J=0.5, Sp=0.5)}
M_MOL = 2 * 12.011 + 2 * 1.008 + 4 * 18.998
for k, d in NUC.items():
    d["mfrac"] = d["n"] * {"F": 18.998, "C": 12.011, "H": 1.008}[k] / M_MOL
MP = 0.938


def helm(q_fm, A):
    if A < 2: return np.ones_like(q_fm)
    s = 0.9; a = 0.52; c = 1.23 * A ** (1 / 3) - 0.6
    rn = np.sqrt(c ** 2 + 7 / 3 * np.pi ** 2 * a ** 2 - 5 * s ** 2)
    x = np.maximum(q_fm * rn, 1e-9)
    return (3 * spherical_jn(1, x) / x) * np.exp(-(q_fm * s) ** 2 / 2)


def spectrum(E_keV, mx, sigma_cm2, kind, nuc):
    """dR/dE in counts / (kg_target_total . day . keV) from nucleus `nuc` in R134a"""
    d = NUC[nuc]; A = d["A"]
    mN = A * AMU; mu_N = mx * mN / (mx + mN); mu_p = mx * MP / (mx + MP)
    if kind == "SD":
        if d["J"] == 0: return np.zeros_like(E_keV)
        enh = (4 / 3) * (d["J"] + 1) / d["J"] * d["Sp"] ** 2
        sN = sigma_cm2 * (mu_N / mu_p) ** 2 * enh
        F2 = np.exp(-((np.sqrt(2 * mN * E_keV * 1e-6) / 0.1973) * (1.0 * A ** (1 / 3))) ** 2 / 5) if A > 1 else 1.0
    else:
        sN = sigma_cm2 * (mu_N / mu_p) ** 2 * A ** 2
        F2 = helm(np.sqrt(2 * mN * E_keV * 1e-6) / 0.1973, A) ** 2
    # SI units
    mN_kg, mu_kg, mx_kg = mN * GEV, mu_N * GEV, mx * GEV
    E_J = E_keV * KEV
    vmin = np.sqrt(mN_kg * E_J / (2 * mu_kg ** 2))
    rho = RHO_X * 1e6 * GEV * C_LIGHT ** 2 / (mx * GEV * C_LIGHT ** 2) * mx_kg   # kg/m3 -> mass density of WIMPs
    n_x = RHO_X * 1e6 / mx                                                           # WIMPs per m3
    sN_m2 = sN * 1e-4
    # dR/dE per target nucleus: n_x sN mN/(2 mu^2) F2 eta    [1/(s J)]
    per_nuc = n_x * sN_m2 * mN_kg / (2 * mu_kg ** 2) * F2 * eta(vmin)
    n_per_kg = d["mfrac"] / mN_kg                                                    # nuclei per kg of R134a
    return per_nuc * n_per_kg * 86400 * KEV


E = np.logspace(-1, 2.3, 400)                  # keV
MASSES = [10, 30, 100, 1000]
cols = ["#C0392B", "#E08A2E", "#2A78D6", "#7E57C2"]
SIG_SD, SIG_SI = 1e-40, 1e-46
out = {"halo": dict(rho=RHO_X, v0=V0, vE=VE, vesc=VESC), "sigma_SD_p_cm2": SIG_SD, "sigma_SI_n_cm2": SIG_SI, "rates": {}}

fig, ax = plt.subplots(1, 2, figsize=(14, 5.0))
for mx, c in zip(MASSES, cols):
    sd = sum(spectrum(E, mx, SIG_SD, "SD", n) for n in NUC)
    si = sum(spectrum(E, mx, SIG_SI, "SI", n) for n in NUC)
    ax[0].loglog(E, sd, color=c, lw=2.2, label=f"m_χ = {mx} GeV")
    ax[1].loglog(E, si, color=c, lw=2.2, label=f"m_χ = {mx} GeV")
ax[0].set_title(f"Spin-dependent (proton), σ_p = {SIG_SD:.0e} cm²"); ax[1].set_title(f"Spin-independent, σ_n = {SIG_SI:.0e} cm²")
for a in ax:
    a.set_xlabel("nuclear recoil energy, keV"); a.set_ylabel("events / (kg · day · keV) in R134a"); a.set_ylim(1e-9, 1e-1)
    a.grid(color="#e5e9ef", which="both"); a.legend(frameon=False)
fig.suptitle("WIMP recoil spectra in R134a (C₂H₂F₄), standard halo model", x=0.01, ha="left", fontsize=12.5, weight="bold", color=NAVY)
fig.tight_layout(); fig.savefig("figs/wimp_spectra.png", dpi=160); plt.close(fig)

# integrated rate above threshold
Eth = np.logspace(-0.5, 2, 120)
fig, ax = plt.subplots(1, 2, figsize=(14, 5.0))
for mx, c in zip(MASSES, cols):
    sd = sum(spectrum(E, mx, SIG_SD, "SD", n) for n in NUC); si = sum(spectrum(E, mx, SIG_SI, "SI", n) for n in NUC)
    Rsd = [np.trapezoid(sd[E >= e], E[E >= e]) for e in Eth]; Rsi = [np.trapezoid(si[E >= e], E[E >= e]) for e in Eth]
    ax[0].loglog(Eth, np.array(Rsd) * 365, color=c, lw=2.2, label=f"{mx} GeV"); ax[1].loglog(Eth, np.array(Rsi) * 365, color=c, lw=2.2, label=f"{mx} GeV")
    out["rates"][str(mx)] = {f"Eth_{e}": dict(SD_per_kg_yr=float(np.trapezoid(sd[E >= e], E[E >= e]) * 365), SI_per_kg_yr=float(np.trapezoid(si[E >= e], E[E >= e]) * 365)) for e in (1, 3, 5, 10, 20)}
for a, t in zip(ax, (f"Spin-dependent, σ_p = {SIG_SD:.0e} cm²", f"Spin-independent, σ_n = {SIG_SI:.0e} cm²")):
    for e0 in (3, 10):
        a.axvline(e0, color="0.6", ls="--", lw=0.9)
    a.set_title(f"Events per kg per year above the bubble threshold\n{t}"); a.set_xlabel("bubble-nucleation threshold E_c, keV"); a.set_ylabel("events / (kg · year)")
    a.grid(color="#e5e9ef", which="both"); a.legend(frameon=False, title="WIMP mass")
fig.tight_layout(); fig.savefig("figs/wimp_rate_vs_threshold.png", dpi=160); plt.close(fig)

# ----------------------------------------------------------------------------- Seitz threshold
def threshold(Tc, pl):
    T = Tc + 273.15
    s = PropsSI("I", "T", T, "Q", 0, F)
    ds = (PropsSI("I", "T", T + 0.05, "Q", 0, F) - PropsSI("I", "T", T - 0.05, "Q", 0, F)) / 0.1
    pv = PropsSI("P", "T", T, "Q", 0, F); rv = PropsSI("D", "T", T, "Q", 1, F)
    hfg = PropsSI("H", "T", T, "Q", 1, F) - PropsSI("H", "T", T, "Q", 0, F)
    dp = pv - pl
    if dp <= 0: return np.nan, np.nan
    rc = 2 * s / dp
    return rc, (4 * np.pi * rc ** 2 * (s - T * ds) + 4 / 3 * np.pi * rc ** 3 * rv * hfg - 4 / 3 * np.pi * rc ** 3 * dp)


RHO_L = 1300.0
DEDX_E = 2.0 * RHO_L / 1000 * 1e3 * 1e-4          # minimum-ionising electron, ~2 MeV cm2/g -> keV/um (=0.26)
A_SEITZ = 6.0                                     # energy must be deposited within ~ a * r_c
P_Z1 = PropsSI("P", "T", 243.15, "Q", 0, F)       # 84.4 kPa
Tl = np.linspace(-10, 35, 91)
fig, ax = plt.subplots(1, 2, figsize=(14, 5.2))
pcol = {P_Z1 / 1e3: "#C0392B", 101.325: "#E08A2E", 200: "#1B9E8A", 300: "#2A78D6", 400: "#7E57C2"}
for p, c in pcol.items():
    rr, ee = zip(*[threshold(t, p * 1e3) for t in Tl])
    ee = np.array(ee) / KEV; rr = np.array(rr)
    lab = f"{p:.1f} kPa (set by Zone 1 at −30 °C)" if abs(p - P_Z1 / 1e3) < 0.1 else f"{p:g} kPa"
    ax[0].semilogy(Tl, ee, color=c, lw=2.2, label=lab)
    # gamma-blind criterion: dE/dx needed = E_c / (a r_c); electrons give ~0.26 keV/um
    need = ee / (A_SEITZ * rr * 1e6)
    ax[1].semilogy(Tl, need, color=c, lw=2.2, label=lab)
ax[0].axhspan(1, 10, color="#1B9E8A", alpha=0.08); ax[0].text(-9, 4, "typical WIMP-search\nthresholds 1–10 keV", fontsize=9, color="#1B6E5A")
ax[0].set_title("Bubble-nucleation threshold E_c (Seitz)"); ax[0].set_xlabel("liquid temperature, °C"); ax[0].set_ylabel("E_c, keV"); ax[0].set_ylim(0.05, 1e4)
ax[1].axhline(DEDX_E, color="k", ls="--", lw=1.2); ax[1].text(-9, DEDX_E * 1.3, f"electron / gamma background: ≈ {DEDX_E:.2f} keV/µm", fontsize=9)
ax[1].text(14, 1500, "nuclear recoils (WIMPs, neutrons):\n≈ 100–1000 keV/µm deposited", fontsize=9, color="#1B6E5A")
ax[1].set_title("Energy density needed to make a bubble: E_c / (6 r_c)"); ax[1].set_xlabel("liquid temperature, °C"); ax[1].set_ylabel("dE/dx needed, keV/µm"); ax[1].set_ylim(0.05, 3e3)
ax[1].text(20, 0.08, "below the dashed line the chamber also\nbubbles on gamma-ray electrons", fontsize=9, color="#C0392B")
ax[0].legend(frameon=False, fontsize=9, title="chamber pressure", loc="upper right")
ax[1].legend(frameon=False, fontsize=9, title="chamber pressure", loc="center left", bbox_to_anchor=(0.0, 0.33))
for a in ax:
    a.grid(color="#e5e9ef", which="both")
fig.tight_layout(); fig.savefig("figs/wimp_threshold_map.png", dpi=160); plt.close(fig)

# ----------------------------------------------------------------------------- pressure set by Zone 1: threshold sensitivity
rows = []
for Tliq in (-10, -5, 0, 5, 10, 20, 30):
    rc, Ec = threshold(Tliq, P_Z1)
    dE = []
    for dT in (-0.15, 0.15):
        p = PropsSI("P", "T", 243.15 + dT, "Q", 0, F)
        dE.append(threshold(Tliq, p)[1] / KEV)
    rows.append(dict(T_liquid_C=Tliq, superheat_K=Tliq + 30, r_c_nm=rc * 1e9, E_c_keV=Ec / KEV, E_c_at_zone1_minus015=dE[0], E_c_at_zone1_plus015=dE[1],
                     dEdx_needed_keV_um=Ec / KEV / (A_SEITZ * rc * 1e6)))
    print(f"T_liq {Tliq:4.0f} C  superheat {Tliq + 30:4.0f} K  r_c {rc * 1e9:6.1f} nm  E_c {Ec / KEV:8.3f} keV  "
          f"(Zone1 -0.15/+0.15 K: {dE[0]:.3f} / {dE[1]:.3f} keV)  needs {Ec / KEV / (A_SEITZ * rc * 1e6):7.2f} keV/um")
dpdT = (PropsSI("P", "T", 243.25, "Q", 0, F) - PropsSI("P", "T", 243.05, "Q", 0, F)) / 0.2
out.update(P_zone1_kPa=P_Z1 / 1e3, dpdT_zone1_kPa_per_K=dpdT / 1e3, zone1_operating=rows, dEdx_electron_keV_um=DEDX_E, a_seitz=A_SEITZ)
print("dp/dT at -30 C:", dpdT / 1e3, "kPa/K")
for m in MASSES:
    print(m, {k: (round(v["SD_per_kg_yr"], 4), round(v["SI_per_kg_yr"], 5)) for k, v in out["rates"][str(m)].items()})
# ----------------------------------------------------------------------------- condenser temperature needed
Tc_list = np.linspace(-60, -20, 81)
fig, ax = plt.subplots(1, 2, figsize=(14, 5.0))
cond = {}
for Tliq, c in ((0, "#2A78D6"), (10, "#1B9E8A"), (20, "#E08A2E"), (30, "#C0392B")):
    ee = np.array([threshold(Tliq, PropsSI("P", "T", tc + 273.15, "Q", 0, F))[1] / KEV for tc in Tc_list])
    ax[0].semilogy(Tc_list, ee, color=c, lw=2.2, label=f"liquid at {Tliq} °C")
    cond[Tliq] = {f"{tc:g}": float(e) for tc, e in zip(Tc_list[::10], ee[::10])}
ax[0].axhspan(1, 10, color="#1B9E8A", alpha=0.08); ax[0].axvline(-30, color="0.4", ls="--", lw=1); ax[0].text(-29.5, 2e3, "Zone 1\n−30 °C", fontsize=9)
ax[0].set_title("Threshold vs condenser (coldest zone) temperature"); ax[0].set_xlabel("condenser temperature = vapour-pressure setpoint, °C")
ax[0].set_ylabel("bubble threshold E_c, keV"); ax[0].set_ylim(0.3, 1e4); ax[0].grid(color="#e5e9ef", which="both"); ax[0].legend(frameon=False)
Tl2 = np.linspace(-5, 35, 81)
for p_, c, lab in ((P_Z1, "#C0392B", "84.4 kPa (Zone 1 at −30 °C)"),):
    ee = np.array([threshold(t, p_)[1] / KEV for t in Tl2])
    sens = -np.gradient(np.log(ee), Tl2) * 100
    ax[1].plot(Tl2, sens, color=c, lw=2.2, label=f"liquid temperature (at {lab})")
dEz = []
for t in Tl2:
    e1 = threshold(t, PropsSI("P", "T", 243.15 - 0.15, "Q", 0, F))[1]; e2 = threshold(t, PropsSI("P", "T", 243.15 + 0.15, "Q", 0, F))[1]
    dEz.append(abs(e2 - e1) / (e1 + e2) * 100)
ax[1].plot(Tl2, np.array(dEz), color=NAVY, lw=2.2, label="Zone 1 temperature ±0.15 K (whole band)")
ax[1].set_title("How strongly the threshold moves"); ax[1].set_xlabel("liquid temperature, °C"); ax[1].set_ylabel("threshold change, % (per K of liquid / over ±0.15 K of Zone 1)")
ax[1].grid(color="#e5e9ef"); ax[1].legend(frameon=False, fontsize=9.5)
fig.tight_layout(); fig.savefig("figs/wimp_condenser.png", dpi=160); plt.close(fig)
out["threshold_vs_condenser"] = cond
for t in (0, 20, 30):
    e0 = threshold(t, P_Z1)[1]; e1 = threshold(t + 0.1, P_Z1)[1]
    print(f"liquid {t} C: dE_c/dT_liquid = {(e1 - e0) / e0 / 0.1 * 100:.1f} %/K")
json.dump(out, open("results/wimp_bubble.json", "w"), indent=1)
