#!/usr/bin/env python3
"""Heat-load sweeps with the axisymmetric chamber model (heatload_axi.solve):
insulation thickness (foam beyond the 43 mm plates and above the 425 mm cap), foam conductivity, lab temperature,
and the distribution of the heat along the height of each copper zone.   -> results/heatload_sweeps.json
"""
import json
import time

import numpy as np

from heatload_axi import solve

D = 0.5
out = {"thickness": [], "k_foam": [], "T_lab": [], "h": []}
t0 = time.time()
for k in (0.035, 0.025, 0.015):
    for t in (10, 20, 25, 30, 40, 50, 60, 75, 100):
        r = solve(k_foam=k, r_out=43.0 + t, z_out=425.0 + t, d=D)
        out["thickness"].append(dict(k=k, t=t, Q1=r["Q1"], Q2=r["Q2"], bal=r["bal"]))
        print("t", k, t, round(r["Q1"], 3), round(r["Q2"], 3), f"{time.time() - t0:.0f}s", flush=True)
for t in (25, 50, 75):
    for k in (0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050):
        r = solve(k_foam=k, r_out=43.0 + t, z_out=425.0 + t, d=D)
        out["k_foam"].append(dict(k=k, t=t, Q1=r["Q1"], Q2=r["Q2"]))
        print("k", t, k, round(r["Q1"], 3), round(r["Q2"], 3), flush=True)
for T in (20, 25, 30, 35, 40):
    r = solve(T_lab=T, d=D)
    out["T_lab"].append(dict(T_lab=T, Q1=r["Q1"], Q2=r["Q2"]))
for h in (4, 6, 8, 10, 15, 25):
    r = solve(h=h, d=D)
    out["h"].append(dict(h=h, Q1=r["Q1"], Q2=r["Q2"]))
# distribution along the height, base case: heat into the copper per mm of height, by surface kind
r = solve(d=D)
prof = {}
for zn, kind, rr, z, q in r["surf"]:
    zone = "Z1" if zn == 2 else "Z2"
    part = "bore (inner wall)" if (kind == "r_in" and abs(rr - 13.5) < 1e-6) else ("plates" if kind.startswith("z") or abs(rr - 43) < 1e-6 else "band outer")
    prof.setdefault(zone, {}).setdefault(part, []).append((z, q))
out["profile"] = {zn: {p: sorted(v) for p, v in d.items()} for zn, d in prof.items()}
out["base"] = dict(Q1=r["Q1"], Q2=r["Q2"], Qlab=r["Qlab"], Qice=r["Qice"])
json.dump(out, open("results/heatload_sweeps.json", "w"), indent=1)
print("done", f"{time.time() - t0:.0f}s")
