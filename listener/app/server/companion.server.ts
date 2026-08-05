/**
 * The Ismaili Scholar Companion — read by ONE account, and by no other.
 *
 * Its own module rather than a function in catalog.server.ts, because that file
 * says of itself that nothing in it asks who may see what, and this asks exactly
 * that. A privileged read living among the unprivileged ones would make that
 * sentence false and the file no longer auditable at a glance.
 *
 * The gate is INSIDE the query function, not at its call site. A loader that
 * remembered to check would be a loader that could forget, and there will be
 * more callers than there are today; written this way there is one place to get
 * right and one place to test. It also means the DATABASE IS NEVER TOUCHED for
 * anyone else — the cards have no path to a response they do not belong in,
 * rather than a filter standing between them and one.
 *
 * "One account" is `viewer.isAdmin`, which layer 1 computed as
 * normalizeEmail(session email) === normalizeEmail(env.ADMIN_EMAIL) — the same
 * comparator every other privilege decision in this app goes through. There is
 * no second identity mechanism here and no `companion` column anywhere: no row
 * write can grant this, and a missing or unusable ADMIN_EMAIL fails closed.
 *
 * These notes are a private authoring layer. They are not the book, they are
 * not part of the reading edition, and nobody signed in has ever been offered
 * them — so the failure to avoid is not "someone is annoyed", it is a reader
 * being shown teaching notes written about them being taught.
 */

import type { Viewer } from "~/middleware/session";

export interface CompanionCard {
  id: string;
  /** Order within the chapter, as the notes were filed. */
  idx: number;
  /** The card's short label. Null when the note was saved without one. */
  title: string | null;
  /** The verbatim chapter sentence this card explains, if it names one. */
  quote: string | null;
  /** Rendered at publish time by the admin site's own card renderer. */
  bodyHtml: string;
  /** One entry per term, exactly as stored. Empty for most cards. */
  etymology: string[];
}

/**
 * The cards written against one chapter, in the order they were filed.
 *
 * Returns an empty list — having asked the database nothing at all — for every
 * viewer but the administrator, including a signed-out one.
 */
export async function companionFor(
  db: D1Database,
  viewer: Viewer | null,
  slug: string,
  anchorKey: string,
): Promise<CompanionCard[]> {
  if (viewer === null || !viewer.isAdmin) return [];

  const { results } = await db
    .prepare(
      `SELECT note_id, idx, title, quote, body_html, etymology FROM companion_note
       WHERE slug = ?1 AND anchor_key = ?2 ORDER BY idx`,
    )
    .bind(slug, anchorKey)
    .all<{
      note_id: string;
      idx: number;
      title: string | null;
      quote: string | null;
      body_html: string;
      etymology: string | null;
    }>();

  return results.map((row) => ({
    id: row.note_id,
    idx: row.idx,
    title: row.title,
    quote: row.quote,
    bodyHtml: row.body_html,
    etymology: parseEtymology(row.etymology),
  }));
}

/**
 * The etymology column, which is a JSON array of strings or nothing.
 *
 * Tolerant on purpose: a card whose etymology cannot be read is still a card
 * worth showing, and throwing here would take the whole chapter's panel down
 * over a field most notes do not have at all.
 */
function parseEtymology(raw: string | null): string[] {
  if (raw === null) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((row): row is string => typeof row === "string" && row.trim() !== "");
  } catch {
    return [];
  }
}
