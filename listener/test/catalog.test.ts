import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  chapterOf,
  chaptersOf,
  deckPagesOf,
  episodesOf,
  libraryCards,
  mediaByKey,
  playableEpisodesForCards,
  sessionsOf,
} from "../app/server/catalog.server";
import { readingMinutes } from "../app/lib/reading";
import { createTestDb } from "./d1";

/**
 * The content layer, against real SQLite running the real migrations.
 *
 * What is worth testing here is not "does a SELECT work" but the two rules that
 * make a half-published library readable rather than broken: an episode with no
 * recording is SHOWN and marked, and an asset that exists on disk but not in R2
 * is treated as absent rather than linked.
 */


function seed() {
  const test = createTestDb();

  test.exec(`
    INSERT INTO content_unit (slug, bucket, title, kind, status) VALUES
      ('book-a', 'Islamic', 'Book A', 'book', 'published'),
      ('book-b', 'Islamic', 'Book B', 'book', 'published');

    INSERT INTO unit_detail (slug, title_arabic, blurb_html, published_at, pdf_key) VALUES
      ('book-a', 'كتاب', '<p>A blurb.</p>', '2026-08-03T00:00:00Z', 'book-a/book.pdf');

    INSERT INTO chapter (slug, anchor_key, idx, title, html, word_count) VALUES
      ('book-a', 'one',   1, '1. One',   '<p>one</p>',   440),
      ('book-a', 'two',   2, '2. Two',   '<p>two</p>',   220),
      ('book-a', 'three', 3, '3. Three', '<p>three</p>', 110);

    INSERT INTO episode (slug, number, title, blurb, style, audio_key, duration_s) VALUES
      ('book-a', 1, 'Episode one', 'About one.', 'deep_dive', 'book-a/audio/ep01.m4a', 1800),
      ('book-a', 2, 'Episode two', NULL,         'deep_dive', 'book-a/audio/ep02.m4a', 900),
      ('book-a', 3, 'Episode three', NULL,       'debate',    NULL,                    NULL);

    -- ep01 is uploaded; ep02 exists on disk only. That difference is the point.
    INSERT INTO media_asset (key, slug, kind, content_type, bytes, sha256, source_path, uploaded_at) VALUES
      ('book-a/audio/ep01.m4a', 'book-a', 'audio', 'audio/mp4', 100, 'aa', 'x/ep01.m4a', '2026-08-03T00:00:00Z'),
      ('book-a/audio/ep02.m4a', 'book-a', 'audio', 'audio/mp4', 200, 'bb', 'x/ep02.m4a', NULL),
      ('book-a/book.pdf',       'book-a', 'pdf',   'application/pdf', 4000, 'cc', 'x/b.pdf', NULL),
      ('book-a/deck/page-01.jpg','book-a','deck-page','image/jpeg', 50, 'dd', 'x/p1.jpg', '2026-08-03T00:00:00Z'),
      ('book-a/deck/page-02.jpg','book-a','deck-page','image/jpeg', 50, 'ee', 'x/p2.jpg', NULL);
  `);

  return test;
}

describe("episodes", () => {
  it("shows an episode with no recording rather than hiding it", async () => {
    const { db, close } = seed();

    const episodes = await episodesOf(db, "book-a");
    expect(episodes.map((e) => e.number)).toEqual([1, 2, 3]);
    expect(episodes[2].hasAudio).toBe(false);

    close();
  });

  it("treats an un-uploaded file as no audio at all", async () => {
    // The failure this prevents: a media_asset row exists because the file is on
    // the author's disk, the UI reads `audio_key` and renders a play button, and
    // the reader gets a 404 from a book they were told they could listen to.
    const { db, close } = seed();

    const episodes = await episodesOf(db, "book-a");
    expect(episodes[0].hasAudio, "uploaded").toBe(true);
    expect(episodes[1].hasAudio, "on disk only").toBe(false);
    expect(episodes[1].audioKey, "the key is still known").not.toBeNull();

    close();
  });

  it("carries no chapter links unless a human recorded them", async () => {
    const { db, close } = seed();

    for (const episode of await episodesOf(db, "book-a")) {
      expect(episode.chapters).toEqual([]);
    }

    close();
  });

  it("reports the links that were recorded", async () => {
    const test = seed();
    test.exec(`
      INSERT INTO episode_chapter (slug, number, anchor_key) VALUES
        ('book-a', 1, 'one'), ('book-a', 1, 'two');
    `);

    const episodes = await episodesOf(test.db, "book-a");
    expect(episodes[0].chapters.sort()).toEqual(["one", "two"]);
    expect(episodes[1].chapters).toEqual([]);

    test.close();
  });
});

describe("sessions", () => {
  it("keeps ungrouped episodes visible in a titleless trailing group", async () => {
    // The invariant that matters: an episode belongs to exactly one group and no
    // episode can fall out of the list by having no session to belong to. A book
    // that was never grouped is one titleless group, which the page renders as a
    // plain list — one code path, not two.
    const { db, close } = seed();

    const sessions = await sessionsOf(db, "book-a");
    expect(sessions).toHaveLength(1);
    expect(sessions[0]).toMatchObject({ number: 0, title: "" });
    expect(sessions[0].episodes.map((e) => e.number)).toEqual([1, 2, 3]);

    close();
  });

  it("groups by the sessions that were declared", async () => {
    const test = seed();
    test.exec(`
      INSERT INTO book_session (slug, number, title) VALUES
        ('book-a', 1, 'The First Run'), ('book-a', 2, 'The Second');
      UPDATE episode SET session_number = 1 WHERE slug = 'book-a' AND number IN (1, 2);
      UPDATE episode SET session_number = 2 WHERE slug = 'book-a' AND number = 3;
    `);

    const sessions = await sessionsOf(test.db, "book-a");
    expect(sessions.map((s) => [s.number, s.title, s.episodes.length])).toEqual([
      [1, "The First Run", 2],
      [2, "The Second", 1],
    ]);

    test.close();
  });

  it("rescues an episode pointing at a session that does not exist", async () => {
    // Otherwise a mistyped or deleted session would silently swallow episodes —
    // the reader would simply never see them, with nothing anywhere saying so.
    const test = seed();
    test.exec(`
      INSERT INTO book_session (slug, number, title) VALUES ('book-a', 1, 'Only One');
      UPDATE episode SET session_number = 1 WHERE slug = 'book-a' AND number = 1;
      UPDATE episode SET session_number = 9 WHERE slug = 'book-a' AND number = 2;
    `);

    const sessions = await sessionsOf(test.db, "book-a");
    const seen = sessions.flatMap((s) => s.episodes.map((e) => e.number)).sort();
    expect(seen, "every episode appears exactly once").toEqual([1, 2, 3]);
    expect(sessions.at(-1)?.title, "the strays land in the titleless group").toBe("");

    test.close();
  });

  it("drops a declared session that ended up with no episodes", async () => {
    const test = seed();
    test.exec(`INSERT INTO book_session (slug, number, title) VALUES ('book-a', 4, 'Empty')`);

    const sessions = await sessionsOf(test.db, "book-a");
    expect(sessions.some((s) => s.title === "Empty")).toBe(false);

    test.close();
  });
});

describe("chapters", () => {
  it("returns the table of contents in order, without the prose", async () => {
    const { db, close } = seed();

    const chapters = await chaptersOf(db, "book-a");
    expect(chapters.map((c) => c.idx)).toEqual([1, 2, 3]);
    expect(chapters[0]).not.toHaveProperty("html");

    close();
  });

  it("finds one chapter by its anchor key", async () => {
    const { db, close } = seed();

    expect((await chapterOf(db, "book-a", "two"))?.title).toBe("2. Two");
    // A key from another book must not resolve, or the reading route becomes a
    // way to read one book's prose through another book's gate.
    expect(await chapterOf(db, "book-b", "two")).toBeNull();

    close();
  });
});

describe("deck pages", () => {
  it("marks the un-uploaded ones unavailable", async () => {
    const { db, close } = seed();

    const decks = await deckPagesOf(db, "book-a");
    expect(decks).toHaveLength(1);
    expect(decks[0].pages.map((p) => p.available)).toEqual([true, false]);

    close();
  });

  it("collects rows written before decks had ids into one untitled deck", async () => {
    // Migration 0010 leaves `deck_id` NULL on every existing row. Those rows are
    // not wrong — they are from a world with one deck in it — so the site has to
    // render correctly the moment the migration lands and before anything is
    // re-published. The fixture is deliberately pre-0010 shaped.
    const { db, close } = seed();

    const decks = await deckPagesOf(db, "book-a");
    expect(decks.map((d) => [d.id, d.title])).toEqual([["", null]]);

    close();
  });

  it("keeps one book's several decks apart, in order, each with its own name", async () => {
    // Ayyuha al-Walad's shape: four chapter decks. Before this they collided —
    // `key` is the primary key and every deck offers a `page-01.jpg`, so three
    // decks' pages silently overwrote each other.
    const test = seed();
    test.exec(`
      INSERT INTO media_asset (key, slug, kind, content_type, bytes, sha256, source_path, uploaded_at, deck_id, deck_title) VALUES
        ('book-a/deck/ch02/page-01.jpg','book-a','deck-page','image/jpeg',10,'f1','x','now','ch02','The Second Talk'),
        ('book-a/deck/ch01/page-02.jpg','book-a','deck-page','image/jpeg',10,'f2','x','now','ch01','The First Talk'),
        ('book-a/deck/ch01/page-01.jpg','book-a','deck-page','image/jpeg',10,'f3','x','now','ch01','The First Talk');
    `);

    const decks = await deckPagesOf(test.db, "book-a");
    const named = decks.filter((d) => d.id !== "");

    expect(named.map((d) => [d.id, d.title])).toEqual([
      ["ch01", "The First Talk"],
      ["ch02", "The Second Talk"],
    ]);
    // Pages in page order within a deck, not interleaved with the other's.
    expect(named[0].pages.map((p) => p.key)).toEqual([
      "book-a/deck/ch01/page-01.jpg",
      "book-a/deck/ch01/page-02.jpg",
    ]);

    test.close();
  });
});

describe("library cards", () => {
  it("keeps 'exists' and 'can be opened' apart", async () => {
    // The fixture's PDF row exists but has uploaded_at NULL — the file is on the
    // author's disk and not in R2. Both facts travel, because they are answered
    // differently on screen: the card used to carry only the second, collapsed
    // into `hasPdf`, so it could either promise a download that 404s or say
    // nothing at all. It can now say "not uploaded yet", the way the book page
    // always could. `describeContents` is the one place that decides the words.
    const { db, close } = seed();

    const cards = await libraryCards(db, ["book-a", "book-b"]);
    expect(cards.get("book-a")).toMatchObject({
      chapters: 3,
      firstChapterKey: "one",
      episodes: 3,
      recorded: 1,
      hasPdf: true,
      pdfAvailable: false,
      deckPages: 2,
      deckAvailable: true,
    });

    close();
  });

  it("marks the PDF available once it is uploaded", async () => {
    const test = seed();
    test.exec(`UPDATE media_asset SET uploaded_at = 'now' WHERE key = 'book-a/book.pdf'`);

    const cards = await libraryCards(test.db, ["book-a"]);
    expect(cards.get("book-a")?.pdfAvailable).toBe(true);

    test.close();
  });

  it("carries raw words, not a precomputed reading time", async () => {
    // The card used to receive `minutes`, worked out server-side, while the book
    // page worked the same figure out client-side from words — with a different
    // zero rule, so one book could show no pill on its card and "1 min read" on
    // its own page. One computation now, in `app/lib/facts.ts`.
    const { db, close } = seed();

    const card = (await libraryCards(db, ["book-a"])).get("book-a")!;
    expect(card).not.toHaveProperty("minutes");
    expect(typeof card.words).toBe("number");

    close();
  });

  it("is scoped to the slugs it was given", async () => {
    // Counting the whole catalog and filtering afterwards would put the shape of
    // books the viewer cannot see into a network response.
    const { db, close } = seed();

    const cards = await libraryCards(db, ["book-b"]);
    expect([...cards.keys()]).toEqual(["book-b"]);

    close();
  });

  it("returns nothing for an empty list rather than everything", async () => {
    const { db, close } = seed();
    expect((await libraryCards(db, [])).size).toBe(0);
    close();
  });

  it("returns only uploaded playable episodes for card actions", async () => {
    const { db, close } = seed();

    const playable = await playableEpisodesForCards(db, ["book-a", "book-b"]);
    expect(playable.get("book-a")?.map((e) => [e.number, e.audioKey])).toEqual([
      [1, "book-a/audio/ep01.m4a"],
    ]);
    expect(playable.has("book-b")).toBe(false);

    close();
  });

  it("carries uploaded transcripts for card-started playback", async () => {
    const test = seed();
    test.exec(`
      INSERT INTO media_asset (key, slug, kind, content_type, bytes, sha256, source_path, uploaded_at) VALUES
        ('book-a/transcripts/ep01.vtt', 'book-a', 'transcript', 'text/vtt', 25, 'vv', 'x/ep01.vtt', '2026-08-03T00:00:00Z');
      UPDATE episode SET transcript_key = 'book-a/transcripts/ep01.vtt'
        WHERE slug = 'book-a' AND number = 1;
    `);

    const playable = await playableEpisodesForCards(test.db, ["book-a"]);
    expect(playable.get("book-a")?.[0].transcriptKey).toBe("book-a/transcripts/ep01.vtt");

    test.close();
  });
});

describe("media lookup", () => {
  it("carries the owning slug, so the caller need not trust the URL", async () => {
    const { db, close } = seed();

    const asset = await mediaByKey(db, "book-a/audio/ep01.m4a");
    expect(asset?.slug).toBe("book-a");

    close();
  });
});

describe("reading time", () => {
  it("never says zero minutes", () => {
    expect(readingMinutes(0)).toBe(1);
    expect(readingMinutes(10)).toBe(1);
    expect(readingMinutes(2200)).toBe(10);
  });
});

describe("the publish step's privilege discipline", () => {
  const PUBLISH = readFileSync(
    new URL("../../scripts/podcast/publish_to_listener.py", import.meta.url),
    "utf8",
  );

  it("never writes status or open_to_all", () => {
    // The whole reason the publish step can be trusted with a database handle.
    // Comments are stripped first: the module docstring explains at length that
    // it does not touch these columns, and a check that cannot tell an
    // explanation from a statement fires on its own documentation.
    const code = PUBLISH.replace(/"""[\s\S]*?"""/g, "").replace(/^\s*#.*$/gm, "");

    expect(code).not.toMatch(/open_to_all/);
    expect(code).not.toMatch(/\bstatus\b\s*=/);
    expect(code).not.toMatch(/UPDATE\s+content_unit\s+SET[^;]*status/i);
  });

  it("keeps the INSERT column list explicit", () => {
    // `INSERT INTO content_unit VALUES (...)` without a column list would supply
    // every column positionally — including the two above — and would keep
    // working right up until the schema gained a column.
    expect(PUBLISH).toMatch(/INSERT INTO content_unit \(slug, bucket, title, kind, sort_order\)/);
  });
});
