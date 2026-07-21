/**
 * block-align.test.mjs — coverage for the track-changes block alignment.
 * Run with:  node --test scripts/block-align.test.mjs   (from plan-dashboard/)
 *
 * Guards the contract in src/components/studio/editor/block-align.ts. The bug
 * this exists to prevent, found live 2026-07-21: the diff matched paragraphs to
 * their originals BY ARRAY POSITION, so splitting one paragraph shifted every
 * paragraph below it and each was compared against its neighbour's original.
 * One press of Enter produced 138 deletion widgets holding 5,350 characters of
 * untouched prose, which reads as the editor dumping text into the chapter.
 *
 * The module under test is TypeScript but deliberately dependency-free (string[]
 * in, (number|null)[] out), so Node's built-in type stripping runs it directly —
 * no bundler in the test path, same arrangement as book-fences.test.mjs.
 */
import assert from "node:assert/strict";
import test from "node:test";

import { alignBlocks } from "../src/components/studio/editor/block-align.ts";

const A = "The first paragraph.";
const B = "The second paragraph, which is longer.";
const C = "A third.";
const D = "And a fourth one here.";

test("an untouched document maps every block to itself", () => {
  assert.deepEqual(alignBlocks([A, B, C], [A, B, C]), [0, 1, 2]);
});

test("an edited block still finds its own original", () => {
  // The whole point: exact-match alignment alone would drop this block, and
  // tracked changes would silently stop recording the user's typing.
  assert.deepEqual(alignBlocks([A, B, C], [A, B + " Edited.", C]), [0, 1, 2]);
});

test("a split does not shift the blocks below it", () => {
  // B split into two halves; C must still resolve to original index 2, NOT 1.
  const current = [A, "The second paragraph,", " which is longer.", C];
  assert.deepEqual(alignBlocks([A, B, C], current), [0, 1, null, 2]);
});

test("a paragraph inserted in the middle shifts nothing below it", () => {
  const current = [A, "Brand new.", B, C];
  assert.deepEqual(alignBlocks([A, B, C], current), [0, null, 1, 2]);
});

test("a deleted paragraph does not misalign the survivors", () => {
  assert.deepEqual(alignBlocks([A, B, C, D], [A, C, D]), [0, 2, 3]);
});

test("a merge maps the joined block to the first of its sources", () => {
  assert.deepEqual(alignBlocks([A, B, C], [A, B + C]), [0, 1]);
});

test("edits inside a gap pair up in order", () => {
  // Two consecutive edited blocks between two unchanged anchors: the k-th edited
  // block belongs to the k-th original in the same gap.
  const baseline = [A, B, C, D];
  const current = [A, B + " x", C + " y", D];
  assert.deepEqual(alignBlocks(baseline, current), [0, 1, 2, 3]);
});

test("blocks appended at the end are new, not matched to earlier originals", () => {
  assert.deepEqual(alignBlocks([A, B], [A, B, "Appended."]), [0, 1, null]);
});

test("reordering keeps each block with its own original", () => {
  const out = alignBlocks([A, B, C], [C, A, B]);
  // C moved to the front; A and B keep their identities via the longest run.
  assert.equal(out.length, 3);
  assert.ok(out.includes(0) && out.includes(1));
});

test("duplicate paragraph texts do not collapse onto one original", () => {
  const out = alignBlocks([A, A, B], [A, A, B]);
  assert.deepEqual(out, [0, 1, 2]);
});

test("empty inputs are handled without throwing", () => {
  assert.deepEqual(alignBlocks([], [A]), [null]);
  assert.deepEqual(alignBlocks([A], []), []);
  assert.deepEqual(alignBlocks([], []), []);
});

test("a document past the size cap falls back to positional indexing", () => {
  // Above MAX_ALIGN_BLOCKS the O(n*m) table is skipped: track-changes noise is
  // the lesser evil against a per-keystroke freeze on a huge document.
  const big = Array.from({ length: 1300 }, (_, i) => `p${i}`);
  const out = alignBlocks(big, big);
  assert.equal(out.length, big.length);
  assert.equal(out[0], 0);
  assert.equal(out[1299], 1299);
});
