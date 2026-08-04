import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  addBookmark,
  InvalidMarkError,
  listeningFor,
  markCounts,
  marksFor,
  progressForAll,
  removeAnnotation,
  removeBookmark,
  saveAnnotation,
  setListening,
  setProgress,
} from "~/server/marks.server";
import { createTestDb, type TestDb } from "./d1";

/**
 * What a reader accumulates, and what must survive.
 *
 * These tables are the first per-person state in the database, and the two ways
 * they can fail badly are both about DURABILITY rather than about correctness in
 * the moment: a re-publish quietly erasing everyone's highlights, and one
 * person's notes appearing under another person's account. Both are tested here
 * against the real migrations.
 */

const MIGRATIONS = ["0001_auth", "0002_access", "0004_catalog", "0006_reader_state"];

const SLUG = "ayyuhal-walad";
const CHAPTER = "introduction-to-the-book";
const NOW = "2026-08-03T12:00:00.000Z";
const LATER = "2026-08-03T13:00:00.000Z";

const READER = "reader@example.com";
const OTHER = "other@example.com";

const uuid = (n: number) => `0000000${n}-0000-4000-a000-000000000000`.slice(-36);

let t: TestDb;

beforeEach(() => {
  t = createTestDb(MIGRATIONS);
  t.exec(`
    INSERT INTO content_unit (slug, bucket, title, kind, sort_order, status)
      VALUES ('${SLUG}', 'Islamic', 'Ayyuha al-Walad', 'book', 1, 'published');
    INSERT INTO chapter (slug, anchor_key, idx, title, html, word_count)
      VALUES ('${SLUG}', '${CHAPTER}', 1, 'Introduction', '<p>x</p>', 200);
  `);
});

afterEach(() => t.close());

const annotate = (email: string, over: Record<string, unknown> = {}) =>
  saveAnnotation(
    t.db,
    email,
    SLUG,
    {
      id: uuid(1),
      anchorKey: CHAPTER,
      blockIndex: 0,
      startOffset: 0,
      endOffset: 11,
      quote: "This is the",
      prefix: "",
      colour: "gold",
      ...over,
    },
    NOW,
  );

describe("a highlight survives the book being re-published", () => {
  it("is still there after the chapter row is deleted and re-inserted", async () => {
    await annotate(READER);

    // Exactly what scripts/podcast/publish_to_listener.py does on every
    // re-publish. If `annotation` ever grows a foreign key to `chapter` with a
    // cascade, this is the test that fails — and the failure is the whole
    // library losing every highlight the next time a book is re-composed.
    t.exec(`
      DELETE FROM chapter WHERE slug = '${SLUG}';
      INSERT INTO chapter (slug, anchor_key, idx, title, html, word_count)
        VALUES ('${SLUG}', '${CHAPTER}', 1, 'Introduction', '<p>rewritten</p>', 210);
    `);

    const marks = await marksFor(t.db, READER, SLUG);
    expect(marks.annotations).toHaveLength(1);
    expect(marks.annotations[0].quote).toBe("This is the");
  });
});

describe("one reader's marks are their own", () => {
  it("does not show another reader's highlights in the same book", async () => {
    await annotate(READER);
    await annotate(OTHER, { id: uuid(2), quote: "different words" });

    const mine = await marksFor(t.db, READER, SLUG);
    expect(mine.annotations.map((a) => a.quote)).toEqual(["This is the"]);
  });

  it("does not let one reader delete another's highlight by guessing its id", async () => {
    await annotate(OTHER);
    // Same id, different person. Client-generated ids are not secrets, so the
    // scoping in the WHERE clause is what actually protects the row.
    await removeAnnotation(t.db, READER, SLUG, uuid(1), LATER);

    const theirs = await marksFor(t.db, OTHER, SLUG);
    expect(theirs.annotations).toHaveLength(1);
  });

  it("keeps progress separate", async () => {
    await setProgress(t.db, READER, SLUG, { anchorKey: CHAPTER, fraction: 0.5, chaptersDone: 2 }, NOW);
    await setProgress(t.db, OTHER, SLUG, { anchorKey: CHAPTER, fraction: 0.9, chaptersDone: 7 }, NOW);

    expect((await progressForAll(t.db, READER))[SLUG].fraction).toBe(0.5);
    expect((await progressForAll(t.db, OTHER))[SLUG].fraction).toBe(0.9);
  });
});

describe("Gmail folding runs end to end", () => {
  it("gives a dotted address and its canonical form one set of notes", async () => {
    await annotate("Read.Er+books@gmail.com", { id: uuid(3) });

    // Written under one spelling, read under another. Without normalizeEmail on
    // both sides these are two accounts holding two separate sets of notes, and
    // nothing tells the reader which one they are looking at.
    const marks = await marksFor(t.db, "reader@googlemail.com", SLUG);
    expect(marks.annotations).toHaveLength(1);
  });

  it("does not fold dots on a domain that does not fold them", async () => {
    await annotate("read.er@example.com", { id: uuid(4) });
    const marks = await marksFor(t.db, "reader@example.com", SLUG);
    expect(marks.annotations).toHaveLength(0);
  });
});

describe("writes are idempotent, because the client replays them", () => {
  it("re-sending the same highlight does not duplicate it", async () => {
    await annotate(READER);
    await annotate(READER);
    expect((await marksFor(t.db, READER, SLUG)).annotations).toHaveLength(1);
  });

  it("add, remove and add again ends with the mark present", async () => {
    // An outbox flushed twice replays this whole sequence. The last statement
    // has to win rather than collide with the primary key.
    await addBookmark(
      t.db,
      READER,
      SLUG,
      { id: uuid(5), anchorKey: CHAPTER, blockIndex: 3, label: "A passage" },
      NOW,
    );
    await removeBookmark(t.db, READER, SLUG, uuid(5), LATER);
    await addBookmark(
      t.db,
      READER,
      SLUG,
      { id: uuid(5), anchorKey: CHAPTER, blockIndex: 3, label: "A passage" },
      LATER,
    );

    expect((await marksFor(t.db, READER, SLUG)).bookmarks).toHaveLength(1);
  });

  it("a removed highlight stays removed when a stale device re-sends the delete", async () => {
    await annotate(READER);
    await removeAnnotation(t.db, READER, SLUG, uuid(1), LATER);
    await removeAnnotation(t.db, READER, SLUG, uuid(1), LATER);
    expect((await marksFor(t.db, READER, SLUG)).annotations).toHaveLength(0);
  });

  it("progress is last-writer-wins", async () => {
    await setProgress(t.db, READER, SLUG, { anchorKey: CHAPTER, fraction: 0.9, chaptersDone: 4 }, NOW);
    await setProgress(t.db, READER, SLUG, { anchorKey: CHAPTER, fraction: 0.2, chaptersDone: 1 }, LATER);
    expect((await progressForAll(t.db, READER))[SLUG].fraction).toBe(0.2);
  });
});

describe("a note is part of its highlight", () => {
  it("is saved and read back through the same record", async () => {
    await annotate(READER, { note: "Worth returning to." });
    const marks = await marksFor(t.db, READER, SLUG);
    expect(marks.annotations[0].note).toBe("Worth returning to.");
    expect(marks.annotations[0].colour).toBe("gold");
  });

  it("recolouring keeps the note", async () => {
    await annotate(READER, { note: "Kept." });
    await annotate(READER, { note: "Kept.", colour: "sky" });
    const marks = await marksFor(t.db, READER, SLUG);
    expect(marks.annotations[0].colour).toBe("sky");
    expect(marks.annotations[0].note).toBe("Kept.");
  });

  it("stores an empty note as absent rather than as an empty string", async () => {
    await annotate(READER, { note: "   " });
    expect((await marksFor(t.db, READER, SLUG)).annotations[0].note).toBeNull();
  });
});

describe("bad input is refused rather than stored", () => {
  it("rejects an id that is not a uuid", async () => {
    await expect(annotate(READER, { id: "../../etc/passwd" })).rejects.toBeInstanceOf(
      InvalidMarkError,
    );
  });

  it("rejects a colour the schema does not allow", async () => {
    await expect(annotate(READER, { colour: "chartreuse" })).rejects.toBeInstanceOf(
      InvalidMarkError,
    );
  });

  it("rejects an empty selection", async () => {
    await expect(annotate(READER, { startOffset: 5, endOffset: 5 })).rejects.toBeInstanceOf(
      InvalidMarkError,
    );
  });

  it("rejects a quote long enough to be an attack rather than a passage", async () => {
    await expect(annotate(READER, { quote: "x".repeat(5000) })).rejects.toBeInstanceOf(
      InvalidMarkError,
    );
  });
});

describe("listening position", () => {
  it("is keyed by episode, not by the media file", async () => {
    // The point of the whole table: `media_asset.key` changes when audio is
    // re-uploaded, and the old localStorage map keyed on it, so a re-upload
    // silently lost everyone's place.
    await setListening(t.db, READER, SLUG, { number: 3, seconds: 742 }, NOW);
    expect(await listeningFor(t.db, READER, SLUG)).toEqual({ 3: 742 });
  });

  it("advances rather than duplicating", async () => {
    await setListening(t.db, READER, SLUG, { number: 3, seconds: 100 }, NOW);
    await setListening(t.db, READER, SLUG, { number: 3, seconds: 900 }, LATER);
    expect(await listeningFor(t.db, READER, SLUG)).toEqual({ 3: 900 });
  });
});

describe("counts for the library card", () => {
  it("counts live marks per book and omits deleted ones", async () => {
    await annotate(READER);
    await addBookmark(
      t.db,
      READER,
      SLUG,
      { id: uuid(6), anchorKey: CHAPTER, blockIndex: 0, label: "here" },
      NOW,
    );
    await annotate(READER, { id: uuid(7), quote: "gone soon" });
    await removeAnnotation(t.db, READER, SLUG, uuid(7), LATER);

    expect(await markCounts(t.db, READER)).toEqual({ [SLUG]: { notes: 1, bookmarks: 1 } });
  });

  it("is empty for a reader who has marked nothing", async () => {
    expect(await markCounts(t.db, OTHER)).toEqual({});
  });
});
