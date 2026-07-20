/**
 * book-fences.test.mjs — the FIRST coverage of the book.md rich-text round trip.
 * Run with:  node --test scripts/book-fences.test.mjs   (from plan-dashboard/)
 *
 * Guards the contract in src/lib/reader/book-fences.ts: the pipeline's machine
 * fences (editorial / bridge / study-summary) must survive an edit made in the
 * Book Composer, because `_book_voice.py` relies on them to shield asides from
 * re-voicing and `_book_augment._strip_existing_blocks` relies on them to
 * replace rather than stack asides on the next run.
 *
 * The module under test is TypeScript, but it is deliberately dependency-free
 * (pure string in / string out, no fs, no imports), so Node's built-in type
 * stripping runs it directly — no bundler in the test path.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { preserveFences, extractSpans } from "../src/lib/reader/book-fences.ts";

const ORIGINAL = [
  "Opening prose of the chapter.",
  "",
  "<!-- editorial:begin -->",
  "> **Editorial note (source-grounded).**",
  "> A grounding note for the reader.",
  "<!-- editorial:end -->",
  "",
  "Closing prose.",
].join("\n");

test("extractSpans finds a balanced fenced span", () => {
  const spans = extractSpans(ORIGINAL);
  assert.equal(spans.length, 1);
  assert.equal(spans[0].kind, "editorial");
  assert.ok(spans[0].inner.join(" ").includes("A grounding note"));
});

test("REGRESSION: markers that survive as bare text are restored to comments", () => {
  // Exactly what the TipTap serializer produces today: the .md-comment div is
  // parsed as a paragraph, so the marker comes back as a bare text line.
  const edited = [
    "Opening prose of the chapter, lightly edited.",
    "",
    "editorial:begin",
    "",
    "> **Editorial note (source-grounded).**",
    "> A grounding note for the reader.",
    "",
    "editorial:end",
    "",
    "Closing prose.",
  ].join("\n");

  const { body, restored, appended } = preserveFences(ORIGINAL, edited);

  assert.ok(body.includes("<!-- editorial:begin -->"), "begin fence restored");
  assert.ok(body.includes("<!-- editorial:end -->"), "end fence restored");
  assert.equal(restored, 2, "both markers restored");
  assert.equal(appended, 0, "nothing needed re-appending");
  assert.ok(
    !/^editorial:(begin|end)$/m.test(body),
    "no bare marker text left in the prose",
  );
  assert.ok(
    body.includes("lightly edited"),
    "the human's prose edit is preserved",
  );
  assert.equal(
    extractSpans(body).length,
    1,
    "exactly one span, not duplicated",
  );
});

test("markers lost entirely are re-wrapped around the surviving prose, in place", () => {
  const edited = [
    "Opening prose of the chapter.",
    "",
    "> **Editorial note (source-grounded).**",
    "> A grounding note for the reader.",
    "",
    "Closing prose.",
  ].join("\n");

  const { body, rewrapped, appended } = preserveFences(ORIGINAL, edited);

  assert.equal(rewrapped, 1, "span re-wrapped");
  assert.equal(appended, 0, "not appended — its prose was still present");
  assert.equal(extractSpans(body).length, 1, "span is whole again");
  // Position preserved: the aside still sits before the closing prose.
  assert.ok(
    body.indexOf("<!-- editorial:end -->") < body.indexOf("Closing prose."),
    "the aside keeps its original position",
  );
  assert.equal(
    (body.match(/A grounding note/g) || []).length,
    1,
    "content is not duplicated",
  );
});

test("a span deleted outright is re-appended rather than lost", () => {
  const edited = ["Opening prose.", "", "Closing prose."].join("\n");
  const { body, appended } = preserveFences(ORIGINAL, edited);

  assert.equal(appended, 1, "span re-appended");
  assert.equal(extractSpans(body).length, 1, "the aside is back and balanced");
  assert.ok(body.includes("A grounding note"), "its content is recovered");
});

test("an unbalanced marker is dropped, never written into book.md", () => {
  const edited = ["Prose.", "", "editorial:begin", "", "More prose."].join(
    "\n",
  );
  const { body, orphansDropped } = preserveFences("Prose.", edited);

  assert.equal(orphansDropped, 1, "the dangling begin is dropped");
  assert.ok(!body.includes("editorial:begin"), "no orphan marker survives");
  assert.ok(body.includes("More prose."), "prose is untouched");
});

test("bridge and study-summary fences get the same protection", () => {
  for (const kind of ["bridge", "study-summary"]) {
    const original = [
      "Prose.",
      "",
      `<!-- ${kind}:begin -->`,
      `> A ${kind} line.`,
      `<!-- ${kind}:end -->`,
    ].join("\n");
    const edited = [
      "Prose.",
      "",
      `${kind}:begin`,
      "",
      `> A ${kind} line.`,
      "",
      `${kind}:end`,
    ].join("\n");

    const { body } = preserveFences(original, edited);
    assert.ok(
      body.includes(`<!-- ${kind}:begin -->`),
      `${kind} begin restored`,
    );
    assert.ok(body.includes(`<!-- ${kind}:end -->`), `${kind} end restored`);
  }
});

test("a fence-free chapter is passed through untouched", () => {
  const original = "Just prose.\n\nMore prose.";
  const edited = "Just prose, edited.\n\nMore prose.";
  const { body, restored, rewrapped, appended } = preserveFences(
    original,
    edited,
  );
  assert.equal(body, edited, "byte-identical passthrough");
  assert.equal(restored + rewrapped + appended, 0, "no fence work done");
});
