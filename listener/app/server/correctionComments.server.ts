/**
 * Comments on a correction. Any moderator or admin may comment on ANY correction, whatever its
 * status - how moderators discuss each other's work without being able to change it.
 *
 * Split out of `corrections.server.ts` (size ceiling).
 */

import type { CorrectionComment } from "~/lib/corrections";
import {
  CorrectionError,
  DISPLAY,
  audit,
  load,
  nameOf,
  need,
  sameAddress,
  type Actor,
} from "./correctionKit.server";
import { normalizeEmail } from "./email.server";

/* ---- Comments -------------------------------------------------------------- */

const MAX_COMMENT = 2_000;

interface CommentRow {
  id: string;
  correction_id: string;
  author: string;
  author_name: string | null;
  body: string;
  created_at: string;
}

/**
 * Every live comment on one book's corrections, grouped by correction, oldest first.
 *
 * SHARED between moderators like the corrections themselves: every moderator and admin sees every
 * comment. Empty for anyone else without a query.
 */
export async function commentsFor(
  db: D1Database,
  actor: Actor,
  slug: string,
): Promise<Map<string, CorrectionComment[]>> {
  const grouped = new Map<string, CorrectionComment[]>();
  if (!actor.isModerator) return grouped;

  const { results } = await db
    .prepare(
      `SELECT c.id, c.correction_id, c.author, c.body, c.created_at, ${DISPLAY("i")} AS author_name
         FROM correction_comment c
         LEFT JOIN invite i ON i.email = c.author
        WHERE c.slug = ?1 AND c.deleted_at IS NULL
        ORDER BY c.created_at, c.id`,
    )
    .bind(slug)
    .all<CommentRow>();

  for (const r of results) {
    const mine = sameAddress(r.author, actor.email);
    const list = grouped.get(r.correction_id) ?? [];
    list.push({
      id: r.id,
      authorName: nameOf(r.author_name, r.author),
      body: r.body,
      createdAt: r.created_at,
      mine,
      canDelete: mine || actor.isAdmin,
    });
    grouped.set(r.correction_id, list);
  }
  return grouped;
}

/**
 * Comment on a correction. ANY moderator or admin, on ANY correction, whatever its status — a
 * correction an admin has decided can still be discussed. Commenting is not changing: it never
 * touches the correction, so it needs no authority over it.
 */
export async function addComment(
  db: D1Database,
  actor: Actor,
  slug: string,
  correctionId: string,
  body: unknown,
  now: string,
): Promise<string> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");
  await load(db, slug, correctionId); // 'missing' for another book's id or a deleted one
  const text = need(body, MAX_COMMENT, "the comment").trim();

  const id = crypto.randomUUID();
  await db.batch([
    db
      .prepare(
        `INSERT INTO correction_comment (id, correction_id, slug, author, body, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)`,
      )
      .bind(id, correctionId, slug, normalizeEmail(actor.email), text, now),
    audit(db, now, actor, "comment-correction", slug, correctionId, null),
  ]);
  return id;
}

/** Remove a comment. Its author, or an admin. Soft, like every other removal. */
export async function removeComment(
  db: D1Database,
  actor: Actor,
  slug: string,
  commentId: string,
  now: string,
): Promise<void> {
  if (!actor.isModerator)
    throw new CorrectionError("forbidden", "not a moderator");

  const row = await db
    .prepare(
      `SELECT author, correction_id FROM correction_comment
        WHERE id = ?1 AND slug = ?2 AND deleted_at IS NULL`,
    )
    .bind(commentId, slug)
    .first<{ author: string; correction_id: string }>();
  if (row === null) throw new CorrectionError("missing", "no such comment");
  if (!actor.isAdmin && !sameAddress(row.author, actor.email))
    throw new CorrectionError("forbidden", "not your comment");

  await db.batch([
    db
      .prepare(
        `UPDATE correction_comment SET deleted_at = ?2, deleted_by = ?3
          WHERE id = ?1 AND deleted_at IS NULL`,
      )
      .bind(commentId, now, normalizeEmail(actor.email)),
    audit(
      db,
      now,
      actor,
      "uncomment-correction",
      slug,
      row.correction_id,
      null,
    ),
  ]);
}
