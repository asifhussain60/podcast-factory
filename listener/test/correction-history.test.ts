import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { historyMarkdown } from "../app/lib/correctionHistory";
import { historyFor } from "../app/server/correctionHistory.server";
import {
  addComment,
  decideCorrection,
  listCorrections,
  proposeCorrection,
  reviseCorrection,
  type Actor,
} from "../app/server/corrections.server";
import { createTestDb, type TestDb } from "./d1";

const T = (n: number) => `2026-09-20T1${n}:00:00.000Z`;
const mk = (email: string, admin = false, mod = true): Actor => ({
  email,
  isAdmin: admin,
  isModerator: mod,
});
const layla = mk("layla@example.com");
const omar = mk("omar@example.com");
const asif = mk("asif@example.com", true);
const reader = mk("reader@example.com", false, false);
const SLUG = "isaf-al-talib";

let t: TestDb;
beforeEach(() => {
  t = createTestDb();
});
afterEach(() => t.close());

const raise = () =>
  proposeCorrection(
    t.db,
    layla,
    SLUG,
    {
      anchorKey: "chapter-1",
      blockIndex: 0,
      startOffset: 0,
      endOffset: 10,
      quote: "the teacher",
      prefix: "",
      proposedText: "the master",
      rationale: "<p>Source says master.</p>",
      kind: "meaning",
    },
    T(0),
  );

describe("correction history", () => {
  it("records the wording before and after EVERY revision, even the raiser's own", async () => {
    const id = await raise();
    await reviseCorrection(
      t.db,
      layla,
      SLUG,
      id,
      {
        proposedText: "the guide",
        kind: "meaning",
        rationale: "<p>Better.</p>",
      },
      T(1),
    );
    const [raised, revised] = await historyFor(t.db, omar, SLUG, id);
    expect(raised!.detail).toEqual({
      now: {
        text: "the master",
        kind: "meaning",
        reason: "<p>Source says master.</p>",
      },
    });
    expect(revised!.detail).toMatchObject({
      was: { text: "the master" },
      now: { text: "the guide", reason: "<p>Better.</p>" },
    });
  });

  it("is oldest first, complete, and names people instead of addresses", async () => {
    const id = await raise();
    await addComment(t.db, omar, SLUG, id, "agreed", T(1));
    await reviseCorrection(
      t.db,
      asif,
      SLUG,
      id,
      { proposedText: "the guide", kind: "meaning" },
      T(2),
    );
    const [c] = await listCorrections(t.db, asif, SLUG);
    await decideCorrection(
      t.db,
      asif,
      SLUG,
      id,
      "accepted",
      (await listCorrections(t.db, asif, SLUG))[0]!.updatedAt,
      "ok",
      T(3),
    );
    expect(c).toBeDefined();

    const all = await historyFor(t.db, layla, SLUG, null);
    expect(all.map((e) => e.action)).toEqual([
      "raise-correction",
      "comment-correction",
      "revise-correction",
      "accept-correction",
    ]);
    expect(all[1]!.detail).toEqual({ body: "agreed" });
    expect(all[3]!.detail).toEqual({ note: "ok" });
    expect(all.map((e) => e.mine)).toEqual([true, false, false, false]);
    expect(JSON.stringify(all)).not.toContain("@");
  });

  it("returns nothing to a non-moderator, without querying", async () => {
    const id = await raise();
    expect(await historyFor(t.db, reader, SLUG, id)).toEqual([]);
    expect(await historyFor(t.db, reader, SLUG, null)).toEqual([]);
  });

  it("does not leak another book's history through a borrowed id", async () => {
    const id = await raise();
    expect(await historyFor(t.db, layla, "some-other-book", id)).toEqual([]);
  });
});

describe("copy for AI", () => {
  it("is self-contained Markdown: passage, proposal, reason, then the timeline", async () => {
    const id = await raise();
    await reviseCorrection(
      t.db,
      asif,
      SLUG,
      id,
      { proposedText: "the guide", kind: "typo" },
      T(1),
    );
    const items = await listCorrections(t.db, asif, SLUG);
    const md = historyMarkdown(
      "Isʿāf al-Ṭālib",
      items,
      await historyFor(t.db, asif, SLUG, null),
    );
    expect(md).toContain("# Corrections — Isʿāf al-Ṭālib");
    expect(md).toContain("Book prints: “the teacher”");
    expect(md).toContain("Proposed: “the guide”");
    expect(md).toContain("### History");
    expect(md).toContain("raised it");
    expect(md).toContain("“the master” → “the guide”");
    expect(md).not.toContain("<p>");
    expect(md).not.toContain("@");
  });
});
