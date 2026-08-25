/**
 * Every entitlement decision in the application.
 *
 * Nothing outside this module asks the database who may see what. The resolver
 * is one query rather than a set of checks scattered across loaders, because a
 * rule that exists in two places is a rule that will disagree with itself.
 *
 * Two properties this file must never lose:
 *
 *   1. `email` is always the NORMALIZED form and always comes from a verified
 *      session — never from a request body, route param or query string.
 *   2. The `status = 'published'` filter lives INSIDE the resolver. Hoisting it
 *      to callers is how a draft with open_to_all=1 leaks through a `.data`
 *      request that skipped whichever caller remembered to apply it.
 */

import { normalizeEmail, tryNormalizeEmail } from "./email.server";

export interface ContentUnit {
  slug: string;
  bucket: string;
  title: string;
  kind: "book" | "work";
  workSlug: string | null;
  status: "draft" | "published" | "archived";
  openToAll: boolean;
}

export interface Grant {
  scopeType: "unit" | "work" | "library";
  scopeId: string;
  grantedBy: string;
  grantedAt: string;
}

interface UnitRow {
  slug: string;
  bucket: string;
  title: string;
  kind: "book" | "work";
  work_slug: string | null;
  status: ContentUnit["status"];
  open_to_all: number;
}

const toUnit = (r: UnitRow): ContentUnit => ({
  slug: r.slug,
  bucket: r.bucket,
  title: r.title,
  kind: r.kind,
  workSlug: r.work_slug,
  status: r.status,
  openToAll: r.open_to_all === 1,
});

/**
 * The readable-content predicate, as SQL.
 *
 * A unit is readable when it is published AND ( it is open to all
 * OR granted directly OR its parent work is granted OR the whole library is
 * granted ). Work parents are excluded from results because they carry no
 * chapters — they exist to be *granted*, not read.
 *
 * `?1` is the normalized email, bound once and reused.
 *
 * EXPORTED so that a new reader of content — search, at the time of writing — can
 * JOIN to it rather than re-state it. That is the whole point: this expression is
 * the only place the entitlement rule is written, and a second query that decided
 * for itself which books to look in would be a second rule to keep in step. Any
 * module that reads passages, chapters or media MUST join to this and bind the
 * viewer's normalized email to `?1`. Nothing else may filter by slug alone.
 */
export const VISIBLE_SQL = `
  SELECT u.slug, u.bucket, u.title, u.kind, u.work_slug, u.status, u.open_to_all
  FROM content_unit u
  WHERE u.status = 'published'
    AND u.kind <> 'work'
    AND (
      u.open_to_all = 1
      OR EXISTS (
        SELECT 1 FROM access_grant g
        WHERE g.user_email = ?1
          AND g.revoked_at IS NULL
          AND (
               (g.scope_type = 'unit'    AND g.scope_id = u.slug)
            OR (g.scope_type = 'work'    AND g.scope_id = u.work_slug)
            OR (g.scope_type = 'library' AND g.scope_id = '*')
          )
      )
    )
`;

/**
 * Everything this person may actually read, most recent series first.
 *
 * Returns published units only. There is no parameter to relax that — an admin
 * previewing drafts uses `listCatalogForAdmin`, which is a different function
 * reached only from behind the admin gate.
 */
/**
 * Whether this address may sign in at all: an invite row, not revoked.
 *
 * Defined ONCE, here, and imported by both the per-request gate
 * (middleware/authed.ts) and Better Auth's sign-in hooks (auth.server.ts).
 * Those two answering differently is how a revoked person keeps a session.
 *
 * A malformed address simply has no invite — never a reason to fail open.
 */
export async function hasLiveInvite(
  db: D1Database,
  rawEmail: string,
): Promise<boolean> {
  const email = tryNormalizeEmail(rawEmail);
  if (email === null) return false;

  const row = await db
    .prepare(
      `SELECT 1 AS ok FROM invite WHERE email = ? AND revoked_at IS NULL LIMIT 1`,
    )
    .bind(email)
    .first<{ ok: number }>();

  return row !== null;
}

/** Identity of one unit, for the detail page. Says nothing about access. */
export async function unitBySlug(
  db: D1Database,
  slug: string,
): Promise<ContentUnit | null> {
  const row = await db
    .prepare(
      `SELECT slug, bucket, title, kind, work_slug, status, open_to_all
       FROM content_unit WHERE slug = ? LIMIT 1`,
    )
    .bind(slug)
    .first<UnitRow>();

  return row === null ? null : toUnit(row);
}

export async function visibleUnits(
  db: D1Database,
  email: string,
): Promise<ContentUnit[]> {
  const { results } = await db
    .prepare(`${VISIBLE_SQL} ORDER BY u.sort_order, u.title`)
    .bind(normalizeEmail(email))
    .all<UnitRow>();

  return results.map(toUnit);
}

/**
 * The `kind='work'` parent's own title, for each work_slug the caller asks
 * about — the multi-volume set card's header when one exists.
 *
 * A work parent is excluded from `VISIBLE_SQL` on purpose (it carries no
 * chapters, nothing to read) and carries no entitlement check of its own
 * here, on purpose too: a caller may pass ONLY work_slugs already proven
 * visible by `visibleUnits()` returning 2+ volumes under it, and access to
 * THOSE volumes is what already proved this reader may see this set — the
 * parent row's own `status`/`open_to_all` add no real access decision on
 * top of that, they only decide whether a title is ever returned at all.
 * That distinction is not hypothetical: `sync_listener_work_groups.py`
 * documents, deliberately, that it never sets either column on a parent row
 * it creates ("those are the admin's privilege bits and this script has no
 * opinion on visibility") — and nothing else in this codebase sets them
 * either, so a parent-level entitlement check here can never once pass for
 * any set the grouping tool creates. An earlier version of this function
 * re-ran the full entitlement predicate anyway, which is why every
 * multi-volume card fell back to a single volume's own title instead of the
 * set's. This is a narrow, obviously-safe read precisely because it trusts
 * the caller's own contract instead of re-deriving it.
 *
 * A work parent's own `slug` IS the `work_slug` its volumes carry (its own
 * `work_slug` column is NULL — see migration 0002).
 */
export async function workTitles(
  db: D1Database,
  workSlugs: string[],
): Promise<Map<string, string>> {
  const titles = new Map<string, string>();
  if (workSlugs.length === 0) return titles;

  const placeholders = workSlugs.map((_, i) => `?${i + 1}`).join(", ");

  const { results } = await db
    .prepare(
      `SELECT u.slug, u.title
         FROM content_unit u
        WHERE u.kind = 'work'
          AND u.slug IN (${placeholders})`,
    )
    .bind(...workSlugs)
    .all<{ slug: string; title: string }>();

  for (const r of results) titles.set(r.slug, r.title);
  return titles;
}

/**
 * Whether this person may read this one unit.
 *
 * Deliberately re-runs the same predicate against a single slug rather than
 * calling visibleUnits() and searching it — one SQL expression, so the list view
 * and the detail gate cannot drift apart. Callers turn `false` into a 404.
 */
export async function canRead(
  db: D1Database,
  email: string,
  slug: string,
): Promise<boolean> {
  const row = await db
    .prepare(`SELECT 1 AS ok FROM (${VISIBLE_SQL}) u WHERE u.slug = ?2 LIMIT 1`)
    .bind(normalizeEmail(email), slug)
    .first<{ ok: number }>();

  return row !== null;
}

// ---------------------------------------------------------------------------
// Admin-only. Reachable exclusively from behind the admin gate in
// app/middleware/admin.ts. The people/invite/grant administration that used to
// live here moved to people.server.ts on 2026-08-17.
// ---------------------------------------------------------------------------

/** The whole catalog, drafts included, for the provisioning screens. */
export async function listCatalogForAdmin(
  db: D1Database,
): Promise<ContentUnit[]> {
  const { results } = await db
    .prepare(
      `SELECT slug, bucket, title, kind, work_slug, status, open_to_all
       FROM content_unit ORDER BY sort_order, title`,
    )
    .all<UnitRow>();

  return results.map(toUnit);
}

/**
 * One audit row on its own, for an action with nothing else to write.
 *
 * Everything else here writes its event inside the same `batch` as the row it
 * describes, which is what keeps the two from disagreeing. Simulation has no row
 * — it is a cookie — so it is the one action whose only trace IS the event, and
 * it needs a way to leave one. Impersonation with no record is the last feature
 * that should be quiet.
 */
export async function recordEvent(
  db: D1Database,
  action: string,
  subject: string,
  now: string,
  actor: string,
): Promise<void> {
  await event(db, now, actor, action, subject, null, null, null).run();
}

/**
 * One audit row, as a statement for the caller to put in its own `db.batch`.
 *
 * EXPORTED since 2026-08-17 for people.server.ts, which writes the invitation
 * and grant mutations. It is deliberately a statement rather than a write: every
 * caller batches it with the row it describes, so an action and its audit record
 * land together or not at all.
 */
export function event(
  db: D1Database,
  now: string,
  actor: string,
  action: string,
  subject: string,
  scopeType: string | null,
  scopeId: string | null,
  detail: string | null,
) {
  return db
    .prepare(
      `INSERT INTO access_event (at, actor, action, subject, scope_type, scope_id, detail)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    )
    .bind(now, actor, action, subject, scopeType, scopeId, detail);
}
