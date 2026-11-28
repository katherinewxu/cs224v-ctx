// Builds poster.pptx (48 x 36 in, landscape) from the figures in figs/png and the numbers below.
//   cd notes/poster && for f in figs/*.svg; do rsvg-convert -z 4 -o figs/png/$(basename $f .svg).png $f; done
//   NODE_PATH=<dir with pptxgenjs> node build_poster.js
// Update the DATA block when new runs land; everything else is layout.
const pptxgen = require("pptxgenjs");
const path = require("path");

// ---------------------------------------------------------------- data
const DATA = {
  v3: [ // final grading rules, 100x32
    ["Prototype", "194", "0.048", "2", "23.8M"],
    ["Plain Codex", "205", "0.055", "18", "12.0M"],
  ],
  v3Note: "Offline rules (no LLM): group hits by shared neighbours / group hits at random / random genes. Seed 0. Seed 1 and the strategy-hint runs: results Nov 29 [update before printing].",
  hint: null, // e.g. [["Prototype + hint", "…", "…", "…", "…"], ["Plain Codex + hint", …]]
  hits: [
    ["Prototype", "198* / 215 / 218 / 194", "206", "28 / 3 / 3 / 2", "23.0M", "3.5 h"],
    ["Plain Codex", "188 / 185 / 189 / 205", "192", "161 / 4 / 195 / 18", "11.6M", "1.6 h"],
  ],
};

// ---------------------------------------------------------------- style
const W = 48, H = 36, M = 1.0, GAP = 0.9;
const COLW = (W - 2 * M - 2 * GAP) / 3;
const COLX = [M, M + COLW + GAP, M + 2 * (COLW + GAP)];
const TOP = 4.6, BOTTOM = H - 1.4;
const INK = "1F2328", MUTED = "5B6168", BLUE = "2A78D6", ORANGE = "EB6834", TINT = "EEF3FA", RULE = "D5D9DE";
const HEAD = "Cambria", BODY = "Calibri";
const BODY_PT = 28, SMALL_PT = 22, H_PT = 46;

const pres = new pptxgen();
pres.defineLayout({ name: "POSTER", width: W, height: H });
pres.layout = "POSTER";
pres.title = "Does Structured Context Management Help Long-Horizon Agents?";
pres.author = "Katherine Xu, Karen Vo";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
const s = pres.addSlide();
s.background = { color: "FFFFFF" };

// rough text height: Calibri averages ~0.5 em per character
function textH(paras, pt, w) {
  const lineH = (pt * 1.2) / 72, cw = (pt * 0.43) / 72;
  let lines = 0;
  for (const p of paras) lines += Math.max(1, Math.ceil((p.length * cw) / (w - 0.3)));
  return lines * lineH + paras.length * (pt * 0.35) / 72 + 0.15;
}

const cursor = [TOP, TOP, TOP];
function header(c, num, title) {
  const y = cursor[c];
  s.addText([
    { text: num ? num + "  " : "", options: { color: BLUE } },
    { text: title, options: { color: INK } },
  ], { x: COLX[c], y, w: COLW, h: 0.95, fontFace: HEAD, fontSize: H_PT, bold: true, margin: 0, valign: "bottom", isTextBox: true });
  cursor[c] = y + 1.2;
}
// items: strings or arrays of runs ({text, b})
function bullets(c, items, opts = {}) {
  const pt = opts.pt || BODY_PT;
  const plain = items.map(it => (Array.isArray(it) ? it.map(r => r.text).join("") : it));
  const h = textH(plain, pt, COLW - 0.5);
  const runs = [];
  items.forEach((it, i) => {
    const parts = Array.isArray(it) ? it : [{ text: it }];
    parts.forEach((r, j) => runs.push({
      text: r.text,
      options: Object.assign({ bold: !!r.b, color: r.color || INK },
                j === parts.length - 1 && i < items.length - 1 ? { breakLine: true } : {},
        { paraSpaceAfter: 8 }),
    }));
  });
  s.addText(runs, { x: COLX[c], y: cursor[c], w: COLW, h, fontFace: BODY, fontSize: pt, valign: "top", margin: [2, 0, 0, 0], isTextBox: true });
  cursor[c] += h + (opts.after ?? 0.35);
}
function para(c, text, opts = {}) { bullets(c, [text], Object.assign({ bullet: false }, opts)); }
function figure(c, file, pxW, pxH, alt) {
  const h = COLW * pxH / pxW;
  s.addImage({ path: path.join(__dirname, "figs/png", file), x: COLX[c], y: cursor[c], w: COLW, h, altText: alt });
  cursor[c] += h + 0.35;
}
function table(c, head, rows, colW, note) {
  const opt = { fontFace: BODY, fontSize: SMALL_PT + 2, color: INK, valign: "middle", margin: [4, 6, 4, 6] };
  const hdr = head.map(t => ({ text: t, options: { bold: true, fill: { color: TINT } } }));
  const body = rows.map(r => r.map((t, i) => ({ text: t, options: { bold: i === 0 } })));
  const rowH = 0.62;
  const k = COLW / colW.reduce((a, b) => a + b, 0); colW = colW.map(v => v * k);
  s.addTable([hdr, ...body], Object.assign({ x: COLX[c], y: cursor[c], w: COLW, colW, rowH,
    border: { type: "solid", color: RULE, pt: 1 } }, opt));
  cursor[c] += rowH * (rows.length + 1) + 0.35;
  if (note) para(c, note, { pt: SMALL_PT, after: 0.5 });
}

// ---------------------------------------------------------------- title
s.addText("Does Structured Context Management Help Long-Horizon Agents?", {
  x: M, y: 0.8, w: W - 2 * M, h: 1.5, fontFace: HEAD, fontSize: 88, bold: true, color: INK, margin: 0, isTextBox: true });
s.addText([
  { text: "A 100-round gene-screen test of a structured-memory harness vs plain Codex", options: { color: MUTED, breakLine: true } },
  { text: "Katherine Xu, Karen Vo  ·  Mentor: Yucheng Jiang  ·  CS 224V, Stanford, Fall 2026", options: { color: INK, bold: true } },
], { x: M, y: 2.35, w: W - 2 * M, h: 1.6, fontFace: BODY, fontSize: 38, margin: 0, valign: "top", isTextBox: true });

// ---------------------------------------------------------------- left: question, testbed, finding 1
header(0, "1", "The question");
para(0, "Long-horizon agents outgrow their context window and must compact it. Does a harness that manages context with structured external memory (the prototype) beat plain Codex, which compacts and keeps whatever notes it chooses?");
bullets(0, [[{ text: "Same model, tools and task; ", b: true }, { text: "only the harness differs, in a testbed where forgetting has a measurable cost." }]], { after: 0.6 });

header(0, "2", "Testbed: a closed-loop CRISPR screen");
// round loop diagram
{
  const steps = ["Look up DepMap neighbours of up to 4 genes", "Propose 32 untested genes", "See their scores once", "Context compacts (16K window)"];
  const n = steps.length, aw = 0.45, bw = (COLW - (n - 1) * aw) / n, bh = 2.1, y = cursor[0];
  steps.forEach((t, i) => {
    const x = COLX[0] + i * (bw + aw);
    s.addText(t, { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.15, x, y, w: bw, h: bh,
      fill: { color: i === 3 ? "FDEEE7" : TINT }, line: { color: i === 3 ? ORANGE : BLUE, width: 2 },
      fontFace: BODY, fontSize: 22, color: INK, align: "center", valign: "middle", margin: 6, objectName: "step" + (i + 1) });
    if (i < n - 1) s.addShape(pres.shapes.LINE, { x: x + bw + 0.05, y: y + bh / 2, w: aw - 0.1, h: 0,
      line: { color: MUTED, width: 2.5, endArrowType: "triangle" } });
  });
  s.addText("× 100 rounds, one model turn per round", { x: COLX[0], y: y + bh + 0.1, w: COLW, h: 0.5,
    fontFace: BODY, fontSize: SMALL_PT, italic: true, color: MUTED, align: "center", margin: 0, isTextBox: true });
  cursor[0] = y + bh + 0.85;
}
bullets(0, [
  [{ text: "Task: ", b: true }, { text: "find hits among 18,418 anonymized genes (IFNG screen from BioDiscoveryAgent, about 920 hits)." }],
  [{ text: "Forgetting is costly: ", b: true }, { text: "results are shown once (no history tool), and re-proposing a tested gene wastes a slot." }],
  [{ text: "Fair and sealed: ", b: true }, { text: "a hashed round token forces one turn per round; agents can't reach the evaluator, data or seed; every trace is audited." }],
  [{ text: "Measures: ", b: true }, { text: "hits, repeats, a top-10 recall probe, and graded hypotheses every 10 rounds (section 5)." }],
], { after: 0.6 });

header(0, "3", "Without files, plain Codex forgets what it tested");
figure(0, "repeats_100x32.png", 800, 470, "Repeated proposals per round for plain Codex without files vs the prototype");
bullets(0, [
  [{ text: "Told not to write files, plain Codex re-proposed " }, { text: "811 and 1,167", b: true }, { text: " tested genes, yet named its top 10 correctly at every probe: it kept the short list and lost the long one." }],
  [{ text: "The prototype stayed exact ", b: true }, { text: "in every run (0-28 repeats). Allowed files, plain Codex usually kept its own record, but not always (161 and 195 repeats in two seeds)." }],
  [{ text: "Forgetting is cumulative: ", b: true }, { text: "repeats build up over the run rather than spiking at compactions." }],
]);

// ---------------------------------------------------------------- middle: hits, grading
header(1, "4", "Slightly more hits, at twice the cost");
figure(1, "hits_100x32.png", 800, 470, "Cumulative hits over 100 rounds, 4 runs per arm");
table(1, ["100x32, 4 runs", "hits", "mean", "repeats", "tokens", "time"], DATA.hits,
  [2.6, 4.0, 1.1, 3.0, 1.9, 1.2],
  "+14.5 hits (+8%) for 2x tokens and time; ranges overlap (permutation p = 0.07, one-sided). A no-LLM heuristic with the same lookups gets about 221. *Stopped at round 99.");

header(1, "5", "Agents game the grader: three fixes");
para(1, "Every 10 rounds the agent submits 5 modules (3-10 tested genes + a predicted sign), graded on held-out genes most frequent in its members' neighbour lists.", { after: 0.3 });
figure(1, "grading_rules.png", 780, 470, "Offline strategies under each grading rule");
bullets(1, [
  [{ text: "Froze modules", b: true }, { text: " after round 30 → " }, { text: "fresh:", b: true }, { text: " a module needs a newly tested gene." }],
  [{ text: "Missing held-out genes", b: true }, { text: " capped scores → " }, { text: "found:", b: true }, { text: " grade on those actually found." }],
  [{ text: "Copied one module 5 times", b: true }, { text: " (0.50 vs 0.03) → " }, { text: "dedup:", b: true }, { text: " each held-out gene counts once." }],
  [{ text: "Final rules: ", b: true }, { text: "copying scores like random (0.019 vs 0.017), freezing 0.006, grouping hits by shared neighbours 0.106." }],
]);

// ---------------------------------------------------------------- right: final results, diagnosis, takeaways
header(2, "6", "Results under the final rules");
table(2, ["100x32, v3 grading", "hits", "hypothesis", "repeats", "tokens"],
  DATA.v3.concat(DATA.hint || []).concat([["Offline rules", "–", "0.106 / 0.067 / 0.017", "–", "0"]]),
  [4.4, 1.6, 3.6, 1.9, 1.7], DATA.v3Note);

header(2, "7", "Low scores: reasoning, not memory");
figure(2, "diagnosis_modules.png", 760, 330, "Module members by outcome and whether the agent's files held the correct score");
bullets(2, [
  [{ text: "Both agents had the facts: ", b: true }, { text: "in 7 of 8 runs, every bad member's correct score was in the agent's own files." }],
  [{ text: "They chose badly: ", b: true }, { text: "most bad members were new genes the agent knew were not hits (55 of 83; 90 of 132)." }],
  [{ text: "Same data, simple rule, 2x the score: ", b: true }, { text: "neighbour grouping on each agent's own data scores 0.095 / 0.100 vs 0.048 / 0.055." }],
  [{ text: "Memory is re-read: ", b: true }, { text: "after compaction the prototype re-read its files 666 of 668 times; plain Codex after 68-98%." }],
], { after: 0.6 });

header(2, "8", "Next: does telling them the rule help?");
para(2, "Running now: both agents get the neighbour-grouping strategy in their instructions. If scores rise toward 0.10, the gap was strategy; if not, they can't carry it out even when told. Then: context-window sizes (16K to 128K) without files, to trace forgetting to compaction pressure.", { after: 0.6 });

header(2, "", "Takeaways");
{
  const tk = ["Structured memory matters when the agent won't keep its own record. The prototype stayed exact; plain Codex depended on choosing to keep files.",
    "The bottleneck has moved from memory to reasoning. Neither agent used its facts as well as a two-line grouping rule.",
    "Long-horizon benchmarks must be graded adversarially. Both agents found shortcuts within one pilot; random, copy and freeze strategies are cheap checks.",
    "Cost: the prototype uses about 2x the tokens and time for a small, uncertain gain in hits."];
  const y = cursor[2], h = textH(tk, BODY_PT, COLW - 0.8) + 0.6;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: COLX[2], y, w: COLW, h, rectRadius: 0.2, fill: { color: TINT }, line: { color: TINT }, objectName: "takeaways-card" });
  s.addText([
    { text: "Structured memory matters when the agent won't keep its own record. ", options: { bold: true } },
    { text: "The prototype stayed exact; plain Codex depended on choosing to keep files.", options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: "The bottleneck has moved from memory to reasoning. ", options: { bold: true } },
    { text: "Neither agent used its facts as well as a two-line grouping rule.", options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: "Long-horizon benchmarks must be graded adversarially. ", options: { bold: true } },
    { text: "Both agents found shortcuts within one pilot; random, copy and freeze strategies are cheap checks.", options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: "Cost: ", options: { bold: true } },
    { text: "the prototype uses about 2x the tokens and time for a small, uncertain gain in hits." },
  ], { x: COLX[2] + 0.4, y: y + 0.3, w: COLW - 0.8, h: h - 0.6, fontFace: BODY, fontSize: BODY_PT, color: INK, valign: "top", margin: 0, isTextBox: true });
  cursor[2] = y + h;
}

// ---------------------------------------------------------------- footer
s.addText("Task and data: BioDiscoveryAgent (Roohani et al., 2024); DepMap. Model: gpt-6.1-terra, same for both arms. Prototype: research harness by Yucheng Jiang.",
  { x: M, y: H - 1.15, w: W - 2 * M, h: 0.6, fontFace: BODY, fontSize: 20, color: MUTED, margin: 0, isTextBox: true });

for (let c = 0; c < 3; c++) if (cursor[c] > BOTTOM + 0.01) console.error(`column ${c} overflows: ends at ${cursor[c].toFixed(2)} in (limit ${BOTTOM})`);
console.log("column ends:", cursor.map(v => v.toFixed(2)).join(", "), "limit", BOTTOM);
pres.writeFile({ fileName: path.join(__dirname, "poster.pptx") }).then(f => console.log("wrote", f));
