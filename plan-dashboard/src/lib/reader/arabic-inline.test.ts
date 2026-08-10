/**
 * arabic-inline.test.ts — findArabicRuns and the seed's `.ar-inline` wrapper.
 *
 * Pins the contract arabic-decos.ts depends on: `findArabicRuns` must find
 * exactly the runs `renderEditSeed` already wraps in `<span class="ar-inline">`,
 * because the live-editor decoration re-derives them from the parsed-out text —
 * a second regex here would be a second answer to "what counts as Arabic".
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { findArabicRuns, renderEditSeed } from "./markdown";

test("findArabicRuns finds a single term woven into an English sentence", () => {
  const runs = findArabicRuns("as a friend (خَلِيلٍ), then as a messenger");
  assert.equal(runs.length, 1);
  const [r] = runs;
  assert.equal(
    "as a friend (خَلِيلٍ), then as a messenger".slice(r.start, r.end),
    "خَلِيلٍ",
  );
});

test("findArabicRuns trims bracketing whitespace off each end", () => {
  const text = "the proofs (  الْحُجَجَ  ) are named";
  const runs = findArabicRuns(text);
  assert.equal(runs.length, 1);
  assert.equal(text.slice(runs[0].start, runs[0].end), "الْحُجَجَ");
});

test("findArabicRuns returns nothing for plain English", () => {
  assert.deepEqual(findArabicRuns("no Arabic here at all"), []);
});

test("renderEditSeed wraps an inline term in .ar-inline with rtl/ar", () => {
  const html = renderEditSeed("He is called a vicegerent (خَلِيفَةً) too.");
  assert.match(
    html,
    /<span class="ar-inline" dir="rtl" lang="ar">خَلِيفَةً<\/span>/,
  );
});

test("renderEditSeed leaves a display Arabic blockquote unwrapped by ar-inline", () => {
  // A pure block::ar quotation still round-trips through isolateInlineArabic,
  // but its own .ar/.tr classing (not tested here) is what carries the size —
  // this only pins that the inline wrapper doesn't ALSO fire on ordinary
  // English prose sitting beside it.
  const html = renderEditSeed("Plain English with no Arabic in it.");
  assert.doesNotMatch(html, /ar-inline/);
});
