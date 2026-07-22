/**
 * Self-checking test for visual-layout.mjs (no test runner in this project).
 * Run: node scripts/visual-layout.test.mjs   (exit 0 = pass, 1 = fail)
 * Kept in sync with scripts/podcast/tests/test_visual_layout.py.
 */
import assert from "node:assert/strict";
import {
  SCHEMA,
  WRAP_MAX_WIDTH_PCT,
  normalizePlacement,
  validateLayout,
  figureHtml,
  applyLayout,
  anchorKey,
} from "./visual-layout.mjs";

let n = 0;
const t = (_name, fn) => {
  fn();
  n++;
};

// ── normalization mirrors the Python side ──
t("center forces standalone", () => {
  const { placement } = normalizePlacement({
    visual_id: "a",
    align: "center",
    flow: "wrap",
  });
  assert.equal(placement.flow, "standalone");
});
t("wide wrap promoted to standalone", () => {
  const { placement, warnings } = normalizePlacement({
    visual_id: "a",
    align: "left",
    flow: "wrap",
    width_pct: 80,
  });
  assert.equal(placement.flow, "standalone");
  assert.ok(warnings.some((w) => w.includes(`>${WRAP_MAX_WIDTH_PCT}`)));
});
t("valid wrap kept", () => {
  const { placement, warnings } = normalizePlacement({
    visual_id: "a",
    align: "left",
    flow: "wrap",
    width_pct: 40,
  });
  assert.equal(placement.flow, "wrap");
  assert.equal(placement.width_pct, 40);
  assert.deepEqual(warnings, []);
});
t("width clamped", () => {
  assert.equal(
    normalizePlacement({ visual_id: "a", width_pct: 999 }).placement.width_pct,
    100,
  );
  assert.equal(
    normalizePlacement({ visual_id: "a", width_pct: -5 }).placement.width_pct,
    1,
  );
});
t("validate skips id-less placement", () => {
  const { placements } = validateLayout({
    schema: SCHEMA,
    placements: [{ anchor: "x" }, { visual_id: "ok" }],
  });
  assert.equal(placements.length, 1);
  assert.equal(placements[0].visual_id, "ok");
});

// ── figure HTML ──
t("figure wrap-left carries classes + width var", () => {
  const html = figureHtml(
    {
      align: "left",
      flow: "wrap",
      width_pct: 40,
      caption: "A tree",
      page_fit: "avoid",
    },
    "/book/visuals/x.svg",
  );
  assert.ok(html.includes("flow-wrap"));
  assert.ok(html.includes("align-left"));
  assert.ok(html.includes("--fig-w:40%"));
  assert.ok(html.includes("<figcaption>A tree</figcaption>"));
});
t("caption suppressed when it duplicates embedded title", () => {
  const html = figureHtml(
    {
      align: "center",
      flow: "standalone",
      width_pct: 60,
      caption: "The Seven",
      page_fit: "avoid",
    },
    "/book/visuals/x.png",
    "the seven",
  );
  assert.ok(!html.includes("<figcaption>"));
});
t("empty caption -> no figcaption", () => {
  const html = figureHtml(
    {
      align: "center",
      flow: "standalone",
      width_pct: 60,
      caption: "",
      page_fit: "avoid",
    },
    "/x.png",
  );
  assert.ok(!html.includes("<figcaption>"));
});

// ── anchor matching + injection ──
t("anchorKey normalizes markup + numbering", () => {
  assert.equal(anchorKey("## 2. Patience"), "patience");
  assert.equal(anchorKey("<h2>2. Patience</h2>"), "patience");
});
function norm(raw) {
  return validateLayout({ schema: SCHEMA, placements: [raw] }).placements[0];
}

t("applyLayout default places figure AFTER the intro paragraph (§26.3)", () => {
  const body =
    '<section class="chapter-open"><h2>2. Patience</h2></section>\n<p>intro</p>\n<p>more</p>';
  const p = norm({
    visual_id: "f1",
    anchor: "## 2. Patience",
    flow: "standalone",
    width_pct: 60,
    caption: "c",
  });
  const out = applyLayout(
    body,
    [p],
    new Map([["f1", { src: "/book/visuals/f1.svg" }]]),
  );
  assert.ok(out.includes("v2-fig"));
  assert.ok(out.indexOf("v2-fig") > out.indexOf("<p>intro</p>")); // after intro
  assert.ok(out.indexOf("v2-fig") < out.indexOf("<p>more</p>")); // before 2nd para
});
t("anchor_para=0 places figure at chapter top", () => {
  const body =
    '<section class="chapter-open"><h2>2. Patience</h2></section>\n<p>intro</p>';
  const p = norm({
    visual_id: "f1",
    anchor: "## 2. Patience",
    anchor_para: 0,
    flow: "standalone",
    width_pct: 60,
    caption: "c",
  });
  const out = applyLayout(body, [p], new Map([["f1", { src: "/x.svg" }]]));
  assert.ok(out.indexOf("v2-fig") < out.indexOf("<p>intro</p>")); // before any paragraph
});
t("anchor_para=2 places figure after the 2nd paragraph", () => {
  const body =
    '<section class="chapter-open"><h2>2. Patience</h2></section>\n<p>a</p>\n<p>b</p>\n<p>c</p>';
  const p = norm({
    visual_id: "f1",
    anchor: "## 2. Patience",
    anchor_para: 2,
    flow: "standalone",
    width_pct: 60,
    caption: "c",
  });
  const out = applyLayout(body, [p], new Map([["f1", { src: "/x.svg" }]]));
  assert.ok(out.indexOf("v2-fig") > out.indexOf("<p>b</p>"));
  assert.ok(out.indexOf("v2-fig") < out.indexOf("<p>c</p>"));
});
t("overflow anchor_para flushes at chapter end (before next chapter)", () => {
  const body =
    '<section class="chapter-open"><h2>1. A</h2></section>\n<p>only</p>\n<section class="chapter-open"><h2>2. B</h2></section>\n<p>next</p>';
  const p = norm({
    visual_id: "f1",
    anchor: "## 1. A",
    anchor_para: 9,
    flow: "standalone",
    width_pct: 60,
    caption: "c",
  });
  const out = applyLayout(body, [p], new Map([["f1", { src: "/x.svg" }]]));
  assert.ok(out.indexOf("v2-fig") > out.indexOf("<p>only</p>"));
  assert.ok(out.indexOf("v2-fig") < out.indexOf("2. B")); // did not leak into chapter 2
});
t("applyLayout skips unknown visual id (partial contract tolerant)", () => {
  const body = '<section class="chapter-open"><h2>2. Patience</h2></section>';
  const placements = [
    {
      visual_id: "missing",
      anchor: "## 2. Patience",
      align: "center",
      flow: "standalone",
      width_pct: 60,
      caption: "",
      page_fit: "avoid",
    },
  ];
  const out = applyLayout(body, placements, new Map());
  assert.equal(out, body);
});
t("applyLayout no-ops with empty placements", () => {
  const body = '<section class="chapter-open"><h2>X</h2></section>';
  assert.equal(applyLayout(body, [], new Map()), body);
});

console.log(`visual-layout.mjs: ${n} tests passed`);
