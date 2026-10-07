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

s = content("The cold stage: two copper zones on one open vapour bore", SEC[0], "Each copper zone must hold its inner wall within ±0.15 K of its set point; the coil removes the heat that leaks in from the lab");
addFit(s, fig("chamber_schematic.png"), 0.35, 1.05, 5.6, 5.9, { name: "chamber schematic" });
const NI = JSON.parse(fs.readFileSync(path.join(path.dirname(SUMMARY), "heatload_noinsulation.json"), "utf8"));
const ZC = [
  ["Zone 1 · copper, z 247–365 mm", HEX.accent1, [`Set point −30 °C ± 0.15 K (wall −30.15 to −29.85 °C)`, `Length 118 mm = 11 plate + 96 coil + 11 plate`, `Heat to remove ≈ ${f2(Z1)} W (${f2(base.Q1)} W conduction ${sgn(Z1 - base.Q1, 2)} W net from the moving vapour)`]],
  ["Zone 2 · copper, z 60–187 mm", HEX.accent1, [`Set point −15 °C ± 0.15 K (wall −15.15 to −14.85 °C)`, `Length 127 mm = 11 plate + 105 coil + 11 plate`, `Heat to remove ≈ ${f2(Z2)} W (${f2(base.Q2)} W conduction ${sgn(Z2 - base.Q2, 2)} W net from the moving vapour)`]],
  ["Heat leak: with and without insulation", HEX.dk2, [`No insulation (bare copper in 35 °C air, h = 8): Zone 1 ≈ ${f0(NI.bare.Q1)} W, Zone 2 ≈ ${f0(NI.bare.Q2)} W`, `Outer foam removed (filling between the plates kept): ${f1(NI.no_outer_foam.Q1)} W and ${f1(NI.no_outer_foam.Q2)} W`, `50 mm foam (k 0.035): ${f2(base.Q1)} W and ${f2(base.Q2)} W by conduction, about 8× less than bare`]],
];
ZC.forEach(([t, col, items], i) => {
  const y = 1.2 + i * 1.92;
  card(s, 6.2, y, 6.6, 1.78, `zone card ${i}`);
  s.addText(t, { x: 6.4, y: y + 0.08, w: 6.2, h: 0.4, fontFace: "Cambria", fontSize: 15, bold: true, color: col, isTextBox: true, margin: 0 });
  bullets(s, items, 6.4, y + 0.5, 6.25, 1.25, 11.5, `zone list ${i}`);
});

// ================================================================= 01 heat load
divider("01", "Heat from the lab", "How much heat reaches each copper zone, by which path, and what sets it", SEC[1]);
const HS = JSON.parse(fs.readFileSync(path.join(path.dirname(SUMMARY), "heatload_sweeps.json"), "utf8"));
const P1 = HS.profile.Z1, P2 = HS.profile.Z2;
const sumq = (a) => (a || []).reduce((t, x) => t + x[1], 0);
const z1p = sumq(P1["plates"]), z1b = sumq(P1["band outer"]), z1r = sumq(P1["bore (inner wall)"]);
const z2p = sumq(P2["plates"]), z2b = sumq(P2["band outer"]), z2r = sumq(P2["bore (inner wall)"]);
const rad = S.radiation.find((r) => Math.abs(r.eps_cu - 0.3) < 1e-6);
s = content("Where each zone's heat comes from: conduction, vapour, radiation", SEC[1], `Zone 1 ≈ ${f2(Z1)} W and Zone 2 ≈ ${f2(Z2)} W; conduction through the copper end plates is the largest part in both zones`);
s.addChart(pres.charts.BAR, [
  { name: "end plates (conduction)", labels: ["Zone 1 (−30 °C)", "Zone 2 (−15 °C)"], values: [+z1p.toFixed(3), +z2p.toFixed(3)] },
  { name: "outer face of the copper band (conduction)", labels: ["Zone 1 (−30 °C)", "Zone 2 (−15 °C)"], values: [+z1b.toFixed(3), +z2b.toFixed(3)] },
  { name: "moving vapour on the bore (convection)", labels: ["Zone 1 (−30 °C)", "Zone 2 (−15 °C)"], values: [+(-vc.z1 / 1000).toFixed(3), 0] },
], { x: 0.5, y: 1.2, w: 5.6, h: 5.7, barDir: "col", barGrouping: "stacked", barGapWidthPct: 55, chartColors: [HEX.accent1, "8A9BB0", HEX.accent2],
  showValue: true, dataLabelFontSize: 10, dataLabelFormatCode: "0.00;;", dataLabelColor: "FFFFFF", showLegend: true, legendPos: "b", legendFontSize: 10,
  catAxisLabelFontSize: 12, valAxisLabelFontSize: 10, valAxisTitle: "heat, W", showValAxisTitle: true, valAxisTitleFontSize: 11, valGridLine: { color: "E5E9EF", size: 0.5 }, objectName: "budget chart" });
const BT = [["Path, W", "Zone 1", "Zone 2"],
  ["Conduction through the two end plates", f2(z1p), f2(z2p)],
  ["Conduction through the outer face of the copper band", f2(z1b), f2(z2b)],
  ["Conduction through the bore (vapour still)", f2(z1r), f2(z2r)],
  ["Total by conduction (50 mm foam, 35 °C lab)", f2(base.Q1), f2(base.Q2)],
  ["Change of conduction when the vapour moves", sgn(cr.zone_room[1] - base.Q1, 2), sgn(cr.zone_room[0] - base.Q2, 2)],
  ["Vapour convection on the bore", sgn(-vc.z1 / 1000, 2), sgn(-vc.z2 / 1000, 2)],
  ["Total heat to remove", f2(Z1), f2(Z2)],
  ["Radiation in the bore (not included, ε 0.3)", `+${f2(rad.Z1_absorbed_mW / 1000)}`, `+${f2(rad.Z2_absorbed_mW / 1000)}`]];
s.addTable(BT.map((r, i) => i === 0 ? r.map(HDR) : r.map((c, j) => TD(c, { bold: i === 4 || i === 7, align: j ? "right" : "left", color: i === 7 ? HEX.accent1 : HEX.dk1 }))),
  { x: 6.4, y: 1.25, w: 6.4, colW: [4.2, 1.1, 1.1], rowH: 0.42, border: TB, objectName: "budget table" });
note(s, `Chamber balance: ${f2(HS.base.Qlab)} W enters from the lab through the foam; ${f2(base.Q1)} W reaches Zone 1, ${f2(base.Q2)} W Zone 2 and ${f2(HS.base.Qice)} W the 0 °C ice tray. Zone 2 is warmer than the vapour around it, so it gives a little heat to the vapour (−0.02 W).`, 6.4, 5.2, 6.4, 1.5, 11);

const STEPS = [["Hand calculation (side wall only)", 2.0609, 1.7062], ["Chamber conduction model (vapour still)", base.Q1, base.Q2],
  ["Same, finest grid (0.25 mm)", hrow("grid 0.25").Q1, hrow("grid 0.25").Q2], ["+ moving vapour (3-D CFD, coupled to the room)", Z1, Z2],
  ["+ bore radiation estimate (ε 0.3)", Z1 + rad.Z1_absorbed_mW / 1000, Z2 + rad.Z2_absorbed_mW / 1000]];
s = content("How the heat load builds up, model by model", SEC[1], `Use about ${f2(Z1)} W for Zone 1 and ${f2(Z2)} W for Zone 2 (50 mm foam, 35 °C lab); foam k ±0.005 moves both by about ±14 %`);
[[1, "Zone 1 (−30 °C)", HEX.accent2, 0.4], [2, "Zone 2 (−15 °C)", "1B9E8A", 6.7]].forEach(([j, ttl, col, x]) => {
  s.addChart(pres.charts.BAR, [{ name: ttl, labels: STEPS.map((r) => r[0]).reverse(), values: STEPS.map((r) => +r[j].toFixed(3)).reverse() }],
    { x, y: 1.15, w: 6.2, h: 3.7, barDir: "bar", barGapWidthPct: 45, chartColors: [col], showValue: true, dataLabelFontSize: 10, dataLabelFormatCode: "0.000 \"W\"",
      catAxisLabelFontSize: 10, valAxisLabelFontSize: 9, valAxisMinVal: 0, valAxisMaxVal: 3.2, showLegend: false, showTitle: true, title: ttl, titleFontSize: 12, titleColor: HEX.dk2,
      valGridLine: { color: "E5E9EF", size: 0.5 }, objectName: `${ttl} build-up` });
});
card(s, 0.5, 5.05, 6.05, 1.8, "cond card");
s.addText("Conduction: the insulation decides", { x: 0.7, y: 5.12, w: 5.7, h: 0.4, fontFace: "Cambria", fontSize: 14, bold: true, color: C.text2, isTextBox: true, margin: 0 });
s.addText(`The side-wall formula gives ${f2(2.0609)} W for Zone 1; the full chamber adds the end plates, ends and the Perspex/vapour paths: ${f2(base.Q1)} W. Grid-independent to 0.1 %.`, { x: 0.7, y: 5.55, w: 5.7, h: 1.2, fontSize: 11.5, color: C.text1, isTextBox: true, margin: 0, valign: "top" });
card(s, 6.8, 5.05, 6.0, 1.8, "vap card");
s.addText(`The moving vapour: Zone 1 needs about +${f0((Z1 / base.Q1 - 1) * 100)} %`, { x: 7.0, y: 5.12, w: 5.6, h: 0.4, fontFace: "Cambria", fontSize: 14, bold: true, color: C.text2, isTextBox: true, margin: 0 });
s.addText(`Convection adds ${f0(-vc.z1)} mW to Zone 1 and takes ${f0((base.Q2 - Z2) * 1000)} mW from Zone 2: the ice tray and the Perspex connectors now feed Zone 1 through the vapour. Radiation would add ${f0(rad.Z1_absorbed_mW)} mW more.`, { x: 7.0, y: 5.55, w: 5.6, h: 1.2, fontSize: 11.5, color: C.text1, isTextBox: true, margin: 0, valign: "top" });

s = content("Deriving the heat-loss equation, and what the heat depends on", SEC[1], "Heat ∝ ΔT and ≈ ∝ k; it falls with foam thickness, but more slowly than 1/t");
addFit(s, fig("hl_derivation.png"), 0.4, 1.1, 6.3, 5.85, { name: "derivation", align: "left" });
const PR = [["Heat loss is …", "to", "Check with the chamber model"],
  ["directly ∝", "ΔT (lab − copper)", "exactly linear: 38.8 mW/K (Z1), 35.6 mW/K (Z2)"],
  ["directly ∝ (almost)", "foam conductivity k", "Q/k changes only 7 % over k 0.010–0.050"],
  ["directly ∝", "area: zone height, radius", "side-wall heat is per mm of height"],
  ["increases, weakly", "outer film h", "h 4 → 25 W/m²K: +6 %"],
  ["inversely ∝", "foam thickness t (flat); ln(r_o/r_i) (cylinder)", "10 → 100 mm: Z1 4.71 → 2.02 W, only 2.3× less"],
  ["inversely ∝", "total resistance R", "all of the above act through R"]];
s.addTable(PR.map((r, i) => i === 0 ? r.map(HDR) : [TD(r[0], { bold: true, color: r[0].startsWith("inv") ? "B4471A" : "138A5E" }), TD(r[1]), TD(r[2], { fontSize: 10 })]),
  { x: 6.9, y: 1.3, w: 5.95, colW: [1.45, 1.95, 2.55], rowH: 0.7, border: TB, objectName: "proportionality table" });

s = content("Heat against insulation thickness, both zones", SEC[1], `Doubling the foam from 50 to 100 mm cuts Zone 1 only from 2.58 to 2.02 W: a better foam beats more thickness`);
addFit(s, fig("hl_thickness.png"), 0.4, 1.2, 12.5, 5.6, { name: "thickness" });
s = content("Heat against foam thermal conductivity, both zones", SEC[1], "At 50 mm: PU (k 0.025) cuts the heat by 27 %, aerogel (k 0.015) by 56 %");
addFit(s, fig("hl_kfoam.png"), 0.4, 1.2, 12.5, 5.6, { name: "kfoam" });
s = content("Where the heat enters along the height of each zone", SEC[1], `The two 11 mm end plates take ${f0(z1p / base.Q1 * 100)} % of Zone 1's heat and ${f0(z2p / base.Q2 * 100)} % of Zone 2's: the coil must work hardest at the ends`);
addFit(s, fig("hl_height.png"), 0.4, 1.2, 12.5, 5.6, { name: "height" });

s = content("How the coolant inlet temperature is calculated", SEC[1], "The inlet must sit below −30 °C by half the coolant warming plus the wall-to-coolant offset: about −30.15 °C at 17.5 g/s, −30.3 °C at 5 g/s");
addFit(s, fig("inlet_derivation.png"), 0.4, 1.1, 6.3, 5.85, { name: "inlet derivation", align: "left" });
const IT = [["Coil, flow", "Coolant warming, mK", "Q/UA, mK", "Hand estimate, °C", "3-D inlet, °C", "Window, °C"]];
[["A_built", 17.5], ["A_built", 5], ["P", 17.5], ["P", 5], ["B", 17.5], ["B", 5], ["E_PDF", 17.5], ["E_PDF", 5]].forEach(([k, fl]) => {
  const r = lay(k, fl);
  const est = -30 - r.rise / 2000 - base.Q1 / r.UA;
  IT.push([TD(`${short(k)}, ${fl} g/s`, { bold: true, fontSize: 10 }), TD(f0(r.rise), { fontSize: 10, align: "center" }), TD(f0(base.Q1 / r.UA * 1000), { fontSize: 10, align: "center" }),
    TD(f2(est), { fontSize: 10, align: "center" }), TD(f3(r.inlet), { fontSize: 10, align: "center", bold: true, color: HEX.accent1 }),
    TD(`${f2(r.inlet - r.margin / 1000)} to ${f2(r.inlet + r.margin / 1000)}`, { fontSize: 10, align: "center" })]);
});
s.addTable(IT.map((r, i) => i === 0 ? r.map((c) => Object.assign(HDR(c), { options: Object.assign(HDR(c).options, { fontSize: 10 }) })) : r),
  { x: 6.85, y: 1.3, w: 6.0, colW: [1.15, 0.85, 0.7, 1.0, 0.95, 1.35], rowH: 0.42, border: TB, objectName: "inlet table" });
card(s, 6.85, 5.6, 6.0, 1.3, "inlet card");
s.addText([{ text: "Why −31.5 °C does not work: ", options: { bold: true, color: HEX.dk2 } },
  { text: "it is 1.2–1.35 K below the centring inlet, far outside every ±0.1 K window, so the whole wall would sit about 1.3 K too cold." }],
  { x: 7.05, y: 5.65, w: 5.6, h: 1.2, fontSize: 12, color: C.text1, isTextBox: true, margin: 0, valign: "middle" });

// ================================================================= 02 coil layouts
divider("02", "The 11 coil types", "Same Zone 1, same heat, same coolant: each coil type, its passages, and how flat it keeps the inner copper wall", SEC[2]);
const DESC = {
  A_built: "Bifilar Ø5/4 mm copper tube wound on the 5 mm buffer (r 15–20 mm), as built: supply and return strands interleaved.",
  P: "One Ø4 mm passage: a plain helix (6.9 mm pitch) on r 22 mm, in at the bottom, out at the top.",
  A: "Folded bifilar helix: one strand up, hairpin at the top, the return strand down between its turns.",
  B: "Two helical layers in series: the inner layer (r 21 mm) goes up, the outer layer (r 27 mm) comes back down.",
  C: "Two helices fed from opposite ends: half the flow enters at the bottom, half at the top.",
  D: "Axial serpentine: 16 straight Ø4 mm legs up and down round the zone, joined by short turns.",
  E: "Paired axial sleeve: thin 6 × 0.5 mm axial lanes along the wall, fed and collected by galleries.",
  E_PDF: "Paired axial sleeve with the sleeve-drawing dimensions: lanes at r 23.75–24.25 mm, galleries in the header.",
  F: "Eight horizontal ring channels in parallel, fed from a vertical supply spine and collected by a return spine.",
  G: "Two short folded coils, one in the lower and one in the upper half, each with half the flow.",
  H: "Full annular jacket: a 1 mm gap (r 20–21 mm) round the zone, inlet ring at the bottom, outlet ring at the top.",
};
const TITLE11 = { A_built: "as built", P: "plain helix", A: "folded helix", B: "two radial layers", C: "opposite-end feeds", D: "axial serpentine",
  E: "paired axial sleeve", E_PDF: "sleeve (drawing)", F: "stacked rings", G: "two short coils", H: "annular jacket" };
const SHORTD = { A_built: "bifilar tube wound on the buffer (as built)", P: "one helix: in at the bottom, out at the top", A: "helix up, hairpin, back down between the turns",
  B: "inner helix up, outer helix back down", C: "two helices fed from opposite ends", D: "16 straight legs up and down",
  E: "thin axial lanes fed by galleries", E_PDF: "axial lanes, sleeve-drawing dimensions", F: "8 rings in parallel between two spines",
  G: "two short folded coils, fed at mid-height", H: "1 mm annular gap, rings at top and bottom" };
s = content("Eleven coil types for Zone 1", SEC[2], "Colour = methanol temperature: blue cold at the inlet → red warm at the outlet. Copper wall and end plates solid; carrier see-through");
ORDER.forEach((k, i) => {
  const col = i % 6, row = Math.floor(i / 6);
  const x = 0.4 + col * 2.1, y = 1.1 + row * 2.95;
  addFit(s, fig(`coils/${k}.png`), x, y + 0.62, 2.0, 2.3, { name: `${k} render` });
  s.addText([{ text: short(k) + "  ", options: { bold: true, color: HEX.accent1, fontFace: "Cambria", fontSize: 15 } },
    { text: TITLE11[k], options: { fontSize: 10.5, color: HEX.dk2, bold: true } }],
    { x, y, w: 2.05, h: 0.32, isTextBox: true, margin: 0, valign: "top" });
  s.addText(SHORTD[k], { x, y: y + 0.3, w: 2.05, h: 0.34, fontSize: 9, color: HEX.accent6, isTextBox: true, margin: 0, valign: "top" });
});
// colour key in the free cell
s.addText([{ text: "How to read", options: { bold: true, fontFace: "Cambria", fontSize: 14, color: HEX.dk2, breakLine: true } },
  { text: "IN / OUT arrows: where the methanol enters and leaves.", options: { fontSize: 10.5, breakLine: true } },
  { text: "Tube colour: methanol temperature along the path, cold (blue) to warm (red).", options: { fontSize: 10.5, breakLine: true } },
  { text: "Bronze: the inner copper wall and the two end plates; the faint shell is the copper carrier the passages sit in.", options: { fontSize: 10.5 } }],
  { x: 10.95, y: 4.3, w: 2.0, h: 2.6, isTextBox: true, margin: 0, valign: "top", color: C.text1 });

s = content("Zone 1 inner-wall spread for every coil type, at both flows", SEC[2], `All 11 coil types keep Zone 1 well inside the 300 mK band; B, E_PDF and E are the flattest (42–45 mK)`);
s.addChart(pres.charts.BAR, [
  { name: "17.5 g/s", labels: ORDER.map(short), values: ORDER.map((k) => +lay(k, 17.5).spread.toFixed(1)) },
  { name: "5 g/s", labels: ORDER.map(short), values: ORDER.map((k) => +lay(k, 5).spread.toFixed(1)) },
], { x: 0.5, y: 1.3, w: 12.3, h: 5.5, barDir: "col", barGapWidthPct: 50, chartColors: [HEX.accent2, HEX.accent1], showValue: true, dataLabelFontSize: 10, dataLabelFormatCode: "0",
  showLegend: true, legendPos: "t", legendFontSize: 12, catAxisLabelFontSize: 13, valAxisLabelFontSize: 11, valAxisMinVal: 0, valAxisMaxVal: 150,
  valAxisTitle: "Zone 1 (−30 °C) inner-wall spread, max − min, mK", showValAxisTitle: true, valAxisTitleFontSize: 12, valGridLine: { color: "E5E9EF", size: 0.5 },
  showTitle: true, title: "Zone 1 copper wall, set point −30 °C, heat 2.58 W", titleFontSize: 12, titleColor: HEX.dk2, objectName: "spread chart" });

const T1 = [["Layout", "Spread, mK\n17.5 / 5 g/s", "Inlet that centres the wall, °C\n17.5 / 5 g/s", "Allowed inlet window, °C\n17.5 g/s", "Δp 17.5 g/s, kPa\n(friction)", "Re\n17.5 g/s"]];
ORDER.forEach((k) => {
  const a = lay(k, 17.5), b = lay(k, 5);
  const re = a.Re[0] === a.Re[1] ? f0(a.Re[0]) : `${f0(a.Re[0])}–${f0(a.Re[1])}`;
  T1.push([TD(nm(a.name), { bold: true }), TD(`${f0(a.spread)} / ${f0(b.spread)}`), TD(`${f3(a.inlet)} / ${f3(b.inlet)}`),
    TD(`${f2(a.inlet - a.margin / 1000)} to ${f2(a.inlet + a.margin / 1000)}`), TD(f1(a.dp)), TD(re)]);
  T1[T1.length - 1].forEach((c) => { c.options.fontSize = 10; });
});
s = content("Zone 1, coil by coil: spread, inlet temperature, pressure drop", SEC[2], "Set the Zone 1 inlet near −30.15 °C at 17.5 g/s and −30.3 °C at 5 g/s (D and F colder, see table); −31.5 °C is outside every window");
s.addTable(T1.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 0.5, y: 1.3, w: 12.3, colW: [3.6, 1.6, 2.5, 2.0, 1.4, 1.2], rowH: 0.38, border: TB, objectName: "layout table" });
note(s, "Window = inlet range that keeps every point of the inner wall within −30 ± 0.15 °C. Δp is straight-pipe friction only (bends and fittings add to it). D's film is taken laminar at Re ≈ 3900; if it is turbulent its inlet moves to about −30.12 °C.", 0.5, 6.5, 12.3, 0.4, 9.5);

// ================================================================= 03 coolant CFD
divider("03", "The methanol itself, in 3-D", "Laminar Navier–Stokes in every passage, the coolant warming as it travels, and the copper around it", SEC[3]);
const e17 = cfd("E_PDF", 17.5);
s = content("Paired axial sleeve (E_PDF): temperature, streamlines and pressure", SEC[3], `E_PDF at 17.5 g/s in the 3-D flow: spread ${f0(e17.spread_mK)} mK, inlet ${f3(e17.inlet_C)} °C, methanol warms ${f0(e17.rise_mK)} mK, Δp ${f1(e17.dp_kPa)} kPa including the galleries`);
addFit(s, fig("coolant/E_PDF_17.5_3d.png"), 0.4, 1.15, 12.5, 5.7, { name: "E_PDF 3d" });

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
  "The 3-D flow resolves the gallery and lane split, so its spreads and Δp differ from the coil table (slide 14), which uses the coolant network: E_PDF 37 vs 43 mK, 14.3 vs 10.7 kPa (friction only).",
  "Grid 0.4 mm in r and z, 2° round; thin channels refined to 0.125 mm (E lanes) and 0.25 mm (H gap); 0.07–0.4 M methanol cells per layout.",
  "Steady laminar flow including the centrifugal and Coriolis effects of the curved channels; then one coupled heat solve of methanol, copper and foam.",
  `The jacket (H) spreads ${f0(cfd("H", 17.5).spread_mK)} mK in 3-D: its rings are fed from one side and do not share the flow evenly.`,
], 0.5, 5.15, 12.3, 1.8, 12.5, "cfd notes");

// ================================================================= 04 vapour
divider("04", "The vapour column, coupled to the room", "Transient 3-D CFD of the R134a vapour inside the bore, 0–120 s, exchanging heat with the room and insulation every second", SEC[4]);
s = content("Vapour column model: walls from the room and insulation model", SEC[4], "Copper walls at set point, ice tray at 0 °C, Perspex walls see the room through the insulation");
addFit(s, fig("v_bc_model_noG.png"), 0.4, 1.2, 12.5, 5.0, { name: "bc model" });
note(s, "Boussinesq R134a vapour at 84.4 kPa, 1 mm grid (0.24 M cells), 0–120 s. 0–60 s: walls fixed to the still-vapour state; 60–120 s: walls updated every 1 s from the room model (two-way). Radiation not included.", 0.5, 6.3, 12.3, 0.6, 11);

s = content("Transient, t = 0 to 120 s, next to the time-mean field", SEC[4], `Plumes form within 3 s; the mean is one slow loop, and Zone 1 draws a steady ~${f0(-vc.z1)} mW from the vapour`);
s.addText("Animation, t = 0–120 s (plays in slide show)", { x: 0.5, y: 1.15, w: 5.4, h: 0.35, fontSize: 13, bold: true, color: C.text2, isTextBox: true, margin: 0, align: "center" });
addFit(s, fig("vapour_0_120s.gif"), 0.5, 1.5, 5.4, 5.4, { name: "animation 0-120 s" });
s.addText("Time mean, t = 85–120 s", { x: 6.05, y: 1.15, w: 5.4, h: 0.35, fontSize: 13, bold: true, color: C.text2, isTextBox: true, margin: 0, align: "center" });
addFit(s, fig("vapour_mean_midplane.png"), 6.05, 1.5, 5.4, 5.4, { name: "time mean" });
bullets(s, [
  "Left of each: mid-plane temperature; right: vertical velocity.",
  "0–60 s: walls held at the still-vapour state; 60–120 s: walls coupled to the room every 1 s.",
  "Mean: in Zone 1 the vapour falls along the cold copper and rises in the core; in the connectors it rises along the warm Perspex.",
  `w ${f3(V.w_rms_stat)} m/s rms.`,
], 11.55, 1.5, 1.4, 5.3, 11, "gif bullets");

s = content("Streamlines: the time-mean flow and one instant", SEC[4], "One slow loop in the mean; at any instant the rising and falling streams twist round each other");
addFit(s, fig("vapour_streamlines.png"), 0.3, 1.1, 9.3, 5.85, { name: "vapour streamlines" });
bullets(s, [
  "Left: streamlines of the time-mean velocity (85–120 s): a slow loop from the ice tray up to Zone 1 and back.",
  "Middle: streamlines at t = 120 s: the cold stream falling from Zone 1 and the warm stream rising from the ice tray twist round each other in the middle connector.",
  "The top region is stably stratified: closed, slow cells under the cap.",
], 9.8, 1.4, 3.1, 5.4, 13, "streamline bullets");

s = content("Cross-sections: the streams are not axisymmetric", SEC[4], "At any instant the column carries one rising and one falling stream; on average Zone 1's vapour falls along the cold wall");
addFit(s, fig("vapour_sections.png"), 0.4, 1.1, 12.5, 5.85, { name: "sections" });

s = content("In 3-D: one rising and one falling stream, wandering in time", SEC[4], "The bore is open from ice tray to cap, so the unstable part acts as one tall convection loop");
addFit(s, fig("vapour_3d_four.png"), 0.3, 1.1, 6.6, 5.85, { name: "3d four" });
const RN = ["lower connector", "Zone 2 (wall −15)", "middle connector", "Zone 1 (wall −30)", "top region"];
const VT = [["Region", "Mean T (°C)", "Fluctuation (K rms)"]];
RN.forEach((n, i) => VT.push([TD(n, { fontSize: 11 }), TD(f1(V.T_mean[i + 1]), { fontSize: 11, align: "center" }), TD(f1(V.T_rms[i + 1]), { fontSize: 11, align: "center" })]));
s.addText("Vapour temperature by region (time mean, 85–120 s)", { x: 7.1, y: 1.15, w: 5.8, h: 0.4, fontSize: 13, bold: true, color: C.text2, isTextBox: true, margin: 0 });
s.addTable(VT.map((r, i) => i === 0 ? r.map(HDR) : r), { x: 7.1, y: 1.6, w: 5.75, colW: [2.45, 1.5, 1.8], rowH: 0.42, border: TB, objectName: "region table" });
card(s, 7.1, 4.35, 5.75, 2.55, "take card");
s.addText("What to take from it", { x: 7.3, y: 4.45, w: 5.4, h: 0.4, fontFace: "Cambria", fontSize: 15, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  "The bore is open from the ice tray to the cap: the unstable part (0 °C at the bottom, −30 °C 250 mm higher) acts as one tall convection loop.",
  "In a 27 mm bore the vapour crosses a zone in a few seconds, faster than it can reach the wall temperature, so warm vapour reaches Zone 1.",
  "The vapour temperature is not uniform inside the zones (1–2 K rms).",
], 7.3, 4.85, 5.4, 2.0, 11.5, "take list");

s = content("Where the vapour's heat comes from and where it goes", SEC[4], "Zone 1 collects nearly all of the convected heat; the ice tray and the Perspex next to it are the sources");
addFit(s, fig("v_heatflow_0_120.png"), 0.4, 1.1, 12.5, 4.75, { name: "heat flows" });
card(s, 0.5, 5.95, 12.3, 0.95, "means card");
s.addText(`Time means 85–120 s: ice tray ${f0(vc.ice)} + lower connector ${f0(vc.conn_lo)} + middle connector ${f0(vc.conn_mid)} = ${f0(vc.ice + vc.conn_lo + vc.conn_mid)} mW in;  Zone 1 wall ${f0(-vc.z1)} mW out (±${f1(vc.z1_scatter)});  Zone 2 wall ${sgn(vc.z2, 0)} mW (it heats the vapour on balance);  top wall and cap ${f0(vc.top_wall + vc.cap)} mW.`,
  { x: 0.7, y: 6.0, w: 11.9, h: 0.85, fontSize: 12.5, color: C.text1, isTextBox: true, margin: 0, valign: "middle" });

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
s = content("Summary: every coil layout holds the inner wall within ±0.15 K", SEC[5], `Design basis: Zone 1 ≈ ${f2(Z1)} W, Zone 2 ≈ ${f2(Z2)} W; flattest wall with B and E_PDF (42–43 mK)`);
stat(s, 0.5, 1.35, 3.0, `${f2(Z1)} W`, "heat into Zone 1 (−30 °C), including the moving vapour column", null, "z1");
stat(s, 3.65, 1.35, 3.0, `${f2(Z2)} W`, "heat into Zone 2 (−15 °C), including the moving vapour column", null, "z2");
stat(s, 6.8, 1.35, 3.0, `${f0(lay("B", 17.5).spread)}–${f0(best.spread)} mK`, "smallest inner-wall spread: B and E_PDF at 17.5 g/s", null, "best");
stat(s, 9.95, 1.35, 2.85, `≥ ${f0(minMargin)} mK`, "margin left inside ±0.15 K, worst layout and flow", null, "margin");
card(s, 0.5, 3.3, 6.05, 3.55, "found card");
s.addText("What we found", { x: 0.7, y: 3.4, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  `Conduction alone brings ${f2(base.Q1)} W into Zone 1 and ${f2(base.Q2)} W into Zone 2 (50 mm foam, 35 °C lab); ${f0(base.plates * 100)} % enters through the copper end plates.`,
  `All 11 coil layouts hold ±0.15 K at both 17.5 and 5 g/s, at the right Zone 1 inlet: −30.09 to −30.15 °C at 17.5 g/s for most layouts (D −30.68 °C, F −30.30 °C).`,
  `The methanol warms ${f0(lay("P", 17.5).rise)} mK through the zone at 17.5 g/s and ${f0(lay("P", 5).rise)} mK at 5 g/s.`,
  `The vapour column turns over in one slow loop and adds about ${f0(-vc.z1)} mW to Zone 1.`,
], 0.7, 3.9, 5.7, 2.9, 13, "found list");
card(s, 6.8, 3.3, 6.0, 3.55, "means card");
s.addText("What it means for the design", { x: 7.0, y: 3.4, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  "The inlet temperature matters more than the layout: −31.5 °C is too cold for Zone 1 with every layout.",
  `Lowest spread: B (${f0(lay("B", 17.5).spread)} mK), E_PDF (${f0(best.spread)} mK) and E (${f0(lay("E", 17.5).spread)} mK). The as-built bifilar tube A* is the widest (${f0(lay("A_built", 17.5).spread)} mK), but still inside the band.`,
  "Insulation sets the load: better foam cuts the heat by 27–56 %.",
  `The vapour column changes the coil wall spread by 0–2.5 mK and needs a 9–19 mK colder inlet.`,
], 7.0, 3.9, 5.6, 2.9, 13, "means list");

s = content("Conclusions and next steps", SEC[5], "Any of the 11 layouts works at the right inlet; B or E_PDF for the flattest wall, A* is acceptable as built");
card(s, 0.5, 1.35, 6.0, 5.4, "conclusions card");
s.addText("Conclusions", { x: 0.7, y: 1.45, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  `Design heat load: Zone 1 ≈ ${f2(Z1)} W, Zone 2 ≈ ${f2(Z2)} W (50 mm foam, 35 °C lab, moving vapour).`,
  `Every layout holds ±0.15 K with at least ${f0(minMargin)} mK to spare, at 17.5 and at 5 g/s.`,
  "Flattest walls: B, E_PDF and E (42–45 mK at 17.5 g/s). Widest: A* as built (≈ 100–115 mK).",
  "Zone 1 inlet ≈ −30.15 °C at 17.5 g/s and −30.3 °C at 5 g/s (D −30.68 °C, F −30.30 °C); −31.5 °C is too cold.",
  "The vapour column adds ~0.17 W to Zone 1 and changes the coil wall spread by 0–2.5 mK.",
], 0.7, 1.95, 5.6, 4.7, 13, "conclusions list");
card(s, 6.8, 1.35, 6.0, 5.4, "next card");
s.addText("Next steps", { x: 7.0, y: 1.45, w: 5.6, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: C.text2, isTextBox: true, margin: 0 });
bullets(s, [
  "Settle the flow regime at 17.5 g/s (laminar or transitional film), mainly for the straight passages (D, F, H).",
  "Jacket H: improve the ring feed, or use a plenum-fed axial jacket.",
  "Vapour CFD on a finer grid with longer statistics, with radiation in the bore.",
  "Pump-stop and chiller-stop transients on the 3-D copper model.",
], 7.0, 1.95, 5.6, 4.7, 13, "next list");

pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
});
