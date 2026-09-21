/**
 * Moderators, and the books held back for them.
 *
 * Its own module, like `companion.server.ts`, because `catalog.server.ts` states of itself
 * that nothing in it asks who may see what — and this is entirely about who may.
 *
 * Two properties this file must keep:
 *   1. `isModeratorEmail` FAILS CLOSED. Any error, a malformed address, a missing table:
 *      the answer is "not a moderator". The lookup runs on every signed-in request, so a
 *      thrown exception here would otherwise be a way to take the whole site down, and a
 *      default of `true` would be a way to leak it.
 *   2. Nothing here ever grants ADMIN. Admin is `ADMIN_EMAIL` and nothing else; the caller
 *      (session middleware) ORs the two together. A moderator row can never widen into it.
 */

import { event } from "./access.server";
import { normalizeEmail, tryNormalizeEmail } from "./email.server";

export async function isModeratorEmail(
  db: D1Database,
  rawEmail: string,
): Promise<boolean> {
  const email = tryNormalizeEmail(rawEmail);
  if (email === null) return false;

  try {
    const row = await db
      .prepare(
        `SELECT 1 AS ok FROM moderator WHERE user_email = ?1 AND revoked_at IS NULL LIMIT 1`,
      )
      .bind(email)
      .first<{ ok: number }>();
    return row !== null;
  } catch {
    return false;
  }
}

/** Make somebody a moderator, or take it away. Admin session only. Audited in the same batch. */
export async function setModerator(
  db: D1Database,
  rawEmail: string,
  on: boolean,
  actor: string,
  now: string,
): Promise<void> {
  const email = normalizeEmail(rawEmail);

  await db.batch([
    on
      ? db
          .prepare(
            `INSERT INTO moderator (user_email, granted_by, granted_at, revoked_at)
             VALUES (?1, ?2, ?3, NULL)
             ON CONFLICT(user_email) DO UPDATE SET
               granted_by = ?2, granted_at = ?3, revoked_at = NULL`,
          )
          .bind(email, actor, now)
      : db
          .prepare(`UPDATE moderator SET revoked_at = ?2 WHERE user_email = ?1`)
          .bind(email, now),
    event(
      db,
      now,
      actor,
      on ? "grant-moderator" : "revoke-moderator",
      email,
      null,
      null,
      null,
    ),
  ]);
}

/**
 * Hold a book back for moderation, or release it. Admin session only.
 *
 * Written ONLY from here. `publish_to_listener.py` never names this column — a test greps
 * for exactly that — because it runs unattended and this is a privilege bit.
 */
export async function setUnderModeration(
  db: D1Database,
  slug: string,
  on: boolean,
  actor: string,
  now: string,
): Promise<void> {
  await db.batch([
    db
      .prepare(`UPDATE content_unit SET under_moderation = ?2 WHERE slug = ?1`)
      .bind(slug, on ? 1 : 0),
    event(
      db,
      now,
      actor,
      on ? "hold-for-moderation" : "release-from-moderation",
      slug,
      null,
      null,
      null,
    ),
  ]);
}

/**
 * How many people have reading state in each book — a bookmark, a note or a place held.
 *
 * Shown BEFORE a book is held back, because holding a live book takes it away from every
 * one of them at once. Their marks are kept, not deleted: the book is hidden, so the marks
 * are hidden with it and return exactly as they were when it is released.
 */
export async function readersByBook(
  db: D1Database,
): Promise<Map<string, number>> {
  const { results } = await db
    .prepare(
      `SELECT slug, count(DISTINCT user_email) AS n FROM (
         SELECT slug, user_email FROM reading_progress
         UNION SELECT slug, user_email FROM bookmark   WHERE deleted_at IS NULL
         UNION SELECT slug, user_email FROM annotation WHERE deleted_at IS NULL
       ) GROUP BY slug`,
    )
    .all<{ slug: string; n: number }>();

  return new Map(results.map((r) => [r.slug, r.n]));
}

export interface ModeratorRow {
  email: string;
  displayName: string;
  grantedBy: string;
  grantedAt: string;
  /** Whether they have been invited, and so can actually sign in to use it. */
  invited: boolean;
}

/** Everyone holding a live moderator row, newest first. Admin screen only. */
export async function listModerators(db: D1Database): Promise<ModeratorRow[]> {
  const { results } = await db
    .prepare(
      `SELECT m.user_email AS email, m.granted_by, m.granted_at,
              COALESCE(NULLIF(TRIM(COALESCE(i.first_name, '') || ' ' || COALESCE(i.last_name, '')), ''),
                       i.email_raw, m.user_email) AS display_name,
              (i.email IS NOT NULL AND i.revoked_at IS NULL) AS invited
         FROM moderator m LEFT JOIN invite i ON i.email = m.user_email
        WHERE m.revoked_at IS NULL
        ORDER BY m.granted_at DESC`,
    )
    .all<{
      email: string;
      granted_by: string;
      granted_at: string;
      display_name: string;
      invited: number;
    }>();

  return results.map((r) => ({
    email: r.email,
    displayName: r.display_name,
    grantedBy: r.granted_by,
    grantedAt: r.granted_at,
    invited: r.invited === 1,
  }));
}
