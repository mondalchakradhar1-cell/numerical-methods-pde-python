# SAHA cold-stage re-validation

Independent models written to check the 4–6 Oct 2026 SAHA decks (heat load, coil archetypes, coupled vapour column).

| file | what it does |
|---|---|
| `heatload_axi.py` | axisymmetric conduction of the 425 mm chamber stack: heat gain of each copper zone |
| `bore_radiation.py` | gray-diffuse radiation in the bore with exact cylinder view factors |
| `props.py` | methanol properties and developed-flow correlations (helical coil, ducts, Shah–London) |
| `cht3d.py` | 3-D finite-volume copper zone + 1-D coolant network solver |
| `layouts.py` | the 11 Zone-1 layouts of the result sheets (A*, P, A, B, C, D, E, E_PDF, F, G, H) |
| `run_layouts.py` | runs layouts and flows, writes `results/layouts_<tag>.json` |
| `vapour/room.py` | room / insulation side of the vapour coupling (T_ext, G_out, two-way re-solve) |
| `vapour/vapour3d.py` | transient 3-D Boussinesq CFD of the vapour column, 0–120 s, one-way then two-way |
| `vapour/render3d.py`, `vapour/vfigs.py` | 3-D renders, GIF and 2-D figures of the vapour run |
| `sheets.py` | six-panel result sheets per layout and flow, sheet vs model |
| `coolant_cfd.py`, `viz_coolant.py` | coarse 3-D CFD of the methanol in the passages; 3-D renders and tracer GIFs |
| `vapour/bands.py` | stable band-level two-way exchange between the vapour and the room model |
| `vapour/history_from_snaps.py`, `vapour/export_map.py` | heat history from snapshots; vapour heat map for the coil models |
| `figures.py`, `summary.py`, `deck/build_deck.js` | figures, the numbers summary and the decks (`FULL=1` adds the appendix) |
| `WORKLOG.md` | what was done, why, and what each result means |

Typical use:

    python3 heatload_axi.py results/heatload_axi.json
    python3 run_layouts.py base --fields
    python3 vapour/vapour3d.py --out results/vapour_run
    python3 vapour/vapour3d.py --out results/vapour_run2 --restart <snapshot.npz>   # restart from a saved state
    python3 sheets.py base
    python3 coolant_cfd.py E_PDF B A P H --flows 17.5,5
    python3 summary.py
    FULL=1 node deck/build_deck.js results/summary.json figs SAHA_revalidation_FULL.pptx
