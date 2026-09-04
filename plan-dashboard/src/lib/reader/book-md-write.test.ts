/**
 * book-md-write.test.ts — the sole writer into `book/book.md`.
 *
 * The first test under `src/`. Until 2026-07-21 `npm test` globbed only
 * `scripts/**\/*.test.mjs`, so this function — which rewrites a chapter of a book
 * that is being published — had no test, and neither did the sidecar write that is
 * the only reason a Composer edit survives the next compose.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { writeChapterBody } from "./book-md-write.ts";

const BOOK =
  "# The Book\n\n## 1. On Knowledge\n\nPipeline prose for one.\n\n## 2. On Patience\n\nPipeline prose for two.\n";

function makeBook(md = BOOK): string {
  const dir = mkdtempSync(join(tmpdir(), "book-md-write-"));
  mkdirSync(join(dir, "book"), { recursive: true });
  mkdirSync(join(dir, "_system"), { recursive: true });
  writeFileSync(join(dir, "book", "book.md"), md, "utf8");
  return dir;
}

function sidecar(dir: string) {
  return JSON.parse(
    readFileSync(join(dir, "_system", "composer-edits.json"), "utf8"),
  );
}

test("it replaces one chapter body and leaves the others byte-identical", () => {
  const dir = makeBook();
  const result = writeChapterBody(
    dir,
    "on knowledge",
    "The author's own sentence.",
  );
  assert.equal(result.ok, true);
  const out = readFileSync(join(dir, "book", "book.md"), "utf8");
  assert.match(out, /## 1\. On Knowledge\n\nThe author's own sentence\./);
  assert.match(out, /## 2\. On Patience\n\nPipeline prose for two\./);
  assert.equal(out.includes("Pipeline prose for one."), false);
});

test("it records the sidecar entry the pipeline replays", () => {
  // book.md alone is not durable: compose regenerates its layers every run.
  const dir = makeBook();
  writeChapterBody(dir, "on patience", "Patience, in the author's own words.");
  const data = sidecar(dir);
  assert.equal(data.edits.length, 1);
  assert.equal(data.edits[0].chapter_key, "on patience");
  assert.equal(data.edits[0].body_md, "Patience, in the author's own words.");
});

test("base_fingerprint is quoted from the pipeline stamp, never hashed here", () => {
  // Hashing the live body here was the bug: it carries the introduction and the
  // comprehension bridges, and the replay compares against the composed body from
  // before either is injected — so every such chapter reported a conflict forever.
  const dir = makeBook();
  writeFileSync(
    join(dir, "_system", "composer-base.json"),
    JSON.stringify({ chapters: { "on knowledge": "deadbeefdeadbeef" } }),
    "utf8",
  );
  writeChapterBody(dir, "on knowledge", "The author's own sentence.");
  assert.equal(sidecar(dir).edits[0].base_fingerprint, "deadbeefdeadbeef");
});

test("a missing stamp records an empty fingerprint, which means unknown", () => {
  const dir = makeBook();
  writeChapterBody(dir, "on knowledge", "The author's own sentence.");
  assert.equal(sidecar(dir).edits[0].base_fingerprint, "");
});

test("an unreadable sidecar is refused, not silently replaced", () => {
  // Returning "no edits" and writing that back is how one truncated file used to
  // discard every edit the author had ever made.
  const dir = makeBook();
  writeChapterBody(dir, "on knowledge", "worth keeping");
  writeFileSync(
    join(dir, "_system", "composer-edits.json"),
    '{"edits": [{"chap',
    "utf8",
  );
  const result = writeChapterBody(dir, "on patience", "new");
  assert.equal(result.ok, true); // book.md is still saved — that is what the author sees
  assert.equal(result.sidecar?.ok, false); // ...but they are told the edit is not durable
  assert.equal(
    readFileSync(join(dir, "_system", "composer-edits.json"), "utf8"),
    '{"edits": [{"chap',
  );
});

test("the sidecar is recorded BEFORE book.md, so a failed write loses nothing", () => {
  // The two writes are not one operation. Whichever runs second, a crash between
  // them leaves the book in one of two states, and only one of them is
  // recoverable: a sidecar entry not yet in book.md is replayed into place by the
  // next compose, while an edit in book.md that no sidecar records is discarded by
  // that same compose, silently. So the sidecar goes first.
  const dir = makeBook();
  chmodSync(join(dir, "book", "book.md"), 0o444); // book.md write will fail
  assert.throws(() =>
    writeChapterBody(dir, "on knowledge", "The author's own sentence."),
  );
  chmodSync(join(dir, "book", "book.md"), 0o644);
  const data = sidecar(dir);
  assert.equal(data.edits.length, 1);
  assert.equal(data.edits[0].body_md, "The author's own sentence.");
});

test("an unknown chapter key is refused rather than written somewhere", () => {
  const dir = makeBook();
  const result = writeChapterBody(
    dir,
    "a chapter that was renamed",
    "orphan text",
  );
  assert.equal(result.ok, false);
  assert.equal(readFileSync(join(dir, "book", "book.md"), "utf8"), BOOK);
});

test("it takes a one-time backup before the first write", () => {
  const dir = makeBook();
  writeChapterBody(dir, "on knowledge", "first");
  writeChapterBody(dir, "on knowledge", "second");
  assert.equal(readFileSync(join(dir, "book", "book.md.bak"), "utf8"), BOOK);
});

// ─── the edition's introduction is apparatus, not an editable chapter ─────────
const BOOK_WITH_INTRO = [
  "# The Book",
  "",
  "<!-- edition-intro:begin -->",
  "## Introduction",
  "",
  "The editor's orientation to the work.",
  "<!-- edition-intro:end -->",
  "",
  "## 1. On Knowledge",
  "",
  "Pipeline prose for one.",
  "",
  "## 2. On Patience",
  "",
  "Pipeline prose for two.",
  "",
].join("\n");

test("the fenced introduction cannot be written as a chapter", () => {
  // Its `## Introduction` heading lives inside the edition-intro span, and the
  // pipeline strips and re-authors that span on every compose — so an edit
  // recorded against it could never survive. Refusing is the honest answer.
  const dir = makeBook(BOOK_WITH_INTRO);
  const result = writeChapterBody(
    dir,
    "introduction",
    "A rewrite of the front matter.",
  );
  assert.equal(result.ok, false);
  assert.equal(
    readFileSync(join(dir, "book", "book.md"), "utf8"),
    BOOK_WITH_INTRO,
  );
});

test("real chapters around the introduction still resolve", () => {
  const dir = makeBook(BOOK_WITH_INTRO);
  const result = writeChapterBody(
    dir,
    "on knowledge",
    "The author's own sentence.",
  );
  assert.equal(result.ok, true);
  const out = readFileSync(join(dir, "book", "book.md"), "utf8");
  assert.match(out, /## 1\. On Knowledge\n\nThe author's own sentence\./);
  assert.match(out, /<!-- edition-intro:begin -->/); // apparatus untouched
});
