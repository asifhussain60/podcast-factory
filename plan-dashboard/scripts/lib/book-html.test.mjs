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
import { renderMarkdown } from "../../src/lib/reader/markdown.ts";
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

test("seeded sawH2 keeps a later unnumbered heading out of the front-matter treatment", () => {
  const later = "## An Unnumbered Later Heading\n\nSome prose.";
  const asFirst = renderMd(later);
  const asLater = renderMd(later, new Map(), { sawH2: true });

  assert.ok(
    asFirst.includes("chapter-open"),
    "an unnumbered FIRST heading still opens the book",
  );
  assert.ok(
    !asFirst.includes("ch-eyebrow"),
    "and carries NO eyebrow — the section names itself",
  );
  assert.ok(
    asLater.includes('<h3 class="section-heading">'),
    "an unnumbered LATER heading renders as an in-flow section heading instead",
  );
});

test("an unnumbered front-matter heading never prints a label above its own title", () => {
  // `Preface` used to be hardcoded here, and since the section became
  // "Introduction to the Book" it printed one line above the other.
  const out = renderMd("## Introduction to the Book\n\nProse.");

  assert.ok(!out.includes("Preface"), "no stale label");
  assert.ok(
    out.includes("<h2>Introduction to the Book</h2>"),
    "title stands alone",
  );
});

test("sawH2 defaults to false — whole-book callers are unaffected", () => {
  const md = "## A Preface\n\nProse.";
  assert.equal(
    renderMd(md),
    renderMd(md, new Map(), {}),
    "omitting the option matches passing an empty options object",
  );
  assert.ok(renderMd(md).includes("A Preface"), "default behaviour preserved");
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

// ── the printed page and the reader must agree on what a list is ────────────

/** The <li> ordinals a render actually NUMBERS, read off the markup. */
function orderedNumbers(html) {
  const out = [];
  let counter = 0;
  for (const m of html.matchAll(/<(ol|\/ol|li)(?:\s+value="(\d+)")?[^>]*>/g)) {
    if (m[1] === "ol" || m[1] === "/ol") counter = 0;
    else if (m[2]) out.push((counter = Number(m[2])));
    else out.push((counter += 1));
  }
  return out;
}

const LIST_FIXTURES = [
  {
    name: "the real 5-condition enumeration from the-master-and-the-disciple",
    md: [
      'The Master said, "My conditions upon you are five:',
      "",
      "1. Do not fail me if I entrust you with something.",
      "2. Do not conceal anything from me if I ask you.",
      "3. Do not seek me out until I answer you.",
      "4. Do not ask me for anything until I begin with you.",
      '5. Do not mention my affair to your father."',
      "",
      "The boy accepted.",
    ].join("\n"),
    numbers: [1, 2, 3, 4, 5],
  },
  {
    name: "a list starting at 3",
    md: "3. Third.\n4. Fourth.\n",
    numbers: [3, 4],
  },
  {
    name: "a loose list, blank lines between items",
    md: "1. One.\n\n2. Two.\n\n3. Three.\n",
    numbers: [1, 2, 3],
  },
  {
    name: "source numbering that repeats",
    md: "1. One.\n1. Also one.\n",
    numbers: [1, 1],
  },
];

for (const fx of LIST_FIXTURES) {
  test(`print and reader agree on ${fx.name}`, () => {
    // renderMd builds book.pdf; renderMarkdown's default profile builds the
    // Composer's Read view. Both read book.md. Before renderMd had an
    // ordered-list parser it emitted a run-together paragraph with the numbering
    // as literal text while the reader emitted a real <ol> — the two deliverables
    // disagreeing about the same source.
    const print = renderMd(fx.md);
    const reader = renderMarkdown(fx.md);
    assert.deepEqual(orderedNumbers(print), fx.numbers, "print numbering");
    assert.deepEqual(orderedNumbers(reader), fx.numbers, "reader numbering");
    for (const [label, html] of [
      ["print", print],
      ["reader", reader],
    ]) {
      assert.equal(
        (html.match(/<ol/g) ?? []).length,
        1,
        `${label} must emit exactly one <ol>`,
      );
      assert.doesNotMatch(
        html,
        /<p>[^<]*\b1\.\s/,
        `${label} left literal numbering in a paragraph`,
      );
    }
  });
}

test("prose around a list survives in both renderers", () => {
  const md = "Before.\n\n1. One.\n2. Two.\n\nAfter.\n";
  for (const html of [renderMd(md), renderMarkdown(md)]) {
    assert.match(html, /Before\./);
    assert.match(html, /After\./);
    assert.ok(
      html.indexOf("</ol>") < html.indexOf("After."),
      "the list must close before the following prose",
    );
  }
});

test("a bulleted line is still NOT a list in the default print render", () => {
  // Deliberate: no book.md in the corpus uses '- ' bullets, so enabling them for
  // print would be an unverifiable change. Pinned so the asymmetry is a decision
  // rather than an oversight.
  const html = renderMd("- alpha\n- beta\n");
  assert.equal((html.match(/<ul/g) ?? []).length, 0);
});
