/**
 * arabic-block.test.mjs — the JS half of the standalone-Arabic-paragraph mirror.
 *
 * THREE implementations answer this question, one per surface that renders a
 * book: `isArabicOnlyParagraph` in book-html.mjs (the PDF and the Composer's Read
 * view), the same function in src/lib/reader/markdown.ts (the reader, which is
 * client-bundled and so cannot import the Node-only mjs module), and
 * `_book_mirror.is_arabic_block` in Python (the paragraph merge). This file pins
 * the two JS copies; `scripts/podcast/tests/test_book_mirror.py` pins the Python
 * one against the SAME fixtures.
 *
 * Drift here is silent by nature: a paragraph one surface treats as a centered
 * display quotation, another renders as left-aligned running prose at body
 * leading, and nothing errors.
 *
 * Run: node --test plan-dashboard/scripts/lib/arabic-block.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { isArabicOnlyParagraph } from "./book-html.mjs";
import { isArabicOnlyParagraph as readerImpl } from "../../src/lib/reader/markdown.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const { cases } = JSON.parse(
  readFileSync(join(HERE, "arabic-block.fixtures.json"), "utf8"),
);

test("book-html.mjs matches the shared fixtures", () => {
  assert.ok(cases.length > 0, "fixture file is empty");
  for (const { in: input, out, why } of cases) {
    assert.equal(isArabicOnlyParagraph(input), out, why);
  }
});

test("the reader's copy matches the shared fixtures", () => {
  for (const { in: input, out, why } of cases) {
    assert.equal(readerImpl(input), out, why);
  }
});

test("the fixtures exercise both answers", () => {
  // A fixture set that is all-true (or all-false) passes against a function that
  // ignores its argument, which is the way a pinning test goes vacuous.
  assert.ok(
    cases.some((c) => c.out) && cases.some((c) => !c.out),
    "fixtures must cover both outcomes",
  );
});
