// SAHA re-validation deck. node build_deck.js <summary.json> <figs dir> <out.pptx>
const fs = require("fs");
const path = require("path");
const pptxgen = require(process.env.PPTXGENJS || "pptxgenjs");
const { applyTheme } = require(process.env.APPLY_THEME);

const [, , SUMMARY, FIGS, OUT] = process.argv;
const S = JSON.parse(fs.readFileSync(SUMMARY, "utf8"));
const fig = (f) => path.join(FIGS, f);

const THEME = {
  name: "SAHA Cryo",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "14213D", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "EEF3F8",
    accent1: "B8693D", accent2: "2A6FDB", accent3: "8EB8D8", accent4: "2E8B57", accent5: "C0392B", accent6: "6B7686",
    hlink: "2A6FDB", folHlink: "1F3A5F",
  },
};
const HEX = THEME.colors;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "SAHA re-validation";
pres.author = "SAHA thermal study";
const C = pres.SchemeColor;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.0, w: 11.9, h: 1.8, fontFace: "Cambria", fontSize: 40, bold: true, color: C.background1, valign: "bottom", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 3.95, w: 11.9, h: 1.6, fontFace: "Calibri", fontSize: 18, color: C.accent3, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "SECTION",
  background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.4, w: 11.9, h: 1.4, fontFace: "Cambria", fontSize: 36, bold: true, color: C.background1, valign: "bottom", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 3.9, w: 11.9, h: 1.4, fontFace: "Calibri", fontSize: 18, color: C.accent3, valign: "top" }, text: "" } },
  ],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontFace: "Calibri", fontSize: 10, color: HEX.accent3 },
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 12.3, h: 0.85, fontFace: "Cambria", fontSize: 28, bold: true, color: C.text1, valign: "middle", align: "left" }, text: "" } },
    { text: { text: "SAHA cold stage · independent re-validation · 7 Oct 2026", options: { x: 0.5, y: 7.0, w: 8, h: 0.3, fontFace: "Calibri", fontSize: 10, color: HEX.accent6 } } },
  ],
  slideNumber: { x: 12.4, y: 7.0, w: 0.6, h: 0.3, fontFace: "Calibri", fontSize: 10, color: HEX.accent6 },
});

// ---------------------------------------------------------------- helpers
function imgSize(f) {
  const b = fs.readFileSync(f);
  if (b.slice(1, 4).toString() === "PNG") return [b.readUInt32BE(16), b.readUInt32BE(20)];
  if (b.slice(0, 3).toString() === "GIF") return [b.readUInt16LE(6), b.readUInt16LE(8)];
  throw new Error("unknown image " + f);
}
function addFit(slide, f, x, y, w, h, opts = {}) {
  const [iw, ih] = imgSize(f);
  const s = Math.min(w / iw, h / ih);
  const W = iw * s, H = ih * s;
  const X = x + (opts.align === "left" ? 0 : (w - W) / 2), Y = y + (opts.valign === "top" ? 0 : (h - H) / 2);
  slide.addImage({ path: f, x: X, y: Y, w: W, h: H, objectName: opts.name || path.basename(f), altText: opts.name || path.basename(f) });
  return { x: X, y: Y, w: W, h: H };
}
function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}
function card(s, x, y, w, h, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: HEX.lt2 }, line: { color: HEX.lt2 }, rectRadius: 0.08, objectName: name });
}
function stat(s, x, y, w, big, small, color, name) {
  card(s, x, y, w, 1.75, name + " card");
  s.addText(big, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.8, fontFace: "Cambria", fontSize: 32, bold: true, color: color || C.accent1, isTextBox: true, margin: 0, objectName: name + " value" });
  s.addText(small, { x: x + 0.2, y: y + 0.95, w: w - 0.4, h: 0.72, fontSize: 12, color: C.text1, isTextBox: true, margin: 0, valign: "top", objectName: name + " label" });
}
function bullets(s, items, x, y, w, h, size = 14, name = "bullets") {
  const arr = items.map((t, i) => ({ text: t, options: { bullet: { indent: 15 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } }));
  s.addText(arr, { x, y, w, h, fontSize: size, color: C.text1, valign: "top", isTextBox: true, objectName: name });
}
function note(s, text, x, y, w, h, size = 11) {
  s.addText(text, { x, y, w, h, fontSize: size, color: C.accent6, italic: true, isTextBox: true, valign: "top", objectName: "caption" });
}
const f1 = (v) => v.toFixed(1), f0 = (v) => v.toFixed(0), f3 = (v) => v.toFixed(3), f2 = (v) => v.toFixed(2);
const sgn = (v, d = 1) => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d);
const HDR = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 11, valign: "middle" } });
const TD = (t, o = {}) => ({ text: String(t), options: Object.assign({ fontSize: 11, color: HEX.dk1, valign: "middle" }, o) });
const OK = HEX.accent4, MID = "A86A12", BAD = HEX.accent5;
const verdictCell = (v) => TD(v === "ok" ? "same" : v === "close" ? "close" : "differs", { bold: true, color: v === "ok" ? OK : v === "close" ? MID : BAD });
const TB = { type: "solid", pt: 0.5, color: "D5DCE4" };

// ---------------------------------------------------------------- data
const L = S.layouts;
const LS = S.layout_stats;
const HL = S.heatload;
const base = HL[0];
const V = S.vapour || null;
const rad = S.radiation.find((r) => Math.abs(r.eps_cu - 0.3) < 1e-6);
const lay = (k, f) => L.find((r) => r.layout === k && Math.abs(r.flow - f) < 1e-6);
const short = (k) => (k === "A_built" ? "A*" : k);
const H5 = lay("H", 5), H17 = lay("H", 17.5), D17 = lay("D", 17.5), A5 = lay("A_built", 5), A17 = lay("A_built", 17.5);
const minMargin = Math.min(...L.map((r) => r.margin));
const cr = V && V.coupling_result ? V.coupling_result : null;
const Z1c = cr ? cr.zone_room[1] - V.coupled.z1 / 1000 : null;
const Z2c = cr ? cr.zone_room[0] - V.coupled.z2 / 1000 : null;

// ================================================================= 1 title
pres.addSection({ title: "Overview" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Overview" });
s.addText("SAHA cold stage: independent re-validation", { placeholder: "title" });
s.addText("Geometry, heat load, the 11 coil archetypes in 3-D and the coupled vapour column, rebuilt from scratch and compared with the 4–6 Oct decks · 7 Oct 2026", { placeholder: "body" });
s.addNotes("All models in this deck were written fresh for this check (saha_validation/ in the repository). They share only the inputs stated in the decks, not code. Radiation is left out of the vapour simulation by request; it was checked separately with a view-factor model.");

// ================================================================= 2 answer
s = content("The answer: the decks' numbers reproduce, with a few exceptions", "Overview");
stat(s, 0.5, 1.35, 3.0, `${f2(base.Q1)} W`, `Zone 1 heat gain, my conduction model (decks 2.58 / 2.575 W)`, C.accent1, "heat");
stat(s, 3.65, 1.35, 3.0, `${LS.within5} / ${LS.n}`, `layout cases within 5 mK of the result sheets (median ${f1(LS.median_abs)} mK)`, C.accent2, "layouts");
stat(s, 6.8, 1.35, 3.0, V ? `${f0(-V.coupled.z1)} mW` : "–", `vapour convection into Zone 1, coupled, no radiation (deck 178 mW with radiation)`, C.accent1, "vapour");
stat(s, 9.95, 1.35, 2.85, Z1c ? `${f2(Z1c)} W` : "–", `Zone 1 total, coupled, no radiation (deck 2.776 W incl. 34 mW)`, C.accent2, "z1total");
card(s, 0.5, 3.3, 6.05, 3.55, "same card");
s.addText("What is the same", { x: 0.7, y: 3.4, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.accent4, isTextBox: true, margin: 0 });
bullets(s, [
  `Heat load: ${f3(base.Q1)} W into Zone 1, ${f0(base.plates * 100)} % through the end plates (decks 2.58 W, 74 %).`,
  `Coil archetypes: spread, inlet and UA agree; ${LS.inlet_within20} / ${LS.n} inlets within 20 mK. Ranking unchanged: E_PDF, B and E flattest, A* worst.`,
  V ? `Vapour column: the same overturning loop from the ice tray to Zone 1; ice tray ${f0(V.coupled.ice)} mW, connectors ${f0(V.coupled.conn_lo)} / ${f0(V.coupled.conn_mid)} mW in.` : "Vapour column: see section C.",
  `Every layout holds ±0.15 K, with at least ${f0(minMargin)} mK to spare.`,
], 0.7, 3.9, 5.7, 2.9, 13, "same list");
card(s, 6.8, 3.3, 6.0, 3.55, "differs card");
s.addText("What differs or stays open", { x: 7.0, y: 3.4, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.accent5, isTextBox: true, margin: 0 });
bullets(s, [
  `Zone 2 conducts ${f2(base.Q2)} W, not the 1.9 W of the cold-zone deck (the room CFD's 1.80 W agrees with me).`,
  `Jacket H: the sheet's UA of ${f1(H17.UA_sheet)} W/K fits one wetted wall; with copper on both sides UA ≈ ${f0(H17.UA)} W/K and the inlet is ${f0((H17.inlet - H17.inlet_sheet) * 1000)} mK warmer.`,
  `Serpentine D: ${f1(D17.dp)} kPa laminar friction vs ${f1(D17.dp_sheet)} kPa on the sheet, while its film is taken laminar at Re ≈ 3900.`,
  `Jacket H in the 3-D coolant CFD: ${(S.coolant_cfd || []).find((r) => r.layout === "H" && r.m_gs === 17.5) ? f0(S.coolant_cfd.find((r) => r.layout === "H" && r.m_gs === 17.5).spread_mK) : "–"} mK vs 69 mK: its rings spread the coolant unevenly.`,
], 7.0, 3.9, 5.6, 2.9, 13, "differs list");

// ================================================================= 3 method
s = content("What was rebuilt, independently of the original code", "Overview");
const steps = [
  ["1", "Chamber heat load", "Axisymmetric conduction of the 425 mm stack: vapour, Perspex, foam, copper at set point, lab h 8 W/m²K at 35 °C, ice tray 0 °C. 0.25–1 mm grids."],
  ["2", "11 archetypes in 3-D", "Finite-volume copper zone (r, θ, z; 1.3–1.9 M cells) with voxelised passages and a 1-D coolant network: upwind energy balance, helical and duct correlations. 22 cases."],
  ["3", "Vapour column CFD", "Transient 3-D Boussinesq, 1 mm MAC grid, 0.24 M cells, 0–120 s. Robin walls from the room model; two-way exchange every 1 s from 60 s. No radiation."],
  ["4", "Checks", "Energy balance per case, a finer grid for A* and P, a gray-body radiation model, the Fluent mesh verifier (PASS) and the benchmark mesh orientation."],
];
steps.forEach((st, i) => {
  const x = 0.5 + i * 3.1;
  card(s, x, 1.45, 2.9, 4.7, `step ${st[0]}`);
  s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: 1.65, w: 0.7, h: 0.7, fill: { color: i === 2 ? HEX.accent1 : HEX.dk2 }, line: { color: HEX.lt2 }, objectName: `step ${st[0]} badge` });
  s.addText(st[0], { x: x + 0.2, y: 1.65, w: 0.7, h: 0.7, fontFace: "Cambria", fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle", isTextBox: true, margin: 0 });
  s.addText(st[1], { x: x + 0.2, y: 2.5, w: 2.5, h: 0.6, fontFace: "Cambria", fontSize: 17, bold: true, color: C.text1, isTextBox: true, margin: 0 });
  s.addText(st[2], { x: x + 0.2, y: 3.15, w: 2.5, h: 2.9, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: "top" });
});
note(s, "Inputs are the ones printed in the decks (methanol ρ 840, cp 2286, μ 1.43 mPa·s, Pr 15.5; R134a vapour at 84.4 kPa; copper k 390, foam 0.035, Perspex 0.19). Code: saha_validation/ in the repository.", 0.5, 6.3, 12.3, 0.6);

// ================================================================= section A
pres.addSection({ title: "A · Geometry and heat load" });
s = pres.addSlide({ masterName: "SECTION", sectionTitle: "A · Geometry and heat load" });
s.addText("A · Geometry and heat load", { placeholder: "title" });
s.addText("Is the chamber the decks describe self-consistent, and is 2.6 / 1.8 W the right heat to remove?", { placeholder: "body" });

s = content("Geometry is consistent; the '30 mm bore' is the neck OD", "A · Geometry and heat load");
const G = [
  ["Item", "Sources", "Value used here", "Check"],
  ["Stack (z, mm)", "Assembly PDF, cold-zone deck, Fluent sheet", "Perspex 0–60 · Z2 60–187 · Perspex 187–247 · Z1 247–365 · top 365–425", "ok"],
  ["Bore", "old PDF 25 mm · revised STEP 27 mm · atlas and sleeve PDF '30 mm bore'", "27 mm (r 13.5); 30 mm is the neck OD the sleeve clamps on", "close"],
  ["Zone 1 / Zone 2 copper", "118 = 11 + 96 + 11 · 127 = 11 + 105 + 11", "same", "ok"],
  ["Buffer · plates", "40/30 mm · 86 mm OD × 11 mm", "r 15–20 · r 13.5–43", "ok"],
  ["Coil", "Ø5/4 mm on Ø45.2 mm, 13.83 mm per strand", "0.1 mm radial gap to the 40 mm buffer; solder strip 3 × 0.3 mm assumed", "close"],
  ["Copper heat capacity, Zone 1", "deck 620–650 J/K", "1.84e-4 m³ × 8960 × 385 = 634 J/K", "ok"],
  ["Fluent vapour mesh", "920,052 hex, volumes 0.13 % under exact", "re-verified: every volume > 0, areas and extents PASS", "ok"],
];
s.addTable(G.map((r, i) => i === 0 ? r.map(HDR) : [TD(r[0], { bold: true }), TD(r[1]), TD(r[2]), verdictCell(r[3])]),
  { x: 0.5, y: 1.35, w: 12.3, colW: [2.2, 4.0, 4.9, 1.2], rowH: 0.55, border: TB, fill: { color: HEX.lt1 }, objectName: "geometry table" });
note(s, "The sleeve PDF's '30 mm nominal chamber bore' is the 30 mm OD of the copper neck (wall r 13.5–15). Layout E_PDF in the result sheets already uses it that way: body bore r 15, lanes at r 23.75–24.25.", 0.5, 6.15, 12.3, 0.7);

s = content(`Heat load: ${f2(base.Q1)} W into Zone 1 and ${f2(base.Q2)} W into Zone 2 by conduction`, "A · Geometry and heat load");
addFit(s, fig("heatload.png"), 0.4, 1.3, 7.4, 3.8, { name: "heat load chart" });
addFit(s, fig("chamber_field.png"), 7.9, 1.2, 2.6, 5.7, { name: "chamber field" });
const hrow = (k) => HL.find((r) => r.case.startsWith(k));
const HT = [["Case", "Z1, W", "Z2, W"],
  ["base, 0.5 mm grid", f3(base.Q1), f3(base.Q2)],
  ["grid 0.25 mm", f3(hrow("grid 0.25").Q1), f3(hrow("grid 0.25").Q2)],
  ["grid 1.0 mm", f3(hrow("grid 1.0").Q1), f3(hrow("grid 1.0").Q2)],
  ["lab 30 °C", f3(hrow("lab 30").Q1), f3(hrow("lab 30").Q2)],
  ["foam k 0.025", f3(hrow("foam k 0.025").Q1), f3(hrow("foam k 0.025").Q2)],
  ["foam k 0.015", f3(hrow("foam k 0.015").Q1), f3(hrow("foam k 0.015").Q2)]];
s.addTable(HT.map((r, i) => i === 0 ? r.map(HDR) : r.map((c, j) => TD(c, { align: j ? "right" : "left", fontSize: 10 }))),
  { x: 10.6, y: 1.35, w: 2.25, colW: [1.05, 0.6, 0.6], rowH: 0.42, border: TB, objectName: "heat table" });
bullets(s, [
  `Zone 1 matches the cold-zone deck (2.58 W) and the room CFD (2.575 W) to 0.2 %.`,
  `Zone 2 is ${f2(base.Q2)} W: the room CFD's 1.80 W is right; the cold-zone deck's 1.9 W is about 5 % high.`,
  `${f0(base.plates * 100)} % of the Zone 1 heat enters through the copper end plates, as stated.`,
  `Foam conductivity is the dominant uncertainty: PU or aerogel cut the load by 27 % or 56 %.`,
], 0.5, 5.15, 7.3, 1.8, 13, "heat bullets");

s = content("The supporting arithmetic in the decks checks out", "A · Geometry and heat load");
const AR = [["Claim in the decks", "Deck", "Re-computed", "Check"],
  ["Coolant bulk rise at 17.5 / 5 g/s (2.58 W)", "64 / 225 mK", "2.58 / (ṁ · 2286) = 64 / 226 mK", "ok"],
  ["17.5 g/s came from 40 W at a 1 K rise", "17.5 g/s", "40 / (2286 · 1) = 17.5 g/s", "ok"],
  ["Coolant friction heat at 17.5 g/s", "0.68 W", "33 kPa × 2.08e-5 m³/s = 0.69 W, about 25 % of the load: not small", "close"],
  ["Margin = 150 mK − spread / 2", "97.8 mK for A*", "150 − 104.4 / 2 = 97.8 mK", "ok"],
  ["'Spread at 5 W, same pattern'", "P 138 mK", "linear scaling: 71.4 × 5 / 2.58 = 138 mK", "ok"],
  ["−31.5 °C inlet fails for Zone 1", "1.0–1.4 K too cold", "walls centred by −30.15 / −30.30 °C inlets → 1.2–1.35 K", "ok"],
  ["Paired lane Re and Δp per branch", "471, 9.06 kPa", "471, 9.06 kPa (Shah–London f·Re)", "ok"],
  ["Helical-coil critical Re (d/D = 0.089)", "≈ 8400 vs 'onset ≈ 2400'", "Ito / Schmidt correlation: 9000; the low onset is an experiment", "close"],
  ["Bore radiation into Zone 1, ε 0.3, one-way", "≈ +40 mW", `${f0(rad.Z1_absorbed_mW)} mW (exact view factors, closure 2e-16)`, "ok"],
];
s.addTable(AR.map((r, i) => i === 0 ? r.map(HDR) : [TD(r[0]), TD(r[1]), TD(r[2]), verdictCell(r[3])]),
  { x: 0.5, y: 1.35, w: 12.3, colW: [3.9, 2.0, 5.2, 1.2], rowH: 0.5, border: TB, objectName: "arithmetic table" });

// ================================================================= section B
pres.addSection({ title: "B · Coil archetypes in 3-D" });
s = pres.addSlide({ masterName: "SECTION", sectionTitle: "B · Coil archetypes in 3-D" });
s.addText("B · The 11 coil archetypes in 3-D", { placeholder: "title" });
s.addText("Same zone, same heat, same coolant: does an independent conjugate model give the result sheets' wall spread, inlet, pressure drop and UA?", { placeholder: "body" });

s = content("Inner-wall maps from the new 3-D model, 17.5 g/s", "B · Coil archetypes in 3-D");
addFit(s, fig("wallmaps_17.5.png"), 0.4, 1.2, 8.6, 5.75, { name: "wall maps" });
bullets(s, [
  "Copper zone on an (r, θ, z) grid: 0.5 mm in the copper, 2° round, 0.5 mm in z; 1.3–1.9 M cells.",
  "Passages voxelised from the sheets' geometry notes; film coefficient scaled to the true wetted area.",
  "External heat applied as the surface flux of the chamber model: bore, plates, rims, carrier.",
  "Linear problem: one solve, then the inlet that centres the wall is read off.",
  "Energy balance closes to 1e-11 W (F and H to < 5 mW, manifold rounding).",
], 9.2, 1.35, 3.7, 5.4, 13, "model bullets");

s = content(`${LS.within5} of ${LS.n} cases agree within 5 mK; ${LS.inlet_within20} inlets within 20 mK`, "B · Coil archetypes in 3-D");
addFit(s, fig("parity.png"), 0.4, 1.3, 12.5, 4.3, { name: "parity" });
note(s, "Each point is one layout at one flow (blue 17.5 g/s, orange 5 g/s). Grey band: ±10 mK on spread, ±20 mK on inlet. The outliers are H (UA, and spread at 5 g/s), A* at 5 g/s and E_PDF; see the next slides.", 0.5, 5.75, 12.3, 0.8, 12);

s = content("Layout by layout: result sheet against this re-validation", "B · Coil archetypes in 3-D");
const T1 = [["Layout", "Spread 17.5 g/s, mK\nsheet / mine", "Inlet 17.5 g/s, °C\nsheet / mine", "Spread 5 g/s, mK\nsheet / mine", "Δp 17.5 g/s, kPa\nsheet / mine", "UA 17.5, W/K\nsheet / mine", "Check"]];
const order = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"];
order.forEach((k) => {
  const a = lay(k, 17.5), b = lay(k, 5);
  const ds = Math.max(Math.abs(a.spread - a.spread_sheet), Math.abs(b.spread - b.spread_sheet));
  const di = Math.abs(a.inlet - a.inlet_sheet);
  const v = ds <= 5 && di <= 0.02 ? "ok" : ds <= 13 && di <= 0.12 ? "close" : "bad";
  T1.push([TD(short(k), { bold: true }), TD(`${f1(a.spread_sheet)} / ${f1(a.spread)}`), TD(`${f3(a.inlet_sheet)} / ${f3(a.inlet)}`),
    TD(`${f1(b.spread_sheet)} / ${f1(b.spread)}`), TD(`${f1(a.dp_sheet)} / ${f1(a.dp)}`), TD(`${f1(a.UA_sheet)} / ${f1(a.UA)}`), verdictCell(v)]);
});
s.addTable(T1.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 0.5, y: 1.3, w: 12.3, colW: [1.0, 2.0, 2.3, 2.0, 2.0, 1.8, 1.2], rowH: 0.42, border: TB, objectName: "layout table" });
note(s, "My Δp is fully developed friction only (no bends, galleries or fittings); it sits 2–4 kPa under the sheets for the coils, which include minor losses.", 0.5, 6.45, 12.3, 0.45, 11);

s = content("Where the new model disagrees, and why", "B · Coil archetypes in 3-D");
const turb = (S.turb || []).find((r) => r.layout === "D");
const dif = [
  ["H · annular jacket", `UA ${f1(H17.UA_sheet)} → ${f1(H17.UA)} W/K`, `The sheet's UA fits a 1 mm gap with one wetted wall. In the carrier both gap walls are copper, so UA roughly doubles and the centring inlet is ${f0((H17.inlet - H17.inlet_sheet) * 1000)} mK warmer. At 5 g/s my spread is ${f0(H5.spread)} vs ${f0(H5.spread_sheet)} mK; at 17.5 g/s it agrees.`],
  ["D · axial serpentine", `Δp ${f1(D17.dp_sheet)} → ${f1(D17.dp)} kPa`, `Laminar friction over 1.4 m of 4 mm passage gives ~7 kPa; 50 kPa needs ~15 bend losses or turbulent friction. Yet the sheet's UA (${f1(D17.UA_sheet)} W/K) is laminar, Nu 4.36, at Re 3900.` + (turb ? ` A turbulent film (Gnielinski) moves the inlet to ${f3(turb.inlet_C)} °C, spread ${f0(turb.spread_mK)} mK.` : "")],
  ["A* · as built, 5 g/s", `${f0(A5.spread_sheet)} → ${f0(A5.spread)} mK`, `The solder strip and 0.1 mm gap are smaller than a cell; the as-built tube is the most resolution-sensitive case. At 17.5 g/s: ${f0(A17.spread)} vs ${f0(A17.spread_sheet)} mK.` + (S.grid ? ` Fine grid (0.25 mm): ${S.grid.filter((r) => r.layout === "A_built").map((r) => `${f0(r.spread_mK)} mK at ${r.m_gs} g/s`).join(", ")}.` : "")],
  ["E_PDF · sleeve", `${f0(lay("E_PDF", 17.5).spread_sheet)} → ${f0(lay("E_PDF", 17.5).spread)} mK`, "Header and gallery geometry are not fixed in the PDF; I placed the galleries in the 72 mm header. It stays among the two flattest layouts."],
];
dif.forEach((d, i) => {
  const y = 1.35 + i * 1.38;
  card(s, 0.5, y, 12.3, 1.25, `diff ${i}`);
  s.addText(d[0], { x: 0.7, y: y + 0.12, w: 2.9, h: 0.45, fontFace: "Cambria", fontSize: 16, bold: true, color: C.text1, isTextBox: true, margin: 0 });
  s.addText(d[1], { x: 0.7, y: y + 0.6, w: 2.9, h: 0.5, fontSize: 14, bold: true, color: C.accent5, isTextBox: true, margin: 0 });
  s.addText(d[2], { x: 3.7, y: y + 0.08, w: 8.9, h: 1.1, fontSize: 12, color: C.text1, isTextBox: true, margin: 0, valign: "middle" });
});

s = content("Wall spread and pressure drop, side by side", "B · Coil archetypes in 3-D");
addFit(s, fig("cmp_spread.png"), 0.5, 1.15, 12.3, 2.85, { name: "spread bars" });
addFit(s, fig("cmp_dp.png"), 0.5, 4.05, 12.3, 2.85, { name: "dp bars" });

s = content("Inlet temperature: every centring inlet and window reproduces", "B · Coil archetypes in 3-D");
addFit(s, fig("inlet_validation.png"), 0.4, 1.2, 12.5, 4.9, { name: "inlet validation" });
note(s, `Grey bars: the result sheets' allowed inlet windows; coloured bars: this model. ${LS.inlet_within20} of ${LS.n} centring inlets agree within 20 mK; the exceptions are H (film area) and A* at 5 g/s. The −31.5 °C setting lies outside every window.`, 0.5, 6.2, 12.3, 0.7, 12);

for (const k of ["A_built_17.5", "E_PDF_17.5"]) {
  const f = fig(`sheets/${k}.png`);
  if (!fs.existsSync(f)) continue;
  const [lk, lf] = [k.slice(0, k.lastIndexOf("_")), k.slice(k.lastIndexOf("_") + 1)];
  s = content(`Re-validated result sheet: ${short(lk)} at ${lf} g/s`, "B · Coil archetypes in 3-D");
  addFit(s, f, 0.4, 1.1, 12.5, 5.85, { name: `sheet ${k}` });
}

// ================================================================= section B2: coolant CFD
if (S.coolant_cfd && S.coolant_cfd.length) {
  pres.addSection({ title: "B2 · 3-D coolant CFD" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "B2 · 3-D coolant CFD" });
  s.addText("B2 · The methanol itself, in 3-D", { placeholder: "title" });
  s.addText("A coarse conjugate CFD: laminar Navier–Stokes in every passage, the coolant warming as it travels, and the copper around it. No film correlation.", { placeholder: "body" });

  s = content("Coolant CFD set-up", "B2 · 3-D coolant CFD");
  bullets(s, [
    "Same cylindrical grid as the layout model, refined: 0.4 mm in r and z, 2° round; thin channels refined to 0.125 mm (E lanes) and 0.25 mm (H gap). 0.07–0.4 M methanol cells per layout.",
    "Steady incompressible laminar Navier–Stokes by artificial compressibility, staggered faces, second-order upwind advection, Heun (RK2) pseudo-time, centrifugal and Coriolis terms of the curved channels. Joins between passages overlap by a fraction of a cell so the voxels connect.",
    "Inlet: a volume source in the first 2 mm of the passage; outlet: p = 0. Hairpins and the radial link of B are mass + mixed-enthalpy links.",
    "Then one conjugate energy solve: methanol + copper + foam, upwind advection with the CFD fluxes, the same external heat as the layout model.",
    "Limit: walls are voxel stair-steps (one 0.4 mm step every ~8 mm along a helix), which adds form losses: CFD Δp is an upper bound. Heat transfer, temperatures and flow paths are the useful output.",
  ], 0.5, 1.35, 12.3, 5.4, 15, "cfd setup");

  const CR = [["Layout, flow", "Spread, mK\nsheet / 1-D / CFD", "Inlet, °C\nsheet / 1-D / CFD", "Coolant rise, mK\n1-D / CFD", "Δp, kPa\nsheet / 1-D / CFD", "Check"]];
  const order2 = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"];
  [17.5, 5].forEach((fl) => order2.forEach((k) => {
    const c = S.coolant_cfd.find((r) => r.layout === k && Math.abs(r.m_gs - fl) < 1e-6);
    const a = lay(k, fl);
    if (!c) return;
    const ds = Math.abs(c.spread_mK - a.spread_sheet), di = Math.abs(c.inlet_C - a.inlet_sheet);
    const v = ds <= 5 && di <= 0.03 ? "ok" : ds <= 10 && di <= 0.1 ? "close" : "bad";
    CR.push([TD(`${short(k)}, ${fl} g/s`, { bold: true, fontSize: 10 }), TD(`${f1(a.spread_sheet)} / ${f1(a.spread)} / ${f1(c.spread_mK)}`, { fontSize: 10 }),
      TD(`${f3(a.inlet_sheet)} / ${f3(a.inlet)} / ${f3(c.inlet_C)}`, { fontSize: 10 }), TD(`${f0(a.rise)} / ${f0(c.rise_mK)}`, { fontSize: 10 }),
      TD(`${f1(a.dp_sheet)} / ${f1(a.dp)} / ${f1(c.dp_kPa)}`, { fontSize: 10 }), verdictCell(v)]);
  }));
  s = content("Coolant CFD against the sheets and the 1-D network model", "B2 · 3-D coolant CFD");
  s.addTable(CR.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 0.5, y: 1.25, w: 12.3, colW: [1.6, 2.6, 3.2, 1.6, 2.3, 1.0], rowH: 0.38, border: TB, objectName: "cfd table" });
  note(s, "Layouts chosen with the user: the two flattest on the sheets (E_PDF, B), folded bifilar A, plain helix P, jacket H, plus the as-built A*. CFD Δp of the helices is high because the voxel walls are stair-stepped; E_PDF and H have straight walls and their Δp is close to the sheets. H is less uniform in 3-D: its one-side-fed rings do not spread the coolant evenly.", 0.5, 6.2, 12.3, 0.75, 10.5);

  for (const k of order2) {
    const f3d = fig(`coolant/${k}_17.5_3d.png`), fp = fig(`coolant/${k}_17.5_paths.png`);
    if (!fs.existsSync(f3d)) continue;
    const c = S.coolant_cfd.find((r) => r.layout === k && Math.abs(r.m_gs - 17.5) < 1e-6);
    s = content(`${short(k)}: methanol temperature, streamlines and pressure (17.5 g/s)`, "B2 · 3-D coolant CFD");
    addFit(s, f3d, 0.4, 1.1, 12.5, 4.0, { name: `${k} 3d` });
    if (fs.existsSync(fp)) addFit(s, fp, 0.4, 5.1, 9.6, 1.85, { name: `${k} paths` });
    note(s, `CFD: spread ${f0(c.spread_mK)} mK, centring inlet ${f3(c.inlet_C)} °C, coolant rise ${f0(c.rise_mK)} mK, peak speed ${f2(c.umax)} m/s, ${c.cells_fluid.toLocaleString("en-US")} methanol cells.`, 10.1, 5.2, 2.8, 1.7, 11);
  }
  for (const k of ["P", "A_built", "E_PDF", "H"]) {
    const gif = fig(`coolant/${k}_17.5_flow.gif`);
    if (!fs.existsSync(gif)) continue;
    s = content(`${short(k)}: methanol tracers travelling and warming (animated)`, "B2 · 3-D coolant CFD");
    addFit(s, gif, 0.4, 1.1, 7.5, 5.85, { name: `${k} gif` });
    note(s, "Tracers released at the inlet follow the CFD streamlines; colour is the local methanol temperature. Plays in slide show.", 8.2, 1.4, 4.6, 2, 13);
  }
}

// ================================================================= section C
pres.addSection({ title: "C · Coupled vapour column" });
s = pres.addSlide({ masterName: "SECTION", sectionTitle: "C · Coupled vapour column" });
s.addText("C · The coupled vapour column, re-simulated", { placeholder: "title" });
s.addText("A new transient 3-D CFD of the R134a column, coupled both ways to the room and insulation, 0–120 s. Radiation left out, as requested.", { placeholder: "body" });

s = content("Model: the vapour column, with walls from the room model", "C · Coupled vapour column");
addFit(s, fig("v_bc_model.png"), 0.4, 1.2, 12.5, 5.0, { name: "bc model" });
note(s, "T_ext and G_out come from my axisymmetric room / insulation model: G_out is the collective response of each Perspex face to the vapour being raised 1 K. With the bore adiabatic it gives Zone 1 2.574 W and Zone 2 1.808 W (coupled deck: 2.5751 / 1.7995 W).", 0.5, 6.3, 12.3, 0.6, 11);

s = content("Making the two-way exchange stable", "C · Coupled vapour column");
const steps2 = [
  ["Run 1", "Face-by-face exchange T_ext = T_room + q / G_out", "Ran away after ~25 s of coupling at the middle connector (G_out ≈ 2.3 W/m²K): vapour cells at 63–126 °C, impossible without a heat source. 0–75 s kept (clean)."],
  ["Run 2", "Exchange through the room's full face admittance", "Its diagonal is ~145× G_out·A, so face-to-face noise was amplified: middle-connector T_ext +18 K on average. Bounded, but wrong: discarded."],
  ["Run 3", "Same deck exchange on smooth ~10 mm bands, relaxed", "Stable in ~10 exchanges offline; restarted from the clean t = 75 s state. This is the run reported here (85–120 s means)."],
];
steps2.forEach((st, i) => {
  const y = 1.35 + i * 1.75;
  card(s, 0.5, y, 12.3, 1.6, `coupling step ${i}`);
  s.addText(st[0], { x: 0.7, y: y + 0.15, w: 1.4, h: 0.5, fontFace: "Cambria", fontSize: 18, bold: true, color: i === 2 ? C.accent4 : C.accent5, isTextBox: true, margin: 0 });
  s.addText(st[1], { x: 2.2, y: y + 0.15, w: 10.4, h: 0.45, fontSize: 15, bold: true, color: C.text1, isTextBox: true, margin: 0 });
  s.addText(st[2], { x: 2.2, y: y + 0.65, w: 10.4, h: 0.85, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: "top" });
});
note(s, "Why it matters: for one 0.5 mm strip of Perspex the room is far stiffer than the smooth G_out law says, so a face-level update over-corrects and grows. The deck's exchange is fine once it is applied to smoothed (row-averaged) quantities, as the deck did.", 0.5, 6.6, 12.3, 0.4, 10.5);

if (V) {
  s = content("Mid-plane: still vapour, time mean and one instant", "C · Coupled vapour column");
  addFit(s, fig("v_midplane.png"), 0.4, 1.15, 12.5, 5.8, { name: "midplane" });

  s = content("In 3-D: one rising and one falling stream", "C · Coupled vapour column");
  addFit(s, fig("vapour_3d_four.png"), 0.3, 1.15, 9.0, 5.8, { name: "3d four" });
  const RN = ["lower connector", "Zone 2 (wall −15)", "middle connector", "Zone 1 (wall −30)", "top region"];
  const dT = [-9.0, -15.2, -20.8, -26.5, -2.8], dR = [1.6, 1.4, 2.3, 1.0, 0.3];
  const VT = [["Region", "Mean T, °C\ndeck / mine", "rms, K\ndeck / mine"]];
  RN.forEach((n, i) => VT.push([TD(n, { fontSize: 10 }), TD(`${f1(dT[i])} / ${f1(V.T_mean[i + 1])}`, { fontSize: 10 }), TD(`${f1(dR[i])} / ${f1(V.T_rms[i + 1])}`, { fontSize: 10 })]));
  s.addTable(VT.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 9.45, y: 1.4, w: 3.45, colW: [1.35, 1.1, 1.0], rowH: 0.48, border: TB, objectName: "region table" });
  note(s, `Time means over 85–120 s. Vertical velocity ${f3(V.w_rms_stat)} m/s rms (deck 0.032). Radius drawn ×2.5; copper = Zones 2 (lower) and 1; blue glass = Perspex; dark slab = ice tray. Deck values include radiation.`, 9.45, 4.6, 3.45, 2.2, 11);

  if (fs.existsSync(fig("vapour_streamlines.png"))) {
    s = content("Streamlines: the time-mean flow and one instant", "C · Coupled vapour column");
    addFit(s, fig("vapour_streamlines.png"), 0.3, 1.1, 9.3, 5.85, { name: "vapour streamlines" });
    bullets(s, [
      "Left: streamlines of the time-mean velocity (85–120 s): a slow loop from the ice tray up to Zone 1 and back.",
      "Middle: streamlines of the full velocity field at t = 120 s: the cold stream falling from Zone 1 and the warm stream rising from the ice tray twist round each other in the middle connector.",
      "The top region is stably stratified: closed, slow cells under the cap.",
    ], 9.8, 1.4, 3.1, 5.4, 13, "streamline bullets");
  }

  s = content("Transient, t = 0 to 120 s (animated in slide show)", "C · Coupled vapour column");
  addFit(s, fig("vapour_0_120s.gif"), 0.4, 1.15, 7.2, 5.8, { name: "animation 0-120 s" });
  bullets(s, [
    "Starts from the still-vapour conduction field with a 1 mK random disturbance.",
    "Plumes break the symmetry within 2–3 s; Zone 1 draws about 150 mW by 5 s.",
    "0–60 s: walls one-way (T_ext frozen). 60–120 s: two-way, T_ext updated every 1 s from the room model.",
    "Right: 2000 tracers carried by the flow, last 1 s of path, coloured by local temperature.",
  ], 7.9, 1.4, 5.0, 5.2, 14, "gif bullets");

  s = content("Where the heat comes from and where it goes (coupled, 60–120 s)", "C · Coupled vapour column");
  addFit(s, fig("v_history_60_120.png"), 0.3, 1.15, 12.7, 4.6, { name: "history" });
  const c = V.coupled;
  card(s, 0.5, 5.9, 12.3, 0.95, "history summary");
  s.addText(`Time means 85–120 s: ice tray ${f0(c.ice)} + lower connector ${f0(c.conn_lo)} + middle connector ${f0(c.conn_mid)} mW in; Zone 1 wall ${f0(-c.z1)} mW out; Zone 2 wall ${sgn(c.z2, 0)} mW into the vapour; top wall + cap ${f0(c.top_wall + c.cap)} mW. Block scatter on Zone 1: ±${f1(c.z1_scatter)} mW.`,
    { x: 0.7, y: 5.95, w: 11.9, h: 0.85, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: "middle" });

  s = content("What the two-way coupling changes on the Perspex walls", "C · Coupled vapour column");
  addFit(s, fig("v_coupling.png"), 0.3, 1.15, 12.7, 5.2, { name: "coupling" });
  if (cr) {
    note(s, `Coupled walls run colder than one-way by ${f1(-cr.dT_lo)} K (lower connector), ${f1(-cr.dT_mid)} K (middle) and ${f1(-cr.dT_top)} K (top) on average; deck, with radiation: 2.2 / 2.8 / 2.2 K. Cap underside ${f1(cr.T_cap_cpl)} °C (one-way ${f1(cr.T_cap_one)} °C).`, 0.5, 6.4, 12.3, 0.55, 11);
  }

  s = content("Coupled vapour column: deck against this re-simulation", "C · Coupled vapour column");
  const VR = [["Quantity", "Deck one-way\n(no radiation)", "Deck coupled\n(+ radiation, ε 0.3)", "This study, coupled\n(no radiation)", "Check"],
    ["Zone 1 total heat, W", "2.732", "2.776", f3(Z1c), Math.abs(Z1c - 2.742) < 0.03 ? "ok" : "close"],
    ["Zone 2 total heat, W", "1.751", "1.747", f3(Z2c), Math.abs(Z2c - 1.75) < 0.03 ? "ok" : "close"],
    ["Vapour → Zone 1 wall, mW", "172", "178", f0(-V.coupled.z1), Math.abs(-V.coupled.z1 - 175) < 20 ? "ok" : "close"],
    ["Ice tray → vapour, mW", "51", "49", f0(V.coupled.ice), Math.abs(V.coupled.ice - 50) < 10 ? "ok" : "close"],
    ["Lower / middle connector → vapour, mW", "60 / 51", "58 / 51", `${f0(V.coupled.conn_lo)} / ${f0(V.coupled.conn_mid)}`, Math.abs(V.coupled.conn_lo - 59) < 10 && Math.abs(V.coupled.conn_mid - 51) < 10 ? "ok" : "close"],
    ["Zone 2 wall → vapour, mW", "+9", "+17", sgn(V.coupled.z2, 0), "close"],
    ["Zone 1 vapour mean / rms", "–", "−26.5 °C / 1.0 K", `${f1(V.T_mean[4])} °C / ${f1(V.T_rms[4])} K`, Math.abs(V.T_mean[4] + 26.5) < 1 ? "ok" : "close"],
    ["Vertical velocity rms, m/s", "–", "0.032", f3(V.w_rms_stat), Math.abs(V.w_rms_stat - 0.032) < 0.008 ? "ok" : "close"],
  ];
  s.addTable(VR.map((r, i) => i === 0 ? r.map(HDR) : [TD(r[0]), TD(r[1]), TD(r[2]), TD(r[3], { bold: true }), verdictCell(r[4])]),
    { x: 0.5, y: 1.3, w: 12.3, colW: [3.6, 2.0, 2.3, 2.9, 1.5], rowH: 0.5, border: TB, objectName: "vapour table" });
  note(s, `Without radiation the deck's coupled Zone 1 total would be about 2.776 − 0.034 = 2.742 W. Zone 1 total here = room-side conduction with the vapour heat drawn from the Perspex (${f3(cr.zone_room[1])} W) + vapour convection. Grid 1.0 mm, 0.24 M cells, ${V.steps} time steps; means over 85–120 s.`, 0.5, 5.95, 12.3, 0.9, 11);

  if (S.vapourmap) {
    s = content("What the vapour heat does to the coil wall", "C · Coupled vapour column");
    const VM = [["Coil, flow", "Spread without vapour, mK", "With the CFD vapour map, mK", "Change, mK", "Inlet shift, mK", "Deck, with radiation"]];
    const deckv = { "A_built17.5": "106 → 111 mK, −10 mK", "A_built5": "122 → 129 mK, −23 mK", "E_PDF17.5": "40 → 42 mK, −10 mK", "H17.5": "69 → 70 mK, −21 mK" };
    S.vapourmap.forEach((r) => {
      const b0 = lay(r.layout, r.m_gs);
      VM.push([TD(`${short(r.layout)}, ${r.m_gs} g/s`, { bold: true }), TD(f1(b0.spread)), TD(f1(r.spread_mK)), TD(sgn(r.spread_mK - b0.spread)), TD(sgn((r.inlet_C - b0.inlet) * 1000, 0)), TD(deckv[r.layout + r.m_gs] || "–")]);
    });
    s.addTable(VM.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 0.5, y: 1.4, w: 12.3, colW: [2.0, 2.2, 2.4, 1.6, 1.7, 2.4], rowH: 0.55, border: TB, objectName: "coil vapour table" });
    note(s, "The time-mean convective heat from the CFD (a θ–z map on the Zone 1 bore) is added to the external load and the 3-D layout model is re-solved. Every layout still holds ±0.15 K.", 0.5, 1.6 + 0.55 * VM.length, 12.3, 0.9, 12);
  }
}

// ================================================================= section D
pres.addSection({ title: "D · Verdict" });
s = content("Verdict: is the answer the same?", "D · Verdict");
const VD = [["Claim", "Decks", "This re-validation", "Same?"],
  ["Zone 1 / Zone 2 conduction heat", "2.58 / 1.9 W (room CFD 2.575 / 1.80)", `${f3(base.Q1)} / ${f3(base.Q2)} W`, "close"],
  ["About 74 % of Zone 1 heat enters via the plates", "74 %", `${f0(base.plates * 100)} %`, "ok"],
  ["Every archetype holds ±0.15 K", "yes, margin ≥ 90 mK", `yes, margin ≥ ${f0(minMargin)} mK`, "ok"],
  ["Spread and inlet per layout", "result sheets", `${LS.within5} / ${LS.n} within 5 mK; ${LS.inlet_within20} / ${LS.n} inlets within 20 mK`, "ok"],
  ["Flattest: E_PDF, B, E", "38 / 43 / 46 mK", `${f0(lay("E_PDF", 17.5).spread)} / ${f0(lay("B", 17.5).spread)} / ${f0(lay("E", 17.5).spread)} mK`, "ok"],
  ["Jacket H film and inlet", "UA 13.2 W/K, −30.239 °C", `UA ${f0(H17.UA)} W/K, ${f3(H17.inlet)} °C (both walls wetted)`, "bad"],
  ["Serpentine D pressure drop", "50 kPa", `${f1(D17.dp)} kPa laminar; regime unresolved`, "bad"],
];
const cfdE = (S.coolant_cfd || []).find((r) => r.layout === "E_PDF" && Math.abs(r.m_gs - 17.5) < 1e-6);
const cfdH = (S.coolant_cfd || []).find((r) => r.layout === "H" && Math.abs(r.m_gs - 17.5) < 1e-6);
if (cfdE) VD.push(["E_PDF in 3-D coolant CFD (17.5 g/s)", "38 mK, 14.4 kPa", `${f0(cfdE.spread_mK)} mK, ${f1(cfdE.dp_kPa)} kPa`, "ok"]);
if (cfdH) VD.push(["Jacket H in 3-D coolant CFD (17.5 g/s)", "69 mK", `${f0(cfdH.spread_mK)} mK: rings spread the flow unevenly`, "close"]);
if (V) {
  VD.push(["Vapour convection into Zone 1", "172–178 mW", `${f0(-V.coupled.z1)} mW (no radiation)`, Math.abs(-V.coupled.z1 - 175) < 20 ? "ok" : "close"]);
  VD.push(["Zone 1 total with the vapour", "2.732 W one-way / 2.776 W", `${f3(Z1c)} W (no radiation)`, Math.abs(Z1c - 2.742) < 0.03 ? "ok" : "close"]);
}
s.addTable(VD.map((r, i) => i === 0 ? r.map(HDR) : [TD(r[0]), TD(r[1]), TD(r[2]), verdictCell(r[3])]),
  { x: 0.5, y: 1.25, w: 12.3, colW: [4.0, 3.3, 3.8, 1.2], rowH: 0.43, border: TB, objectName: "verdict table" });

s = content("Limits of this check, and the deeper study it sets up", "D · Verdict");
card(s, 0.5, 1.35, 6.0, 5.4, "limits card");
s.addText("Limits", { x: 0.7, y: 1.45, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text1, isTextBox: true, margin: 0 });
bullets(s, [
  "Same physics family as the decks (developed-flow h, Boussinesq, laminar): shared modelling assumptions are not tested, only their implementation and numbers.",
  "Passage geometry rebuilt from the sheets' notes; the manifolds of E, E_PDF, F and H are my reading.",
  "Vapour CFD on a 1 mm stepped grid, one 120 s realisation; no radiation, no condensation.",
  "No experiment anchors any of it.",
], 0.7, 1.95, 5.6, 4.7, 13, "limits list");
card(s, 6.8, 1.35, 6.0, 5.4, "next card");
s.addText("Proposed deeper study", { x: 7.0, y: 1.45, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text1, isTextBox: true, margin: 0 });
bullets(s, [
  "Settle the high-flow regime: laminar vs transitional film for the 17.5 g/s coils and the straight passages (D, F spine, H rings).",
  "Jacket H and a plenum-fed axial jacket (V5): gap flow with both walls wetted, guard lengths, buoyancy.",
  "Vapour CFD at 0.75 mm with longer statistics; feed its wall map into every layout.",
  "Pump-stop and chiller-stop transients on the 3-D copper model.",
  "Then the Fluent comparison (steps 2–6) against these numbers.",
], 7.0, 1.95, 5.6, 4.7, 13, "next list");

pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
});
