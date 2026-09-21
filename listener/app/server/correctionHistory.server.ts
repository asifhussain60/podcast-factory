/**
 * The history of corrections — every action taken on them, oldest first, for moderators and
 * admins only.
 *
 * It is READ from `access_event`, the audit trail every correction action already writes into,
 * so history costs no new table and cannot disagree with what actually happened: a change and
 * its record land in one `db.batch`. Like `sourceOcr.server.ts`, the gate is INSIDE the function
 * and returns before any query, so no route can forget it. Addresses never leave: an actor is
 * shown by name, and `mine` tells the panel which entries are the viewer's own.
 */
import type { CorrectionEvent } from "~/lib/correctionHistory";
import {
  DISPLAY,
  nameOf,
  sameAddress,
  type Actor,
} from "./correctionKit.server";

interface Raw {
  at: string;
  actor: string;
  action: string;
  scope_id: string;
  detail: string | null;
  actor_name: string | null;
}

const parse = (detail: string | null): Record<string, unknown> | null => {
  if (detail === null) return null;
  try {
    const value: unknown = JSON.parse(detail);
    return typeof value === "object" && value !== null
      ? (value as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
};

/** One correction's history, or — with `id` null — every live correction on the book. */
export async function historyFor(
  db: D1Database,
  actor: Actor,
  slug: string,
  id: string | null,
): Promise<CorrectionEvent[]> {
  if (!actor.isModerator) return [];

  const { results } = await db
    .prepare(
      `SELECT e.at, e.actor, e.action, e.scope_id, e.detail,
              ${DISPLAY("i")} AS actor_name
         FROM access_event e
         JOIN correction c ON c.id = e.scope_id AND c.slug = ?1 AND c.deleted_at IS NULL
         LEFT JOIN invite i ON i.email = e.actor
        WHERE e.scope_type = 'correction' AND e.subject = ?1
          AND (?2 IS NULL OR e.scope_id = ?2)
        ORDER BY e.at, e.id`,
    )
    .bind(slug, id)
    .all<Raw>();

  return results.map((row) => ({
    correctionId: row.scope_id,
    at: row.at,
    action: row.action,
    actorName:
      row.actor === "pipeline"
        ? "Pipeline audit"
        : nameOf(row.actor_name, row.actor),
    mine: sameAddress(row.actor, actor.email),
    detail: parse(row.detail),
  }));
}
