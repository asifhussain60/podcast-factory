/**
 * The paragraph lit up must be the paragraph being spoken.
 *
 * The index that finds a paragraph is produced by the pipeline and the document
 * it indexes into is built by the editor — two counts from two sides. So the
 * index locates and the text confirms, and a poor match paints nothing. These
 * pin the confirming half, which is the half that keeps a wrong highlight off a
 * page of scripture.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { blockMatches, resolveBlock } from "./read-along-decos";

const SPOKEN =
  "Hasad is probably one of the most serious diseases. There is a difference of opinion among scholars about which disease is the root of all others.";

test("the paragraph the cue came from is recognised", () => {
  assert.equal(blockMatches(SPOKEN, SPOKEN), true);
});

test("a paragraph missing its Arabic still matches the cue", () => {
  // The cue's text had its Arabic script stripped on the way to a speech
  // engine, so it is never character-identical to what the editor holds.
  const inEditor =
    "Hasad حَسَدٌ is probably one of the most serious diseases. There is a difference of opinion among scholars about which disease is the root of all others.";
  assert.equal(blockMatches(inEditor, SPOKEN), true);
});

test("a different paragraph of the same chapter is refused", () => {
  const other =
    "According to the scholars, envy was the first manifestation of disobedience in the heavenly realm, because nothing prevented that refusal except pride.";
  assert.equal(blockMatches(other, SPOKEN), false);
});

test("an empty paragraph is refused", () => {
  assert.equal(blockMatches("", SPOKEN), false);
});

test("a cue with nothing comparable is accepted on the index alone", () => {
  // A line of pure Arabic or a bare numeral gives nothing to check against, and
  // refusing every one would blank the highlight through passages of scripture —
  // exactly where a reader most wants to keep their place.
  assert.equal(blockMatches("قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ", "١٤٤"), true);
});

test("short words alone are not evidence", () => {
  // "the", "and", "of" agree between any two English paragraphs.
  assert.equal(
    blockMatches("the and of is to a in on", "the and of is to a in on but"),
    true,
  );
  assert.equal(
    blockMatches("the cat sat on the mat and it was fine", SPOKEN),
    false,
  );
});

// ── Finding the paragraph when the two counts disagree ───────────────────────
// The cue's index counts the chapter's markdown blocks; the editor counts
// document nodes, and it holds nodes the markdown split never produced. On
// `purification-of-the-heart` that is 102 nodes against 94 timed blocks by the
// end of one chapter — and the index alone was right for 8 of 94. Searching
// outward from it, and confirming by text, made it 94 of 94.

/** The smallest thing shaped like a ProseMirror doc that resolveBlock reads. */
function doc(...texts: string[]) {
  return {
    childCount: texts.length,
    child: (i: number) => ({ textContent: texts[i] }),
  } as unknown as Parameters<typeof resolveBlock>[0];
}

test("the hint is used when it is right", () => {
  assert.equal(resolveBlock(doc("alpha beta gamma", SPOKEN), 1, SPOKEN), 1);
});

test("a paragraph the editor inserted shifts the hint, and it is still found", () => {
  // A figure the markdown split never counted sits at index 1, pushing the
  // paragraph one place down from where the cue says it is.
  const d = doc("alpha beta gamma", "IMAGE", SPOKEN, "delta epsilon zeta");
  assert.equal(resolveBlock(d, 1, SPOKEN), 2);
});

test("a paragraph before the hint is found too", () => {
  assert.equal(resolveBlock(doc(SPOKEN, "alpha beta gamma"), 1, SPOKEN), 0);
});

test("nothing is found when nothing matches, and nothing is lit", () => {
  assert.equal(resolveBlock(doc("alpha beta", "gamma delta"), 0, SPOKEN), -1);
});

test("an empty document finds nothing rather than throwing", () => {
  assert.equal(resolveBlock(doc(), 0, SPOKEN), -1);
});

test("the search does not roam the whole chapter", () => {
  // Far enough away and the answer is refused, because a paragraph found
  // halfway across a chapter from where it was said is a confident wrong
  // answer, not a rescued one.
  const far = doc(
    ...Array.from({ length: 60 }, (_, i) => `filler ${i} words here`),
    SPOKEN,
  );
  assert.equal(resolveBlock(far, 0, SPOKEN), -1);
});
