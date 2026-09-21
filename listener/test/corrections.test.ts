import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  CorrectionError,
  authority,
  decideCorrection,
  listCorrections,
  proposeCorrection,
  removeCorrection,
  reviseCorrection,
  type Actor,
} from "../app/server/corrections.server";
import { createTestDb, type TestDb } from "./d1";

const T1 = "2026-09-20T10:00:00.000Z";
const T2 = "2026-09-20T11:00:00.000Z";
const T3 = "2026-09-20T12:00:00.000Z";

const layla: Actor = {
  email: "layla@example.com",
  isAdmin: false,
  isModerator: true,
};
const omar: Actor = {
  email: "omar@example.com",
  isAdmin: false,
  isModerator: true,
};
const asif: Actor = {
  email: "asif@example.com",
  isAdmin: true,
  isModerator: true,
};
const reader: Actor = {
  email: "reader@example.com",
  isAdmin: false,
  isModerator: false,
};

const SLUG = "isaf-al-talib";
const input = (over: Record<string, unknown> = {}) => ({
  anchorKey: "chapter-4",
  blockIndex: 2,
  startOffset: 10,
  endOffset: 40,
  quote: "the teacher said to him",
  prefix: "When the teacher heard, ",
  proposedText: "the teacher wrote to him",
  rationale: "<p>The source says wrote.</p>",
  kind: "meaning",
  ...over,
});

let t: TestDb;
beforeEach(() => {
  t = createTestDb();
});
afterEach(() => t.close());

const raise = (by: Actor, over: Record<string, unknown> = {}) =>
  proposeCorrection(t.db, by, SLUG, input(over), T1);

const rowOf = (id: string) =>
  t.db
    .prepare(`SELECT * FROM correction WHERE id = ?`)
    .bind(id)
    .first<Record<string, unknown>>();

const events = async (action: string) =>
  (
    await t.db
      .prepare(`SELECT actor, detail FROM access_event WHERE action = ?`)
      .bind(action)
      .all<{ actor: string; detail: string | null }>()
  ).results;

const refused = async (p: Promise<unknown>, reason: string) => {
  await expect(p).rejects.toBeInstanceOf(CorrectionError);
  await p.catch((e: CorrectionError) => expect(e.reason).toBe(reason));
};

describe("reading is SHARED between moderators — the inverse of a reader's private marks", () => {
  it("shows every moderator and admin the same list", async () => {
    await raise(layla);
    await raise(omar, {
      startOffset: 50,
      endOffset: 70,
      quote: "another passage",
    });

    const asLayla = await listCorrections(t.db, layla, SLUG);
    const asOmar = await listCorrections(t.db, omar, SLUG);
    const asAsif = await listCorrections(t.db, asif, SLUG);

    expect(asLayla).toHaveLength(2);
    expect(asOmar.map((c) => c.id)).toEqual(asLayla.map((c) => c.id));
    expect(asAsif.map((c) => c.id)).toEqual(asLayla.map((c) => c.id));
  });

  it("shows an ordinary reader NOTHING, without querying for them", async () => {
    await raise(layla);
    expect(await listCorrections(t.db, reader, SLUG)).toEqual([]);
  });

  it("marks which are yours, and never puts another person's address in the payload", async () => {
    await raise(layla);
    const seenByOmar = await listCorrections(t.db, omar, SLUG);
    expect(seenByOmar[0]!.mine).toBe(false);
    expect(JSON.stringify(seenByOmar)).not.toContain("layla@example.com");
    expect(seenByOmar[0]!.raisedByName).toBe("layla");
    expect((await listCorrections(t.db, layla, SLUG))[0]!.mine).toBe(true);
  });
});

describe("the authority table", () => {
  const open = { raised_by: "layla@example.com", status: "open" as const };

  it("an ordinary reader has none, whatever they hold", () => {
    expect(authority(reader, open)).toBe("none");
  });
  it("a moderator owns their own while it is open, and no one else's", () => {
    expect(authority(layla, open)).toBe("own");
    expect(authority(omar, open)).toBe("none");
  });
  it("a moderator's own LOCKS once an admin has decided", () => {
    expect(authority(layla, { ...open, status: "accepted" })).toBe("none");
    expect(authority(layla, { ...open, status: "dismissed" })).toBe("none");
  });
  it("an admin has full authority always", () => {
    expect(authority(asif, { ...open, status: "accepted" })).toBe("full");
  });
  it("compares the NORMALIZED address, so a Gmail dot cannot claim or dodge ownership", () => {
    const g: Actor = {
      email: "L.Ayla+x@gmail.com",
      isAdmin: false,
      isModerator: true,
    };
    expect(authority(g, { raised_by: "layla@gmail.com", status: "open" })).toBe(
      "own",
    );
  });
});

describe("raising", () => {
  it("lets a moderator and an admin, and refuses a reader", async () => {
    expect(await raise(layla)).toMatch(/^[0-9a-f-]{36}$/);
    expect(await raise(asif)).toBeTruthy();
    await refused(raise(reader), "forbidden");
  });

  it("refuses a replacement identical to the book, an empty one, and an unknown kind", async () => {
    await refused(
      raise(layla, { proposedText: "the teacher said to him" }),
      "invalid",
    );
    await refused(raise(layla, { proposedText: "   " }), "invalid");
    await refused(raise(layla, { kind: "vibes" }), "invalid");
    await refused(raise(layla, { startOffset: 40, endOffset: 40 }), "invalid");
  });

  it("cleans the reason on WRITE — stored markup is rendered to an admin", async () => {
    const id = await raise(layla, {
      rationale: `<p onclick="steal()">ok</p><script>alert(1)</script><b>bold</b>`,
    });
    const stored = String((await rowOf(id))!.rationale_html);
    // The sanitiser neutralises by ESCAPING what is not on its allowlist, so the words
    // survive as inert text. What must never survive is a live tag or a live handler.
    expect(stored).not.toContain("<script");
    expect(stored).not.toMatch(/<\w+[^>]*\son\w+=/i);
    expect(stored).toContain("&lt;script&gt;");
  });

  it("audits it", async () => {
    await raise(layla);
    expect(await events("raise-correction")).toHaveLength(1);
  });
});

describe("editing", () => {
  it("lets the raiser edit their own while open", async () => {
    const id = await raise(layla);
    await reviseCorrection(
      t.db,
      layla,
      SLUG,
      id,
      { proposedText: "the teacher wrote", kind: "typo" },
      T2,
    );
    expect((await rowOf(id))!.proposed_text).toBe("the teacher wrote");
  });

  it("refuses another moderator", async () => {
    const id = await raise(layla);
    await refused(
      reviseCorrection(
        t.db,
        omar,
        SLUG,
        id,
        { proposedText: "x y z", kind: "typo" },
        T2,
      ),
      "forbidden",
    );
  });

  it("refuses the raiser once an admin has decided", async () => {
    const id = await raise(layla);
    await decideCorrection(t.db, asif, SLUG, id, "accepted", T1, null, T2);
    await refused(
      reviseCorrection(
        t.db,
        layla,
        SLUG,
        id,
        { proposedText: "changed after approval", kind: "typo" },
        T3,
      ),
      "forbidden",
    );
  });

  it("lets an admin edit anyone's, and records what it WAS so the raiser is never blindsided", async () => {
    const id = await raise(layla);
    await reviseCorrection(
      t.db,
      asif,
      SLUG,
      id,
      { proposedText: "the teacher wrote unto him", kind: "meaning" },
      T2,
    );
    const [e] = await events("revise-correction");
    expect(e!.actor).toBe("asif@example.com");
    expect(JSON.parse(e!.detail!)).toEqual({ was: "the teacher wrote to him" });
  });
});

describe("removing", () => {
  it("lets the raiser withdraw their own open one; it is SOFT — the row stays", async () => {
    const id = await raise(layla);
    await removeCorrection(t.db, layla, SLUG, id, T2);
    expect(await listCorrections(t.db, layla, SLUG)).toEqual([]);
    expect((await rowOf(id))!.deleted_by).toBe("layla@example.com");
    expect(await events("withdraw-correction")).toHaveLength(1);
  });

  it("refuses another moderator, and refuses the raiser after a decision", async () => {
    const id = await raise(layla);
    await refused(removeCorrection(t.db, omar, SLUG, id, T2), "forbidden");
    await decideCorrection(t.db, asif, SLUG, id, "dismissed", T1, null, T2);
    await refused(removeCorrection(t.db, layla, SLUG, id, T3), "forbidden");
  });

  it("lets an admin delete any, and audits it as a delete", async () => {
    const id = await raise(layla);
    await decideCorrection(t.db, asif, SLUG, id, "accepted", T1, null, T2);
    await removeCorrection(t.db, asif, SLUG, id, T3);
    expect(await events("delete-correction")).toHaveLength(1);
    expect(await listCorrections(t.db, asif, SLUG)).toEqual([]);
  });
});

describe("deciding", () => {
  it("is for admins only — a moderator cannot accept even their own", async () => {
    const id = await raise(layla);
    await refused(
      decideCorrection(t.db, layla, SLUG, id, "accepted", T1, null, T2),
      "forbidden",
    );
    await refused(
      decideCorrection(t.db, omar, SLUG, id, "dismissed", T1, null, T2),
      "forbidden",
    );
  });

  it("records who decided, when, and the reason given", async () => {
    const id = await raise(layla);
    await decideCorrection(
      t.db,
      asif,
      SLUG,
      id,
      "dismissed",
      T1,
      "  The source agrees with the book.  ",
      T2,
    );
    const row = (await rowOf(id))!;
    expect(row).toMatchObject({
      status: "dismissed",
      decided_by: "asif@example.com",
      decision_note: "The source agrees with the book.",
    });
    expect(await events("dismiss-correction")).toHaveLength(1);
  });

  it("REFUSES a stale accept: the proposal changed after the admin looked", async () => {
    const id = await raise(layla); // updated_at = T1 — what the admin saw
    await reviseCorrection(
      t.db,
      layla,
      SLUG,
      id,
      { proposedText: "quite different now", kind: "typo" },
      T2,
    );
    await refused(
      decideCorrection(t.db, asif, SLUG, id, "accepted", T1, null, T3),
      "stale",
    );
    // And nothing was decided, and no accept was audited.
    expect((await rowOf(id))!.status).toBe("open");
    expect(await events("accept-correction")).toHaveLength(0);
  });

  it("cannot decide twice", async () => {
    const id = await raise(layla);
    await decideCorrection(t.db, asif, SLUG, id, "accepted", T1, null, T2);
    await refused(
      decideCorrection(t.db, asif, SLUG, id, "dismissed", T2, null, T3),
      "stale",
    );
  });

  it("answers 'missing' for another book's id, so a slug cannot reach a foreign correction", async () => {
    const id = await raise(layla);
    await refused(
      decideCorrection(
        t.db,
        asif,
        "some-other-book",
        id,
        "accepted",
        T1,
        null,
        T2,
      ),
      "missing",
    );
  });
});
