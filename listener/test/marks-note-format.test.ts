import { describe, expect, it } from "vitest";

import { saveAnnotation, saveEpisodeNote } from "../app/server/marks.server";
import { createTestDb, type TestDb } from "./d1";

/**
 * The sanitizer gate `saveAnnotation`/`saveEpisodeNote` now run every `note`
 * through — one owner throughout, never cross-user (that is
 * `marks-isolation.test.ts`'s job, and duplicating it here would only dilute
 * it). What this file pins: rich HTML built from the toolbar's four tokens
 * survives; anything outside them is neutralized to visible text rather than
 * silently dropped; and both write paths apply the same gate, since a
 * divergence between them would mean an annotation and an episode note admit
 * different content through the same `note` shape.
 */

const ME = "reader@example.com";
const BOOK = "book-a";
const ID = "33333333-3333-4333-8333-333333333333";
const NOW = "2026-08-04T12:00:00Z";

async function annotationNoteOf(test: TestDb, id: string): Promise<string | null> {
  const row = await test.db
    .prepare(`SELECT note FROM annotation WHERE id = ?1`)
    .bind(id)
    .first<{ note: string | null }>();
  return row?.note ?? null;
}

async function episodeNoteOf(test: TestDb, id: string): Promise<string | null> {
  const row = await test.db
    .prepare(`SELECT note FROM episode_note WHERE id = ?1`)
    .bind(id)
    .first<{ note: string | null }>();
  return row?.note ?? null;
}

describe("saveAnnotation note sanitization", () => {
  it("stores rich HTML from the allowed toolbar tokens verbatim", async () => {
    const test = createTestDb();
    await saveAnnotation(
      test.db,
      ME,
      BOOK,
      {
        id: ID,
        anchorKey: "one",
        blockIndex: 1,
        startOffset: 0,
        endOffset: 5,
        quote: "mine",
        colour: "gold",
        note: "<p><strong>bold</strong> and a list:</p><ul><li>a</li><li>b</li></ul>",
      },
      NOW,
    );
    expect(await annotationNoteOf(test, ID)).toBe(
      "<p><strong>bold</strong> and a list:</p><ul><li>a</li><li>b</li></ul>",
    );
  });

  it("neutralizes a disallowed tag mixed with allowed ones, keeping the allowed part intact", async () => {
    const test = createTestDb();
    await saveAnnotation(
      test.db,
      ME,
      BOOK,
      {
        id: ID,
        anchorKey: "one",
        blockIndex: 1,
        startOffset: 0,
        endOffset: 5,
        quote: "mine",
        colour: "gold",
        note: "<p><strong>safe</strong></p><script>alert(1)</script>",
      },
      NOW,
    );
    const stored = await annotationNoteOf(test, ID);
    expect(stored).not.toBeNull();
    expect(stored).toContain("<strong>safe</strong>");
    expect(stored).not.toContain("<script>");
  });

  it("stores a freshly-typed legacy-shaped plain-text note as escaped text, not reinterpreted markup", async () => {
    const test = createTestDb();
    await saveAnnotation(
      test.db,
      ME,
      BOOK,
      {
        id: ID,
        anchorKey: "one",
        blockIndex: 1,
        startOffset: 0,
        endOffset: 5,
        quote: "mine",
        colour: "gold",
        note: "a < b and c > d",
      },
      NOW,
    );
    expect(await annotationNoteOf(test, ID)).toBe("a &lt; b and c &gt; d");
  });
});

describe("saveEpisodeNote note sanitization", () => {
  it("stores rich HTML from the allowed toolbar tokens verbatim", async () => {
    const test = createTestDb();
    await saveEpisodeNote(
      test.db,
      ME,
      BOOK,
      {
        id: ID,
        number: 1,
        seconds: 30,
        quote: "what was said",
        note: "<p><em>a thought</em></p><ol><li>first</li><li>second</li></ol>",
      },
      NOW,
    );
    expect(await episodeNoteOf(test, ID)).toBe(
      "<p><em>a thought</em></p><ol><li>first</li><li>second</li></ol>",
    );
  });

  it("neutralizes a disallowed tag the same way `saveAnnotation` does — the gate must not diverge", async () => {
    const test = createTestDb();
    await saveEpisodeNote(
      test.db,
      ME,
      BOOK,
      { id: ID, number: 1, seconds: 30, quote: "what was said", note: '<img src=x onerror="alert(1)">' },
      NOW,
    );
    const stored = await episodeNoteOf(test, ID);
    expect(stored).not.toBeNull();
    expect(stored).not.toContain("<img");
    expect(stored).toContain("alert(1)");
  });

  it("stores a freshly-typed legacy-shaped plain-text note as escaped text", async () => {
    const test = createTestDb();
    await saveEpisodeNote(
      test.db,
      ME,
      BOOK,
      { id: ID, number: 1, seconds: 30, quote: "what was said", note: "a < b and c > d" },
      NOW,
    );
    expect(await episodeNoteOf(test, ID)).toBe("a &lt; b and c &gt; d");
  });
});
