/**
 * passage-match.test.ts — the matcher that decides whether an annotated passage
 * can be found at all.
 *
 * Every failure here is silent in production: the note is stored, the reader
 * looks for it, nothing lights up, and no error is raised anywhere. The cases
 * below are the ones that actually broke — a sentence split by an italic term,
 * a quote whose whitespace differs from the prose, and two paragraphs whose ends
 * would fuse into a match that is not in the text.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { flatten, findPassage, normalizeQuote } from "./passage-match";

/** Text laid out the way the DOM binding does: one coordinate block per chunk. */
function chunks(parts: { text: string; blockStart?: boolean }[]) {
  let at = 0;
  return parts.map((p) => {
    const chunk = { ...p, at };
    at += p.text.length + 1;
    return chunk;
  });
}

test("a passage inside one run of text is found whole", () => {
  const flat = flatten(
    chunks([{ text: "He sat there a while, weighing them." }]),
  );
  const ranges = findPassage(flat, "sat there a while");
  assert.equal(ranges.length, 1);
  assert.deepEqual(ranges[0], { chunk: 0, from: 3, to: 20 });
});

test("a passage split by inline markup comes back as one range per run", () => {
  // "the outward sense, the zahir, of the thing" — with `zahir` italicised.
  const flat = flatten(
    chunks([
      { text: "the outward sense, the ", blockStart: true },
      { text: "zahir" },
      { text: ", of the thing" },
    ]),
  );
  const ranges = findPassage(
    flat,
    "the outward sense, the zahir, of the thing",
  );
  assert.equal(ranges.length, 3, "one range per text run the passage crosses");
  assert.deepEqual(
    ranges.map((r) => r.chunk),
    [0, 1, 2],
  );
});

test("whitespace in the quote need not match the prose", () => {
  const flat = flatten(
    chunks([{ text: "a way that is\n  neither ambiguous" }]),
  );
  assert.equal(findPassage(flat, "a way that is neither ambiguous").length, 1);
});

test("two blocks never fuse into a passage that isn't there", () => {
  const flat = flatten(
    chunks([
      { text: "…the end of it.", blockStart: true },
      { text: "Next paragraph…", blockStart: true },
    ]),
  );
  assert.deepEqual(findPassage(flat, "of it.Next"), []);
  // The same words WITH the block break read as a space still match.
  assert.equal(findPassage(flat, "of it. Next paragraph").length, 2);
});

test("a passage that isn't in the text returns nothing", () => {
  const flat = flatten(chunks([{ text: "He sat there a while." }]));
  assert.deepEqual(findPassage(flat, "a sentence from another chapter"), []);
});

test("a quote too short to be a passage is never guessed at", () => {
  const flat = flatten(chunks([{ text: "the boy at the door" }]));
  assert.deepEqual(findPassage(flat, "the"), []);
});

test("matching ignores case", () => {
  const flat = flatten(chunks([{ text: "The Master and the Disciple" }]));
  assert.equal(findPassage(flat, "master AND the disciple").length, 1);
});

test("normalizeQuote collapses every run of whitespace", () => {
  assert.equal(normalizeQuote("  a \n b\t c "), "a b c");
});
