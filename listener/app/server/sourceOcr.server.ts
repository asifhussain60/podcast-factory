/**
 * The source a chapter was made from — for moderators checking a correction against it.
 *
 * Its own module, like `companion.server.ts`, and for the same reason: `catalog.server.ts` states
 * of itself that nothing in it asks who may see what, and this is entirely about who may. The
 * gate is INSIDE the function and it returns before querying, so there is one place to get it
 * right and nothing for a caller to forget.
 *
 * It must never be joined to `source_reference`. That table is reader-visible by design — a page
 * range and headings — and carries no gate; the verbatim source text is copyrighted prose that no
 * reader-facing surface may reproduce. Separate tables, separate module, separate reader.
 */

import type { SourcePage, SourceView } from "~/lib/corrections";
import type { Actor } from "./corrections.server";

/** Both kinds for a chapter (scan first), or nothing for anyone who is not a moderator or admin. */
export async function sourceFor(
  db: D1Database,
  actor: Actor,
  slug: string,
  anchorKey: string,
): Promise<SourceView[]> {
  if (!actor.isModerator) return [];

  const { results: spans } = await db
    .prepare(
      `SELECT kind, first_page, last_page, quality FROM source_span
        WHERE slug = ?1 AND anchor_key = ?2 ORDER BY kind DESC`,
    )
    .bind(slug, anchorKey)
    .all<{
      kind: SourceView["kind"];
      first_page: number;
      last_page: number;
      quality: SourceView["quality"];
    }>();

  const views: SourceView[] = [];
  for (const span of spans) {
    const { results } = await db
      .prepare(
        `SELECT page, text FROM source_page
          WHERE slug = ?1 AND kind = ?2 AND page BETWEEN ?3 AND ?4 ORDER BY page`,
      )
      .bind(slug, span.kind, span.first_page, span.last_page)
      .all<SourcePage>();

    views.push({
      kind: span.kind,
      firstPage: span.first_page,
      lastPage: span.last_page,
      quality: span.quality,
      pages: results,
    });
  }
  return views;
}
