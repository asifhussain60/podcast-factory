import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  deletePerson,
  grant,
  holdersOf,
  invite,
  listPeople,
  peopleTallies,
  personByEmail,
  renamePerson,
  revokeInvite,
  splitName,
} from "~/server/access.server";
import { selectedPersonPath } from "~/routes/admin._index";
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

describe("opening a newly invited person", () => {
  it("redirects data-action submissions back to the admin page, not /admin.data", () => {
    expect(
      selectedPersonPath(
        "https://podcast-factory.safinaverse.com/admin.data?filter=never&page=2&_routes=routes%2Fadmin._index",
        "mahrooqshamsi@gmail.com",
      ),
    ).toBe(
      "/admin?filter=never&email=mahrooqshamsi%40gmail.com",
    );
  });

  it("preserves an ordinary admin-page redirect too", () => {
    expect(
      selectedPersonPath(
        "http://localhost:5273/admin?q=mahrooq",
        "mahrooqshamsi@gmail.com",
      ),
    ).toBe("/admin?q=mahrooq&email=mahrooqshamsi%40gmail.com");
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

  it("finds the people holding the whole library", async () => {
    // The widest grant this application can give, given by one press of one
    // button. Being able to ask who holds it is the only way to audit it.
    await grant(t.db, "bilal@example.com", "library", "*", ADMIN, NOW);
    await grant(t.db, "amina.yusuf@example.com", "unit", "standalone", ADMIN, NOW);

    const { people } = await listPeople(t.db, { filter: "library" });
    expect(people.map((p) => p.email)).toEqual(["bilal@example.com"]);
  });

  it("says on the row itself that somebody holds everything", async () => {
    // `grantCount` is 1 for a library grant, and a table printing "1" beside the
    // widest grant in the system is not a rounding error — it is the wrong
    // answer. The flag is what lets the column say "Everything".
    await grant(t.db, "bilal@example.com", "library", "*", ADMIN, NOW);
    await grant(t.db, "amina.yusuf@example.com", "unit", "standalone", ADMIN, NOW);

    const rows = (await listPeople(t.db)).people;
    expect(rows.find((p) => p.email === "bilal@example.com")?.library).toBe(true);
    expect(rows.find((p) => p.email === "amina.yusuf@example.com")?.library).toBe(false);
  });

  it("finds the people who signed in once and stopped", async () => {
    // The cutoff is built with `strftime`, not `datetime`. Every timestamp here
    // is an ISO string with a T and a Z and SQLite compares them as TEXT, so
    // `datetime('now','-30 days')` — which has a space where the T is — sorts
    // below every stored value and would have matched nobody, forever. This test
    // fails if that regresses.
    t.exec(`
      UPDATE invite SET redeemed_at = '${NOW}',
                        last_seen_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-90 days')
        WHERE email = 'amina.yusuf@example.com';
      UPDATE invite SET redeemed_at = '${NOW}',
                        last_seen_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-2 days')
        WHERE email = 'bilal@example.com';
    `);

    const { people } = await listPeople(t.db, { filter: "dormant" });
    expect(people.map((p) => p.email)).toEqual(["amina.yusuf@example.com"]);
  });

  it("leaves the revoked out of every filter but their own", async () => {
    // Each new filter carries `revoked_at IS NULL` for the same reason the old
    // ones do: somebody who cannot sign in at all is not "gone quiet", and
    // listing them as such sends an administrator chasing a person they already
    // removed.
    await grant(t.db, "bilal@example.com", "library", "*", ADMIN, NOW);
    await revokeInvite(t.db, "bilal@example.com", ADMIN, LATER);

    expect((await listPeople(t.db, { filter: "library" })).total).toBe(0);
    expect((await listPeople(t.db, { filter: "revoked" })).total).toBe(1);
  });
});

describe("the table reads alphabetically down the column it prints", () => {
  it("orders by the displayed name, addresses included, in one sequence", async () => {
    // It used to order by surname, which is right for a list of one line per
    // person and wrong for a table: the Name column would have read Amina,
    // Bilal, Yusuf in an order keyed to words the column never shows, and a
    // sorted table that looks unsorted reads as a bug. The nameless no longer
    // fall to the bottom either — they sort by their address, in place.
    await invite(t.db, "zaki@example.com", ADMIN, { firstName: "Zaki" }, NOW);
    await invite(t.db, "aardvark@example.com", ADMIN, {}, NOW);

    const { people } = await listPeople(t.db);
    expect(people.map((p) => p.displayName)).toEqual([
      "aardvark@example.com",
      "Amina Yusuf",
      "Bilal Ahmed",
      "nameless@example.com",
      "Zaki",
    ]);
  });
});

describe("one name field, two stored columns", () => {
  it("puts the last word in the surname and the rest in the given name", () => {
    expect(splitName("Ishrat Husain")).toEqual({ firstName: "Ishrat", lastName: "Husain" });
    expect(splitName("Abd al-Rahman ibn Awf")).toEqual({
      firstName: "Abd al-Rahman ibn",
      lastName: "Awf",
    });
  });

  it("does not invent a surname for a single word", () => {
    expect(splitName("Cher")).toEqual({ firstName: "Cher", lastName: null });
  });

  it("stores nothing for an empty or blank name", () => {
    expect(splitName("")).toEqual({ firstName: null, lastName: null });
    expect(splitName("   ")).toEqual({ firstName: null, lastName: null });
  });

  it("is reversible — what is displayed is what was typed", async () => {
    // The one property that makes a heuristic safe here. The two halves rejoin,
    // in order, with one space; nothing is dropped and no word changes places.
    for (const typed of ["Ishrat Husain", "Cher", "Abd al-Rahman ibn Awf", "Mary  Jane   Watson"]) {
      const email = `${typed.replace(/\W+/g, "")}@example.com`;
      await invite(t.db, email, ADMIN, splitName(typed), NOW);
      const person = await personByEmail(t.db, email);
      expect(person?.displayName).toBe(typed.trim().replace(/\s+/g, " "));
    }
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

describe("renaming somebody in the row", () => {
  it("stores the typed name in both columns and leaves the address alone", async () => {
    await renamePerson(t.db, "nameless@example.com", "Ishrat Husain", ADMIN, NOW);

    const person = await personByEmail(t.db, "nameless@example.com");
    expect(person?.firstName).toBe("Ishrat");
    expect(person?.lastName).toBe("Husain");
    expect(person?.emailRaw).toBe("nameless@example.com");
  });

  it("clears back to the address when the name is emptied", async () => {
    // Stored as NULL rather than as an empty string, so the row falls back to
    // displaying the address exactly as it did before a name was recorded.
    await renamePerson(t.db, "amina.yusuf@example.com", "", ADMIN, NOW);

    const person = await personByEmail(t.db, "amina.yusuf@example.com");
    expect(person?.firstName).toBeNull();
    expect(person?.displayName).toBe("Amina.Yusuf@example.com");
  });

  it("does not touch anybody else", async () => {
    await renamePerson(t.db, "bilal@example.com", "Bilal Karim", ADMIN, NOW);
    expect((await personByEmail(t.db, "amina.yusuf@example.com"))?.displayName).toBe("Amina Yusuf");
  });
});

describe("deleting somebody is not revoking them", () => {
  it("takes their grants with them", async () => {
    // `access_grant` keys on EMAIL, not on a user id, so a grant left behind by a
    // deleted invitation is dormant rather than gone — invite that address again,
    // which is a plausible thing to do right after deleting it by mistake, and
    // every book it held would come back with nobody having granted anything.
    await grant(t.db, "bilal@example.com", "unit", "standalone", ADMIN, NOW);
    await grant(t.db, "bilal@example.com", "library", "*", ADMIN, NOW);

    await deletePerson(t.db, "bilal@example.com", ADMIN, LATER);

    expect(await personByEmail(t.db, "bilal@example.com")).toBeNull();

    // Re-invited from scratch: no invitation, no grants, nothing restored.
    await invite(t.db, "bilal@example.com", ADMIN, {}, LATER);
    const back = await personByEmail(t.db, "bilal@example.com");
    expect(back?.grantCount).toBe(0);
    expect(back?.library).toBe(false);
  });

  it("ends their sessions, like a revocation does", async () => {
    t.exec(`
      INSERT INTO user (id, name, email, emailVerified, createdAt, updatedAt)
        VALUES ('u1', 'Bilal', 'bilal@example.com', 1, '${NOW}', '${NOW}');
      INSERT INTO session (id, expiresAt, token, createdAt, updatedAt, userId)
        VALUES ('s1', '2099-01-01', 'tok', '${NOW}', '${NOW}', 'u1');
    `);

    await deletePerson(t.db, "bilal@example.com", ADMIN, LATER);

    const left = await t.db.prepare(`SELECT count(*) AS n FROM session`).bind().first<{ n: number }>();
    expect(left?.n).toBe(0);
  });

  it("leaves the record of what was done", async () => {
    // The row goes; the history of the row going does not.
    await deletePerson(t.db, "bilal@example.com", ADMIN, LATER);
    const ev = await t.db
      .prepare(`SELECT action, subject FROM access_event WHERE action = 'delete-person'`)
      .bind()
      .first<{ action: string; subject: string }>();
    expect(ev?.subject).toBe("bilal@example.com");
  });

  it("leaves everybody else in place", async () => {
    await deletePerson(t.db, "bilal@example.com", ADMIN, LATER);
    expect((await listPeople(t.db)).total).toBe(2);
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
