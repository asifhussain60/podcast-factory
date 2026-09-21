import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { canRead, visibleUnits } from "../app/server/access.server";
import {
  CorrectionError,
  addComment,
  decideCorrection,
  listCorrections,
  proposeCorrection,
  removeComment,
  removeCorrection,
  reviseCorrection,
  type Actor,
} from "../app/server/corrections.server";
import {
  setModerator,
  setUnderModeration,
} from "../app/server/moderation.server";
import { grant, invite } from "../app/server/people.server";
import { createTestDb, type TestDb } from "./d1";

/**
 * The four rules, in the words they were asked for, each proved against the real SQL:
 *
 *  1. Ordinary users must not see a book held for moderation.
 *  2. The correction feature is available to admins AND moderators (and nobody else).
 *  3. An admin can add, modify and delete any correction.
 *  4. Every moderator can see every other moderator's corrections and COMMENT on them, but cannot
 *     change them; a moderator can change only their OWN.
 */
const T = (n: number) => `2026-09-21T10:0${n}:00.000Z`;
const SLUG = "isaf-al-talib";

const actor = (email: string, isAdmin = false, isModerator = true): Actor => ({
  email,
  isAdmin,
  isModerator,
});
const admin = actor("asif@example.com", true);
const layla = actor("layla@example.com");
const omar = actor("omar@example.com");
const reader = actor("reader@example.com", false, false);

let t: TestDb;
beforeEach(async () => {
  t = createTestDb();
  t.exec(`INSERT INTO content_unit (slug, bucket, title, kind, sort_order, status, open_to_all)
            VALUES ('${SLUG}', 'Islamic', 'Isaf al-Talib', 'book', 1, 'draft', 0),
                   ('live', 'Islamic', 'A Live Book', 'book', 2, 'published', 1);`);
  for (const a of [layla, omar, reader])
    await invite(t.db, a.email, "asif@example.com", {}, T(0));
  await grant(t.db, reader.email, "library", "*", "asif@example.com", T(0));
  await setModerator(t.db, layla.email, true, "asif@example.com", T(0));
  await setModerator(t.db, omar.email, true, "asif@example.com", T(0));
  await setUnderModeration(t.db, SLUG, true, "asif@example.com", T(0));
});
afterEach(() => t.close());

const proposal = {
  anchorKey: "ch-1",
  blockIndex: 0,
  startOffset: 0,
  endOffset: 12,
  quote: "the teacher said",
  proposedText: "the teacher wrote",
  kind: "meaning",
};
const raise = (by: Actor) => proposeCorrection(t.db, by, SLUG, proposal, T(1));
const revision = { proposedText: "the teacher wrote to him", kind: "meaning" };
const denied = async (p: Promise<unknown>) => {
  await expect(p).rejects.toBeInstanceOf(CorrectionError);
  await p.catch((e: CorrectionError) => expect(e.reason).toBe("forbidden"));
};

describe("1. ordinary users must not see a held book", () => {
  it("hides it from a reader who holds a whole-library grant", async () => {
    expect(
      (await visibleUnits(t.db, reader.email, false)).map((u) => u.slug),
    ).toEqual(["live"]);
    expect(await canRead(t.db, reader.email, SLUG, false)).toBe(false);
  });
  it("shows it to moderators and admins, though it is a draft nobody was granted", async () => {
    for (const who of [layla, omar, admin]) {
      expect(await canRead(t.db, who.email, SLUG, who.isModerator)).toBe(true);
    }
  });
});

describe("2. the feature is available to admins and moderators, and nobody else", () => {
  it("lets admins and moderators raise corrections and see the list", async () => {
    for (const who of [admin, layla, omar]) await raise(who);
    for (const who of [admin, layla, omar])
      expect(await listCorrections(t.db, who, SLUG)).toHaveLength(3);
  });
  it("gives a reader nothing: no list, no raising, no commenting", async () => {
    const id = await raise(layla);
    expect(await listCorrections(t.db, reader, SLUG)).toEqual([]);
    await denied(raise(reader));
    await denied(addComment(t.db, reader, SLUG, id, "hello", T(2)));
  });
});

describe("3. an admin can add, modify and delete any correction", () => {
  it("adds their own", async () => {
    expect(await raise(admin)).toBeTruthy();
  });
  it("modifies a moderator's — whatever its status", async () => {
    const id = await raise(layla);
    await reviseCorrection(t.db, admin, SLUG, id, revision, T(2));
    await decideCorrection(t.db, admin, SLUG, id, "accepted", T(2), null, T(3));
    await reviseCorrection(
      t.db,
      admin,
      SLUG,
      id,
      { ...revision, proposedText: "the teacher wrote unto him" },
      T(4),
    );
    expect((await listCorrections(t.db, admin, SLUG))[0]!.proposedText).toBe(
      "the teacher wrote unto him",
    );
  });
  it("deletes a moderator's — even one already decided", async () => {
    const id = await raise(layla);
    await decideCorrection(
      t.db,
      admin,
      SLUG,
      id,
      "dismissed",
      T(1),
      null,
      T(2),
    );
    await removeCorrection(t.db, admin, SLUG, id, T(3));
    expect(await listCorrections(t.db, admin, SLUG)).toEqual([]);
  });
  it("shows the admin full authority over every correction", async () => {
    await raise(layla);
    await raise(omar);
    expect(
      (await listCorrections(t.db, admin, SLUG)).map((c) => c.authority),
    ).toEqual(["full", "full"]);
  });
  it("can remove any moderator's comment", async () => {
    const id = await raise(layla);
    const said = await addComment(t.db, omar, SLUG, id, "I disagree", T(2));
    await removeComment(t.db, admin, SLUG, said, T(3));
    expect((await listCorrections(t.db, admin, SLUG))[0]!.comments).toEqual([]);
  });
});

describe("4. moderators see and comment on each other's corrections, but change only their own", () => {
  it("lets every moderator see another moderator's corrections", async () => {
    await raise(layla);
    expect(await listCorrections(t.db, omar, SLUG)).toHaveLength(1);
  });

  it("lets a moderator COMMENT on another's correction — even after an admin has decided it", async () => {
    const id = await raise(layla);
    await decideCorrection(t.db, admin, SLUG, id, "accepted", T(1), null, T(2));
    await addComment(t.db, omar, SLUG, id, "This matches page 14.", T(3));
    const seenByLayla = (await listCorrections(t.db, layla, SLUG))[0]!;
    expect(seenByLayla.comments.map((c) => [c.authorName, c.body])).toEqual([
      ["omar", "This matches page 14."],
    ]);
  });

  it("commenting changes NOTHING about the correction", async () => {
    const id = await raise(layla);
    const before = (await listCorrections(t.db, layla, SLUG))[0]!;
    await addComment(t.db, omar, SLUG, id, "Looks right.", T(2));
    const after = (await listCorrections(t.db, layla, SLUG))[0]!;
    expect({ ...after, comments: [] }).toEqual({ ...before, comments: [] });
  });

  it("does NOT let a moderator edit, withdraw, delete or decide another moderator's correction", async () => {
    const id = await raise(layla);
    await denied(reviseCorrection(t.db, omar, SLUG, id, revision, T(2)));
    await denied(removeCorrection(t.db, omar, SLUG, id, T(2)));
    await denied(
      decideCorrection(t.db, omar, SLUG, id, "accepted", T(1), null, T(2)),
    );
    expect((await listCorrections(t.db, omar, SLUG))[0]!.authority).toBe(
      "none",
    );
  });

  it("lets a moderator change their OWN — edit and withdraw — while it is open", async () => {
    const id = await raise(layla);
    expect((await listCorrections(t.db, layla, SLUG))[0]!.authority).toBe(
      "own",
    );
    await reviseCorrection(t.db, layla, SLUG, id, revision, T(2));
    await removeCorrection(t.db, layla, SLUG, id, T(3));
    expect(await listCorrections(t.db, layla, SLUG)).toEqual([]);
  });

  it("does not let a moderator decide even their own — only an admin accepts or dismisses", async () => {
    const id = await raise(layla);
    await denied(
      decideCorrection(t.db, layla, SLUG, id, "accepted", T(1), null, T(2)),
    );
  });

  it("locks a moderator's own correction once an admin has decided it (the admin's approved text cannot shift)", async () => {
    const id = await raise(layla);
    await decideCorrection(t.db, admin, SLUG, id, "accepted", T(1), null, T(2));
    await denied(reviseCorrection(t.db, layla, SLUG, id, revision, T(3)));
  });

  it("lets a moderator remove their OWN comment but not another's", async () => {
    const id = await raise(layla);
    const mine = await addComment(t.db, omar, SLUG, id, "mine", T(2));
    const theirs = await addComment(t.db, layla, SLUG, id, "theirs", T(3));
    await denied(removeComment(t.db, omar, SLUG, theirs, T(4)));
    await removeComment(t.db, omar, SLUG, mine, T(4));
    expect(
      (await listCorrections(t.db, omar, SLUG))[0]!.comments.map((c) => c.body),
    ).toEqual(["theirs"]);
  });

  it("marks, for each viewer, which comments they may remove", async () => {
    const id = await raise(layla);
    await addComment(t.db, omar, SLUG, id, "from omar", T(2));
    const asOmar = (await listCorrections(t.db, omar, SLUG))[0]!.comments[0]!;
    const asLayla = (await listCorrections(t.db, layla, SLUG))[0]!.comments[0]!;
    const asAdmin = (await listCorrections(t.db, admin, SLUG))[0]!.comments[0]!;
    expect([asOmar.canDelete, asLayla.canDelete, asAdmin.canDelete]).toEqual([
      true,
      false,
      true,
    ]);
  });

  it("refuses an empty or oversized comment, and a comment on another book's correction", async () => {
    const id = await raise(layla);
    await expect(
      addComment(t.db, omar, SLUG, id, "   ", T(2)),
    ).rejects.toMatchObject({ reason: "invalid" });
    await expect(
      addComment(t.db, omar, SLUG, id, "x".repeat(2001), T(2)),
    ).rejects.toMatchObject({ reason: "invalid" });
    await expect(
      addComment(t.db, omar, "some-other-book", id, "hi", T(2)),
    ).rejects.toMatchObject({ reason: "missing" });
  });

  it("audits every comment and every removal", async () => {
    const id = await raise(layla);
    const said = await addComment(t.db, omar, SLUG, id, "note", T(2));
    await removeComment(t.db, omar, SLUG, said, T(3));
    const actions = (
      await t.db
        .prepare(
          `SELECT action FROM access_event WHERE action LIKE '%comment%'`,
        )
        .all<{ action: string }>()
    ).results.map((r) => r.action);
    expect(actions).toEqual(["comment-correction", "uncomment-correction"]);
  });
});
