import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  grant,
  holdersOf,
  invite,
  listPeople,
  peopleTallies,
  personByEmail,
  revokeInvite,
} from "~/server/access.server";
import { createTestDb, type TestDb } from "./d1";

/**
 * The access screen at a size it has never been.
 *
 * The screen this replaces loaded every invitation and every catalogue row on
 * every render and filtered in JavaScript. That works at eight people and fails
 * quietly for a long time before anyone notices, so the point of these tests is
 * that searching and filtering happen in SQL and mean what they say.
 */

const ADMIN = "admin@example.com";
const NOW = "2026-08-03T12:00:00.000Z";
const LATER = "2026-08-04T12:00:00.000Z";

let t: TestDb;

beforeEach(async () => {
  t = createTestDb();

  await invite(t.db, "Amina.Yusuf@example.com", ADMIN, { firstName: "Amina", lastName: "Yusuf" }, NOW);
  await invite(t.db, "bilal@example.com", ADMIN, { firstName: "Bilal", lastName: "Ahmed" }, NOW);
  await invite(t.db, "nameless@example.com", ADMIN, {}, NOW);

  t.exec(`
    INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status)
      VALUES ('vol-one', 'Islamic', 'Volume One', 'book', 'the-work', 1, 'published'),
             ('the-work', 'Islamic', 'The Work', 'work', NULL, 0, 'published'),
             ('standalone', 'Islamic', 'A Standalone', 'book', NULL, 2, 'published');
  `);
});

afterEach(() => t.close());

describe("finding one person among many", () => {
  it("matches on first name", async () => {
    const { people } = await listPeople(t.db, { search: "amina" });
    expect(people.map((p) => p.displayName)).toEqual(["Amina Yusuf"]);
  });

  it("matches on last name", async () => {
    const { people } = await listPeople(t.db, { search: "ahmed" });
    expect(people.map((p) => p.displayName)).toEqual(["Bilal Ahmed"]);
  });

  it("matches on the full name across the gap between the two columns", async () => {
    const { people } = await listPeople(t.db, { search: "bilal ah" });
    expect(people).toHaveLength(1);
  });

  it("matches the address AS TYPED, not only its normalized form", async () => {
    // Stored normalized as `amina.yusuf@example.com` is lower-cased but a Gmail
    // address would also lose its dots. An administrator searching for what they
    // remember typing has to find them.
    const { people } = await listPeople(t.db, { search: "Amina.Yusuf" });
    expect(people).toHaveLength(1);
  });

  it("returns everyone for an empty search rather than nobody", async () => {
    // The clause stays in the query with a `%` pattern; a version that dropped
    // it while still binding its parameter made D1 reject the statement and
    // turned the whole screen into a 500.
    const { people, total, everyone } = await listPeople(t.db, { search: "" });
    expect(people).toHaveLength(3);
    expect(total).toBe(3);
    expect(everyone).toBe(3);
  });

  it("treats an underscore as a character, not as a wildcard", async () => {
    // `_` matches any single character in LIKE. Unescaped, "a_ina" would find
    // Amina — a search that appears to work and is finding the wrong things.
    const { people } = await listPeople(t.db, { search: "a_ina" });
    expect(people).toHaveLength(0);
  });

  it("falls back to the address when no name was recorded", async () => {
    const person = await personByEmail(t.db, "nameless@example.com");
    expect(person?.displayName).toBe("nameless@example.com");
  });
});

describe("the filters answer the questions they are named for", () => {
  it("separates never-signed-in from signed-in", async () => {
    t.exec(`UPDATE invite SET redeemed_at = '${NOW}' WHERE email = 'bilal@example.com'`);

    expect((await listPeople(t.db, { filter: "active" })).people.map((p) => p.email)).toEqual([
      "bilal@example.com",
    ]);
    expect((await listPeople(t.db, { filter: "never" })).total).toBe(2);
  });

  it("finds the people who can sign in and see nothing", async () => {
    await grant(t.db, "bilal@example.com", "unit", "standalone", ADMIN, NOW);
    const { people } = await listPeople(t.db, { filter: "waiting" });
    expect(people.map((p) => p.email).sort()).toEqual([
      "amina.yusuf@example.com",
      "nameless@example.com",
    ]);
  });

  it("counts each filter without loading anybody", async () => {
    await revokeInvite(t.db, "nameless@example.com", ADMIN, LATER);
    const tallies = await peopleTallies(t.db);
    expect(tallies.all).toBe(3);
    expect(tallies.revoked).toBe(1);
    expect(tallies.never).toBe(2);
  });
});

describe("paging", () => {
  it("reports the full total while returning one page", async () => {
    const page = await listPeople(t.db, { limit: 2, offset: 0 });
    expect(page.people).toHaveLength(2);
    expect(page.total).toBe(3);
  });

  it("returns the rest on the next page", async () => {
    const page = await listPeople(t.db, { limit: 2, offset: 2 });
    expect(page.people).toHaveLength(1);
  });
});

describe("re-inviting somebody keeps what was recorded about them", () => {
  it("does not blank the name or the note", async () => {
    await invite(t.db, "carer@example.com", ADMIN, { firstName: "Ada", lastName: "Lovelace", note: "A friend" }, NOW);
    await revokeInvite(t.db, "carer@example.com", ADMIN, LATER);

    // The re-invite button sends no name and no note. A plain assignment would
    // erase both — deleting information the administrator typed, in order to
    // perform an action that means "let them back in".
    await invite(t.db, "carer@example.com", ADMIN, {}, LATER);

    const person = await personByEmail(t.db, "carer@example.com");
    expect(person?.displayName).toBe("Ada Lovelace");
    expect(person?.note).toBe("A friend");
    expect(person?.revokedAt).toBeNull();
  });
});

describe("who can open one book", () => {
  it("says HOW each person holds it", async () => {
    await grant(t.db, "amina.yusuf@example.com", "unit", "vol-one", ADMIN, NOW);
    await grant(t.db, "bilal@example.com", "work", "the-work", ADMIN, NOW);
    await grant(t.db, "nameless@example.com", "library", "*", ADMIN, NOW);

    const holders = await holdersOf(t.db, "vol-one");
    const via = Object.fromEntries(holders.map((h) => [h.email, h.via]));

    expect(via["amina.yusuf@example.com"]).toBe("unit");
    expect(via["bilal@example.com"]).toBe("work");
    expect(via["nameless@example.com"]).toBe("library");
  });

  it("prefers the narrowest grant when somebody holds more than one", async () => {
    // Otherwise the screen offers a "Has it" toggle that writes a unit grant
    // where a library grant is what is actually in force, and pressing it looks
    // like it does nothing.
    await grant(t.db, "amina.yusuf@example.com", "unit", "vol-one", ADMIN, NOW);
    await grant(t.db, "amina.yusuf@example.com", "library", "*", ADMIN, NOW);

    const holders = await holdersOf(t.db, "vol-one");
    expect(holders.find((h) => h.email === "amina.yusuf@example.com")?.via).toBe("unit");
  });

  it("names people rather than addresses where a name is known", async () => {
    await grant(t.db, "bilal@example.com", "unit", "standalone", ADMIN, NOW);
    expect((await holdersOf(t.db, "standalone"))[0].displayName).toBe("Bilal Ahmed");
  });
});
