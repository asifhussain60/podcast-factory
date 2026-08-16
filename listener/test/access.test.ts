import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  canRead,
  grant,
  hasLiveInvite,
  invite,
  revokeGrant,
  revokeInvite,
  setOpenToAll,
  visibleUnits,
} from "../app/server/access.server";
import { createTestDb, type TestDb } from "./d1";

const NOW = "2026-08-03T12:00:00Z";
const ADMIN = "asifhussain60@gmail.com";

let t: TestDb;

/**
 * A miniature of the real catalog: one standalone published book, one draft, one
 * published book inside a work, and a second volume of that work. Enough to
 * exercise every branch of the resolver.
 */
beforeEach(async () => {
  t = createTestDb();
  t.exec(`
    INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES
      ('ayyuhal-walad', 'Islamic', 'Ayyuha al-Walad', 'book', NULL, 10, 'published'),
      ('kitab-al-riyad', 'Islamic', 'Kitab al-Riyad',  'book', NULL, 20, 'draft'),
      ('asaas',         'Islamic', 'Asas al-Taweel',  'work', NULL, 30, 'draft'),
      ('asaas-vol-01',  'Islamic', 'Volume 1',        'book', 'asaas', 31, 'published'),
      ('asaas-vol-02',  'Islamic', 'Volume 2',        'book', 'asaas', 32, 'published');
  `);
  await invite(t.db, "reader@example.com", ADMIN, {}, NOW);
});

afterEach(() => t.close());

const slugs = async (email: string) =>
  (await visibleUnits(t.db, email)).map((u) => u.slug);

describe("default deny", () => {
  it("shows an invited person with no grants nothing at all", async () => {
    expect(await slugs("reader@example.com")).toEqual([]);
  });

  it("refuses a book that exists and is published", async () => {
    expect(await canRead(t.db, "reader@example.com", "ayyuhal-walad")).toBe(
      false,
    );
  });
});

describe("unit grants", () => {
  it("shows exactly the granted book and nothing else", async () => {
    await grant(
      t.db,
      "reader@example.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    expect(await slugs("reader@example.com")).toEqual(["ayyuhal-walad"]);
    expect(await canRead(t.db, "reader@example.com", "asaas-vol-01")).toBe(
      false,
    );
  });

  it("does not surface a granted book that is not published yet", async () => {
    // Provisioning ahead of publication is a supported move; it just does not
    // take effect until the book is published.
    await grant(
      t.db,
      "reader@example.com",
      "unit",
      "kitab-al-riyad",
      ADMIN,
      NOW,
    );
    expect(await slugs("reader@example.com")).toEqual([]);
    expect(await canRead(t.db, "reader@example.com", "kitab-al-riyad")).toBe(
      false,
    );

    t.exec(
      `UPDATE content_unit SET status = 'published' WHERE slug = 'kitab-al-riyad'`,
    );
    expect(await canRead(t.db, "reader@example.com", "kitab-al-riyad")).toBe(
      true,
    );
  });
});

describe("work grants", () => {
  it("granting the work yields every volume", async () => {
    await grant(t.db, "reader@example.com", "work", "asaas", ADMIN, NOW);
    expect(await slugs("reader@example.com")).toEqual([
      "asaas-vol-01",
      "asaas-vol-02",
    ]);
  });

  it("granting one volume yields exactly that volume", async () => {
    await grant(t.db, "reader@example.com", "unit", "asaas-vol-01", ADMIN, NOW);
    expect(await slugs("reader@example.com")).toEqual(["asaas-vol-01"]);
  });

  it("covers a volume added after the grant was made", async () => {
    await grant(t.db, "reader@example.com", "work", "asaas", ADMIN, NOW);
    t.exec(`
      INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status)
      VALUES ('asaas-vol-03', 'Islamic', 'Volume 3', 'book', 'asaas', 33, 'published')
    `);
    expect(await slugs("reader@example.com")).toContain("asaas-vol-03");
  });

  it("never lists the work parent itself — it has nothing to read", async () => {
    await grant(t.db, "reader@example.com", "library", "*", ADMIN, NOW);
    expect(await slugs("reader@example.com")).not.toContain("asaas");
  });
});

describe("open to all", () => {
  it("reaches an invited person holding no grants, and only for that book", async () => {
    await setOpenToAll(t.db, "ayyuhal-walad", true, ADMIN, NOW);
    expect(await slugs("reader@example.com")).toEqual(["ayyuhal-walad"]);
  });

  it("does not expose a draft", async () => {
    await setOpenToAll(t.db, "kitab-al-riyad", true, ADMIN, NOW);
    expect(await slugs("reader@example.com")).toEqual([]);
  });

  it("can be turned back off", async () => {
    await setOpenToAll(t.db, "ayyuhal-walad", true, ADMIN, NOW);
    await setOpenToAll(t.db, "ayyuhal-walad", false, ADMIN, NOW);
    expect(await slugs("reader@example.com")).toEqual([]);
  });
});

describe("revocation", () => {
  it("takes a book away", async () => {
    await grant(
      t.db,
      "reader@example.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    await revokeGrant(
      t.db,
      "reader@example.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    expect(await slugs("reader@example.com")).toEqual([]);
  });

  it("can be re-granted afterwards", async () => {
    // The composite primary key makes a naive re-INSERT a constraint violation.
    // The UPSERT is what stops "give it back" from being a 500.
    await grant(
      t.db,
      "reader@example.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    await revokeGrant(
      t.db,
      "reader@example.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    await grant(
      t.db,
      "reader@example.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    expect(await slugs("reader@example.com")).toEqual(["ayyuhal-walad"]);
  });

  it("revoking sign-in keeps grants so re-inviting restores them", async () => {
    await grant(
      t.db,
      "reader@example.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    await revokeInvite(t.db, "reader@example.com", ADMIN, NOW);

    expect(await hasLiveInvite(t.db, "reader@example.com")).toBe(false);
    // The grant survives — this is the deliberate choice.
    expect(await slugs("reader@example.com")).toEqual(["ayyuhal-walad"]);

    await invite(t.db, "reader@example.com", ADMIN, {}, NOW);
    expect(await hasLiveInvite(t.db, "reader@example.com")).toBe(true);
    expect(await slugs("reader@example.com")).toEqual(["ayyuhal-walad"]);
  });

  it("revoking sign-in deletes that person's sessions", async () => {
    // Otherwise a 30-day cookie keeps working and "revoke" means "in a month".
    t.exec(`
      INSERT INTO user (id, name, email, emailVerified, createdAt, updatedAt)
        VALUES ('u1', 'Reader', 'reader@example.com', 1, '${NOW}', '${NOW}');
      INSERT INTO session (id, expiresAt, token, createdAt, updatedAt, userId)
        VALUES ('s1', '2099-01-01', 'tok', '${NOW}', '${NOW}', 'u1');
    `);

    await revokeInvite(t.db, "reader@example.com", ADMIN, NOW);

    const left = await t.db
      .prepare(`SELECT count(*) AS n FROM session`)
      .bind()
      .first<{ n: number }>();
    expect(left?.n).toBe(0);
  });
});

describe("email folding runs end to end", () => {
  it("matches a grant made with a Gmail alias against the canonical address", async () => {
    // The realistic mistake: Asif types the alias, Google returns the canonical
    // form. Without folding on the WRITE side the grant silently never matches.
    await invite(t.db, "Reader.Person+books@GoogleMail.com", ADMIN, {}, NOW);
    await grant(
      t.db,
      "Reader.Person+books@GoogleMail.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );

    expect(await canRead(t.db, "readerperson@gmail.com", "ayyuhal-walad")).toBe(
      true,
    );
    expect(await hasLiveInvite(t.db, "readerperson@gmail.com")).toBe(true);
  });

  it("does not fold dots on a non-Gmail domain", async () => {
    await grant(
      t.db,
      "first.last@company.com",
      "unit",
      "ayyuhal-walad",
      ADMIN,
      NOW,
    );
    expect(await canRead(t.db, "firstlast@company.com", "ayyuhal-walad")).toBe(
      false,
    );
    expect(await canRead(t.db, "first.last@company.com", "ayyuhal-walad")).toBe(
      true,
    );
  });
});

describe("schema guards", () => {
  it("refuses a library grant with a scope_id other than *", () => {
    expect(() =>
      t.exec(`INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
              VALUES ('a@b.com', 'library', 'ayyuhal-walad', 'x', '${NOW}')`),
    ).toThrow();
  });

  it("refuses an unknown scope_type", () => {
    expect(() =>
      t.exec(`INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
              VALUES ('a@b.com', 'everything', 'x', 'x', '${NOW}')`),
    ).toThrow();
  });

  it("refuses moving an existing account onto the admin address", () => {
    t.exec(`INSERT INTO user (id, name, email, emailVerified, createdAt, updatedAt)
            VALUES ('u9', 'Someone', 'someone@example.com', 1, '${NOW}', '${NOW}')`);
    expect(() =>
      t.exec(`UPDATE user SET email = '${ADMIN}' WHERE id = 'u9'`),
    ).toThrow();
  });
});
