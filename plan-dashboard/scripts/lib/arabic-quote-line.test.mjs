/**
 * arabic-quote-line.test.mjs — the JS half of the quotation-line-direction mirror.
 *
 * TWO renderers answer this question, one per surface that draws a quotation block:
 * `isArabicQuoteLine` in book-html.mjs (the PDF and the Composer's Read view) and the
 * same function in src/lib/reader/markdown.ts (the reader, which is client-bundled and
 * so cannot import the Node-only mjs module). A third copy — the detector in
 * scripts/podcast/tests/test_book_articulation_defects.py — reads the SAME fixtures.
 *
 * Neither renderer was pinned to the other before 2026-08-09, and both were wrong in
 * the same way: they asked whether a line CONTAINED Arabic rather than whether it was
 * mostly Arabic, so an English translation carrying the `(ع)` honorific was set
 * right-to-left in the Arabic face with its quotation marks thrown to the wrong ends.
 * Drift here is silent by nature: the printed page and the reader would give the same
 * paragraph opposite directions and nothing would error.
 *
 * Run: node --test plan-dashboard/scripts/lib/arabic-quote-line.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { isArabicQuoteLine } from "./book-html.mjs";
import { isArabicQuoteLine as readerImpl } from "../../src/lib/reader/markdown.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const { cases } = JSON.parse(
  readFileSync(join(HERE, "arabic-quote-line.fixtures.json"), "utf8"),
);

test("book-html.mjs matches the shared fixtures", () => {
  assert.ok(cases.length > 0, "fixture file is empty");
  for (const { text, arabic, why } of cases) {
    assert.equal(isArabicQuoteLine(text), arabic, why);
  }
});

test("the reader's copy matches the shared fixtures", () => {
  for (const { text, arabic, why } of cases) {
    assert.equal(readerImpl(text), arabic, why);
  }
});

test("the two copies agree on every fixture, case by case", () => {
  for (const { text, why } of cases) {
    assert.equal(
      isArabicQuoteLine(text),
      readerImpl(text),
      `print and reader disagree: ${why}`,
    );
  }
});
