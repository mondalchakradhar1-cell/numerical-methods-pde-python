#!/usr/bin/env python3
"""Rebuild the wall heat-flow history (1 s resolution) of a vapour run from its saved 3-D temperature snapshots.
Used for the first run, stopped after its coupling went unstable at ~85 s: only t <= t_max is kept.
Valid for the one-way phase (T_ext fixed); in the two-way phase the wall heat depends on the then-current T_ext,
which the first run did not save, so its two-way seconds are reported with the one-way T_ext as an approximation."""
import glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import room as roommod
import vapour3d as v3

run, t_max = sys.argv[1], float(sys.argv[2])
rm = roommod.Room()
col = v3.Column(1.0)
v3.CAP_ADIABATIC[0] = False
col.set_bc(*v3.room_bc(col, rm, rm.T_ext0))
hist = []
for f in sorted(glob.glob(os.path.join(run, "snap_*.npz"))):
    d = np.load(f); t = float(d["t"])
    if t > t_max: continue
    T = np.where(col.fl, d["T"].astype(float), 0.0)
    q, _, _ = col.wall_heat(T)
    reg = {}
    for r_ in range(1, 6):
        m = col.fl & (col.region[None, None, :] == r_)
        reg[f"T{r_}"] = float(T[m].mean())
    hist.append(dict(t=t, **{k: v * 1e3 for k, v in q.items()}, **reg))
json.dump(dict(hist=hist, note="rebuilt from snapshots, 1 s resolution"), open(os.path.join(run, "history_rebuilt.json"), "w"), indent=1)
print(len(hist), "samples, last t", hist[-1]["t"])
