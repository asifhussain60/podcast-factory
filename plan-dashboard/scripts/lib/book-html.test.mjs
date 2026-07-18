/**
 * book-html.test.mjs — renderMd() self-study layer + regression guard.
 * Run with:  node --test scripts/lib/book-html.test.mjs   (from plan-dashboard/)
 *
 * Guards the opt-in self-study render mode: default (selfStudy off) rendering must
 * be unchanged, and the augment editorial fences must never leak as visible text.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderMd } from "./book-html.mjs";

const AUGMENTED = [
  "## 1. A Chapter",
  "",
  "Body paragraph here.",
  "",
  "<!-- editorial:begin -->",
  "> **Editorial note (source-grounded).** ",
  "> A grounding note for the reader.",
  "<!-- editorial:end -->",
  "",
].join("\n");

test("default render never emits the editorial fence as visible text", () => {
  const html = renderMd(AUGMENTED);
  assert.ok(
    !html.includes("editorial:begin"),
    "fence must not appear (raw or escaped)",
  );
  assert.ok(!html.includes("&lt;!--"), "no escaped comment leaks into prose");
  assert.ok(
    html.includes("A grounding note for the reader"),
    "the note text still renders",
  );
  assert.ok(
    !html.includes("study-note"),
    "no self-study aside in default mode",
  );
});

test("self-study render turns editorial fences into a styled Contextual-note aside", () => {
  const html = renderMd(AUGMENTED, new Map(), { selfStudy: true });
  assert.ok(html.includes('<aside class="study-note">'), "note aside present");
  assert.ok(html.includes("Contextual note</p>"), "labeled");
  assert.ok(
    html.includes("A grounding note for the reader"),
    "body carried through",
  );
  assert.ok(!html.includes("editorial:begin"), "fence consumed");
  // The bold label line inside the fence is dropped (we render our own label).
  assert.ok(
    !html.includes("<strong>Editorial note"),
    "inner bold label dropped",
  );
});

test("self-study parses bullet lists and study-summary fences; default does not", () => {
  const md = [
    "## 1. A Chapter",
    "",
    "Intro.",
    "",
    "- first point",
    "- second point",
    "",
    "<!-- study-summary:begin -->",
    "> **Study summary.** ",
    "> The key idea in one line.",
    "<!-- study-summary:end -->",
    "",
  ].join("\n");

  const on = renderMd(md, new Map(), { selfStudy: true });
  assert.ok(on.includes('<ul class="study-list">'), "bullet list parsed");
  assert.equal((on.match(/<li>/g) || []).length, 2, "two list items");
  assert.ok(
    on.includes('<aside class="study-summary">'),
    "summary aside present",
  );
  assert.ok(on.includes("Study summary</p>"), "summary labeled");

  const off = renderMd(md);
  assert.ok(
    !off.includes('<ul class="study-list">'),
    "default has no list parser",
  );
  assert.ok(!off.includes("study-summary"), "default has no summary aside");
});

test("default render of ordinary prose is structurally unchanged", () => {
  const md = ["## 1. Title", "", "A paragraph.", "", "> a quote", ""].join(
    "\n",
  );
  const html = renderMd(md);
  assert.ok(
    html.includes('<section class="chapter-open'),
    "chapter open preserved",
  );
  assert.ok(
    html.includes('<p class="ch-first">A paragraph.</p>'),
    "first paragraph preserved",
  );
  assert.ok(html.includes("<blockquote>"), "blockquote preserved");
});
