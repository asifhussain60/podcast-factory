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
  firstName: string | null;
  lastName: string | null;
  /** What to call them: their name if it was recorded, otherwise their address. */
  displayName: string;
  invitedAt: string;
  redeemedAt: string | null;
  lastSeenAt: string | null;
  revokedAt: string | null;
  note: string | null;
  grantCount: number;
}

/**
 * The filters the people screen offers, as SQL.
 *
 * Each is a question an administrator actually asks, and each is a predicate
 * rather than a client-side `.filter` — the whole reason this screen was rebuilt
 * is that it stops working at a hundred people, and shipping a hundred rows to
 * the browser to hide ninety of them is the same failure with more steps.
 *
 * `waiting` is the one worth naming: invited, has signed in, and holds no
 * grants. Those people see an empty library and have no way to know why, so they
 * are the ones most likely to be quietly stuck.
 */
export const PEOPLE_FILTERS = {
  all: "1 = 1",
  active: "i.revoked_at IS NULL AND i.redeemed_at IS NOT NULL",
  never: "i.revoked_at IS NULL AND i.redeemed_at IS NULL",
  waiting:
    "i.revoked_at IS NULL AND (SELECT count(*) FROM access_grant g WHERE g.user_email = i.email AND g.revoked_at IS NULL) = 0",
  revoked: "i.revoked_at IS NOT NULL",
} as const;

export type PeopleFilter = keyof typeof PEOPLE_FILTERS;

export const isPeopleFilter = (v: unknown): v is PeopleFilter =>
  typeof v === "string" && v in PEOPLE_FILTERS;

export interface PeopleQuery {
  search?: string;
  filter?: PeopleFilter;
  limit?: number;
  offset?: number;
}

export interface PeoplePage {
  people: Person[];
  /** How many match the query, regardless of the page — so the UI can say so. */
  total: number;
  /** How many exist at all, for the "showing N of M" line. */
  everyone: number;
}

/**
 * Search across name and address, matched case-insensitively.
 *
 * `email_raw` as well as `email`, because they differ: someone invited as
 * `A.Person+books@gmail.com` is stored normalized as `aperson@gmail.com`, and an
 * administrator typing what they remember typing would otherwise find nobody.
 * `LIKE` is case-insensitive for ASCII in SQLite by default, and every column
 * here is an address or a Latin name.
 *
 * This clause is ALWAYS in the query, even with an empty search box, and that is
 * load-bearing rather than lazy. D1 rejects a statement whose bindings and
 * placeholders disagree — `Wrong number of parameter bindings` — so a version
 * that dropped the clause and still bound its pattern turned every unsearched
 * visit to the people screen into a 500. Keeping the clause and passing `%`
 * means one shape of query with one set of bindings: `email` is NOT NULL, so
 * `LIKE '%'` is true for every row and the empty search matches everyone.
 */
const SEARCH_SQL = `(
     i.email      LIKE ?1 ESCAPE '\\'
  OR i.email_raw  LIKE ?1 ESCAPE '\\'
  OR i.first_name LIKE ?1 ESCAPE '\\'
  OR i.last_name  LIKE ?1 ESCAPE '\\'
  OR (COALESCE(i.first_name, '') || ' ' || COALESCE(i.last_name, '')) LIKE ?1 ESCAPE '\\'
)`;

export async function listPeople(db: D1Database, query: PeopleQuery = {}): Promise<PeoplePage> {
  const filter = query.filter ?? "all";
  const where = PEOPLE_FILTERS[isPeopleFilter(filter) ? filter : "all"];
  const search = (query.search ?? "").trim();

  // `%` and `_` are LIKE wildcards. An administrator searching for "a_b" means
  // those three characters, so they are escaped rather than honoured — otherwise
  // a stray underscore in an address silently matches everything.
  const pattern = search === "" ? "%" : `%${search.replace(/[%_\\]/g, "\\$&")}%`;

  const limit = Math.min(200, Math.max(1, query.limit ?? 50));
  const offset = Math.max(0, query.offset ?? 0);

  const [rows, counted, all] = await Promise.all([
    db
      .prepare(
        `SELECT i.email, i.email_raw, i.first_name, i.last_name, i.invited_at,
                i.redeemed_at, i.last_seen_at, i.revoked_at, i.note,
                (SELECT count(*) FROM access_grant g
                  WHERE g.user_email = i.email AND g.revoked_at IS NULL) AS grant_count
           FROM invite i
          WHERE ${where} AND ${SEARCH_SQL}
          -- Name first when there is one, so the list reads as people rather
          -- than as a mailing list. NULLs sort last in SQLite ASC, which happens
          -- to be exactly what is wanted: the unnamed fall to the bottom.
          ORDER BY i.last_name COLLATE NOCASE, i.first_name COLLATE NOCASE, i.email
          LIMIT ?2 OFFSET ?3`,
      )
      .bind(pattern, limit, offset)
      .all<PersonRow>(),

    db
      .prepare(`SELECT count(*) AS n FROM invite i WHERE ${where} AND ${SEARCH_SQL}`)
      .bind(pattern)
      .first<{ n: number }>(),

    db.prepare(`SELECT count(*) AS n FROM invite`).first<{ n: number }>(),
  ]);

  return {
    people: rows.results.map(toPerson),
    total: counted?.n ?? 0,
    everyone: all?.n ?? 0,
  };
}

/** One person by address, for the detail pane. Never a scan of the whole list. */
export async function personByEmail(db: D1Database, rawEmail: string): Promise<Person | null> {
  const row = await db
    .prepare(
      `SELECT i.email, i.email_raw, i.first_name, i.last_name, i.invited_at,
              i.redeemed_at, i.last_seen_at, i.revoked_at, i.note,
              (SELECT count(*) FROM access_grant g
                WHERE g.user_email = i.email AND g.revoked_at IS NULL) AS grant_count
         FROM invite i WHERE i.email = ?1`,
    )
    .bind(normalizeEmail(rawEmail))
    .first<PersonRow>();

  return row === null ? null : toPerson(row);
}

/** How many people the filters would each return, for the counts on the chips. */
export async function peopleTallies(db: D1Database): Promise<Record<PeopleFilter, number>> {
  const entries = Object.entries(PEOPLE_FILTERS) as [PeopleFilter, string][];
  const counts = await Promise.all(
    entries.map(([, where]) =>
      db.prepare(`SELECT count(*) AS n FROM invite i WHERE ${where}`).first<{ n: number }>(),
    ),
  );

  const out = {} as Record<PeopleFilter, number>;
  entries.forEach(([name], i) => (out[name] = counts[i]?.n ?? 0));
  return out;
}

interface PersonRow {
  email: string;
  email_raw: string;
  first_name: string | null;
  last_name: string | null;
  invited_at: string;
  redeemed_at: string | null;
  last_seen_at: string | null;
  revoked_at: string | null;
  note: string | null;
  grant_count: number;
}

const toPerson = (r: PersonRow): Person => {
  const name = [r.first_name, r.last_name].filter(Boolean).join(" ").trim();
  return {
    email: r.email,
    emailRaw: r.email_raw,
    firstName: r.first_name,
    lastName: r.last_name,
    // The address is the fallback, not a placeholder like "Unnamed": every row
    // predating migration 0006 has no name, and an administrator recognises an
    // address perfectly well.
    displayName: name === "" ? r.email_raw : name,
    invitedAt: r.invited_at,
    redeemedAt: r.redeemed_at,
    lastSeenAt: r.last_seen_at,
    revokedAt: r.revoked_at,
    note: r.note,
    grantCount: r.grant_count,
  };
};

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

export interface Holder {
  email: string;
  displayName: string;
  /** Through what: the book itself, its parent work, or a whole-library grant. */
  via: "unit" | "work" | "library";
}

/**
 * Everyone holding a live grant on one unit — the "who has this" view.
 *
 * Now returns WHY as well as who, because the two are different facts and the
 * screen has to act on the difference: taking a book away from someone who holds
 * it directly is one click, and taking it away from someone who holds the whole
 * library is not something this screen should silently do.
 *
 * `MIN(scope_type)` is not a real aggregate here — a CASE ranks the three so the
 * narrowest wins when a person holds more than one, which is common: an early
 * reader granted one book, later given the library, must show as "library" or
 * revoking the book grant would appear to do nothing.
 */
export async function holdersOf(db: D1Database, slug: string): Promise<Holder[]> {
  const { results } = await db
    .prepare(
      `SELECT g.user_email,
              COALESCE(NULLIF(TRIM(COALESCE(i.first_name,'') || ' ' || COALESCE(i.last_name,'')), ''),
                       i.email_raw, g.user_email) AS display_name,
              MIN(CASE g.scope_type WHEN 'unit' THEN 1 WHEN 'work' THEN 2 ELSE 3 END) AS rank
         FROM access_grant g
         LEFT JOIN invite i ON i.email = g.user_email
        WHERE g.revoked_at IS NULL
          AND (   (g.scope_type = 'unit' AND g.scope_id = ?1)
               OR (g.scope_type = 'work' AND g.scope_id = (SELECT work_slug FROM content_unit WHERE slug = ?1))
               OR (g.scope_type = 'library'))
        GROUP BY g.user_email
        ORDER BY display_name COLLATE NOCASE`,
    )
    .bind(slug)
    .all<{ user_email: string; display_name: string; rank: number }>();

  return results.map((r) => ({
    email: r.user_email,
    displayName: r.display_name,
    via: r.rank === 1 ? "unit" : r.rank === 2 ? "work" : "library",
  }));
}

export interface InviteInput {
  firstName?: string | null;
  lastName?: string | null;
  note?: string | null;
}

export async function invite(
  db: D1Database,
  rawEmail: string,
  actor: string,
  input: InviteInput,
  now: string,
): Promise<void> {
  const email = normalizeEmail(rawEmail);
  const trim = (v: string | null | undefined) => {
    const t = (v ?? "").trim();
    return t === "" ? null : t.slice(0, 100);
  };

  const first = trim(input.firstName);
  const last = trim(input.lastName);
  const note = trim(input.note);

  // UPSERT, not INSERT: re-inviting a revoked address must clear the revocation
  // rather than collide with the existing primary key.
  //
  // `COALESCE(?N, column)` on the three optional fields is what makes re-invite
  // safe. "Re-invite" is a one-button action that sends no name, and a plain
  // assignment would blank the name and the note of everyone ever restored —
  // deleting information the administrator typed, to perform an action that
  // means "let them back in".
  //
  // `redeemed_at` and `last_seen_at` are untouched for the same reason: someone
  // re-invited has still signed in before, and pretending otherwise would put
  // them back in the "never signed in" list.
  await db.batch([
    db
      .prepare(
        `INSERT INTO invite (email, email_raw, invited_by, invited_at, note, first_name, last_name)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
         ON CONFLICT(email) DO UPDATE SET
           revoked_at = NULL,
           email_raw  = ?2,
           invited_by = ?3,
           invited_at = ?4,
           note       = COALESCE(?5, invite.note),
           first_name = COALESCE(?6, invite.first_name),
           last_name  = COALESCE(?7, invite.last_name)`,
      )
      .bind(email, rawEmail.trim(), actor, now, note, first, last),
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
