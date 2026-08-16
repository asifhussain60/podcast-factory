/**
 * The source-reference toggle's data — proof that a chapter traces to a
 * specific span of the original source book.
 *
 * Reader-visible by design, unlike `companionFor` in `companion.server.ts`:
 * this is written to be shown to whoever can already open the chapter, so
 * there is no viewer check here — the row's own existence (or absence) is
 * the only gate. A book with no `source_reference` rows for a chapter (19 of
 * 27 books have none at all) resolves to `null`, which is what keeps the
 * reader's toolbar toggle off the page entirely rather than rendering an
 * empty state.
 */

export interface SourceReference {
  /** e.g. "pp. 1-5". Never the verbatim source text — see the migration. */
  pageRange: string;
  /** The original book's own heading(s) for this chapter's span. */
  headings: string[];
}

/**
 * The source reference for one chapter, or `null` when this book's edition
 * has no crosswalk (or this particular chapter has no matching row).
 */
export async function sourceReferenceFor(
  db: D1Database,
  slug: string,
  anchorKey: string,
): Promise<SourceReference | null> {
  const row = await db
    .prepare(
      `SELECT page_range, headings FROM source_reference
       WHERE slug = ?1 AND anchor_key = ?2`,
    )
    .bind(slug, anchorKey)
    .first<{ page_range: string; headings: string }>();

  if (row === null) return null;

  return {
    pageRange: row.page_range,
    headings: parseHeadings(row.headings),
  };
}

function parseHeadings(raw: string): string[] {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (heading): heading is string =>
        typeof heading === "string" && heading.trim() !== "",
    );
  } catch {
    return [];
  }
}
