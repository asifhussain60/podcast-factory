/**
 * Self-checking test for render-supplication-pdf.mjs (no test runner in this
 * project — matches the visual-layout.test.mjs pattern).
 * Run: node scripts/render-supplication-pdf.test.mjs   (exit 0 = pass, 1 = fail)
 *
 * Covers the pure HTML-assembly and validation layer only. The Playwright print
 * step is proven separately by rendering scripts/fixtures/*.fixture.json.
 */
import assert from "node:assert/strict";

import {
  SCRIPT_LANGS,
  buildTitleBlock,
  buildUnitsTable,
  esc,
  validate,
} from "./render-supplication-pdf.mjs";

let n = 0;
const t = (name, fn) => {
  try {
    fn();
    n++;
  } catch (err) {
    console.error(`FAIL: ${name}\n  ${err.message}`);
    process.exit(1);
  }
};

const doc = (over = {}) => ({
  slug: "test",
  source_language: "ar",
  title_en: "Title",
  units: [{ n: 1, source: "يَا رَبِّ", english: "O my Lord", refrain: false }],
  ...over,
});

// ── escaping ────────────────────────────────────────────────────────────────
t("esc neutralizes markup", () => {
  assert.equal(esc('<b>&"x'), "&lt;b&gt;&amp;&quot;x");
});

t("esc leaves Arabic and tashkeel untouched", () => {
  const ar = "وَ مِنَ اللَّيْلِ";
  assert.equal(esc(ar), ar);
});

t("esc handles null and undefined", () => {
  assert.equal(esc(null), "");
  assert.equal(esc(undefined), "");
});

// ── the row contract — the layout's core guarantee ──────────────────────────
t("each unit is exactly one <tr> with two cells", () => {
  const html = buildUnitsTable(
    doc({
      units: [
        { n: 1, source: "أ", english: "A" },
        { n: 2, source: "ب", english: "B" },
      ],
    }),
  );
  assert.equal((html.match(/<tr/g) || []).length, 2);
  assert.equal((html.match(/<td class="sup-en"/g) || []).length, 2);
  assert.equal((html.match(/<td class="sup-src"/g) || []).length, 2);
});

t("English cell precedes the source cell (English is the LEFT column)", () => {
  const html = buildUnitsTable(doc());
  assert.ok(html.indexOf('class="sup-en"') < html.indexOf('class="sup-src"'));
});

t("source cell carries dir=rtl and the document's lang", () => {
  assert.ok(buildUnitsTable(doc()).includes('dir="rtl" lang="ar"'));
  assert.ok(
    buildUnitsTable(doc({ source_language: "ur" })).includes(
      'dir="rtl" lang="ur"',
    ),
  );
});

t("the English cell is never given a script direction", () => {
  const enCell = buildUnitsTable(doc()).match(/<td class="sup-en"[^>]*>/)[0];
  assert.ok(!enCell.includes("dir="));
  assert.ok(!enCell.includes("lang="));
});

t("refrain rows get the refrain class, others do not", () => {
  const html = buildUnitsTable(
    doc({
      units: [
        { n: 1, source: "أ", english: "A", refrain: true },
        { n: 2, source: "ب", english: "B", refrain: false },
      ],
    }),
  );
  assert.equal((html.match(/class="sup-refrain"/g) || []).length, 1);
});

t("unit numbers are never printed", () => {
  // `n` stays in units.json and the review CLI, but the printed page carries no
  // unit chrome — a supplication is a devotional text, not a numbered edition.
  const html = buildUnitsTable(
    doc({ units: [{ n: 7, source: "أ", english: "A" }] }),
  );
  assert.ok(!html.includes("sup-n"));
  assert.ok(!html.includes(">7<"));
});

t("no <thead> — a repeating header would waste a long litany's page", () => {
  assert.ok(!buildUnitsTable(doc()).includes("<thead"));
});

// ── title block ─────────────────────────────────────────────────────────────
t("metadata renders in the fixed reading order", () => {
  const html = buildTitleBlock(
    doc({
      meta: { place: "Karbala", type: "Ziyarat", attributed_to: "X" },
    }),
  );
  assert.ok(html.indexOf("Type") < html.indexOf("Attributed to"));
  assert.ok(html.indexOf("Attributed to") < html.indexOf("Place"));
});

t("absent metadata fields emit no rows", () => {
  assert.ok(!buildTitleBlock(doc()).includes("<dl"));
});

t("preamble paragraphs split on blank lines", () => {
  const html = buildTitleBlock(doc({ preamble_en: "one\n\ntwo\n\nthree" }));
  assert.equal((html.match(/<p>/g) || []).length, 3);
});

t("the source title is rtl-marked", () => {
  assert.ok(
    buildTitleBlock(doc({ title_src: "مناجات" })).includes('dir="rtl"'),
  );
});

// ── validation ──────────────────────────────────────────────────────────────
t("a well-formed document validates clean", () => {
  assert.deepEqual(validate(doc()), []);
});

t("source_language is never inferred — only ar and ur are accepted", () => {
  assert.deepEqual([...SCRIPT_LANGS].sort(), ["ar", "ur"]);
  for (const bad of [undefined, null, "", "en", "fa", "arabic"]) {
    const errs = validate(doc({ source_language: bad }));
    assert.ok(
      errs.some((e) => e.includes("source_language")),
      `expected a source_language error for ${JSON.stringify(bad)}`,
    );
  }
});

t("an empty unit list is rejected", () => {
  assert.ok(validate(doc({ units: [] })).some((e) => e.includes("non-empty")));
});

t("a unit missing source or english is rejected", () => {
  assert.ok(
    validate(doc({ units: [{ n: 1, english: "A" }] })).some((e) =>
      e.includes("missing 'source'"),
    ),
  );
  assert.ok(
    validate(doc({ units: [{ n: 1, source: "أ" }] })).some((e) =>
      e.includes("missing 'english'"),
    ),
  );
  assert.ok(
    validate(doc({ units: [{ n: 1, source: "   ", english: "   " }] }))
      .length >= 2,
  );
});

console.log(`render-supplication-pdf.test.mjs: ${n} assertions passed`);
