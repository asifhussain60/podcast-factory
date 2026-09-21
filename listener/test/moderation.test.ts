import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { canRead, visibleUnits } from "../app/server/access.server";
import {
  isModeratorEmail,
  setModerator,
  setUnderModeration,
} from "../app/server/moderation.server";
import { grant, invite } from "../app/server/people.server";
import { createTestDb, type TestDb } from "./d1";

const NOW = "2026-09-20T12:00:00Z";
const ADMIN = "asifhussain60@gmail.com";

let t: TestDb;

/**
 * Three books: a live one, and two held for moderation — one still a DRAFT that nobody has
 * been given (the ordinary case: a book waits for moderation before anyone can read it),
 * and one that is published, open to everyone and granted to a reader, i.e. the case where
 * an ordinary reader would otherwise have full access.
 */
beforeEach(async () => {
  t = createTestDb();
  t.exec(`
    INSERT INTO content_unit (slug, bucket, title, kind, sort_order, status, open_to_all, under_moderation) VALUES
      ('live',            'Islamic', 'Live Book',       'book', 10, 'published', 0, 0),
      ('held-draft',      'Islamic', 'Held Draft',      'book', 20, 'draft',     0, 1),
      ('held-published',  'Islamic', 'Held Published',  'book', 30, 'published', 1, 1),
      ('held-archived',   'Islamic', 'Held Archived',   'book', 40, 'archived',  0, 1);
  `);
  await invite(t.db, "reader@example.com", ADMIN, {}, NOW);
  await invite(t.db, "mod@example.com", ADMIN, {}, NOW);
  await grant(t.db, "reader@example.com", "library", "*", ADMIN, NOW);
  await setModerator(t.db, "mod@example.com", true, ADMIN, NOW);
});

afterEach(() => t.close());

const slugs = async (email: string, moderator: boolean) =>
  (await visibleUnits(t.db, email, moderator)).map((u) => u.slug);

describe("an ordinary reader can never see a book held for moderation", () => {
  it("even with a whole-library grant, and even when the book is open to everyone", async () => {
    // `held-published` is published AND open_to_all AND covered by the library grant —
    // every ordinary route to it — and is still invisible.
    expect(await slugs("reader@example.com", false)).toEqual(["live"]);
  });

  it("gets a plain refusal for the slug, indistinguishable from a book that never existed", async () => {
    expect(
      await canRead(t.db, "reader@example.com", "held-published", false),
    ).toBe(false);
    expect(await canRead(t.db, "reader@example.com", "held-draft", false)).toBe(
      false,
    );
  });

  it("fails CLOSED when a caller forgets to pass the moderator flag at all", async () => {
    // The default is `false`, so a call site that was never updated shows nothing extra.
    const forgotten = (await visibleUnits(t.db, "mod@example.com")).map(
      (u) => u.slug,
    );
    expect(forgotten).not.toContain("held-draft");
    expect(forgotten).not.toContain("held-published");
  });
});

describe("a moderator sees what is held for them", () => {
  it("including a DRAFT nobody has been granted — the ordinary state of a book awaiting moderation", async () => {
    expect(await slugs("mod@example.com", true)).toEqual(
      expect.arrayContaining(["held-draft", "held-published"]),
    );
    expect(await canRead(t.db, "mod@example.com", "held-draft", true)).toBe(
      true,
    );
  });

  it("does not see an ARCHIVED book: retired is not held", async () => {
    expect(await slugs("mod@example.com", true)).not.toContain("held-archived");
  });

  it("gets no extra reach over books that are NOT held: a moderator is not a wider reader", async () => {
    // `live` is published but this moderator holds no grant and it is not open to all.
    expect(await slugs("mod@example.com", true)).not.toContain("live");
  });

  it("flags the row so the shelf can say why it looks different", async () => {
    const rows = await visibleUnits(t.db, "mod@example.com", true);
    expect(rows.find((u) => u.slug === "held-draft")?.underModeration).toBe(
      true,
    );
  });
});

describe("holding and releasing a book", () => {
  it("removes a live book from an ordinary reader at once, and restores it exactly on release", async () => {
    expect(await slugs("reader@example.com", false)).toEqual(["live"]);
    await setUnderModeration(t.db, "live", true, ADMIN, NOW);
    expect(await slugs("reader@example.com", false)).toEqual([]);
    await setUnderModeration(t.db, "live", false, ADMIN, NOW);
    expect(await slugs("reader@example.com", false)).toEqual(["live"]);
  });

  it("writes an audit event in the same batch", async () => {
    await setUnderModeration(t.db, "live", true, ADMIN, NOW);
    const row = await t.db
      .prepare(
        `SELECT action, subject FROM access_event WHERE action = 'hold-for-moderation'`,
      )
      .first<{ action: string; subject: string }>();
    expect(row).toEqual({ action: "hold-for-moderation", subject: "live" });
  });
});

describe("moderator rows", () => {
  it("resolve by the normalized address, so a Gmail dot or +tag cannot dodge or forge one", async () => {
    await setModerator(t.db, "New.Mod+tag@gmail.com", true, ADMIN, NOW);
    expect(await isModeratorEmail(t.db, "newmod@gmail.com")).toBe(true);
  });

  it("stop applying when revoked, and the revocation is audited", async () => {
    expect(await isModeratorEmail(t.db, "mod@example.com")).toBe(true);
    await setModerator(t.db, "mod@example.com", false, ADMIN, NOW);
    expect(await isModeratorEmail(t.db, "mod@example.com")).toBe(false);
    const row = await t.db
      .prepare(
        `SELECT 1 AS ok FROM access_event WHERE action = 'revoke-moderator'`,
      )
      .first<{ ok: number }>();
    expect(row).not.toBeNull();
  });

  it("fail closed: an unusable address and a missing table are both 'not a moderator'", async () => {
    expect(await isModeratorEmail(t.db, "not an address")).toBe(false);
    t.exec(`DROP TABLE moderator`);
    expect(await isModeratorEmail(t.db, "mod@example.com")).toBe(false);
  });
});
