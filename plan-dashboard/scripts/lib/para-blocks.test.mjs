/**
 * para-blocks.test.mjs — the JS half of the prose-block mirror pair.
 *
 * Runs the SHARED fixtures that scripts/podcast/tests/test_para_blocks.py runs
 * too. The stake: the Python aligner writes `_system/arabic-alignment.json` keyed
 * by these fingerprints and the Composer looks paragraphs up by them, so the two
 * halves disagreeing does not show LESS Arabic — it shows the WRONG Arabic above
 * a paragraph, confidently.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import {
  proseBlocks,
  paraFingerprint,
  fingerprints,
  blocksFingerprint,
} from "./para-blocks.mjs";

const FX = JSON.parse(
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "para-blocks.fixtures.json"),
    "utf8",
  ),
);

test("mirror: proseBlocks matches the shared fixtures", () => {
  for (const c of FX.proseBlocks)
    assert.deepEqual(proseBlocks(c.in), c.out, c._why ?? c.in);
});

test("mirror: paraFingerprint matches the shared fixtures", () => {
  for (const c of FX.paraFingerprint)
    assert.equal(
      paraFingerprint(c.a) === paraFingerprint(c.b),
      c.equal,
      c._why ?? c.a,
    );
});

test("mirror: blocksFingerprint matches the shared fixtures", () => {
  for (const c of FX.blocksFingerprint)
    assert.equal(
      blocksFingerprint(c.a) === blocksFingerprint(c.b),
      c.equal,
      c._why ?? c.a,
    );
});

test("a fingerprint is a short stable hex name", () => {
  const fp = paraFingerprint("The Master replied.");
  assert.match(fp, /^[0-9a-f]{16}$/);
  assert.equal(fp, paraFingerprint("The Master replied."));
});

test("fingerprints() lines up one-to-one with proseBlocks()", () => {
  const body = "One.\n\n> quoted\n\nTwo.\n\n## head\n\nThree.";
  assert.equal(fingerprints(body).length, proseBlocks(body).length);
  assert.equal(fingerprints(body).length, 3);
});
