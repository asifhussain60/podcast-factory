/**
 * Following an applied correction, so a reader's own marks survive it.
 *
 * A highlight, a note and a Companion card are all located in the chapter by the words they
 * quote. Correct one of those sentences and, without this, every mark on it would silently
 * fall into the "orphaned" list — the tool that improves the book would damage readers' data.
 *
 * `correction_applied` records each EXACT substitution the repo-side apply step made. Here a
 * stored quote that contains the old wording is read back with the new wording in its place, so
 * the reader finds the passage and re-anchors it. Only an exact recorded substitution is ever
 * followed: never a fuzzy match, never a guess. The table is written by the apply step alone;
 * the Worker only reads it.
 */

export interface Substitution {
  anchorKey: string;
  oldText: string;
  newText: string;
}

export async function substitutionsFor(
  db: D1Database,
  slug: string,
): Promise<Substitution[]> {
  const { results } = await db
    .prepare(
      `SELECT anchor_key, old_text, new_text FROM correction_applied
        WHERE slug = ?1 ORDER BY applied_at`,
    )
    .bind(slug)
    .all<{ anchor_key: string; old_text: string; new_text: string }>();

  return results.map((r) => ({
    anchorKey: r.anchor_key,
    oldText: r.old_text,
    newText: r.new_text,
  }));
}

/**
 * `text` as it now reads. Applied in the order the corrections were made, so a passage corrected
 * twice follows both. Scoped to the chapter the correction was made in.
 */
export function followSubstitutions(
  text: string | null,
  anchorKey: string,
  substitutions: Substitution[],
): string | null {
  if (text === null || substitutions.length === 0) return text;

  let out = text;
  for (const s of substitutions)
    if (
      s.anchorKey === anchorKey &&
      s.oldText !== "" &&
      out.includes(s.oldText)
    )
      out = out.replace(s.oldText, s.newText);
  return out;
}
