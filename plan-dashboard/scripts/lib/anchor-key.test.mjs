/**
 * anchor-key.test.mjs — the JS half of the anchorKey mirror pair.
 *
 * The Python half is `scripts/podcast/tests/test_book_edits.py`. Both read the
 * SAME fixture file, so an implementation change on either side that is not
 * matched on the other fails a test instead of silently orphaning every saved
 * Composer edit — which is the one failure mode here that loses human work
 * without saying anything.
 *
 * Run: node --test plan-dashboard/scripts/lib/anchor-key.test.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { anchorKey } from "./anchor-key.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const { cases } = JSON.parse(
  readFileSync(join(HERE, "anchor-key.fixtures.json"), "utf8"),
);

test("anchorKey matches the shared fixtures", () => {
  assert.ok(cases.length > 0, "fixture file is empty");
  for (const { in: input, out } of cases) {
    assert.equal(anchorKey(input), out, JSON.stringify(input));
  }
});

test("anchorKey strips Arabic-Indic heading numerals like Python does", () => {
  // JavaScript's \d is ASCII-only and Python's is Unicode-aware, so an explicit
  // digit class is the only way the two agree. `## ١. Patience` normalized to
  // `patience` in Python and `١. patience` here until 2026-07-20.
  assert.equal(anchorKey("## ١. Patience"), "patience");
  assert.equal(anchorKey("## ۵. Patience"), "patience");
});
