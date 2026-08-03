import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  chapterOf,
  chaptersOf,
  deckPagesOf,
  episodesOf,
  libraryCards,
  mediaByKey,
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

const MIGRATIONS = ["0001_auth", "0002_access", "0004_catalog"];

function seed() {
  const test = createTestDb(MIGRATIONS);

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

    const pages = await deckPagesOf(db, "book-a");
    expect(pages.map((p) => p.available)).toEqual([true, false]);

    close();
  });
});

describe("library cards", () => {
  it("counts only media that is actually available", async () => {
    // The fixture's PDF row exists but has uploaded_at NULL — the file is on the
    // author's disk and not in R2 — so the card must NOT advertise a PDF. A
    // badge promising a download that 404s is worse than no badge.
    const { db, close } = seed();

    const cards = await libraryCards(db, ["book-a", "book-b"]);
    expect(cards.get("book-a")).toMatchObject({
      chapters: 3,
      episodes: 3,
      recorded: 1,
      hasPdf: false,
      deckPages: 2,
    });

    close();
  });

  it("advertises the PDF once it is uploaded", async () => {
    const test = seed();
    test.exec(`UPDATE media_asset SET uploaded_at = 'now' WHERE key = 'book-a/book.pdf'`);

    const cards = await libraryCards(test.db, ["book-a"]);
    expect(cards.get("book-a")?.hasPdf).toBe(true);

    test.close();
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
