/**
 * book-html.test.mjs — renderMd() self-study layer + regression guard.
 * Run with:  node --test scripts/lib/book-html.test.mjs   (from plan-dashboard/)
 *
 * Guards the opt-in self-study render mode: default (selfStudy off) rendering must
 * be unchanged, and the augment editorial fences must never leak as visible text.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderMd, MACHINE_FENCE_KINDS } from "./book-html.mjs";
import { FENCE_KINDS } from "../../src/lib/reader/book-fences.ts";

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

/* ── Per-chapter rendering parity (the Book Composer read-mode contract) ──────
 * The Composer renders ONE chapter at a time; the PDF renders the whole book in
 * a single pass. These guard the invariant that makes the two the same surface:
 * splitting the book and rendering each chapter with `sawH2: i > 0` must
 * reproduce the whole-book render byte-for-byte. If renderMd ever gains state
 * that carries across a "## " boundary, this test fails and the Composer's
 * read mode must be re-derived — it is the canary for silent Preview↔PDF drift. */

/** Split a book body the way lib/reader/composer.ts does. */
function splitChapters(md) {
  const parts = md.split(/^(##\s+.+)$/m);
  const out = [];
  for (let i = 1; i < parts.length; i += 2) {
    out.push(`${parts[i].trim()}\n\n${(parts[i + 1] ?? "").trim()}`);
  }
  return out;
}

const MULTI_CHAPTER = [
  "## 1. First Chapter",
  "",
  "Opening paragraph of chapter one.",
  "",
  "> إن الحمد لله",
  ">",
  "> Praise belongs to God.",
  "",
  "A closing paragraph.",
  "",
  "## 2. Second Chapter",
  "",
  "Opening paragraph of chapter two.",
  "",
  "### An inner heading",
  "",
  "More prose.",
  "",
  "## An Unnumbered Later Heading",
  "",
  "Prose under a source heading that is NOT a chapter opening.",
  "",
].join("\n");

test("per-chapter render with seeded sawH2 equals the whole-book render", () => {
  const whole = renderMd(MULTI_CHAPTER);
  const perChapter = splitChapters(MULTI_CHAPTER)
    .map((chunk, i) => renderMd(chunk, new Map(), { sawH2: i > 0 }))
    .join("\n");
  assert.equal(
    perChapter,
    whole,
    "chapter-by-chapter render must equal the whole-book render",
  );
});

test("seeded sawH2 keeps a later unnumbered heading out of the preface treatment", () => {
  const later = "## An Unnumbered Later Heading\n\nSome prose.";
  const asFirst = renderMd(later);
  const asLater = renderMd(later, new Map(), { sawH2: true });

  assert.ok(
    asFirst.includes("Preface"),
    "an unnumbered FIRST heading is still the preface",
  );
  assert.ok(
    !asLater.includes("Preface"),
    "an unnumbered LATER heading is never the preface",
  );
  assert.ok(
    asLater.includes('<h3 class="section-heading">'),
    "it renders as an in-flow section heading instead",
  );
});

test("sawH2 defaults to false — whole-book callers are unaffected", () => {
  const md = "## A Preface\n\nProse.";
  assert.equal(
    renderMd(md),
    renderMd(md, new Map(), {}),
    "omitting the option matches passing an empty options object",
  );
  assert.ok(renderMd(md).includes("Preface"), "default behaviour preserved");
});

// ── machine fences never render as visible text ─────────────────────────────

test("every machine fence kind is skipped, not escaped into the prose", () => {
  // The regression: the skip listed editorial/study-summary/bridge and missed
  // `edition-intro`. On a book whose front matter opens the first chapter (the
  // introduction is fenced INSIDE that chapter's body), the Composer rendered
  // `<!-- edition-intro:begin -->` as the chapter's first line — and `<!` took
  // the drop-cap treatment. Asserted for EVERY kind so the next one added
  // cannot regress only its own case.
  for (const kind of MACHINE_FENCE_KINDS) {
    const html = renderMd(
      [
        "## 1. A Chapter",
        "",
        `<!-- ${kind}:begin -->`,
        "The fenced prose itself must still render.",
        `<!-- ${kind}:end -->`,
        "",
        "And the prose after it.",
      ].join("\n"),
    );
    assert.ok(!html.includes(kind), `${kind} marker leaked as text`);
    assert.ok(!html.includes("&lt;!--"), `${kind} left an escaped comment`);
    assert.ok(
      html.includes("The fenced prose itself must still render."),
      `${kind} swallowed its own content`,
    );
    assert.ok(html.includes("And the prose after it."));
  }
});

test("the fence-kind list matches the contract's own declaration", () => {
  // This renderer also runs under plain node for the PDF build, so it cannot
  // import the TypeScript contract — the lists are mirrored by hand and pinned
  // here instead. A one-sided edit fails this rather than silently letting one
  // renderer show a marker the other hides.
  assert.deepEqual(
    [...MACHINE_FENCE_KINDS].sort(),
    [...FENCE_KINDS].sort(),
    "book-html.mjs MACHINE_FENCE_KINDS and book-fences.ts FENCE_KINDS diverged",
  );
});
