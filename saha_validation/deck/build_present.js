// SAHA presentation deck (standalone results, no comparison). node build_deck.js <summary.json> <figs dir> <out.pptx>
const fs = require("fs");
const path = require("path");
const pptxgen = require(process.env.PPTXGENJS || "pptxgenjs");
const { applyTheme } = require(process.env.APPLY_THEME);

const [, , SUMMARY, FIGS, OUT] = process.argv;
const S = JSON.parse(fs.readFileSync(SUMMARY, "utf8"));
const fig = (f) => path.join(FIGS, f);

const SHORT = true;
const FOOT = "SAHA cold stage · thermal design of the cold zones · 7 Oct 2026";
// theme of the original SAHA decks (4-6 Oct): Cambria / Calibri, navy + copper
const THEME = {
  name: "SAHA",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A1F2B", lt1: "FFFFFF", dk2: "13294B", lt2: "EEF3F8",
    accent1: "B87333", accent2: "2A78D6", accent3: "EB6834", accent4: "1BAF7A", accent5: "EDA100", accent6: "6B7280",
    hlink: "2A78D6", folHlink: "13294B",
  },
};
const HEX = THEME.colors;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "SAHA cold stage: thermal design";
pres.author = "SAHA thermal study";
const C = pres.SchemeColor;
const SUB = "C9D3E0";

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.85, y: 1.9, w: 11.0, h: 1.9, fontFace: "Cambria", fontSize: 38, bold: true, color: C.background1, valign: "bottom", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.85, y: 3.95, w: 10.5, h: 1.6, fontFace: "Calibri", fontSize: 16, color: SUB, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "SECTION",
  background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.85, y: 3.15, w: 11.5, h: 1.0, fontFace: "Cambria", fontSize: 34, bold: true, color: C.background1, valign: "middle", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.85, y: 4.4, w: 11.0, h: 1.2, fontFace: "Calibri", fontSize: 16, color: SUB, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 12.3, h: 0.75, fontFace: "Cambria", fontSize: 26, bold: true, color: C.text2, valign: "middle", align: "left" }, text: "" } },
    { text: { text: FOOT, options: { x: 0.5, y: 7.05, w: 8, h: 0.25, fontFace: "Calibri", fontSize: 8, color: HEX.accent6 } } },
  ],
  slideNumber: { x: 12.4, y: 7.05, w: 0.5, h: 0.25, fontFace: "Calibri", fontSize: 8, color: HEX.accent6, align: "right" },
});

// ---------------------------------------------------------------- helpers
function imgSize(f) {
  const b = fs.readFileSync(f);
  if (b.slice(1, 4).toString() === "PNG") return [b.readUInt32BE(16), b.readUInt32BE(20)];
  if (b.slice(0, 3).toString() === "GIF") return [b.readUInt16LE(6), b.readUInt16LE(8)];
  throw new Error("unknown image " + f);
}
function addFit(slide, f, x, y, w, h, opts = {}) {
  if (slide === NOOP) return {};
  const [iw, ih] = imgSize(f);
  const s = Math.min(w / iw, h / ih);
  const W = iw * s, H = ih * s;
  const X = x + (opts.align === "left" ? 0 : (w - W) / 2), Y = y + (opts.valign === "top" ? 0 : (h - H) / 2);
  slide.addImage({ path: f, x: X, y: Y, w: W, h: H, objectName: opts.name || path.basename(f), altText: opts.name || path.basename(f) });
  return { x: X, y: Y, w: W, h: H };
}
const NOOP = { addText() {}, addImage() {}, addShape() {}, addTable() {}, addNotes() {} };
function content(title, section, take, fullOnly) {
  if (SHORT && fullOnly) return NOOP;
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  if (!take) return s;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 6.3, w: 12.3, h: 0.55, fill: { color: HEX.dk2 }, line: { color: HEX.dk2 }, rectRadius: 0.06, objectName: "takeaway bar" });
  s.addText(take, { x: 0.7, y: 6.3, w: 11.9, h: 0.55, fontSize: 13, bold: true, color: C.background1, valign: "middle", isTextBox: true, margin: 0, objectName: "takeaway" });
  const k = 5.03 / 5.85;
  const sq = (o) => {
    if (!o || typeof o.y !== "number" || o.y < 1.05) return o;
    const o2 = Object.assign({}, o);
    o2.y = 1.12 + (o.y - 1.1) * k;
    if (typeof o.h === "number") o2.h = o.h * k;
    if (o.path && typeof o.w === "number") { o2.w = o.w * k; o2.x = o.x + (o.w - o2.w) / 2; }
    if (typeof o.rowH === "number") o2.rowH = o.rowH * k;
    return o2;
  };
  const P = {
    addText: (t, o) => s.addText(t, sq(o)),
    addImage: (o) => s.addImage(sq(o)),
    addShape: (t, o) => s.addShape(t, sq(o)),
    addTable: (r, o) => s.addTable(r, sq(o)),
    addNotes: (n) => s.addNotes(n),
    addChart: (t, d, o) => s.addChart(t, d, sq(o)),
  };
  return P;
}
function divider(num, title, sub, section) {
  pres.addSection({ title: section });
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: section });
  s.addText(num, { x: 0.85, y: 1.95, w: 3, h: 1.1, fontFace: "Cambria", fontSize: 60, bold: true, color: C.accent1, isTextBox: true, margin: 0, valign: "bottom", objectName: "section number" });
  s.addText(title, { placeholder: "title" });
  s.addText(sub, { placeholder: "body" });
}
function card(s, x, y, w, h, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: HEX.lt2 }, line: { color: HEX.lt2 }, rectRadius: 0.05, shadow: { type: "outer", color: "000000", opacity: 0.12, blur: 3, offset: 1, angle: 90 }, objectName: name });
}
function stat(s, x, y, w, big, small, color, name) {
  card(s, x, y, w, 1.75, name + " card");
  s.addText(big, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.8, fontFace: "Cambria", fontSize: 30, bold: true, color: C.accent1, isTextBox: true, margin: 0, objectName: name + " value" });
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
const OK = "138A5E", MID = "B07A00", BAD = "C0392B";
const verdictCell = (v) => TD(v === "ok" ? "same" : v === "close" ? "close" : "differs", { bold: true, color: v === "ok" ? OK : v === "close" ? MID : BAD });
const TB = { type: "solid", pt: 0.5, color: "D5DCE4" };

// ---------------------------------------------------------------- data
const L = S.layouts;
const HL = S.heatload;
const base = HL[0];
const V = S.vapour;
const CF = S.coolant_cfd;
const lay = (k, f) => L.find((r) => r.layout === k && Math.abs(r.flow - f) < 1e-6);
const cfd = (k, f) => CF.find((r) => r.layout === k && Math.abs(r.m_gs - f) < 1e-6);
const nm = (n) => n.replace(", PDF dims", " (sleeve drawing)");
const short = (k) => (k === "A_built" ? "A*" : k);
const hrow = (k) => HL.find((r) => r.case.startsWith(k));
const ORDER = ["A_built", "P", "A", "B", "C", "D", "E", "E_PDF", "F", "G", "H"];
const minMargin = Math.min(...L.map((r) => r.margin));
const vc = V.coupled, cr = V.coupling_result;
const Z1 = cr.zone_room[1] - vc.z1 / 1000, Z2 = cr.zone_room[0] - vc.z2 / 1000;
const best = lay("E_PDF", 17.5);
const SEC = ["Overview", "01 · Heat load", "02 · Coil layouts", "03 · Coolant flow in 3-D", "04 · Vapour column", "05 · Conclusions"];

// ================================================================= title + key results
pres.addSection({ title: SEC[0] });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: SEC[0] });
s.addText("SAHA cold stage: thermal design of the cold zones", { placeholder: "title" });
s.addText("How much heat reaches each copper zone, which coil layout holds the inner wall within ±0.15 K, how the methanol flows and warms in 3-D, and what the moving vapour column adds · 7 Oct 2026", { placeholder: "body" });

s = content("Every coil layout holds the inner wall within ±0.15 K", SEC[0], `Design basis: Zone 1 ≈ ${f2(Z1)} W, Zone 2 ≈ ${f2(Z2)} W; flattest wall with the paired axial sleeve (E_PDF)`);
stat(s, 0.5, 1.35, 3.0, `${f2(Z1)} W`, "heat into Zone 1 (−30 °C), including the moving vapour column", null, "z1");
stat(s, 3.65, 1.35, 3.0, `${f2(Z2)} W`, "heat into Zone 2 (−15 °C), including the moving vapour column", null, "z2");
stat(s, 6.8, 1.35, 3.0, `${f0(best.spread)} mK`, "smallest inner-wall spread: paired axial sleeve E_PDF at 17.5 g/s", null, "best");
stat(s, 9.95, 1.35, 2.85, `≥ ${f0(minMargin)} mK`, "margin left inside ±0.15 K, worst layout and flow", null, "margin");
card(s, 0.5, 3.3, 6.05, 3.55, "found card");
s.addText("What we found", { x: 0.7, y: 3.4, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  `Conduction alone brings ${f2(base.Q1)} W into Zone 1 and ${f2(base.Q2)} W into Zone 2 (50 mm foam, 35 °C lab); ${f0(base.plates * 100)} % enters through the copper end plates.`,
  `All 11 coil layouts hold ±0.15 K at both 17.5 and 5 g/s, at the right inlet temperature (about −30.1 to −30.3 °C for Zone 1).`,
  `The methanol warms ${f0(lay("P", 17.5).rise)} mK through the zone at 17.5 g/s and ${f0(lay("P", 5).rise)} mK at 5 g/s.`,
  `The vapour column turns over in one slow loop and adds about ${f0(-vc.z1)} mW to Zone 1.`,
], 0.7, 3.9, 5.7, 2.9, 13, "found list");
card(s, 6.8, 3.3, 6.0, 3.55, "means card");
s.addText("What it means for the design", { x: 7.0, y: 3.4, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  "The inlet temperature matters more than the layout: −31.5 °C is too cold for Zone 1 with every layout.",
  `Lowest spread: E_PDF (${f0(best.spread)} mK), B (${f0(lay("B", 17.5).spread)} mK) and E (${f0(lay("E", 17.5).spread)} mK). The as-built bifilar tube A* is the widest (${f0(lay("A_built", 17.5).spread)} mK), but still inside the band.`,
  "Insulation sets the load: better foam cuts the heat by 27–56 %.",
  `The vapour column shifts the coil wall by only a few mK and the inlet by 10–20 mK.`,
], 7.0, 3.9, 5.6, 2.9, 13, "means list");

s = content("How the cold stage was modelled, in four steps", SEC[0], "Each step feeds the next: chamber heat → copper zone + coil → methanol flow → vapour column");
const steps = [
  ["1", "Chamber heat", "Axisymmetric conduction of the whole 425 mm stack: vapour, Perspex, foam, copper at set point, lab at 35 °C, ice tray at 0 °C. Gives the heat into each zone and where it enters."],
  ["2", "Coil zone in 3-D", "Copper zone on an (r, θ, z) grid, 1.3–1.9 M cells, with every coil passage built in, and a coolant network that warms along the path. 11 layouts × 2 flows."],
  ["3", "Coolant flow in 3-D", "Laminar Navier–Stokes of the methanol in the passages of six layouts, coupled to the copper: streamlines, warming along the path, pressure."],
  ["4", "Vapour column", "Transient 3-D CFD of the R134a column, 0–120 s, coupled two ways to the room and insulation every 1 s. Radiation not included (small)."],
];
steps.forEach((st, i) => {
  const x = 0.5 + i * 3.1;
  s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: 1.3, w: 0.75, h: 0.75, fill: { color: HEX.accent1 }, line: { color: HEX.accent1 }, objectName: `step ${st[0]} badge` });
  s.addText(st[0], { x: x + 0.15, y: 1.3, w: 0.75, h: 0.75, fontFace: "Cambria", fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle", isTextBox: true, margin: 0 });
  card(s, x, 2.25, 2.9, 4.4, `step ${st[0]}`);
  s.addText(st[1], { x: x + 0.2, y: 2.4, w: 2.5, h: 0.5, fontFace: "Cambria", fontSize: 17, bold: true, color: C.text2, isTextBox: true, margin: 0 });
  s.addText(st[2], { x: x + 0.2, y: 2.95, w: 2.5, h: 3.5, fontSize: 13, color: C.text1, isTextBox: true, margin: 0, valign: "top" });
});

// ================================================================= 01 heat load
divider("01", "Heat from the lab", "How much heat reaches each copper zone, and where it enters", SEC[1]);
s = content(`${f2(base.Q1)} W into Zone 1 and ${f2(base.Q2)} W into Zone 2 by conduction`, SEC[1], `Insulation sets the heat load; ${f0(base.plates * 100)} % of Zone 1's heat comes in through the copper end plates`);
const HC = [["foam 50 mm", "base"], ["PU 50 mm", "foam k 0.025"], ["aerogel 50 mm", "foam k 0.015"], ["lab 30 °C", "lab 30"]];
s.addChart(pres.charts.BAR, [
  { name: "Zone 1 (−30 °C)", labels: HC.map((c) => c[0]), values: HC.map((c) => +hrow(c[1]).Q1.toFixed(2)) },
  { name: "Zone 2 (−15 °C)", labels: HC.map((c) => c[0]), values: HC.map((c) => +hrow(c[1]).Q2.toFixed(2)) },
], { x: 0.5, y: 1.3, w: 6.9, h: 5.4, barDir: "col", barGapWidthPct: 60, chartColors: [HEX.accent2, HEX.accent3], showValue: true, dataLabelFontSize: 11, dataLabelFormatCode: "0.00",
  showLegend: true, legendPos: "t", legendFontSize: 11, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, valAxisTitle: "heat reaching the copper, W", showValAxisTitle: true, valAxisTitleFontSize: 11,
  valGridLine: { color: "E5E9EF", size: 0.5 }, showTitle: true, title: "Heat reaching the copper, W (35 °C lab unless stated)", titleFontSize: 12, titleColor: HEX.dk2, objectName: "heat chart" });
addFit(s, fig("chamber_field.png"), 7.5, 1.2, 1.9, 5.6, { name: "chamber field" });
[["Where it enters", `About ${f0(base.plates * 100)} % through the copper end plates, the rest through the buffer and the ends.`],
 ["Insulation", "PU foam cuts the load by 27 %, aerogel by 56 %. A cooler lab (30 °C) cuts it by 8 %."],
 ["Numerically settled", `Grid 0.25 / 0.5 / 1.0 mm: ${f3(hrow("grid 0.25").Q1)} / ${f3(base.Q1)} / ${f3(hrow("grid 1.0").Q1)} W into Zone 1.`]].forEach((c, i) => {
  const y = 1.3 + i * 1.8;
  card(s, 9.6, y, 3.2, 1.65, `heat card ${i}`);
  s.addText(c[0], { x: 9.75, y: y + 0.1, w: 2.9, h: 0.35, fontSize: 13, bold: true, color: C.text2, isTextBox: true, margin: 0 });
  s.addText(c[1], { x: 9.75, y: y + 0.5, w: 2.9, h: 1.1, fontSize: 11.5, color: C.text1, isTextBox: true, margin: 0, valign: "top" });
});

// ================================================================= 02 coil layouts
divider("02", "Coil layouts in 3-D", "Same zone, same heat, same coolant: how flat does each of the 11 layouts keep the inner copper wall?", SEC[2]);
s = content("Inner copper wall of Zone 1 for each layout, 17.5 g/s", SEC[2], "Warm bands at the end plates, cold in the middle: the plates bring in most of the heat");
addFit(s, fig("wallmaps_17.5.png"), 0.4, 1.2, 8.6, 5.75, { name: "wall maps" });
bullets(s, [
  "Copper zone on an (r, θ, z) grid: 0.5 mm in the copper, 2° round, 0.5 mm in height; 1.3–1.9 M cells.",
  "Every coil passage is built into the grid; the methanol warms along its path.",
  "Heat applied as computed for the chamber: bore, end plates, rims and carrier.",
  "Inlet set so the wall is centred on −30 °C.",
  "Energy balance closes to better than 5 mW in every case.",
], 9.2, 1.35, 3.7, 5.4, 13, "model bullets");

s = content("Inner copper wall of Zone 1 for each layout, 5 g/s", SEC[2], "At 5 g/s the methanol warms 3.5× more along its path, so spreads grow; every layout still holds ±0.15 K");
addFit(s, fig("wallmaps_5.png"), 0.4, 1.2, 8.6, 5.75, { name: "wall maps 5" });
bullets(s, [
  "Same zone, same heat; the coolant flow is cut from 17.5 to 5 g/s.",
  `The methanol now warms about ${f0(lay("P", 5).rise)} mK from inlet to outlet (${f0(lay("P", 17.5).rise)} mK at 17.5 g/s).`,
  "Layouts whose inlet and outlet sit side by side (bifilar, paired lanes) cancel this warming best.",
  "Colour: inner-wall temperature minus −30 °C, mK.",
], 9.2, 1.35, 3.7, 5.4, 13, "model bullets 5");

s = content("Wall spread for every layout, at both flows", SEC[2], `Every layout stays well inside the 300 mK band; E_PDF, B and E are the flattest`);
s.addChart(pres.charts.BAR, [
  { name: "17.5 g/s", labels: ORDER.map(short), values: ORDER.map((k) => +lay(k, 17.5).spread.toFixed(1)) },
  { name: "5 g/s", labels: ORDER.map(short), values: ORDER.map((k) => +lay(k, 5).spread.toFixed(1)) },
], { x: 0.5, y: 1.3, w: 12.3, h: 5.5, barDir: "col", barGapWidthPct: 50, chartColors: [HEX.accent2, HEX.accent1], showValue: true, dataLabelFontSize: 10, dataLabelFormatCode: "0",
  showLegend: true, legendPos: "t", legendFontSize: 12, catAxisLabelFontSize: 13, valAxisLabelFontSize: 11, valAxisMinVal: 0, valAxisMaxVal: 150,
  valAxisTitle: "inner-wall spread (max − min), mK", showValAxisTitle: true, valAxisTitleFontSize: 12, valGridLine: { color: "E5E9EF", size: 0.5 }, objectName: "spread chart" });

const T1 = [["Layout", "Spread, mK\n17.5 / 5 g/s", "Inlet that centres the wall, °C\n17.5 / 5 g/s", "Allowed inlet window, °C\n17.5 g/s", "Δp 17.5 g/s, kPa\n(friction)", "Re\n17.5 g/s"]];
ORDER.forEach((k) => {
  const a = lay(k, 17.5), b = lay(k, 5);
  const re = a.Re[0] === a.Re[1] ? f0(a.Re[0]) : `${f0(a.Re[0])}–${f0(a.Re[1])}`;
  T1.push([TD(nm(a.name), { bold: true }), TD(`${f0(a.spread)} / ${f0(b.spread)}`), TD(`${f3(a.inlet)} / ${f3(b.inlet)}`),
    TD(`${f2(a.inlet - a.margin / 1000)} to ${f2(a.inlet + a.margin / 1000)}`), TD(f1(a.dp)), TD(re)]);
  T1[T1.length - 1].forEach((c) => { c.options.fontSize = 10; });
});
s = content("Layout by layout: spread, inlet temperature, pressure drop", SEC[2], "Set the Zone 1 inlet near −30.15 °C at 17.5 g/s and −30.3 °C at 5 g/s; −31.5 °C is outside every window");
s.addTable(T1.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 0.5, y: 1.3, w: 12.3, colW: [3.6, 1.6, 2.5, 2.0, 1.4, 1.2], rowH: 0.38, border: TB, objectName: "layout table" });
note(s, "Window = inlet range that keeps every point of the inner wall within −30 ± 0.15 °C. Δp is straight-pipe friction only (bends and fittings add to it). D's film is taken laminar at Re ≈ 3900; if it is turbulent its inlet moves to about −30.12 °C.", 0.5, 6.5, 12.3, 0.4, 9.5);

// ================================================================= 03 coolant CFD
divider("03", "The methanol itself, in 3-D", "Laminar Navier–Stokes in every passage, the coolant warming as it travels, and the copper around it", SEC[3]);
const e17 = cfd("E_PDF", 17.5);
s = content("Paired axial sleeve (E_PDF): temperature, streamlines and pressure", SEC[3], `E_PDF at 17.5 g/s: spread ${f0(e17.spread_mK)} mK, inlet ${f3(e17.inlet_C)} °C, methanol warms ${f0(e17.rise_mK)} mK, Δp ${f1(e17.dp_kPa)} kPa`);
addFit(s, fig("coolant/E_PDF_17.5_3d.png"), 0.4, 1.1, 12.5, 4.0, { name: "E_PDF 3d" });
addFit(s, fig("coolant/E_PDF_17.5_paths.png"), 0.4, 5.1, 9.6, 1.85, { name: "E_PDF paths" });
note(s, "Left: methanol temperature in the passages. Middle: streamlines from the inlet. Right: static pressure. Bottom: warming and pressure along the path, and the inner wall it produces.", 10.1, 5.2, 2.8, 1.7, 11);

s = content("E_PDF: methanol tracers travelling and warming (animated)", SEC[3], "The feed splits evenly between the paired lanes, so every lane warms the same way");
addFit(s, fig("coolant/E_PDF_17.5_flow.gif"), 0.4, 1.1, 7.5, 5.85, { name: "E_PDF gif" });
bullets(s, [
  "Tracers released at the inlet follow the computed streamlines; colour is the local methanol temperature.",
  "Coolant enters the gallery, splits into the axial lanes and leaves through the opposite gallery.",
  `Peak speed ${f2(e17.umax)} m/s at 17.5 g/s; ${e17.cells_fluid.toLocaleString("en-US")} methanol cells.`,
  "Plays in slide-show mode.",
], 8.2, 1.4, 4.6, 5, 14, "gif bullets");

const SIX = ["E_PDF", "B", "A", "P", "H", "A_built"];
function montage(title, take, suffix, line) {
  const sl = content(title, SEC[3], take);
  SIX.forEach((k, i) => {
    const c = cfd(k, 17.5), x = 0.4 + (i % 3) * 4.15, y = 1.15 + Math.floor(i / 3) * 2.9;
    addFit(sl, fig(`coolant/${k}_17.5_${suffix}.png`), x, y, 2.45, 2.8, { name: `${k} ${suffix}`, align: "left" });
    sl.addText(nm(lay(k, 17.5).name).replace(/^\S+ /, "").replace(/^as built: /, "as built: "), { x: x + 2.5, y: y + 0.25, w: 1.6, h: 0.75, fontFace: "Cambria", fontSize: 12, bold: true, color: C.text2, isTextBox: true, margin: 0, valign: "top" });
    sl.addText(short(k), { x: x + 2.5, y: y - 0.05, w: 1.6, h: 0.32, fontFace: "Cambria", fontSize: 15, bold: true, color: C.accent1, isTextBox: true, margin: 0 });
    sl.addText(line(c), { x: x + 2.5, y: y + 1.05, w: 1.6, h: 1.6, fontSize: 10.5, color: C.text1, isTextBox: true, margin: 0, valign: "top" });
  });
}
montage("Methanol temperature in the passages: six layouts at 17.5 g/s", "Cold methanol enters, warms by ~65 mK along the path; the layout decides where the warm end sits on the wall",
  "Tpanel", (c) => `wall spread ${f0(c.spread_mK)} mK\ninlet ${f3(c.inlet_C)} °C\nwarming ${f0(c.rise_mK)} mK`);
montage("Streamlines of the methanol from the inlet: six layouts at 17.5 g/s", "Helices carry one long path; sleeve lanes and the jacket split the flow, and the jacket's split is uneven",
  "stream", (c) => `peak speed ${f2(c.umax)} m/s\n${c.cells_fluid.toLocaleString("en-US")} methanol cells\ncolour = methanol T`);

const CR = [["Layout", "Spread, mK\n17.5 / 5 g/s", "Inlet that centres the wall, °C\n17.5 / 5 g/s", "Methanol warming, mK\n17.5 / 5 g/s", "Peak speed, m/s\n17.5 / 5 g/s"]];
["E_PDF", "B", "A", "P", "H"].forEach((k) => {
  const a = cfd(k, 17.5), b = cfd(k, 5);
  CR.push([TD(nm(lay(k, 17.5).name), { bold: true }), TD(`${f0(a.spread_mK)} / ${f0(b.spread_mK)}`), TD(`${f3(a.inlet_C)} / ${f3(b.inlet_C)}`), TD(`${f0(a.rise_mK)} / ${f0(b.rise_mK)}`), TD(`${f2(a.umax)} / ${f2(b.umax)}`)]);
});
s = content("Coolant flow in 3-D: five layouts at both flows", SEC[3], "The 3-D coolant flow confirms the ranking: E_PDF and B flattest; the jacket's rings feed unevenly");
s.addTable(CR.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 0.5, y: 1.35, w: 12.3, colW: [3.9, 2.0, 2.7, 1.9, 1.8], rowH: 0.6, border: TB, objectName: "cfd table" });
bullets(s, [
  "Grid 0.4 mm in r and z, 2° round; thin channels refined to 0.125 mm (E lanes) and 0.25 mm (H gap); 0.07–0.4 M methanol cells per layout.",
  "Steady laminar flow including the centrifugal and Coriolis effects of the curved channels; then one coupled heat solve of methanol, copper and foam.",
  `The jacket (H) spreads ${f0(cfd("H", 17.5).spread_mK)} mK in 3-D: its rings are fed from one side and do not share the flow evenly.`,
], 0.5, 5.15, 12.3, 1.8, 12.5, "cfd notes");

// ================================================================= 04 vapour
divider("04", "The vapour column, coupled to the room", "Transient 3-D CFD of the R134a vapour inside the bore, 0–120 s, exchanging heat with the room and insulation every second", SEC[4]);
s = content("Vapour column model: walls from the room and insulation model", SEC[4], "Copper walls at set point, ice tray at 0 °C, Perspex walls see the room through the insulation");
addFit(s, fig("v_bc_model.png"), 0.4, 1.2, 12.5, 5.0, { name: "bc model" });
note(s, "Boussinesq R134a vapour at 84.4 kPa, 1 mm grid (0.24 M cells), 0–120 s. 0–60 s: walls fixed to the still-vapour state; 60–120 s: walls updated every 1 s from the room model (two-way). Radiation not included.", 0.5, 6.3, 12.3, 0.6, 11);

s = content("Transient, t = 0 to 120 s, next to the time-mean field", SEC[4], `Plumes form within 3 s; the mean is one slow loop, and Zone 1 draws a steady ~${f0(-vc.z1)} mW from the vapour`);
s.addText("Animation, t = 0–120 s (plays in slide show)", { x: 0.5, y: 1.15, w: 5.4, h: 0.35, fontSize: 13, bold: true, color: C.text2, isTextBox: true, margin: 0, align: "center" });
addFit(s, fig("vapour_0_120s.gif"), 0.5, 1.5, 5.4, 5.4, { name: "animation 0-120 s" });
s.addText("Time mean, t = 85–120 s", { x: 6.05, y: 1.15, w: 5.4, h: 0.35, fontSize: 13, bold: true, color: C.text2, isTextBox: true, margin: 0, align: "center" });
addFit(s, fig("vapour_mean_midplane.png"), 6.05, 1.5, 5.4, 5.4, { name: "time mean" });
bullets(s, [
  "Left of each: mid-plane temperature; right: vertical velocity.",
  "0–60 s: walls held at the still-vapour state; 60–120 s: walls coupled to the room every 1 s.",
  "Mean: warm vapour rises on one side, cold vapour falls on the other.",
  `w ${f3(V.w_rms_stat)} m/s rms.`,
], 11.55, 1.5, 1.4, 5.3, 11, "gif bullets");

s = content("Streamlines: the time-mean flow and one instant", SEC[4], "One slow loop in the mean; at any instant the rising and falling streams twist round each other");
addFit(s, fig("vapour_streamlines.png"), 0.3, 1.1, 9.3, 5.85, { name: "vapour streamlines" });
bullets(s, [
  "Left: streamlines of the time-mean velocity (85–120 s): a slow loop from the ice tray up to Zone 1 and back.",
  "Middle: streamlines at t = 120 s: the cold stream falling from Zone 1 and the warm stream rising from the ice tray twist round each other in the middle connector.",
  "The top region is stably stratified: closed, slow cells under the cap.",
], 9.8, 1.4, 3.1, 5.4, 13, "streamline bullets");

s = content("Temperature in each region of the column", SEC[4], "The connectors sit between their neighbours; the top region stays near 0 °C under the warm cap");
addFit(s, fig("vapour_3d_four.png"), 0.3, 1.15, 9.0, 5.8, { name: "3d four" });
const RN = ["lower connector", "Zone 2 (wall −15)", "middle connector", "Zone 1 (wall −30)", "top region"];
const VT = [["Region", "Mean T, °C", "rms, K"]];
RN.forEach((n, i) => VT.push([TD(n, { fontSize: 10.5 }), TD(f1(V.T_mean[i + 1]), { fontSize: 10.5 }), TD(f1(V.T_rms[i + 1]), { fontSize: 10.5 })]));
s.addTable(VT.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 9.45, y: 1.4, w: 3.45, colW: [1.65, 0.95, 0.85], rowH: 0.48, border: TB, objectName: "region table" });
note(s, "Time means over 85–120 s. Radius drawn ×2.5; copper = Zones 2 (lower) and 1; blue glass = Perspex; dark slab = ice tray.", 9.45, 4.6, 3.45, 1.6, 11);

s = content("Where the vapour's heat comes from and where it goes", SEC[4], `Zone 1 total ${f2(Z1)} W and Zone 2 total ${f2(Z2)} W with the moving vapour: the design heat load`);
stat(s, 0.5, 1.35, 3.0, `${f0(vc.ice)} mW`, "from the ice tray into the vapour", null, "ice");
stat(s, 3.65, 1.35, 3.0, `${f0(vc.conn_lo)} / ${f0(vc.conn_mid)} mW`, "from the lower / middle Perspex connector into the vapour", null, "conn");
stat(s, 6.8, 1.35, 3.0, `${f0(-vc.z1)} mW`, `out of the vapour into the Zone 1 wall (±${f1(vc.z1_scatter)} mW)`, null, "z1w");
stat(s, 9.95, 1.35, 2.85, `${sgn(-vc.z2, 0)} mW`, "into the Zone 2 wall: Zone 2 gives a little heat to the vapour", null, "z2w");
addFit(s, fig("v_coupling.png"), 0.4, 3.25, 12.5, 3.65, { name: "coupling" });

s = content("What the vapour heat does to the coil wall", SEC[4], "The vapour adds 0–2.5 mK of spread and needs a 9–19 mK colder inlet: every coil still holds ±0.15 K");
const VM = [["Coil, flow", "Spread without vapour, mK", "Spread with vapour, mK", "Inlet without vapour, °C", "Inlet with vapour, °C", "Allowed window with vapour, °C"]];
S.vapourmap.forEach((r) => {
  const b0 = lay(r.layout, r.m_gs);
  VM.push([TD(`${short(r.layout)}, ${r.m_gs} g/s`, { bold: true }), TD(f1(b0.spread)), TD(f1(r.spread_mK)), TD(f3(b0.inlet)), TD(f3(r.inlet_C)), TD(`${f2(r.window[0])} to ${f2(r.window[1])}`)]);
});
s.addTable(VM.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 0.5, y: 1.4, w: 12.3, colW: [1.9, 2.0, 2.0, 2.0, 2.0, 2.4], rowH: 0.6, border: TB, objectName: "coil vapour table" });
note(s, "The time-mean convective heat from the vapour CFD (a map over the Zone 1 bore) is added to the chamber heat, and the 3-D coil model is solved again.", 0.5, 1.6 + 0.6 * VM.length, 12.3, 0.8, 12);

// ================================================================= 05 conclusions
divider("05", "Conclusions", "What to set, what to build, and what to study next", SEC[5]);
s = content("Conclusions and next steps", SEC[5], "Any of the 11 layouts works at the right inlet; E_PDF or B for the flattest wall, A* is acceptable as built");
card(s, 0.5, 1.35, 6.0, 5.4, "conclusions card");
s.addText("Conclusions", { x: 0.7, y: 1.45, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  `Design heat load: Zone 1 ≈ ${f2(Z1)} W, Zone 2 ≈ ${f2(Z2)} W (50 mm foam, 35 °C lab, moving vapour).`,
  `Every layout holds ±0.15 K with at least ${f0(minMargin)} mK to spare, at 17.5 and at 5 g/s.`,
  "Flattest walls: E_PDF, B and E (≈ 40–45 mK at 17.5 g/s). Widest: A* as built (≈ 100–115 mK).",
  "Zone 1 inlet ≈ −30.15 °C at 17.5 g/s and −30.3 °C at 5 g/s; −31.5 °C is too cold.",
  "The vapour column adds ~0.17 W to Zone 1 and moves the coil wall by only a few mK.",
], 0.7, 1.95, 5.6, 4.7, 13, "conclusions list");
card(s, 6.8, 1.35, 6.0, 5.4, "next card");
s.addText("Next steps", { x: 7.0, y: 1.45, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  "Settle the flow regime at 17.5 g/s (laminar or transitional film), mainly for the straight passages (D, F, H).",
  "Jacket H: improve the ring feed, or use a plenum-fed axial jacket.",
  "Vapour CFD on a finer grid with longer statistics, with radiation in the bore.",
  "Pump-stop and chiller-stop transients on the 3-D copper model.",
  "Full Fluent run of the chosen layout.",
], 7.0, 1.95, 5.6, 4.7, 13, "next list");

pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
});
