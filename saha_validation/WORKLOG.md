# SAHA re-validation — work log

A running record of what was done, why, and what each result means. Newest entries are at the bottom.
Numbers in **bold** are the ones to quote; "deck" means the uploaded SAHA decks/PDFs (4–6 Oct 2026).

---

## 0. Goal

Rebuild the SAHA cold-stage thermal results independently (own code, same inputs) and say, item by item,
whether the decks' numbers come out the same:

1. geometry and heat load of the two copper zones;
2. the 11 coil archetypes (layouts A*, P, A, B, C, D, E, E_PDF, F, G, H) — wall uniformity, inlet temperature,
   pressure drop, film conductance — first as 2-D result sheets like `SAHA_layout_result_sheets.pdf`, then as a
   coarse 3-D CFD of the methanol inside the passages;
3. the two-way coupled vapour column (`SAHA_vapour_coupled_radiation.pptx`) as a transient 3-D CFD, 0–120 s,
   **without radiation** (user's decision: radiation is small, it will be checked in later detailed runs).

---

## 1. Geometry check

What: compared every dimension across the assembly PDF, cold-zone deck, concept atlas, sleeve PDF and the
Fluent mesh files.

Result: consistent. The only apparent conflict is the "30 mm bore" in the atlas / sleeve PDF: it is the
**30 mm OD of the copper neck** (wall r 13.5–15 mm), the real bore is 27 mm. Copper heat capacity of Zone 1
re-computed **634 J/K** (deck 620–650). The Fluent vapour mesh passes its own verifier here (all volumes
positive, areas and extents match).

Meaning: the models in the decks all use the same chamber; nothing to correct.

## 2. Heat load (`heatload_axi.py`)

What: axisymmetric conduction of the whole 425 mm stack — vapour, Perspex, foam, copper held at −30/−15 °C,
lab 35 °C with h = 8 W/m²K, ice tray 0 °C.

Result: **Zone 1 2.579 W, Zone 2 1.809 W, 74 % of Zone 1's heat through the end plates.**
Grid 0.25/0.5/1 mm changes it by < 0.2 %. Foam conductivity is the big lever (PU −27 %, aerogel −56 %).

Meaning: Zone 1 matches the decks (2.58 W, room CFD 2.575 W). Zone 2 matches the room CFD (1.80 W); the
cold-zone deck's 1.9 W is ~5 % high.

## 3. Bore radiation check (`bore_radiation.py`)

What: gray-body radiation inside the bore with exact view factors (one-way).

Result: **37 mW into Zone 1 at copper ε 0.3** (16 / 50 mW at ε 0.05 / 0.9). Deck: 34 mW coupled, ~40 mW
one-way. Meaning: the deck's radiation number is right — and small, which is why it is left out of the CFD.

## 4. Coil archetypes — 1-D network + 3-D copper model (`cht3d.py`, `layouts.py`, `run_layouts.py`)

What: 3-D finite-volume copper zone (wall, carrier/buffer, end plates) on an (r, θ, z) grid, coolant
passages voxelised from the sheets' geometry notes, coolant as a 1-D network with developed-flow film
coefficients (helical-coil and duct correlations). External heat = surface flux from step 2.
Every layout at 17.5 and 5 g/s (22 cases).

Result: **18 SAME, 4 CLOSE, 0 DIFFERS** against the result sheets (SAME = spread within 5 mK and inlet
within 20 mK). Median spread difference 1.4 mK.

Changes made along the way:
- jacket H: film coefficient now based on the 2 mm hydraulic diameter of the 1 mm gap (my bug, fixed);
- E / E_PDF: lanes lengthened to ~85 mm to match the sheets' passage plots (the PDF says 72 mm);
- A*: a contact resistance was wrongly applied across the copper end plates (my bug, fixed);
- A*: tube-to-buffer joint made an **ideal connection** (no gap, no solder resistance) — user's instruction.

Differences that remain and what they mean:
- **H jacket**: the sheet's UA (13.2 W/K) fits one wetted wall; with copper on both sides of the gap UA ≈ 31 W/K,
  the centring inlet is ~0.1 K warmer. Uniformity at 17.5 g/s agrees.
- **D serpentine**: sheet Δp 50 kPa vs 6.7 kPa laminar friction; its straight legs run at Re ≈ 3900, so the
  laminar film used on the sheet is questionable (turbulent film moves its inlet −30.68 → −30.12 °C).
- **A* at 5 g/s**: 112 vs 119 mK — the joint detail is resolution-sensitive.
- Pressure drops of the coils: mine are friction-only, 2–4 kPa under the sheets (which include bends).

Film sensitivity (h × 0.75): spread changes ~1 mK, inlet ~20 mK → the laminar/transitional question
moves the inlet setting, not the uniformity.

## 5. 2-D result sheets (`sheets.py`)

What: one sheet per layout and flow in the same six-panel layout as the PDF (passages, inner-wall map,
results table with sheet-vs-model columns, coolant along each passage, r–z section, wall along the height),
plus an inlet-window chart. Output: `figs/sheets/*.png`, `figs/result_sheets_revalidated.pdf`,
`figs/inlet_validation.png`.

Meaning: "2-D" = the inner copper surface results, like the PDF. **20 of 22 centring inlets agree within
20 mK**; the old −31.5 °C setting is outside every window.

## 6. Coarse 3-D coolant CFD (`coolant_cfd.py`, `viz_coolant.py`)

What: the methanol itself in 3-D — steady laminar Navier–Stokes inside the voxelised passages (artificial
compressibility, staggered grid, 2nd-order upwind, Heun RK2, centrifugal/Coriolis terms), then one conjugate
energy solve of methanol + copper with **no film correlation**. Grid 0.4 mm in r/z, 2° round; thin channels
refined. Renders: methanol temperature in the passages, streamlines, pressure, tracer GIFs.

Fixes needed to make it work: first-order advection was far too diffusive (9× too much friction) → 2nd-order
upwind; plain Euler with 2nd-order upwind diverged on the finer grid → Heun RK2; a flow-rate controller speeds
up the slow pressure build-up (steady state unchanged).

Result so far (17.5 g/s):

| layout | spread sheet / 1-D / CFD (mK) | inlet sheet / 1-D / CFD (°C) | rise CFD | Δp sheet / CFD (kPa) |
|---|---|---|---|---|
| A* | 104.4 / 101.3 / 101.9 | −30.136 / −30.149 / −30.168 | 69 mK | 32.6 / 105 |
| P  | 71.4 / 72.5 / 71.1 | −30.118 / −30.118 / −30.143 | 66 mK | 33.1 / 74 |
| A  | 60.0 / 60.1 / 60.3 | −30.120 / −30.120 / −30.145 | 69 mK | 32.0 / 87 |

Meaning: the uniformity from a resolved film agrees within ~3 mK → the developed-flow correlations behind
the sheets are adequate. The CFD inlet is 25–30 mK colder (coarse film). **CFD pressure drop is not a
validation**: the voxel walls are stair-stepped (a 0.4 mm step every ~8 mm along a helix) and add form
losses, so Δp comes out 2–3× too high; quote the 1-D values for Δp.

## 7. Vapour column CFD, two-way coupled, no radiation (`vapour/room.py`, `vapour/vapour3d.py`)

What: transient 3-D Boussinesq CFD of the R134a vapour (Ø27 × 423.5 mm, 1 mm grid, 0.24 M cells).
Copper bands fixed at −15/−30 °C, ice tray 0 °C, Perspex walls and cap with a Robin law
q = G_out (T_ext − T_w). G_out and T_ext come from my room/insulation model (same as the deck's first figure;
with the bore adiabatic it gives 2.574 / 1.808 W, deck 2.5751 / 1.7995 W). 0–60 s one-way, from 60 s two-way
(T_ext updated every 1 s from the room model). Pressure by an exact DCT + eigen solver (divergence 4e-11).

Results 0–85 s (good): **Zone 1 draws 170–176 mW from the vapour, ice tray gives 45–51 mW**
(deck: 172 one-way / 178 coupled with radiation; ice 51 / 49). Region means: Zone 1 vapour −26.0 to −26.8 °C
(deck −26.5), lower connector −8.5 to −9.2 (deck −9.0), top region −0.8 to −1.0 (deck −2.8).

What went wrong at ~85 s: my first two-way exchange (T_ext = T_room + q/G_out) ran away at the middle
connector where G_out is smallest (~2.3 W/m²K): cells reached 63–126 °C, which is impossible (the vapour has
no heat source, so it must stay between the coldest boundary, −30 °C, and the warmest, the cap at ~21 °C).
Fix: exchange through the wall temperature and the room's admittance matrix, under-relaxed and bounded.
Restarted from the clean **t = 75 s** snapshot (not from zero), velocity re-spun from rest, means over 85–120 s.

Why the top is warm: the ~21 °C is the **cap boundary** (T_ext through 50 mm foam from the 35 °C lab), not the
vapour. The deck has the same: its cap is 20 °C one-way and 13 °C coupled because radiation cools it. The
vapour mean in the top region is ≈ −1 °C here vs −2.8 °C in the deck (no radiation here → warmer cap).

Adiabatic cap: tried at the user's request, then reverted (user: it was a mistake). The cap is a Robin
boundary, as in the deck. The option remains as `--cap_adiabatic` but is not used.

---

## Status log

- 05:21 UTC — original vapour run at t = 92 s, coupling instability found; CFD A*, A done.
- 05:40 UTC — corrected vapour run restarted from t = 75 s (Robin cap, stable coupling) → `results/vapour_run2`.
  Original run left running to keep its 0–85 s heat history. Coolant CFD batch on B.
- 05:48 UTC — coolant CFD scope cut (user): run only **E_PDF, B** (two lowest spreads on the sheets), **A** (folded
  bifilar), **P** (plain helix) and **H** (jacket), at **both 17.5 and 5 g/s**. Already done at 17.5 g/s: P, A, B
  (and A*, kept). Remaining 7 runs: E_PDF, H at 17.5; E_PDF, B, A, P, H at 5 g/s. Partial C run stopped.
  Coolant CFD so far: B 40.0 mK / −30.096 °C vs sheet 42.9 mK / −30.086 °C → good; Δp 166 vs 67 kPa (voxel walls).
- 05:55 UTC — the first vapour run (`results/vapour_run`) was stopped at t = 101 s: after 85 s its old coupling had
  driven Zone 1 to −1479 mW (garbage) and it was slowing the other jobs. Its 0–85 s heat history is rebuilt from the
  saved 3-D temperature snapshots at 1 s resolution (`vapour/history_from_snaps.py` → `history_rebuilt.json`):
  exact for the one-way phase (0–60 s), approximate for 60–85 s (uses the one-way T_ext).
  The coupled results (85–120 s means) come from `results/vapour_run2` (restart at 75 s, stable coupling, Robin cap).
- 06:20 UTC — **coupling, second attempt failed too, third attempt works.**
  * Exchange through the room's full face admittance matrix (05:40 run): its diagonal is ~145× the local G_out·A,
    so face-to-face noise of the vapour wall temperature was amplified into T_ext (middle connector +18 K on
    average). Temperatures stayed bounded but the result was wrong → run discarded.
  * Root cause of both failures: exchanging at the room model's 0.5 mm face resolution. For one thin strip the
    room is far stiffer than G_out says, so a face-level update over-corrects and grows (tested offline on a frozen
    vapour field: diverges with and without relaxation).
  * Fix (`vapour/bands.py`): the deck's own exchange, T_ext = T_wall(room, q drawn) + q/G_out, applied on smooth
    bands (~10 mm on the walls, 3 rings on the cap), under-relaxed 0.5. Offline it converges in ~10 exchanges and
    cools the Perspex walls by **2.3 K (lower), 2.3 K (middle), 0.35 K (top)** — deck with radiation 2.2/2.8/2.2 K.
  * Restarted again from the clean t = 75 s snapshot → `results/vapour_run2`.
- 06:20 UTC — coolant CFD fixes: (1) viscous step limit 0.2 h²/ν was above the 3-D stability limit h²/(6ν) → 0.1;
  (2) the pressure update now uses the local speed, β ≥ 1 m/s, and layouts with manifolds start from p = 0 —
  fixes the 5 g/s divergence; (3) "links" (hairpin-type joins) only for one-to-one series joins — the H jacket's
  collector had been mistaken for a hairpin (its 163 mK rise was an artifact); (4) Δp now follows the worst series
  path (E_PDF's 109 kPa had summed parallel lanes). Rerunning E_PDF and H at 17.5 g/s and the five layouts at 5 g/s.
- 06:46 UTC — band-coupled vapour run healthy at t = 85–88 s: Zone 1 draws 177–196 mW (deck 178), region means
  lower conn −9.7…−10.1 °C (deck −9.0), Zone 2 −15.3…−15.4 (−15.2), middle conn −20.7…−21.0 (−20.8), Zone 1
  −26.3…−26.5 (−26.5), top −0.85 (−2.8 with radiation); max 19.9 °C < cap 21.7 °C (physical). E_PDF 17.5 g/s CFD with
  the corrected Δp path: 16.3 kPa vs sheet 14.4 kPa.
- 07:15 UTC — coolant CFD at 5 g/s: A 68.5 mK / −30.267 °C (sheet 68.3 / −30.284) good; P 98.3 / −30.257 (93.7 / −30.272)
  good; E_PDF 57.9 / −30.266 (49.1 / −30.253) close. B at 5 g/s diverged → automatic retry at CFL 0.3 added.
  **H was wrong because of a voxel bug**: the jacket ends at z < 91.0 mm and the outlet ring starts at z > 91.0 mm;
  on the 0.4 mm grid the cell at exactly 91.0 belonged to neither → a one-cell copper seal. The port logic then put
  a p = 0 sink at the top of the jacket and the jacket drained through it (8 m/s, rise 149 mK). Same exact-boundary
  gap between the E / E_PDF lanes and their top pockets (16 spurious links). Joins now overlap by a fraction of a
  cell: H, E, E_PDF have 0 links (fully connected). Rerunning H and E_PDF at both flows and B at 5 g/s.
- 07:35 UTC — **vapour run finished (t = 120 s).** Coupled time means 85–120 s (no radiation) vs coupled deck (with radiation):
  ice tray 49.3 mW (49), lower / middle connector 52.8 / 52.1 mW (58 / 51), Zone 2 wall +18.2 mW (+17),
  **Zone 1 wall 172 ± 2.5 mW (178; 172 one-way)**, region means −9.5 / −15.2 / −20.9 / −26.6 / −0.8 °C
  (−9.0 / −15.2 / −20.8 / −26.5 / −2.8), w rms 0.030 m/s (0.032).
  **Zone totals: Zone 1 = 2.567 W (room, with the vapour heat drawn) + 0.172 W = 2.739 W; Zone 2 = 1.768 − 0.018 = 1.750 W.**
  Deck: 2.776 / 1.747 W including 34 / 6 mW radiation → ≈ 2.742 / 1.741 W without it. **Same answer.**
  The only clear difference is the top region (−0.8 vs −2.8 °C): no radiation here, so the cap is not cooled.
  One-way (25–60 s, rebuilt from snapshots): Zone 1 175 mW, ice 47 mW, connectors 51 / 50 mW, Zone 2 +26 mW
  (deck one-way: 172, 51, 60 / 51, +9).
  Combined record for figures and the GIF: `results/vapour_combined` = run 1 (0–75 s) + run 2 (75–120 s).
- 07:55 UTC — vapour figures done: mid-plane panels, heat histories, coupling plot (Perspex walls cool **2.4 / 2.8 / 0.26 K**
  lower / middle / top vs deck 2.2 / 2.8 / 2.2 K with radiation), 3-D four-panel, **streamlines of the time-mean flow and
  at one instant (t = 120 s, the full velocity checkpoint)**, and the 0–120 s GIF (mid-plane T and w in 3-D).
- 07:55 UTC — vapour heat map (172 mW, θ–z map on the Zone 1 bore) applied to the coils: A* 17.5 g/s 101.3 → 103.5 mK,
  inlet −9 mK; A* 5 g/s 111.8 → 114.3 mK, −19 mK; E_PDF 43.5 → 44.5 mK, −9 mK; H 69.0 → 68.8 mK, −10 mK
  (deck with radiation: 106→111 / −10, 122→129 / −23, 40→42 / −10, 69→70 / −21) → same effect, slightly smaller without radiation.
- 07:55 UTC — coolant CFD reruns with connected joins: E_PDF 17.5 g/s **37.3 mK, −30.107 °C, Δp 14.31 kPa** (sheet 38.0,
  −30.124, 14.43); E_PDF 5 g/s 55.7 mK, −30.253 °C, 3.20 kPa (49.1, −30.253, 3.76); H 17.5 g/s 78.2 mK, −30.144 °C, 2.08 kPa
  (68.6, −30.239, 3.35); H 5 g/s 96.5 mK, −30.270 °C, 0.24 kPa (80.8, −30.339, 0.52). Coolant rises now 64 / 225 mK (energy
  conserved). H is less uniform in 3-D than on the sheet: the one-side-fed rings do not spread the coolant evenly.
- 08:15 UTC — **coolant CFD complete for the chosen set** (both flows): B 5 g/s 60.5 mK / −30.244 °C (sheet 61.0 / −30.248)
  after one automatic retry at CFL 0.3. Full table in the deck. **Deck rebuilt: `SAHA_revalidation.pptx` (42 slides)** —
  overview and verdict, geometry and heat load, 11 archetypes (1-D model, result sheets, inlet windows), 3-D coolant CFD
  (table, per-layout 3-D renders, tracer GIFs), coupled vapour column (model, coupling fix, mid-plane, 3-D, streamlines
  mean + instant, 0–120 s GIF, heat flows, Perspex coupling, deck comparison, coil effect), limits and next steps.
- 08:20 UTC — **full deck and archive**: `SAHA_revalidation_FULL.pptx` (96 slides: main deck + appendix with all 22 result
  sheets, every coolant CFD case at both flows with tracer animations, extra wall maps/profiles, work-log timeline) and
  `SAHA_revalidation_all.zip` (inputs, code, all results incl. vapour runs, figures, both decks, work log, README).
  Both are too large for the git branch (98 MB / 437 MB) and are delivered as files; the code and main deck are on the branch.
