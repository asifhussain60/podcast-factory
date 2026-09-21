import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { marksFor } from "../app/server/marks.server";
import {
  CorrectionError,
  decideCorrection,
  findOccurrences,
  listCorrections,
  proposeCorrection,
  proposeMany,
  triageSuggestion,
  type Actor,
} from "../app/server/corrections.server";
import {
  chapterProgress,
  claimChapter,
  moderationReadiness,
  setChapterReviewed,
} from "../app/server/moderationProgress.server";
import { sourceFor } from "../app/server/sourceOcr.server";
import {
  followSubstitutions,
  substitutionsFor,
} from "../app/server/substitutions.server";
import { createTestDb, type TestDb } from "./d1";

const T1 = "2026-09-20T10:00:00.000Z";
const T2 = "2026-09-20T11:00:00.000Z";
const T3 = "2026-09-20T12:00:00.000Z";
const SLUG = "isaf-al-talib";

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

let t: TestDb;
beforeEach(() => {
  t = createTestDb();
  t.exec(`
    INSERT INTO content_unit (slug, bucket, title, kind, sort_order, status)
      VALUES ('${SLUG}', 'Islamic', 'Isaf al-Talib', 'book', 1, 'published');
    INSERT INTO chapter (slug, anchor_key, idx, title, html, word_count) VALUES
      ('${SLUG}', 'ch-1', 1, '1. First',  '<p>x</p>', 1),
      ('${SLUG}', 'ch-2', 2, '2. Second', '<p>y</p>', 1),
      ('${SLUG}', 'ch-3', 3, '3. Third',  '<p>z</p>', 1);
  `);
});
afterEach(() => t.close());

const rows = () =>
  t.db
    .prepare(`SELECT id, status, updated_at FROM correction ORDER BY raised_at`)
    .all<{ id: string; status: string; updated_at: string }>()
    .then((r) => r.results);

const refused = async (p: Promise<unknown>, reason: string) => {
  await expect(p).rejects.toBeInstanceOf(CorrectionError);
  await p.catch((e: CorrectionError) => expect(e.reason).toBe(reason));
};

const suggest = (id = "sweep-1") =>
  t.exec(`INSERT INTO correction
    (id, slug, anchor_key, block_index, start_offset, end_offset, quote, proposed_text,
     rationale_html, kind, status, origin, certainty, raised_by, raised_at, updated_at)
    VALUES ('${id}', '${SLUG}', 'ch-1', 0, 0, 9, 'the neighbor who is a relative',
            'the neighbor who is a stranger', 'Found by the audit.', 'meaning',
            'suggested', 'sweep', 85, 'pipeline', '${T1}', '${T1}')`);

describe("pipeline suggestions", () => {
  it("are visible to every moderator, with the audit's own confidence", async () => {
    suggest();
    const [c] = await listCorrections(t.db, layla, SLUG);
    expect(c).toMatchObject({
      status: "suggested",
      origin: "sweep",
      certainty: 85,
    });
    expect(await listCorrections(t.db, reader, SLUG)).toEqual([]);
  });

  it("give any moderator triage authority, and never edit or delete authority", async () => {
    suggest();
    const [c] = await listCorrections(t.db, layla, SLUG);
    expect(c!.authority).toBe("triage");
  });

  it("are CONFIRMED into ordinary open corrections by any moderator — not accepted", async () => {
    suggest();
    await triageSuggestion(
      t.db,
      layla,
      SLUG,
      "sweep-1",
      "confirm",
      T1,
      null,
      T2,
    );
    const [c] = await listCorrections(t.db, omar, SLUG);
    expect(c!.status).toBe("open");
    // An admin still has to decide it.
    await refused(
      decideCorrection(t.db, layla, SLUG, "sweep-1", "accepted", T2, null, T3),
      "forbidden",
    );
  });

  it("can be dismissed with a reason", async () => {
    suggest();
    await triageSuggestion(
      t.db,
      omar,
      SLUG,
      "sweep-1",
      "dismiss",
      T1,
      "Book is right here.",
      T2,
    );
    const [c] = await listCorrections(t.db, layla, SLUG);
    expect(c).toMatchObject({
      status: "dismissed",
      decisionNote: "Book is right here.",
    });
  });

  it("refuses a stale confirm, an ordinary reader, and a row that is not a suggestion", async () => {
    suggest();
    await refused(
      triageSuggestion(
        t.db,
        layla,
        SLUG,
        "sweep-1",
        "confirm",
        "old",
        null,
        T2,
      ),
      "stale",
    );
    await refused(
      triageSuggestion(t.db, reader, SLUG, "sweep-1", "confirm", T1, null, T2),
      "forbidden",
    );
    await triageSuggestion(
      t.db,
      layla,
      SLUG,
      "sweep-1",
      "confirm",
      T1,
      null,
      T2,
    );
    await refused(
      triageSuggestion(t.db, omar, SLUG, "sweep-1", "confirm", T2, null, T3),
      "stale",
    );
  });

  it("an admin may accept one directly, skipping confirmation", async () => {
    suggest();
    await decideCorrection(
      t.db,
      asif,
      SLUG,
      "sweep-1",
      "accepted",
      T1,
      null,
      T2,
    );
    expect((await rows())[0]!.status).toBe("accepted");
  });
});

describe("AI review", () => {
  const review = (updated: string, verdict = "supports") =>
    t.exec(`INSERT INTO correction_review
      (correction_id, correction_updated, verdict, confidence, summary, suggested_text,
       detail_json, source_kind, model, reviewed_at)
      VALUES ('sweep-1', '${updated}', '${verdict}', 'high', 'The source agrees.', NULL,
              '{"checks":[{"id":"quote","result":"ok","note":"found once"},{"id":"bad","result":"???","note":"dropped"}]}',
              'scan', 'claude-test', '${T2}')`);

  it("is shown for the version it was given for, with only well-formed checks", async () => {
    suggest();
    review(T1);
    const [c] = await listCorrections(t.db, layla, SLUG);
    expect(c!.review).toMatchObject({
      verdict: "supports",
      confidence: "high",
      sourceKind: "scan",
    });
    expect(c!.review!.checks).toEqual([
      { id: "quote", result: "ok", note: "found once" },
    ]);
  });

  it("shows NO verdict once the proposal has changed since it was given", async () => {
    suggest();
    review(T1);
    await triageSuggestion(
      t.db,
      layla,
      SLUG,
      "sweep-1",
      "confirm",
      T1,
      null,
      T3,
    ); // new updated_at
    const [c] = await listCorrections(t.db, layla, SLUG);
    expect(c!.review).toBeNull();
  });
});

describe("fix everywhere", () => {
  const passage = (chapter: string, ordinal: number, text: string) =>
    t.exec(`INSERT INTO search_passage
      (slug, kind, anchor_key, heading, ordinal, quote, prefix, heading_fold, body_fold)
      VALUES ('${SLUG}', 'chapter', '${chapter}', 'H', ${ordinal}, '${text}', '', 'h', '${text.toLowerCase()}')`);

  beforeEach(() => {
    passage(
      "ch-1",
      0,
      "In the year the teacher said to him that patience is the first door.",
    );
    passage("ch-2", 3, "Later the teacher said to him nothing at all.");
    passage(
      "ch-3",
      1,
      "He said it twice: the teacher said to him, and the teacher said to him again.",
    );
    passage("ch-3", 2, "An unrelated paragraph.");
  });

  it("finds other places, skips the origin, and skips a block that holds it twice", async () => {
    const found = await findOccurrences(
      t.db,
      layla,
      SLUG,
      "the teacher said to him",
      {
        anchorKey: "ch-1",
        blockIndex: 0,
      },
    );
    expect(found.map((o) => [o.anchorKey, o.blockIndex])).toEqual([
      ["ch-2", 3],
    ]);
    expect(found[0]).toMatchObject({ startOffset: 6, endOffset: 29 });
  });

  it("finds nothing for an ordinary reader, or for a very short phrase", async () => {
    expect(
      await findOccurrences(t.db, reader, SLUG, "the teacher said to him", {
        anchorKey: "x",
        blockIndex: 0,
      }),
    ).toEqual([]);
    expect(
      await findOccurrences(t.db, layla, SLUG, "th", {
        anchorKey: "x",
        blockIndex: 0,
      }),
    ).toEqual([]);
  });

  it("leaves out a place a live correction already covers", async () => {
    await proposeCorrection(
      t.db,
      layla,
      SLUG,
      {
        anchorKey: "ch-2",
        blockIndex: 3,
        startOffset: 6,
        endOffset: 29,
        quote: "the teacher said to him",
        proposedText: "the teacher wrote to him",
        kind: "meaning",
      },
      T1,
    );
    expect(
      await findOccurrences(t.db, layla, SLUG, "the teacher said to him", {
        anchorKey: "ch-1",
        blockIndex: 0,
      }),
    ).toEqual([]);
  });

  it("raises one batch, all reviewed together, each carrying the same wording", async () => {
    const { batchId, ids } = await proposeMany(
      t.db,
      layla,
      SLUG,
      "the teacher said to him",
      [
        {
          anchorKey: "ch-2",
          blockIndex: 3,
          startOffset: 6,
          endOffset: 29,
          prefix: "Later ",
        },
        {
          anchorKey: "ch-3",
          blockIndex: 1,
          startOffset: 0,
          endOffset: 23,
          prefix: "",
        },
      ],
      {
        proposedText: "the teacher wrote to him",
        kind: "meaning",
        rationale: "",
      },
      T1,
    );
    expect(ids).toHaveLength(2);
    const all = await listCorrections(t.db, omar, SLUG);
    expect(all.map((c) => c.batchId)).toEqual([batchId, batchId]);
    expect(
      all.every(
        (c) =>
          c.proposedText === "the teacher wrote to him" &&
          c.quote === "the teacher said to him",
      ),
    ).toBe(true);
  });

  it("refuses an empty batch, a huge one, an identical replacement, and a reader", async () => {
    const item = {
      anchorKey: "ch-2",
      blockIndex: 3,
      startOffset: 6,
      endOffset: 29,
      prefix: "",
    };
    const ok = { proposedText: "the teacher wrote to him", kind: "meaning" };
    await refused(
      proposeMany(t.db, layla, SLUG, "the teacher said to him", [], ok, T1),
      "invalid",
    );
    await refused(
      proposeMany(
        t.db,
        layla,
        SLUG,
        "the teacher said to him",
        Array(41).fill(item),
        ok,
        T1,
      ),
      "invalid",
    );
    await refused(
      proposeMany(
        t.db,
        layla,
        SLUG,
        "the teacher said to him",
        [item],
        { ...ok, proposedText: "the teacher said to him" },
        T1,
      ),
      "invalid",
    );
    await refused(
      proposeMany(
        t.db,
        reader,
        SLUG,
        "the teacher said to him",
        [item],
        ok,
        T1,
      ),
      "forbidden",
    );
  });
});

describe("chapter review and readiness", () => {
  it("counts a book as not ready until every chapter is read AND nothing awaits a decision", async () => {
    expect(await moderationReadiness(t.db, SLUG)).toMatchObject({
      chapters: 3,
      reviewed: 0,
      ready: false,
    });
    for (const k of ["ch-1", "ch-2", "ch-3"])
      await setChapterReviewed(t.db, layla, SLUG, k, true, T1);
    expect((await moderationReadiness(t.db, SLUG)).ready).toBe(true);

    suggest(); // an undecided suggestion blocks release
    expect(await moderationReadiness(t.db, SLUG)).toMatchObject({
      reviewed: 3,
      undecided: 1,
      ready: false,
    });
  });

  it("lets only whoever marked a chapter (or an admin) take the mark back", async () => {
    await setChapterReviewed(t.db, layla, SLUG, "ch-1", true, T1);
    await refused(
      setChapterReviewed(t.db, omar, SLUG, "ch-1", false, T2),
      "forbidden",
    );
    await setChapterReviewed(t.db, asif, SLUG, "ch-1", false, T2);
    expect((await moderationReadiness(t.db, SLUG)).reviewed).toBe(0);
  });

  it("refuses a claim on a chapter somebody else is reading, and finishing ends the claim", async () => {
    await claimChapter(t.db, layla, SLUG, "ch-2", true, T1);
    await refused(
      claimChapter(t.db, omar, SLUG, "ch-2", true, T2),
      "forbidden",
    );
    await setChapterReviewed(t.db, layla, SLUG, "ch-2", true, T2);
    const ch2 = (await chapterProgress(t.db, layla, SLUG)).find(
      (c) => c.anchorKey === "ch-2",
    )!;
    expect(ch2).toMatchObject({
      claimedByName: null,
      reviewedByName: "layla",
      reviewedByMe: true,
    });
  });

  it("refuses an unknown chapter, and gives an ordinary reader nothing", async () => {
    await refused(
      setChapterReviewed(t.db, layla, SLUG, "nope", true, T1),
      "missing",
    );
    await refused(
      setChapterReviewed(t.db, reader, SLUG, "ch-1", true, T1),
      "forbidden",
    );
    expect(await chapterProgress(t.db, reader, SLUG)).toEqual([]);
  });
});

describe("the source pane", () => {
  beforeEach(() => {
    t.exec(`
      INSERT INTO source_page (slug, kind, page, text) VALUES
        ('${SLUG}', 'scan', 1, 'page one'), ('${SLUG}', 'scan', 2, 'page two'), ('${SLUG}', 'scan', 3, 'other chapter'),
        ('${SLUG}', 'extracted', 1, 'english one');
      INSERT INTO source_span (slug, anchor_key, kind, first_page, last_page, quality) VALUES
        ('${SLUG}', 'ch-1', 'scan', 1, 2, 'unreliable'), ('${SLUG}', 'ch-1', 'extracted', 1, 1, 'clean');
    `);
  });

  it("gives a moderator the chapter's own pages only, scan first, with its quality", async () => {
    const views = await sourceFor(t.db, layla, SLUG, "ch-1");
    expect(views.map((v) => v.kind)).toEqual(["scan", "extracted"]);
    expect(views[0]).toMatchObject({
      quality: "unreliable",
      firstPage: 1,
      lastPage: 2,
    });
    expect(views[0]!.pages.map((p) => p.text)).toEqual([
      "page one",
      "page two",
    ]);
  });

  it("gives an ordinary reader NOTHING — without asking the database", async () => {
    // Prove it never queried: drop the tables. A reader still gets [] rather than an error.
    t.exec(`DROP TABLE source_span; DROP TABLE source_page;`);
    expect(await sourceFor(t.db, reader, SLUG, "ch-1")).toEqual([]);
  });

  it("is a moderator's, and an admin's — and nobody else's", async () => {
    expect((await sourceFor(t.db, asif, SLUG, "ch-1")).length).toBe(2);
    expect(await sourceFor(t.db, layla, SLUG, "no-such-chapter")).toEqual([]);
  });
});

describe("applied corrections and readers' own marks", () => {
  const subs = (anchorKey = "ch-1") => [
    {
      anchorKey,
      oldText: "the teacher said to him",
      newText: "the teacher wrote to him",
    },
  ];

  it("follows an exact recorded substitution inside a stored quote", () => {
    expect(
      followSubstitutions("When the teacher said to him that", "ch-1", subs()),
    ).toBe("When the teacher wrote to him that");
  });

  it("never follows one from another chapter, and never guesses at a near miss", () => {
    expect(followSubstitutions("the teacher said to him", "ch-2", subs())).toBe(
      "the teacher said to him",
    );
    expect(followSubstitutions("the teacher says to him", "ch-1", subs())).toBe(
      "the teacher says to him",
    );
  });

  it("leaves a null or an untouched quote alone", () => {
    expect(followSubstitutions(null, "ch-1", subs())).toBeNull();
    expect(followSubstitutions("unrelated", "ch-1", [])).toBe("unrelated");
  });

  it("lets a reader's highlight on a corrected sentence still find it", async () => {
    t.exec(`
      INSERT INTO annotation (id, user_email, slug, anchor_key, block_index, start_offset, end_offset,
                              quote, prefix, colour, created_at, updated_at)
        VALUES ('11111111-1111-4111-8111-111111111111', 'reader@example.com', '${SLUG}', 'ch-1', 0, 5, 28,
                'the teacher said to him', 'When ', 'gold', '${T1}', '${T1}');
      INSERT INTO correction_applied (slug, anchor_key, old_text, new_text, applied_at)
        VALUES ('${SLUG}', 'ch-1', 'the teacher said to him', 'the teacher wrote to him', '${T2}');
    `);
    expect(await substitutionsFor(t.db, SLUG)).toHaveLength(1);
    const marks = await marksFor(t.db, "reader@example.com", SLUG);
    expect(marks.annotations[0]!.quote).toBe("the teacher wrote to him");
  });

  it("does not disturb marks when nothing was corrected", async () => {
    t.exec(`INSERT INTO annotation (id, user_email, slug, anchor_key, block_index, start_offset, end_offset,
                              quote, prefix, colour, created_at, updated_at)
        VALUES ('22222222-2222-4222-8222-222222222222', 'reader@example.com', '${SLUG}', 'ch-1', 0, 0, 5,
                'hello', '', 'sage', '${T1}', '${T1}')`);
    expect(
      (await marksFor(t.db, "reader@example.com", SLUG)).annotations[0]!.quote,
    ).toBe("hello");
  });
});
