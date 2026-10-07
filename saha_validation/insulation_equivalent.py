#!/usr/bin/env python3
"""Thickness of other insulation materials that gives the same Zone 1 heat as 50 mm of EPS foam (k 0.035),
found with the axisymmetric chamber model (all foam replaced by the material).  -> results/insulation_equivalent.json"""
import json
import time

from heatload_axi import solve

MAT = [  # name, k (W/m.K, around -30..35 C), density kg/m3
    ("Vacuum insulation panel (VIP)", 0.007, 190),
    ("Aerogel blanket", 0.015, 150),
    ("PIR / PU rigid foam", 0.023, 35),
    ("XPS foam", 0.033, 35),
    ("EPS foam (design)", 0.035, 20),
    ("Elastomeric foam (Armaflex)", 0.036, 60),
    ("Mineral / glass wool", 0.040, 50),
    ("Polyethylene foam", 0.040, 30),
    ("Cork board", 0.045, 120),
]
ref = solve(k_foam=0.035, r_out=93.0, z_out=475.0, d=0.5)
target = ref["Q1"]
out = []
t0 = time.time()
import math


def match(k, key, tgt):
    lo, hi = 0.5, 50.0
    while solve(k_foam=k, r_out=43.0 + hi, z_out=425.0 + hi, d=0.5)[key] > tgt and hi < 300:
        lo, hi = hi, hi * 2
    for _ in range(13):
        mid = 0.5 * (lo + hi)
        q = solve(k_foam=k, r_out=43.0 + mid, z_out=425.0 + mid, d=0.5)[key]
        lo, hi = (mid, hi) if q > tgt else (lo, mid)
    return 0.5 * (lo + hi)


for name, k, rho in MAT:
    t1 = match(k, "Q1", target); t2 = match(k, "Q2", ref["Q2"])
    R, Ztop = (43.0 + t1) / 1e3, (425.0 + t1) / 1e3
    vol = math.pi * R ** 2 * Ztop - math.pi * 0.043 ** 2 * 0.425
    out.append(dict(name=name, k=k, rho=rho, t_z1=t1, t_z2=t2, t_flat=50.0 * k / 0.035, outer_d_mm=2 * (43.0 + t1), mass_kg=vol * rho))
    print(f"{name:32s} k {k:.3f}  t_Z1 {t1:6.1f}  t_Z2 {t2:6.1f}  flat {50 * k / 0.035:5.1f}  OD {2 * (43 + t1):.0f}  mass {vol * rho:.2f} kg  {time.time() - t0:.0f}s", flush=True)
# wood: side-wall formula only (the equivalent block is too large for the chamber grid)
kw = 0.12
ro = 43.0 * (93.0 / 43.0) ** (kw / 0.035)
wood = dict(name="Wood (pine, across grain)", k=kw, rho=500, t_sidewall=ro - 43.0, t_flat=50.0 * kw / 0.035)
print("wood side-wall formula t", ro - 43.0)
json.dump(dict(target_Q1=target, ref_Q2=ref["Q2"], materials=out, wood=wood), open("results/insulation_equivalent.json", "w"), indent=1)
