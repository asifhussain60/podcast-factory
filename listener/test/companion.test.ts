import { describe, expect, it } from "vitest";

import { companionFor } from "../app/server/companion.server";
import type { Viewer } from "../app/middleware/session";
import { createTestDb } from "./d1";

/**
 * The Scholar Companion reaches one account and no other.
 *
 * The interesting assertion here is not "the administrator gets the cards" — it
 * is that everybody else's request NEVER REACHES THE DATABASE. That is the whole
 * shape of the gate: not a filter applied to a result, but a query that is not
 * made. A test that only checked the returned value would pass just as happily
 * against a version that fetched every card and then dropped them, which is one
 * refactor away from returning them.
 */


const viewer = (over: Partial<Viewer> = {}): Viewer => ({
  email: "asifhussain60@gmail.com",
  rawEmail: "asifhussain60@gmail.com",
  name: "Asif",
  image: null,
  isAdmin: true,
  ...over,
});

function seed() {
  const test = createTestDb();

  test.exec(`
    INSERT INTO companion_note (slug, anchor_key, note_id, idx, title, quote, body_html, etymology) VALUES
      ('book-a', 'chapter-three', 'n2', 2, 'Milk before meat', NULL, '<p>Second.</p>', NULL),
      ('book-a', 'chapter-three', 'n1', 1, 'Five conditions', 'The Master replied', '<p>First.</p>',
        '["ميثاق (covenant)","أمانة (trust)"]'),
      ('book-a', 'chapter-four',  'n3', 1, NULL, NULL, '<p>Elsewhere.</p>', 'not json at all');
  `);

  return test;
}

describe("who the companion answers", () => {
  it("gives the administrator this chapter's cards, in the order they were filed", async () => {
    const test = seed();
    try {
      const cards = await companionFor(test.db, viewer(), "book-a", "chapter-three");

      expect(cards.map((c) => c.id)).toEqual(["n1", "n2"]);
      expect(cards[0]).toEqual({
        id: "n1",
        idx: 1,
        title: "Five conditions",
        quote: "The Master replied",
        bodyHtml: "<p>First.</p>",
        etymology: ["ميثاق (covenant)", "أمانة (trust)"],
      });
    } finally {
      test.close();
    }
  });

  it("gives an invited non-admin nothing, and asks the database nothing", async () => {
    const cards = await companionFor(refuses(), viewer({ isAdmin: false }), "book-a", "chapter-three");
    expect(cards).toEqual([]);
  });

  it("gives a signed-out caller nothing, and asks the database nothing", async () => {
    const cards = await companionFor(refuses(), null, "book-a", "chapter-three");
    expect(cards).toEqual([]);
  });

  it("returns nothing for a chapter that has no cards", async () => {
    const test = seed();
    try {
      expect(await companionFor(test.db, viewer(), "book-a", "chapter-nine")).toEqual([]);
    } finally {
      test.close();
    }
  });

  it("shows a card whose etymology is unreadable rather than losing the card", async () => {
    const test = seed();
    try {
      const cards = await companionFor(test.db, viewer(), "book-a", "chapter-four");
      expect(cards).toHaveLength(1);
      expect(cards[0].etymology).toEqual([]);
    } finally {
      test.close();
    }
  });
});

/** A database that fails the test if anything is asked of it. */
function refuses(): D1Database {
  return new Proxy({} as D1Database, {
    get(_target, property) {
      throw new Error(`the companion query reached the database (.${String(property)})`);
    },
  });
}
