/**
 * TS half of the Arabic fold mirror pin. Python half: tests/test_buckwalter.py.
 * Both read buckwalter.fixtures.json in this directory; a one-sided change to
 * the skeleton or fold rules fails here before it can skew a morphology lookup.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  arabicFold,
  foldsMatch,
  latinFold,
  normalizeArabic,
} from "../../src/lib/arabic-fold.ts";

const FIX = JSON.parse(
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "buckwalter.fixtures.json"),
    "utf-8",
  ),
);

test("normalizeArabic matches the shared fixtures", () => {
  for (const c of FIX.normalize_cases) {
    assert.equal(normalizeArabic(c.arabic), c.skeleton, c.name);
  }
});

test("fold space matches the shared fixtures", () => {
  for (const c of FIX.fold_cases) {
    assert.equal(latinFold(c.latin), c.latin_fold, `${c.name}: latin_fold`);
    assert.equal(
      arabicFold(c.skeleton),
      c.arabic_fold,
      `${c.name}: arabic_fold`,
    );
    assert.equal(
      foldsMatch(c.latin_fold, c.arabic_fold),
      c.match,
      `${c.name}: match`,
    );
  }
});

test("skeleton cases agree end-to-end (vowelled arabic -> skeleton)", () => {
  for (const c of FIX.bw2ar_cases) {
    const expected = FIX.normalize_cases.find((n) => n.name === c.name);
    if (expected)
      assert.equal(normalizeArabic(c.ar), expected.skeleton, c.name);
  }
});

test("folds never match empty", () => {
  assert.equal(foldsMatch("", ""), false);
  assert.equal(foldsMatch("nfs", ""), false);
});
