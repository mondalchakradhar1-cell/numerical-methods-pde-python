#!/usr/bin/env python3
"""time-mean convective heat from the vapour into the Zone-1 copper bore, as q(theta, z_local) for run_layouts.py"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vapour3d as v3

run, out = sys.argv[1], sys.argv[2]
m = np.load(os.path.join(run, "mean_2.npz"))
col = v3.Column(1.0)
T = m["T"].astype(float)
X, Y = np.meshgrid(col.xc, col.xc, indexing="ij")
th_cell = np.mod(np.arctan2(Y, X), 2 * np.pi)
kz = np.nonzero(col.kind == "z1")[0]
hcell = v3.KV / (0.5 * col.dx)
nb = 36
edges = np.linspace(0, 2 * np.pi, nb + 1)
q = np.zeros((nb, len(kz))); Qtot = 0.0
for n, k in enumerate(kz):
    heat = col.nside * col.dx * col.dz * col.fA * hcell * (T[:, :, k] - (-30.0))   # W into the copper
    heat[~col.sec] = 0
    Qtot += heat.sum()
    hb, _ = np.histogram(th_cell[col.sec], bins=edges, weights=heat[col.sec])
    q[:, n] = hb / (R_ := v3.R * (2 * np.pi / nb) * col.dz)
z_local = col.zc[kz] * 1e3 - 258.0
theta = 0.5 * (edges[1:] + edges[:-1])
# pad the ends so interpolation covers the full bore (-11 .. 107 mm local)
np.savez(out, theta=np.r_[theta[-1] - 2 * np.pi, theta, theta[0] + 2 * np.pi], z=z_local,
         q=np.vstack([q[-1:], q, q[:1]]), Q=Qtot)
print("vapour heat into Zone 1 bore (time mean):", Qtot * 1e3, "mW; q range", q.min(), q.max(), "W/m2")
