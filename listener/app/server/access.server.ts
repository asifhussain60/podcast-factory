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
 */
const VISIBLE_SQL = `
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
export async function hasLiveInvite(db: D1Database, rawEmail: string): Promise<boolean> {
  const email = tryNormalizeEmail(rawEmail);
  if (email === null) return false;

  const row = await db
    .prepare(`SELECT 1 AS ok FROM invite WHERE email = ? AND revoked_at IS NULL LIMIT 1`)
    .bind(email)
    .first<{ ok: number }>();

  return row !== null;
}

/** Identity of one unit, for the detail page. Says nothing about access. */
export async function unitBySlug(db: D1Database, slug: string): Promise<ContentUnit | null> {
  const row = await db
    .prepare(
      `SELECT slug, bucket, title, kind, work_slug, status, open_to_all
       FROM content_unit WHERE slug = ? LIMIT 1`,
    )
    .bind(slug)
    .first<UnitRow>();

  return row === null ? null : toUnit(row);
}

export async function visibleUnits(db: D1Database, email: string): Promise<ContentUnit[]> {
  const { results } = await db
    .prepare(`${VISIBLE_SQL} ORDER BY u.sort_order, u.title`)
    .bind(normalizeEmail(email))
    .all<UnitRow>();

  return results.map(toUnit);
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
// Admin-only. Every function below is reachable exclusively from behind the
// admin gate in app/middleware/admin.ts.
// ---------------------------------------------------------------------------

/** The whole catalog, drafts included, for the provisioning screens. */
export async function listCatalogForAdmin(db: D1Database): Promise<ContentUnit[]> {
  const { results } = await db
    .prepare(
      `SELECT slug, bucket, title, kind, work_slug, status, open_to_all
       FROM content_unit ORDER BY sort_order, title`,
    )
    .all<UnitRow>();

  return results.map(toUnit);
}

export interface Person {
  email: string;
  emailRaw: string;
  invitedAt: string;
  redeemedAt: string | null;
  revokedAt: string | null;
  note: string | null;
  grantCount: number;
}

export async function listPeople(db: D1Database): Promise<Person[]> {
  const { results } = await db
    .prepare(
      `SELECT i.email, i.email_raw, i.invited_at, i.redeemed_at, i.revoked_at, i.note,
              (SELECT count(*) FROM access_grant g
               WHERE g.user_email = i.email AND g.revoked_at IS NULL) AS grant_count
       FROM invite i ORDER BY i.invited_at DESC`,
    )
    .all<{
      email: string;
      email_raw: string;
      invited_at: string;
      redeemed_at: string | null;
      revoked_at: string | null;
      note: string | null;
      grant_count: number;
    }>();

  return results.map((r) => ({
    email: r.email,
    emailRaw: r.email_raw,
    invitedAt: r.invited_at,
    redeemedAt: r.redeemed_at,
    revokedAt: r.revoked_at,
    note: r.note,
    grantCount: r.grant_count,
  }));
}

/** The live grants held by one person. */
export async function grantsFor(db: D1Database, email: string): Promise<Grant[]> {
  const { results } = await db
    .prepare(
      `SELECT scope_type, scope_id, granted_by, granted_at
       FROM access_grant WHERE user_email = ? AND revoked_at IS NULL`,
    )
    .bind(normalizeEmail(email))
    .all<{ scope_type: Grant["scopeType"]; scope_id: string; granted_by: string; granted_at: string }>();

  return results.map((r) => ({
    scopeType: r.scope_type,
    scopeId: r.scope_id,
    grantedBy: r.granted_by,
    grantedAt: r.granted_at,
  }));
}

/** Everyone holding a live grant on one unit — the "who has this" view. */
export async function holdersOf(db: D1Database, slug: string): Promise<string[]> {
  const { results } = await db
    .prepare(
      `SELECT DISTINCT user_email FROM access_grant
       WHERE revoked_at IS NULL
         AND (   (scope_type = 'unit' AND scope_id = ?1)
              OR (scope_type = 'work' AND scope_id = (SELECT work_slug FROM content_unit WHERE slug = ?1))
              OR (scope_type = 'library'))
       ORDER BY user_email`,
    )
    .bind(slug)
    .all<{ user_email: string }>();

  return results.map((r) => r.user_email);
}

export async function invite(
  db: D1Database,
  rawEmail: string,
  actor: string,
  note: string | null,
  now: string,
): Promise<void> {
  const email = normalizeEmail(rawEmail);

  // UPSERT, not INSERT: re-inviting a revoked address must clear the revocation
  // rather than collide with the existing primary key.
  await db.batch([
    db
      .prepare(
        `INSERT INTO invite (email, email_raw, invited_by, invited_at, note)
         VALUES (?1, ?2, ?3, ?4, ?5)
         ON CONFLICT(email) DO UPDATE SET
           revoked_at = NULL, email_raw = ?2, invited_by = ?3, invited_at = ?4, note = ?5`,
      )
      .bind(email, rawEmail.trim(), actor, now, note),
    event(db, now, actor, "invite", email, null, null, note),
  ]);
}

/**
 * Revoke sign-in.
 *
 * Three things, and the third is deliberate: the invite is marked revoked, every
 * live session for that person is deleted so the revocation takes effect on the
 * very next request rather than whenever a 30-day cookie expires, and their
 * GRANTS ARE LEFT ALONE so that re-inviting them restores exactly what they had.
 */
export async function revokeInvite(
  db: D1Database,
  rawEmail: string,
  actor: string,
  now: string,
): Promise<void> {
  const email = normalizeEmail(rawEmail);

  await db.batch([
    db.prepare(`UPDATE invite SET revoked_at = ?2 WHERE email = ?1`).bind(email, now),
    db
      .prepare(`DELETE FROM session WHERE userId IN (SELECT id FROM user WHERE email = ?1)`)
      .bind(email),
    event(db, now, actor, "revoke-invite", email, null, null, null),
  ]);
}

export async function grant(
  db: D1Database,
  rawEmail: string,
  scopeType: Grant["scopeType"],
  scopeId: string,
  actor: string,
  now: string,
): Promise<void> {
  const email = normalizeEmail(rawEmail);
  const id = scopeType === "library" ? "*" : scopeId;

  await db.batch([
    db
      .prepare(
        `INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
         VALUES (?1, ?2, ?3, ?4, ?5)
         ON CONFLICT(user_email, scope_type, scope_id) DO UPDATE SET
           revoked_at = NULL, granted_by = ?4, granted_at = ?5`,
      )
      .bind(email, scopeType, id, actor, now),
    event(db, now, actor, "grant", email, scopeType, id, null),
  ]);
}

export async function revokeGrant(
  db: D1Database,
  rawEmail: string,
  scopeType: Grant["scopeType"],
  scopeId: string,
  actor: string,
  now: string,
): Promise<void> {
  const email = normalizeEmail(rawEmail);
  const id = scopeType === "library" ? "*" : scopeId;

  await db.batch([
    db
      .prepare(
        `UPDATE access_grant SET revoked_at = ?4
         WHERE user_email = ?1 AND scope_type = ?2 AND scope_id = ?3`,
      )
      .bind(email, scopeType, id, now),
    event(db, now, actor, "revoke-grant", email, scopeType, id, null),
  ]);
}

/** The one switch that opens a unit to everyone invited. Admin session only. */
export async function setOpenToAll(
  db: D1Database,
  slug: string,
  open: boolean,
  actor: string,
  now: string,
): Promise<void> {
  await db.batch([
    db.prepare(`UPDATE content_unit SET open_to_all = ?2 WHERE slug = ?1`).bind(slug, open ? 1 : 0),
    event(db, now, actor, open ? "open-to-all" : "close-to-all", slug, null, null, null),
  ]);
}

function event(
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
