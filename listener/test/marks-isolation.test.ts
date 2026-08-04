import { describe, expect, it } from "vitest";

import {
  addBookmark,
  listeningFor,
  markCounts,
  marksFor,
  progressForAll,
  removeAnnotation,
  removeBookmark,
  saveAnnotation,
  setListening,
  setProgress,
} from "../app/server/marks.server";
import { createTestDb, type TestDb } from "./d1";

/**
 * WHOSE MARKS ARE THESE — every operation, both directions.
 *
 * A reader's highlights, notes, bookmarks and reading position are the most
 * private thing this application stores, and they are keyed on an email that the
 * caller does not supply: every route passes `viewer.email`, never a value from
 * the request. That makes the routes the first line and these functions the
 * second, and this file tests the second — against real SQLite running the real
 * migrations, so a missing WHERE clause fails here rather than in production.
 *
 * Two properties, exhaustively:
 *
 *   READS   Every reader returns only the caller's own rows. Asked for one
 *           person, another person's marks are absent — not filtered out
 *           afterwards, absent.
 *
 *   WRITES  Every mutation refuses to touch a row it does not own, INCLUDING the
 *           upserts. That last word is why this file exists: `bookmark.id` and
 *           `annotation.id` are CLIENT-generated primary keys, so a conflict can
 *           land on somebody else's row, and until 2026-08-04 the `DO UPDATE`
 *           had no owner check — one reader could rewrite another's note, in a
 *           book they could not open. Six of the cases below are that bug.
 *
 * God mode is the other half and it is deliberately not an exception here: the
 * administrator reads another person's marks by SIMULATING them, at which point
 * `viewer.email` is that person and these functions are asked the ordinary
 * question. There is no admin branch in this module to get wrong — the last case
 * proves the route to everyone's data exists without one.
 */

const MINE = "reader@example.com";
const THEIRS = "other@example.com";
const BOOK = "book-a";
const OTHER_BOOK = "book-b";

const ID_MINE = "11111111-1111-4111-8111-111111111111";
const ID_THEIRS = "22222222-2222-4222-8222-222222222222";

const NOW = "2026-08-04T12:00:00Z";
const LATER = "2026-08-04T13:00:00Z";

/** Both people, with one of everything each, in two different books. */
async function seed(): Promise<TestDb> {
  const test = createTestDb(["0001_auth", "0002_access", "0004_catalog", "0006_reader_state"]);

  await saveAnnotation(
    test.db,
    MINE,
    BOOK,
    {
      id: ID_MINE,
      anchorKey: "one",
      blockIndex: 1,
      startOffset: 0,
      endOffset: 5,
      quote: "mine",
      colour: "gold",
      note: "my own note",
    },
    NOW,
  );
  await saveAnnotation(
    test.db,
    THEIRS,
    OTHER_BOOK,
    {
      id: ID_THEIRS,
      anchorKey: "one",
      blockIndex: 1,
      startOffset: 0,
      endOffset: 6,
      quote: "theirs",
      colour: "sage",
      note: "a private thought",
    },
    NOW,
  );

  await addBookmark(test.db, MINE, BOOK, { id: ID_MINE, anchorKey: "one", blockIndex: 1, label: "mine" }, NOW);
  await addBookmark(
    test.db,
    THEIRS,
    OTHER_BOOK,
    { id: ID_THEIRS, anchorKey: "one", blockIndex: 2, label: "theirs" },
    NOW,
  );

  await setProgress(test.db, MINE, BOOK, { anchorKey: "one", fraction: 0.1, chaptersDone: 1 }, NOW);
  await setProgress(test.db, THEIRS, OTHER_BOOK, { anchorKey: "one", fraction: 0.9, chaptersDone: 9 }, NOW);
  await setListening(test.db, MINE, BOOK, { number: 1, seconds: 10 }, NOW);
  await setListening(test.db, THEIRS, OTHER_BOOK, { number: 1, seconds: 900 }, NOW);

  return test;
}

/** One person's annotation row, straight from the table, whatever it now says. */
async function rowOf(test: TestDb, id: string) {
  return test.db
    .prepare(`SELECT user_email, slug, quote, note, colour, deleted_at FROM annotation WHERE id = ?1`)
    .bind(id)
    .first<{
      user_email: string;
      slug: string;
      quote: string;
      note: string | null;
      colour: string;
      deleted_at: string | null;
    }>();
}

describe("reading somebody else's marks", () => {
  it("does not return them from the chapter reader", async () => {
    const test = await seed();
    try {
      const mine = await marksFor(test.db, MINE, BOOK);
      expect(mine.annotations.map((a) => a.id)).toEqual([ID_MINE]);
      expect(mine.bookmarks.map((b) => b.id)).toEqual([ID_MINE]);
      expect(JSON.stringify(mine)).not.toContain("a private thought");
    } finally {
      test.close();
    }
  });

  it("returns nothing at all for a book that is somebody else's", async () => {
    const test = await seed();
    try {
      // MINE has no rows in OTHER_BOOK. THEIRS does. Asking as MINE must be
      // empty rather than "their rows, filtered".
      const mine = await marksFor(test.db, MINE, OTHER_BOOK);
      expect(mine.annotations).toEqual([]);
      expect(mine.bookmarks).toEqual([]);
      expect(mine.progress).toBeNull();
      expect(mine.listening).toEqual({});
    } finally {
      test.close();
    }
  });

  it("does not leak through the whole-library progress map", async () => {
    const test = await seed();
    try {
      expect(Object.keys(await progressForAll(test.db, MINE))).toEqual([BOOK]);
      expect(Object.keys(await progressForAll(test.db, THEIRS))).toEqual([OTHER_BOOK]);
    } finally {
      test.close();
    }
  });

  it("does not leak through the per-book counts on the library page", async () => {
    const test = await seed();
    try {
      expect(Object.keys(await markCounts(test.db, MINE))).toEqual([BOOK]);
      expect(await markCounts(test.db, THEIRS)).toHaveProperty(OTHER_BOOK);
    } finally {
      test.close();
    }
  });

  it("does not leak listening position", async () => {
    const test = await seed();
    try {
      expect(await listeningFor(test.db, MINE, OTHER_BOOK)).toEqual({});
      expect(await listeningFor(test.db, THEIRS, OTHER_BOOK)).toEqual({ 1: 900 });
    } finally {
      test.close();
    }
  });

  it("folds a Gmail address to one person, and does not fold anyone else's", async () => {
    // Marks key on the same folded form grants do, so the two cannot disagree
    // about who someone is. The folding is Gmail-ONLY on purpose: on a Workspace
    // domain `first.last@` and `firstlast@` can be two different people, and
    // merging them would hand one person's private notes to another.
    const test = await seed();
    try {
      const gmail = "a.reader@gmail.com";
      await saveAnnotation(
        test.db,
        gmail,
        BOOK,
        {
          id: "33333333-3333-4333-8333-333333333333",
          anchorKey: "one",
          blockIndex: 1,
          startOffset: 0,
          endOffset: 4,
          quote: "gmail",
          colour: "gold",
        },
        NOW,
      );

      // Same person, written three ways.
      for (const written of ["a.reader@gmail.com", "AReader@Gmail.com", "a.reader+book@gmail.com"]) {
        expect((await marksFor(test.db, written, BOOK)).annotations).toHaveLength(1);
      }

      // A tagged address on a domain that does not fold is somebody else.
      expect((await marksFor(test.db, "reader+book@example.com", BOOK)).annotations).toEqual([]);
    } finally {
      test.close();
    }
  });
});

describe("writing over somebody else's marks", () => {
  it("cannot rewrite their annotation by re-using its id", async () => {
    const test = await seed();
    try {
      await saveAnnotation(
        test.db,
        MINE,
        BOOK,
        {
          id: ID_THEIRS,
          anchorKey: "one",
          blockIndex: 1,
          startOffset: 0,
          endOffset: 6,
          quote: "overwritten",
          colour: "rose",
          note: "vandalised",
        },
        LATER,
      );

      const row = await rowOf(test, ID_THEIRS);
      expect(row?.user_email).toBe(THEIRS);
      expect(row?.slug).toBe(OTHER_BOOK);
      expect(row?.quote).toBe("theirs");
      expect(row?.note).toBe("a private thought");
      expect(row?.colour).toBe("sage");
    } finally {
      test.close();
    }
  });

  it("cannot delete their annotation", async () => {
    const test = await seed();
    try {
      await removeAnnotation(test.db, MINE, OTHER_BOOK, ID_THEIRS, LATER);
      expect((await rowOf(test, ID_THEIRS))?.deleted_at).toBeNull();
    } finally {
      test.close();
    }
  });

  it("cannot resurrect one they deleted", async () => {
    const test = await seed();
    try {
      await removeAnnotation(test.db, THEIRS, OTHER_BOOK, ID_THEIRS, NOW);
      expect((await rowOf(test, ID_THEIRS))?.deleted_at).not.toBeNull();

      // The upsert clears `deleted_at` — that is what makes a replayed outbox
      // safe — so it is exactly the path that must not fire for anyone else.
      await saveAnnotation(
        test.db,
        MINE,
        BOOK,
        {
          id: ID_THEIRS,
          anchorKey: "one",
          blockIndex: 1,
          startOffset: 0,
          endOffset: 6,
          quote: "back",
          colour: "gold",
        },
        LATER,
      );
      expect((await rowOf(test, ID_THEIRS))?.deleted_at).not.toBeNull();
    } finally {
      test.close();
    }
  });

  it("cannot rewrite or resurrect their bookmark by re-using its id", async () => {
    const test = await seed();
    try {
      await addBookmark(
        test.db,
        MINE,
        BOOK,
        { id: ID_THEIRS, anchorKey: "nine", blockIndex: 99, label: "moved" },
        LATER,
      );

      const theirs = (await marksFor(test.db, THEIRS, OTHER_BOOK)).bookmarks;
      expect(theirs).toHaveLength(1);
      expect(theirs[0].label).toBe("theirs");
      expect(theirs[0].blockIndex).toBe(2);
    } finally {
      test.close();
    }
  });

  it("cannot delete their bookmark", async () => {
    const test = await seed();
    try {
      await removeBookmark(test.db, MINE, OTHER_BOOK, ID_THEIRS, LATER);
      expect((await marksFor(test.db, THEIRS, OTHER_BOOK)).bookmarks).toHaveLength(1);
    } finally {
      test.close();
    }
  });

  it("cannot move where they had got to", async () => {
    const test = await seed();
    try {
      await setProgress(test.db, MINE, OTHER_BOOK, { anchorKey: "one", fraction: 0, chaptersDone: 0 }, LATER);
      await setListening(test.db, MINE, OTHER_BOOK, { number: 1, seconds: 0 }, LATER);

      const theirs = await marksFor(test.db, THEIRS, OTHER_BOOK);
      expect(theirs.progress?.fraction).toBe(0.9);
      expect(theirs.listening).toEqual({ 1: 900 });
    } finally {
      test.close();
    }
  });

  it("still lets a person correct their OWN mark, which is what the upsert is for", async () => {
    // The guard must not cost the legitimate flow: re-saving a re-anchored
    // highlight is how a correction reaches the other devices.
    const test = await seed();
    try {
      await saveAnnotation(
        test.db,
        MINE,
        BOOK,
        {
          id: ID_MINE,
          anchorKey: "one",
          blockIndex: 4,
          startOffset: 10,
          endOffset: 20,
          quote: "mine",
          colour: "sky",
          note: "second thoughts",
        },
        LATER,
      );

      const [only] = (await marksFor(test.db, MINE, BOOK)).annotations;
      expect(only.blockIndex).toBe(4);
      expect(only.colour).toBe("sky");
      expect(only.note).toBe("second thoughts");
    } finally {
      test.close();
    }
  });
});

describe("the administrator seeing everything of everybody", () => {
  it("reads any person's marks as that person, with no admin branch to get wrong", async () => {
    // This is what "See as them" does: `withSession` swaps `viewer.email` for
    // the simulated address, so every function in this module is asked the
    // ordinary question and answers it. God mode is a property of the SESSION,
    // never a bypass inside the resolver — which is why nothing in this file
    // needs to know that an administrator exists.
    const test = await seed();
    try {
      const asThem = await marksFor(test.db, THEIRS, OTHER_BOOK);
      expect(asThem.annotations.map((a) => a.note)).toEqual(["a private thought"]);
      expect(asThem.bookmarks.map((b) => b.label)).toEqual(["theirs"]);
      expect(asThem.progress?.fraction).toBe(0.9);
    } finally {
      test.close();
    }
  });
});
