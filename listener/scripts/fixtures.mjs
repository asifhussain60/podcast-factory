/**
 * The three identities the runtime checks run as, and the book they act on.
 *
 * Shared by `smoke.mjs` and `shots.mjs`. Both need the same setup and neither
 * should own it: two copies would be two definitions of "a reader with one
 * book", and the day they disagreed the screenshots would stop showing what the
 * gate was testing.
 *
 * Local only. Every write here goes to the Miniflare D1 file under
 * `.wrangler/state`, and `wrangler d1 execute` without `--remote` cannot reach
 * the deployed database.
 */
import { execFileSync } from "node:child_process";

export const ADMIN = "asifhussain60@gmail.com";
export const READER = "smoke-reader@example.com";
export const NOBODY = "smoke-nobody@example.com";

/** @param {string} sql @param {boolean} [capture] */
const d1 = (sql, capture = false) =>
  execFileSync(
    "npx",
    [
      "wrangler",
      "d1",
      "execute",
      "podcast-listener",
      "--local",
      "--json",
      "--command",
      sql,
    ],
    { stdio: capture ? "pipe" : ["pipe", "pipe", "pipe"], encoding: "utf8" },
  );

/** Run a query and get its rows back. @param {string} sql @returns {any[]} */
export function query(sql) {
  const out = d1(sql, true);
  // wrangler prints progress lines before the JSON; the payload starts at the
  // first `[`. Parsing from there rather than the whole string keeps this
  // working when it decides to be chattier.
  const at = out.indexOf("[");
  if (at === -1) return [];
  try {
    return JSON.parse(out.slice(at))[0]?.results ?? [];
  } catch {
    return [];
  }
}

/** A session cookie for an address, minted against the local database. @param {string} email */
export function cookieFor(email) {
  const out = execFileSync("node", ["scripts/session-cookie.mjs", email], { encoding: "utf8" })
    .trim()
    .split("\n")
    .pop();

  // An empty cookie would make every "is this denied?" check pass for entirely
  // the wrong reason, so it has to be loud rather than falsy.
  if (!out?.startsWith("better-auth.session_token=")) {
    throw new Error(`could not mint a session for ${email}: ${JSON.stringify(out)}`);
  }
  return out;
}

/**
 * Pick a book that is published AND has a chapter, and set the fixtures up
 * around it.
 *
 * Discovered rather than named: which books are in the local database depends on
 * what has been published on this machine, and a hard-coded slug would make the
 * gate fail on a clean checkout for a reason that has nothing to do with the
 * code. If nothing is published the caller is told so and skips the book routes
 * rather than reporting a false failure.
 */
/**
 * @returns {{
 *   book: { slug: string, title: string, hasDeck: boolean } | null,
 *   chapter: string | null,
 *   cookies: Record<string, string | null>,
 * }}
 */
export function setUp() {
  const books = query(`
    SELECT c.slug, c.title,
           (SELECT count(*) FROM chapter WHERE slug = c.slug) AS chapters,
           (SELECT count(*) FROM media_asset
             WHERE slug = c.slug AND kind = 'deck-page' AND uploaded_at IS NOT NULL) AS deck
      FROM content_unit c
     WHERE c.kind != 'work' AND c.status = 'published'
  `);

  const book = books.find((/** @type {any} */ b) => Number(b.chapters) > 0) ?? null;

  const chapter = book
    ? (query(
        `SELECT anchor_key FROM chapter WHERE slug = '${book.slug}' ORDER BY idx LIMIT 1`,
      )[0]?.anchor_key ?? null)
    : null;

  // READER holds exactly one book. NOBODY holds nothing — and is the control
  // that proves a denial is a denial rather than an empty database.
  d1(`
    INSERT INTO invite (email, email_raw, invited_by, invited_at, first_name, last_name)
      VALUES ('${READER}', '${READER}', 'smoke', 'now', 'Smoke', 'Reader')
      ON CONFLICT(email) DO UPDATE SET revoked_at = NULL;
    INSERT INTO invite (email, email_raw, invited_by, invited_at, first_name, last_name)
      VALUES ('${NOBODY}', '${NOBODY}', 'smoke', 'now', 'No', 'Access')
      ON CONFLICT(email) DO UPDATE SET revoked_at = NULL;
    DELETE FROM access_grant WHERE user_email IN ('${READER}', '${NOBODY}');
    ${
      book
        ? `INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
             VALUES ('${READER}', 'unit', '${book.slug}', 'smoke', 'now');
           -- Part-way through, so the library card renders its progress meter
           -- and the book page offers "Continue reading". Without a row both are
           -- correctly absent — which means neither would ever be visited by the
           -- gate or appear in a screenshot, and a defect in either could ship.
           INSERT INTO reading_progress
                  (user_email, slug, anchor_key, fraction, chapters_done, updated_at)
             VALUES ('${READER}', '${book.slug}', '${chapter}', 0.42, 2, 'now')
             ON CONFLICT(user_email, slug) DO UPDATE SET fraction = 0.42;`
        : ""
    }
  `);

  return {
    book: book === null ? null : { slug: book.slug, title: book.title, hasDeck: Number(book.deck) > 0 },
    chapter,
    cookies: { anon: null, admin: cookieFor(ADMIN), reader: cookieFor(READER), nobody: cookieFor(NOBODY) },
  };
}

/** Remove only what `setUp` created. Never touches a real person's rows. */
export function tearDown() {
  d1(`
    DELETE FROM access_grant WHERE user_email IN ('${READER}', '${NOBODY}');
    DELETE FROM annotation WHERE user_email IN ('${READER}', '${NOBODY}');
    DELETE FROM bookmark WHERE user_email IN ('${READER}', '${NOBODY}');
    DELETE FROM reading_progress WHERE user_email IN ('${READER}', '${NOBODY}');
    DELETE FROM listening_progress WHERE user_email IN ('${READER}', '${NOBODY}');
    DELETE FROM invite WHERE email IN ('${READER}', '${NOBODY}');
    DELETE FROM session WHERE userId IN (SELECT id FROM user WHERE email IN ('${READER}', '${NOBODY}'));
    DELETE FROM user WHERE email IN ('${READER}', '${NOBODY}');
  `);
}

/**
 * Fill `:slug` / `:chapter` in a manifest path.
 * @param {string} path
 * @param {{ slug: string } | null} book
 * @param {string | null} chapter
 */
export const fill = (path, book, chapter) =>
  path
    .replace(":slug", encodeURIComponent(book?.slug ?? ""))
    .replace(":chapter", encodeURIComponent(chapter ?? ""));
