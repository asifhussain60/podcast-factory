/**
 * Pairing composed English paragraphs with the Arabic they came from.
 *
 * Two defects found on 2026-07-30, both of which reached Asif's screen as "the
 * Arabic is a lot more than the English paragraph beside it":
 *
 *   1. The Composer keyed the alignment into a `Map` by paragraph FINGERPRINT. A
 *      book of dialogue repeats its speech tags, so thirteen occurrences of "The
 *      Master replied:" shared one fingerprint and all thirteen rendered the LAST
 *      one's Arabic — 37 paragraphs book-wide pointing at the wrong source.
 *   2. Articulation splits one Arabic paragraph into several English ones, and the
 *      whole source was printed above each of them separately.
 *
 * The first is the dangerous one — it showed a reader the wrong text with no
 * outward sign — so most of what follows is about it.
 */
import { strict as assert } from "node:assert";
import { test } from "node:test";

import { alignmentGroups } from "./arabic-groups";
import type { AlignmentPair } from "./arabic-source";

const pair = (fp: string, ...src: number[]): AlignmentPair => ({
  fp,
  source_paras: src,
  confidence: "verified",
});

test("a repeated speech tag keeps its own source paragraph", () => {
  // The shape that broke: the same line three times, each translating a different
  // Arabic paragraph. Under the old fingerprint Map all three resolved to ¶9.
  const pairs = [
    pair("tag", 1),
    pair("body-a", 2),
    pair("tag", 5),
    pair("body-b", 6),
    pair("tag", 9),
  ];
  const keys = ["tag", "body-a", "tag", "body-b", "tag"];
  const groups = alignmentGroups(pairs, keys);
  assert.deepEqual(
    groups.map((g) => [g.start, g.pair.source_paras[0]]),
    [
      [0, 1],
      [1, 2],
      [2, 5],
      [3, 6],
      [4, 9],
    ],
  );
});

test("consecutive paragraphs from one source become a single group", () => {
  const pairs = [pair("a", 74), pair("b", 74), pair("c", 74), pair("d", 75)];
  const keys = ["a", "b", "c", "d"];
  const groups = alignmentGroups(pairs, keys);
  assert.equal(groups.length, 2);
  assert.deepEqual(
    { start: groups[0].start, end: groups[0].end },
    { start: 0, end: 2 },
  );
  assert.deepEqual(
    { start: groups[1].start, end: groups[1].end },
    { start: 3, end: 3 },
  );
});

test("the same source returning later is a NEW group, not an extension", () => {
  // Only CONSECUTIVE paragraphs group. A source that reappears after an interruption
  // starts again, or the bracket would be drawn around prose it does not cover.
  const pairs = [pair("a", 3), pair("b", 4), pair("c", 3)];
  const groups = alignmentGroups(pairs, ["a", "b", "c"]);
  assert.deepEqual(
    groups.map((g) => [g.start, g.end]),
    [
      [0, 0],
      [1, 1],
      [2, 2],
    ],
  );
});

test("a multi-paragraph source only groups when the whole list matches", () => {
  const pairs = [pair("a", 3, 4), pair("b", 3, 4), pair("c", 4)];
  const groups = alignmentGroups(pairs, ["a", "b", "c"]);
  assert.deepEqual(
    groups.map((g) => [g.start, g.end]),
    [
      [0, 1],
      [2, 2],
    ],
  );
});

test("an edited paragraph is dropped, not pointed at stale Arabic", () => {
  // The fingerprint's remaining job: the Composer rewrote paragraph 1, so its key no
  // longer matches what was aligned and it offers no control at all.
  const pairs = [pair("a", 1), pair("b", 2), pair("c", 3)];
  const groups = alignmentGroups(pairs, ["a", "EDITED", "c"]);
  assert.deepEqual(
    groups.map((g) => [g.start, g.pair.source_paras[0]]),
    [
      [0, 1],
      [2, 3],
    ],
  );
});

test("an edit in the middle of a run breaks the run rather than spanning it", () => {
  const pairs = [pair("a", 7), pair("b", 7), pair("c", 7)];
  const groups = alignmentGroups(pairs, ["a", "EDITED", "c"]);
  assert.deepEqual(
    groups.map((g) => [g.start, g.end]),
    [
      [0, 0],
      [2, 2],
    ],
  );
});

test("a length disagreement yields nothing at all", () => {
  // Positional indexing is only meaningful when the two sides describe the same
  // text. Mismatched, it would be confidently wrong — so it says nothing.
  assert.deepEqual(alignmentGroups([pair("a", 1), pair("b", 2)], ["a"]), []);
  assert.deepEqual(alignmentGroups([], []), []);
});
