#!/usr/bin/env python3
"""Collect every number the validation deck quotes into results/summary.json."""
import json
import os

import numpy as np

from reference import SHEETS, NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")
S = {}
hl = json.load(open(os.path.join(R, "heatload_axi.json")))
S["heatload"] = [dict(case=r["case"], Q1=r["Q1"], Q2=r["Q2"],
                      plates=sum(v for k, v in r["z1_split"].items() if "plate" in k) / sum(r["z1_split"].values())) for r in hl]
S["radiation"] = json.load(open(os.path.join(R, "bore_radiation.json")))
lay = json.load(open(os.path.join(R, "layouts_base.json")))
rows = []
for x in lay:
    s = SHEETS[x["layout"]][5 if x["m_gs"] == 5.0 else 17.5]
    rows.append(dict(layout=x["layout"], name=NAMES[x["layout"]], flow=x["m_gs"], spread=x["spread_mK"], spread_sheet=s[0],
                     inlet=x["inlet_C"], inlet_sheet=s[1], dp=x["dp_kPa"], dp_sheet=s[2], UA=x["UA_WK"], UA_sheet=s[3],
                     Re=x["Re"], Re_sheet=[s[4], s[5]], margin=x["margin_mK"], rise=x["rise_mK"], bal=x["energy_balance_W"]))
order = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"]
rows.sort(key=lambda r: (order.index(r["layout"]), -r["flow"]))
S["layouts"] = rows
d = np.array([r["spread"] - r["spread_sheet"] for r in rows])
S["layout_stats"] = dict(n=len(rows), within5=int((abs(d) <= 5).sum()), within10=int((abs(d) <= 10).sum()),
                         max_abs=float(abs(d).max()), median_abs=float(np.median(abs(d))),
                         inlet_within20=int(sum(abs(r["inlet"] - r["inlet_sheet"]) <= 0.02 for r in rows)))
for tag in ("vapourmap", "grid", "turb", "hx"):
    f = os.path.join(R, f"layouts_{tag}.json")
    if os.path.exists(f):
        S[tag] = json.load(open(f))
cf = os.path.join(R, "coolant_cfd.json")
if os.path.exists(cf):
    S["coolant_cfd"] = [{k: v for k, v in r.items() if k != "flow_hist"} for r in json.load(open(cf))]
sv = os.path.join(R, "sheet_verdicts.json")
if os.path.exists(sv):
    S["sheet_verdicts"] = json.load(open(sv))
vr = os.path.join(R, "vapour_run")
if os.path.exists(os.path.join(vr, "history.json")):
    H = json.load(open(os.path.join(vr, "history.json")))
    h = H["hist"]
    def mean(key, a, b):
        v = [x[key] for x in h if a <= x["t"] <= b]
        return float(np.mean(v)) if v else None
    def block_scatter(key, a, b, n=7):
        v = np.array([x[key] for x in h if a <= x["t"] <= b])
        return float(np.std([c.mean() for c in np.array_split(v, n)]) / np.sqrt(n)) if len(v) else None
    out = {}
    for nm, (a, b) in (("oneway", (25, 60)), ("coupled", (85, 120))):
        out[nm] = {k: mean(k, a, b) for k in ("ice", "conn_lo", "z2", "conn_mid", "z1", "top_wall", "cap", "wrms", "T1", "T2", "T3", "T4", "T5", "storage")}
        out[nm]["z1_scatter"] = block_scatter("z1", a, b)
        out[nm]["umax_peak"] = max(x["umax"] for x in h if a <= x["t"] <= b) if any(a <= x["t"] <= b for x in h) else None
    out["conduction_heat_mW"] = H["conduction_heat_mW"]
    out["grid"] = H["grid"]; out["seconds"] = H["seconds"]; out["steps"] = H["steps"]
    out["room_zone_heat_final"] = H["room_zone_heat_final"]
    cr = os.path.join(vr, "coupling_result.json")
    if os.path.exists(cr):
        out["coupling_result"] = json.load(open(cr))
    # rms of T per region from the time statistics
    m = os.path.join(vr, "mean_2.npz")
    if os.path.exists(m):
        import sys
        sys.path.insert(0, os.path.join(HERE, "vapour"))
        import vapour3d as v3
        col = v3.Column(1.0)
        M = np.load(m)
        rms = np.sqrt(np.maximum(M["T2"] - M["T"] ** 2, 0))
        out["T_rms"] = {}
        out["T_mean"] = {}
        for r_ in range(1, 6):
            mk = col.fl & (col.region[None, None, :] == r_)
            out["T_rms"][r_] = float(rms[mk].mean()); out["T_mean"][r_] = float(M["T"][mk].mean())
        out["w_rms_stat"] = float(np.sqrt(np.maximum(M["w2"], 0))[col.fl].mean())
    S["vapour"] = out
json.dump(S, open(os.path.join(R, "summary.json"), "w"), indent=1)
print(json.dumps(S["layout_stats"]))
