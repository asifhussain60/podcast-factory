// The mermaid check asks one question: has a diagram's SOURCE changed without its committed SVG being re-rendered?
// It compared bytes, but mermaid measures text with the browser, and Chromium on Linux measures the same pinned font a
// fraction differently from Chromium on macOS — so all six committed diagrams "differed" in CI by 1-4% (coordinates
// only) on every push since the check was added, which also stopped that job before its runtime smoke ran. This
// compares STRUCTURE and TEXT and ignores geometry, so a moved coordinate is not a stale diagram but a changed label,
// node, edge or ordering is.
import assert from "node:assert/strict";
import { test } from "node:test";
import { normalizeSvg } from "./svg-normalize.mjs";

const svg = (body, label = "Start") =>
  `<svg viewBox="0 0 100 50"><g class="node" transform="translate(10.5, 20)"><rect x="-4" y="-4" width="40" height="20"/><text x="5" y="10">${label}</text></g>${body}</svg>`;

test("coordinates that differ by platform do not make a diagram stale", () => {
  const mac = `<svg viewBox="0 0 100.25 50"><path d="M 10.5 20 L 30.75 40" transform="translate(1.5, 2)"/></svg>`;
  const linux = `<svg viewBox="0 0 98.5 49.75"><path d="M 10.1 20.3 L 29.9 39.8" transform="translate(1.4, 2.1)"/></svg>`;
  assert.equal(normalizeSvg(mac), normalizeSvg(linux));
});

test("a changed label IS stale, even a digit inside it", () => {
  assert.notEqual(
    normalizeSvg(svg("", "Step 2")),
    normalizeSvg(svg("", "Step 3")),
  );
});

test("an added or removed node is stale", () => {
  assert.notEqual(
    normalizeSvg(svg("")),
    normalizeSvg(svg('<g class="node"><text>Extra</text></g>')),
  );
});

test("a reordered pair of nodes is stale", () => {
  const a =
    '<g class="node"><text>A</text></g><g class="node"><text>B</text></g>';
  const b =
    '<g class="node"><text>B</text></g><g class="node"><text>A</text></g>';
  assert.notEqual(normalizeSvg(svg(a)), normalizeSvg(svg(b)));
});

test("a changed style block IS stale (it is diagram content, not geometry)", () => {
  assert.notEqual(
    normalizeSvg("<svg><style>.node{fill:#123;font-size:16px}</style></svg>"),
    normalizeSvg("<svg><style>.node{fill:#123;font-size:18px}</style></svg>"),
  );
});

test("a changed attribute value that is not a number is stale", () => {
  assert.notEqual(
    normalizeSvg('<svg><g class="edge-a"/></svg>'),
    normalizeSvg('<svg><g class="edge-b"/></svg>'),
  );
});

test("whitespace between tags does not matter", () => {
  assert.equal(
    normalizeSvg("<svg>\n  <g/>\n</svg>"),
    normalizeSvg("<svg><g/></svg>"),
  );
});

test("identical input is identical", () => {
  assert.equal(normalizeSvg(svg("")), normalizeSvg(svg("")));
});

test("describeDifference points at the first place two SVGs diverge", async () => {
  const { describeDifference } = await import("./svg-normalize.mjs");
  const d = describeDifference(
    "<svg><text>Alpha</text></svg>",
    "<svg><text>Alpine</text></svg>",
  );
  assert.ok(d.index > 0);
  assert.match(d.committed, /Alpha/);
  assert.match(d.rendered, /Alpine/);
  assert.equal(describeDifference("<a/>", "<a/>"), null);
});

// Mermaid stores each edge's routing points as base64-encoded JSON in `data-points`, so a coordinate that moves by a
// fraction of a pixel changes the encoded TEXT — letters and all — not just digits. Found from the CI log of 2026-09-19:
// the first divergence in all five "stale" diagrams was inside a data-points attribute. It is geometry, not content.
test("edge routing points (base64 data-points) are geometry and do not make a diagram stale", () => {
  const points = (obj) => Buffer.from(JSON.stringify(obj)).toString("base64");
  const mac = `<path data-points="${points([
    { x: 91.0703125, y: 62 },
    { x: 91.07, y: 98.5 },
  ])}" data-look="classic"/>`;
  const linux = `<path data-points="${points([
    { x: 90.5, y: 62 },
    { x: 90.5, y: 98.5 },
  ])}" data-look="classic"/>`;
  assert.notEqual(mac, linux);
  assert.equal(normalizeSvg(mac), normalizeSvg(linux));
});

test("the attributes AROUND data-points still count", () => {
  const a = '<path data-points="AAAA" data-look="classic" class="edge-a"/>';
  const b = '<path data-points="BBBB" data-look="classic" class="edge-b"/>';
  assert.notEqual(normalizeSvg(a), normalizeSvg(b));
});
