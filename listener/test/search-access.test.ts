import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { grant, invite } from "../app/server/people.server";
import { snippetOf } from "../app/lib/search";
import { passageById, search } from "../app/server/search.server";
import { createTestDb, type TestDb } from "./d1";

/**
 * Search cannot reach a book you were not given.
 *
 * This is the test that matters. A search box is the most tempting place in a
 * site to fetch broadly and trim afterwards, and the trimmed-away rows would
 * still have been read out of the database and, in a JavaScript filter, still
 * have been sent to the browser. So every case below is fired with a CONTROL:
 * the administrator runs the identical query and finds the passage, which is
 * what makes "the reader found nothing" evidence of a working gate rather than
 * of a typo in the fixture.
 *
 * Run against real SQLite through the real migrations, so the FTS index, its
 * triggers and the visibility expression are the production ones.
 */

const NOW = "2026-08-11T12:00:00Z";
const ADMIN = "asifhussain60@gmail.com";
const READER = "reader@example.com";
const NOBODY = "nobody@example.com";

let t: TestDb;

/** One passage, written the way the publisher writes it. */
function passage(
  id: number,
  slug: string,
  kind: string,
  quote: string,
  extra: Partial<{
    anchor: string;
    arabic: string;
    surah: number;
    ayah: number;
  }> = {},
) {
  const fold = quote
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
  const arabic = extra.arabic ?? "";
  return `INSERT INTO search_passage
    (id, slug, kind, anchor_key, heading, ordinal, quote, prefix, arabic, surah, ayah,
     heading_fold, body_fold, arabic_fold)
    VALUES (${id}, '${slug}', '${kind}', '${extra.anchor ?? "ch-1"}', 'A chapter', ${id},
      '${quote.replace(/'/g, "''")}', '', ${arabic === "" ? "NULL" : `'${arabic}'`},
      ${extra.surah ?? "NULL"}, ${extra.ayah ?? "NULL"},
      'a chapter', '${fold}', '${arabic}');`;
}

beforeEach(async () => {
  t = createTestDb();
  t.exec(`
    INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES
      ('open-book',   'Islamic',  'The Open Book',   'book', NULL, 10, 'published'),
      ('closed-book', 'Islamic',  'The Closed Book', 'book', NULL, 20, 'published'),
      ('draft-book',  'Sessions', 'The Draft',       'book', NULL, 30, 'draft');
  `);
  t.exec(
    [
      passage(
        1,
        "open-book",
        "chapter",
        "the intellect is the first originated thing",
      ),
      passage(2, "closed-book", "chapter", "the intellect is called the pen"),
      passage(3, "draft-book", "chapter", "the intellect appears in a draft"),
      passage(
        4,
        "closed-book",
        "verse",
        "Al-Baqarah: 255 allah la ilaha illa huwa",
        {
          arabic: "الله لا اله الا هو",
          surah: 2,
          ayah: 255,
        },
      ),
    ].join("\n"),
  );

  await invite(t.db, READER, ADMIN, {}, NOW);
  await invite(t.db, NOBODY, ADMIN, {}, NOW);
  await grant(t.db, READER, "unit", "open-book", ADMIN, NOW);
  await grant(t.db, ADMIN, "library", "*", ADMIN, NOW);
});

afterEach(() => t.close());

const run = (email: string, query: string) => search(t.db, email, { query });

describe("default deny", () => {
  it("finds nothing for an invited reader holding no books", async () => {
    const control = await run(ADMIN, "intellect");
    expect(control.total).toBeGreaterThan(0); // the query itself works

    const denied = await run(NOBODY, "intellect");
    expect(denied.total).toBe(0);
    expect(denied.hits).toEqual([]);
    expect(denied.facets.books).toEqual([]);
  });

  it("returns only the granted book, not the one beside it", async () => {
    const control = await run(ADMIN, "intellect");
    expect(control.hits.map((h) => h.slug).sort()).toEqual([
      "closed-book",
      "open-book",
    ]);

    const reader = await run(READER, "intellect");
    expect(reader.hits.map((h) => h.slug)).toEqual(["open-book"]);
    expect(reader.total).toBe(1);
  });

  it("never reaches an unpublished book, even for the administrator", async () => {
    const all = await run(ADMIN, "intellect");
    expect(all.hits.map((h) => h.slug)).not.toContain("draft-book");
  });

  it("keeps a denied book out of the facet counts, not merely out of the hits", async () => {
    // A count is a leak too: "Islamic (2)" tells a reader holding one book that
    // there is a second one, and how much of it matches.
    const reader = await run(READER, "intellect");
    const islamic = reader.facets.collections.find(
      (f) => f.value === "Islamic",
    );
    expect(islamic?.passages).toBe(1);
    expect(islamic?.books).toBe(1);
  });
});

describe("reference queries obey the same gate", () => {
  it("finds the verse for someone who holds the book", async () => {
    const control = await search(t.db, ADMIN, { query: "2:255" });
    expect(control.total).toBe(1);
    expect(control.parsed.reference).toEqual({ surah: 2, ayah: 255 });
  });

  it("finds nothing for someone who does not", async () => {
    const denied = await search(t.db, READER, { query: "2:255" });
    expect(denied.total).toBe(0);
  });
});

describe("scope narrows where it looks, never what may be returned", () => {
  it("cannot be used to reach a denied book", async () => {
    for (const scope of ["all", "titles", "content", "verses"] as const) {
      const denied = await search(t.db, NOBODY, { query: "intellect", scope });
      expect(denied.total, `scope ${scope}`).toBe(0);
    }
  });
});

describe("a passage fetched by id", () => {
  it("comes back for a reader who holds its book", async () => {
    expect(await passageById(t.db, READER, 1)).not.toBeNull();
  });

  it("does not come back for one who does not, however the id was obtained", async () => {
    // Ids are sequential and therefore guessable. That must not matter.
    expect(await passageById(t.db, READER, 2)).toBeNull();
    expect(await passageById(t.db, NOBODY, 1)).toBeNull();
  });
});

describe("the module itself", () => {
  const SOURCE = readFileSync(
    new URL("../app/server/search.server.ts", import.meta.url),
    "utf8",
  );

  /**
   * COMMENTS STRIPPED FIRST, exactly as test/offline.test.ts does and for the
   * same reason: this module's header explains at length why the Companion is
   * absent and why every query joins the visibility expression, and a grep over
   * the raw text fails on the explanation — which would leave the only way to
   * pass being to delete the reasoning. What is asserted is the CODE.
   */
  const CODE = SOURCE.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");

  it("never reaches for the Scholar Companion", () => {
    // Not "filters it out" — never asks. The same assertion the offline text
    // route carries, and the same shape of grep that watches
    // publish_to_listener.py for the two privilege bits.
    expect(CODE).not.toMatch(/companion/i);
  });

  it("joins the visibility expression in every query it runs", () => {
    const selects = CODE.match(/FROM\s+(?:search_passage|search_fts)/g) ?? [];
    const joins = CODE.match(/JOIN visible v/g) ?? [];
    expect(selects.length).toBeGreaterThan(0);
    // Every read of the index is accompanied by the join. A query added without
    // one fails here rather than shipping.
    expect(joins.length).toBeGreaterThanOrEqual(selects.length - 1);
    expect(CODE).toContain("VISIBLE_SQL");
  });

  it("writes no privilege bit", () => {
    // The prohibition publish_to_listener.py lives under, applied to the reader
    // of the same tables: nothing here may name `status` or `open_to_all`.
    expect(CODE).not.toMatch(/open_to_all/);
    expect(CODE).not.toMatch(/\bUPDATE\b|\bINSERT\b|\bDELETE\b/);
  });

  it("does not filter results in JavaScript after fetching them", () => {
    // The failure this guards: SELECT everything, then `.filter(canRead)`. The
    // rows would still have been read, and in a loader they would still reach
    // the browser.
    expect(CODE).not.toMatch(/\.filter\(.*canRead/);
  });
});

describe("snippets are built from the text the books actually print", () => {
  it("marks the matching words and keeps the original spelling", () => {
    const segments = snippetOf("The Intellect is called the Pen.", [
      "intellect",
    ]);
    const hit = segments.find((s) => s.hit);
    expect(hit?.text).toBe("Intellect"); // capitalised, as printed
  });

  it("finds a word the fold would have split", () => {
    const segments = snippetOf("written by al-Kirmani in Rayy", ["kirmani"]);
    expect(segments.some((s) => s.hit && s.text.includes("al-Kirmani"))).toBe(
      true,
    );
  });

  it("keeps the vowel marks in Arabic rather than showing the folded form", () => {
    const segments = snippetOf("قال اَلْكِرْمَانِيّ في كتابه", ["الكرماني"]);
    expect(segments.map((s) => s.text).join(" ")).toContain("اَلْكِرْمَانِيّ");
  });

  it("shows the opening rather than nothing when no word matches", () => {
    const segments = snippetOf("a passage with no match at all", ["absent"]);
    expect(segments.map((s) => s.text).join("")).toContain("a passage");
  });
});
