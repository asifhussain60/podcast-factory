/**
 * How far a book's moderation has got: which chapters a person has read against the source, and
 * whether the book is ready to come out of moderation.
 *
 * Without this a book with no corrections is indistinguishable from a book nobody read, and
 * there is no honest way to say "moderation is finished". A chapter is marked reviewed by a
 * moderator or admin; a chapter can also be CLAIMED, so two people do not read the same one.
 *
 * Moderators and admins only — every function returns nothing for anyone else without querying.
 */

import type { ChapterProgress } from "~/lib/corrections";
import { event } from "./access.server";
import { CorrectionError, type Actor } from "./corrections.server";
import { normalizeEmail } from "./email.server";

/**
 * The name to show for whoever holds a mark: their recorded name, else the part of their address
 * before the `@`. An email is a privilege bit in this application and is not shown as such.
 */
const displaySql = (invite: string, column: string) =>
  `COALESCE(NULLIF(TRIM(COALESCE(${invite}.first_name, '') || ' ' || COALESCE(${invite}.last_name, '')), ''),
            substr(cr.${column}, 1, instr(cr.${column}, '@') - 1))`;

export async function chapterProgress(
  db: D1Database,
  actor: Actor,
  slug: string,
): Promise<ChapterProgress[]> {
  if (!actor.isModerator) return [];

  const me = normalizeEmail(actor.email);
  const { results } = await db
    .prepare(
      `SELECT c.anchor_key, c.title,
              ${displaySql("ri", "reviewed_by")} AS reviewed_name, cr.reviewed_by,
              ${displaySql("ci", "claimed_by")}  AS claimed_name,  cr.claimed_by
         FROM chapter c
         LEFT JOIN chapter_review cr ON cr.slug = c.slug AND cr.anchor_key = c.anchor_key
         LEFT JOIN invite ri ON ri.email = cr.reviewed_by
         LEFT JOIN invite ci ON ci.email = cr.claimed_by
        WHERE c.slug = ?1
        ORDER BY c.idx`,
    )
    .bind(slug)
    .all<{
      anchor_key: string;
      title: string;
      reviewed_name: string | null;
      reviewed_by: string | null;
      claimed_name: string | null;
      claimed_by: string | null;
    }>();

  return results.map((r) => ({
    anchorKey: r.anchor_key,
    title: r.title,
    reviewedByName:
      r.reviewed_by === null ? null : (r.reviewed_name ?? "Someone"),
    claimedByName: r.claimed_by === null ? null : (r.claimed_name ?? "Someone"),
    reviewedByMe:
      r.reviewed_by !== null && normalizeEmail(r.reviewed_by) === me,
    claimedByMe: r.claimed_by !== null && normalizeEmail(r.claimed_by) === me,
  }));
}

async function chapterExists(db: D1Database, slug: string, anchorKey: string) {
  const row = await db
    .prepare(`SELECT 1 AS ok FROM chapter WHERE slug = ?1 AND anchor_key = ?2`)
    .bind(slug, anchorKey)
    .first<{ ok: number }>();
  if (row === null) throw new CorrectionError("missing", "no such chapter");
}

/**
 * Mark a chapter reviewed, or take the mark back. Anyone moderating may mark; only whoever marked
 * it (or an admin) may take it back, so one person cannot quietly undo another's read.
 */
export async function setChapterReviewed(
  db: D1Database,
  actor: Actor,
  slug: string,
  anchorKey: string,
  on: boolean,
  now: string,
): Promise<void> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");
  await chapterExists(db, slug, anchorKey);
  const me = normalizeEmail(actor.email);

  if (!on && !actor.isAdmin) {
    const row = await db
      .prepare(
        `SELECT reviewed_by FROM chapter_review WHERE slug = ?1 AND anchor_key = ?2`,
      )
      .bind(slug, anchorKey)
      .first<{ reviewed_by: string | null }>();
    if (row?.reviewed_by && normalizeEmail(row.reviewed_by) !== me)
      throw new CorrectionError("forbidden", "somebody else marked this one");
  }

  await db.batch([
    db
      .prepare(
        `INSERT INTO chapter_review (slug, anchor_key, reviewed_by, reviewed_at)
         VALUES (?1, ?2, ?3, ?4)
         ON CONFLICT(slug, anchor_key) DO UPDATE SET
           reviewed_by = excluded.reviewed_by, reviewed_at = excluded.reviewed_at,
           -- Finishing a chapter ends the claim on it.
           claimed_by = CASE WHEN excluded.reviewed_by IS NULL THEN claimed_by ELSE NULL END,
           claimed_at = CASE WHEN excluded.reviewed_by IS NULL THEN claimed_at ELSE NULL END`,
      )
      .bind(slug, anchorKey, on ? me : null, on ? now : null),
    event(
      db,
      now,
      me,
      on ? "review-chapter" : "unreview-chapter",
      slug,
      "chapter",
      anchorKey,
      null,
    ),
  ]);
}

/** Say "I am reading this one", so two people do not. The claim of a chapter somebody else holds is refused. */
export async function claimChapter(
  db: D1Database,
  actor: Actor,
  slug: string,
  anchorKey: string,
  on: boolean,
  now: string,
): Promise<void> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");
  await chapterExists(db, slug, anchorKey);
  const me = normalizeEmail(actor.email);

  const row = await db
    .prepare(
      `SELECT claimed_by FROM chapter_review WHERE slug = ?1 AND anchor_key = ?2`,
    )
    .bind(slug, anchorKey)
    .first<{ claimed_by: string | null }>();
  const holder = row?.claimed_by ? normalizeEmail(row.claimed_by) : null;
  if (holder !== null && holder !== me && !actor.isAdmin)
    throw new CorrectionError("forbidden", "somebody else is reading this one");

  await db.batch([
    db
      .prepare(
        `INSERT INTO chapter_review (slug, anchor_key, claimed_by, claimed_at)
         VALUES (?1, ?2, ?3, ?4)
         ON CONFLICT(slug, anchor_key) DO UPDATE SET
           claimed_by = excluded.claimed_by, claimed_at = excluded.claimed_at`,
      )
      .bind(slug, anchorKey, on ? me : null, on ? now : null),
    event(
      db,
      now,
      me,
      on ? "claim-chapter" : "release-chapter",
      slug,
      "chapter",
      anchorKey,
      null,
    ),
  ]);
}

export interface Readiness {
  chapters: number;
  reviewed: number;
  /** Corrections still waiting on a decision — `suggested` and `open`. */
  undecided: number;
  /** Every chapter read, and nothing left to decide. */
  ready: boolean;
}

/** What still stands between a held book and its release. Admin screen. */
export async function moderationReadiness(
  db: D1Database,
  slug: string,
): Promise<Readiness> {
  const row = await db
    .prepare(
      `SELECT
         (SELECT count(*) FROM chapter WHERE slug = ?1) AS chapters,
         (SELECT count(*) FROM chapter_review cr JOIN chapter c
            ON c.slug = cr.slug AND c.anchor_key = cr.anchor_key
           WHERE cr.slug = ?1 AND cr.reviewed_by IS NOT NULL) AS reviewed,
         (SELECT count(*) FROM correction
           WHERE slug = ?1 AND deleted_at IS NULL AND status IN ('suggested', 'open')) AS undecided`,
    )
    .bind(slug)
    .first<{ chapters: number; reviewed: number; undecided: number }>();

  const chapters = row?.chapters ?? 0;
  const reviewed = row?.reviewed ?? 0;
  const undecided = row?.undecided ?? 0;
  return {
    chapters,
    reviewed,
    undecided,
    ready: chapters > 0 && reviewed === chapters && undecided === 0,
  };
}
