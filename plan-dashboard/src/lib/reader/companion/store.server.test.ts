/**
 * store.server.test.ts — the two properties the machine-filed note depends on.
 *
 * The student-reader pass files notes directly rather than into a review queue
 * (Asif, 2026-08-06), which puts two requirements on this store that a human's
 * own note never exercised:
 *
 *   1. A caller-supplied id must survive CREATION. The pass derives each id from
 *      the chapter and the sentence the note anchors to, so re-running it over
 *      unchanged prose updates the note it wrote last time. `randomUUID()` on
 *      every create made the pass additive forever — a second run doubling every
 *      chapter's notes. That IS the "deterministic, not random" requirement; it
 *      is not a detail of it.
 *
 *   2. `review` must round-trip, and its ABSENCE must mean kept. Every note
 *      written before this field existed, and every note a person types, has no
 *      `review` — none of them are awaiting approval, so absence cannot mean
 *      "proposed" or the whole existing set would suddenly ask to be reviewed.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = mkdtempSync(join(tmpdir(), "companion-store-"));
process.env.PODCAST_FACTORY_ROOT = root;
const slug = "test-book";
const bookDir = join(root, "content", "Islamic", slug);
mkdirSync(join(bookDir, "_system"), { recursive: true });
writeFileSync(
  join(bookDir, "_system", "series-config.yaml"),
  `slug: ${slug}\n`,
);

const { upsertNote, readChapter, deleteNote } = await import("./store.server");

const CH = "1-a-chapter";

test("a caller-supplied id is honoured on create, so a re-run updates", () => {
  const first = upsertNote(slug, CH, {
    id: "student:1-a-chapter:abc123",
    kind: "explanation",
    body: "The book asserts this and does not say why.",
    quote: "does not say why",
    review: "proposed",
  });
  assert.equal(first.note.id, "student:1-a-chapter:abc123");

  // The same pass, run again over unchanged prose.
  const second = upsertNote(slug, CH, {
    id: "student:1-a-chapter:abc123",
    kind: "explanation",
    body: "The book asserts this and does not say why.",
    quote: "does not say why",
    review: "proposed",
  });

  assert.equal(second.note.id, "student:1-a-chapter:abc123");
  assert.equal(
    readChapter(slug, CH).notes.length,
    1,
    "a second run must UPDATE the note, never file a duplicate beside it",
  );
});

test("a note written without an id still gets one", () => {
  const { note } = upsertNote(slug, "2-another", {
    kind: "note",
    body: "Something a person typed themselves.",
  });
  assert.ok(note.id.length > 0);
  assert.equal(
    note.review,
    undefined,
    "a human's own note is not awaiting review",
  );
});

test("review round-trips and survives an edit that does not mention it", () => {
  upsertNote(slug, "3-third", {
    id: "student:3-third:x",
    kind: "explanation",
    body: "Proposed by the pass.",
    review: "proposed",
  });

  // Accepting it — the only field the caller means to change.
  const kept = upsertNote(slug, "3-third", {
    id: "student:3-third:x",
    kind: "explanation",
    body: "Proposed by the pass.",
    review: "kept",
  });
  assert.equal(kept.note.review, "kept");

  // A later edit that says nothing about review must not un-accept it.
  const edited = upsertNote(slug, "3-third", {
    id: "student:3-third:x",
    kind: "explanation",
    body: "Proposed by the pass, lightly reworded.",
  });
  assert.equal(edited.note.review, "kept");
});

test("deleting a proposed note removes it — the other half of accept-or-delete", () => {
  upsertNote(slug, "4-fourth", {
    id: "student:4-fourth:y",
    kind: "question",
    body: "What supports this?",
    review: "proposed",
  });
  deleteNote(slug, "4-fourth", "student:4-fourth:y");
  assert.equal(readChapter(slug, "4-fourth").notes.length, 0);
});
