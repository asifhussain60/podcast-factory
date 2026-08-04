/**
 * A hundred invented readers, in the LOCAL database only.
 *
 * The people screen is built for a library that grows and it was designed against
 * two rows. This fills it with a hundred so the table, the seven filters, the four
 * pages and the empty cases can be looked at rather than imagined.
 *
 * Three properties, and the first is the reason this is a script and not a
 * migration:
 *
 *   1. LOCAL ONLY. Every write goes through `wrangler d1 execute --local`, which
 *      cannot reach the deployed database, and there is no `--remote` path in
 *      this file. A row in `invite` is not decoration — it is permission to sign
 *      in to podcast-factory.safinaverse.com. A migration would have handed that
 *      permission to a hundred fabricated addresses the next time the Worker
 *      deployed, because the deploy applies migrations before it ships code.
 *
 *   2. Recognisable and unroutable. Every address ends in `@example.invalid`,
 *      a domain RFC 2606 reserves so that it can never resolve, and that suffix
 *      is what `--clear` matches. Nothing else can be caught by it.
 *
 *   3. Spread across every filter on purpose — signed in, never signed in, given
 *      nothing, holding the whole library, gone quiet, revoked — because a table
 *      full of identical rows proves only that rows render.
 *
 * Usage:
 *   node scripts/seed-people.mjs           add (or refresh) the hundred
 *   node scripts/seed-people.mjs --clear   remove them and their grants
 */
import { execFileSync } from "node:child_process";

const DOMAIN = "example.invalid";
const COUNT = 100;
const ACTOR = "seed-people.mjs";

/**
 * The one flag this file refuses.
 *
 * Every `wrangler d1 execute` below passes `--local`, so there is no code path
 * here that reaches production — but "there is no path" is a property of the
 * current text, and the next person to want a hundred rows somewhere else will
 * reach for the obvious flag. This makes that attempt stop rather than be
 * quietly ignored, and says why. Unknown flags are refused for the same reason:
 * a typo that silently does the default is how a guard gets bypassed by
 * accident.
 */
const ALLOWED = new Set(["--clear"]);
const unknown = process.argv.slice(2).filter((a) => !ALLOWED.has(a));
if (unknown.length > 0) {
  const remote = unknown.some((a) => /^--remote|^--env/.test(a));
  console.error(
    remote
      ? `refusing ${unknown.join(" ")}: these hundred people are scenery, and on the live
site every one of them would be an address genuinely permitted to sign in.
This script is local-only by design and has no remote mode to enable.`
      : `unknown option: ${unknown.join(" ")} (only --clear is accepted)`,
  );
  process.exit(2);
}

/** @param {string} sql */
function d1(sql) {
  execFileSync(
    "npx",
    ["wrangler", "d1", "execute", "podcast-listener", "--local", "--command", sql],
    { stdio: ["pipe", "pipe", "inherit"], encoding: "utf8" },
  );
}

/** @param {string} sql @returns {any[]} */
function query(sql) {
  const out = execFileSync(
    "npx",
    ["wrangler", "d1", "execute", "podcast-listener", "--local", "--json", "--command", sql],
    { stdio: ["pipe", "pipe", "pipe"], encoding: "utf8" },
  );
  const at = out.indexOf("[");
  if (at === -1) return [];
  try {
    return JSON.parse(out.slice(at))[0]?.results ?? [];
  } catch {
    return [];
  }
}

if (process.argv.includes("--clear")) {
  // Grants first: they are keyed by email and nothing cascades from `invite`.
  d1(`DELETE FROM access_grant WHERE user_email LIKE '%@${DOMAIN}';
      DELETE FROM invite WHERE email LIKE '%@${DOMAIN}';`);
  console.log(`Removed every invitation at @${DOMAIN}, and their grants.`);
  process.exit(0);
}

/* Plainly invented people. ASCII romanization per the house rule, and a mix of
   name lengths so the Name column is exercised by the short and the long — plus
   two single-word names and two with none at all, which are the rows that used to
   sort to the bottom and now sort in place. */
const GIVEN = [
  "Amina", "Bilal", "Dawud", "Fatima", "Hamza", "Idris", "Jamila", "Khalid",
  "Layla", "Mansur", "Nadia", "Omar", "Rashid", "Safiya", "Tariq", "Umar",
  "Wasim", "Yasmin", "Zainab", "Adnan", "Basma", "Faris", "Ghada", "Hakim",
  "Imran"
];
const FAMILY = [
  "Ahmad", "Baksh", "Chowdhury", "Dehlavi", "Farooqi", "Ghazali", "Husain",
  "Iqbal", "Jafri", "Karim", "Lodhi", "Mirza", "Naqvi", "Qureshi", "Rizvi",
  "Siddiqui", "Tabrizi", "Usmani", "Wahid", "Zaidi"
];

const sq = (/** @type {string} */ s) => s.replace(/'/g, "''");
const iso = (/** @type {number} */ daysAgo) =>
  `strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-${daysAgo} days')`;

/**
 * One person per index, deterministic.
 *
 * No randomness anywhere: running this twice must produce the same hundred people
 * or "the row that looked wrong" cannot be found again.
 */
function person(/** @type {number} */ i) {
  const first = GIVEN[i % GIVEN.length];
  const last = FAMILY[(i * 7) % FAMILY.length];

  // i % 25 spreads the states. The shares are roughly what a real invitation list
  // looks like — most people signed in and reading, a tail of the stuck and the
  // departed — rather than a fifth in each bucket, which would make the counts
  // look designed.
  const bucket = i % 25;
  const nameless = bucket === 11 || bucket === 23;
  const oneWord = bucket === 6 || bucket === 18;
  const revoked = bucket === 21;
  const never = bucket === 2 || bucket === 9 || bucket === 16;
  const dormant = bucket === 4 || bucket === 13;
  const noGrants = bucket === 7 || bucket === 19 || never;
  const wholeLibrary = bucket === 5;

  return {
    email: `${first}.${last}${i}@${DOMAIN}`.toLowerCase(),
    emailRaw: `${first}.${last}${i}@${DOMAIN}`,
    firstName: nameless ? null : first,
    lastName: nameless || oneWord ? null : last,
    invitedDaysAgo: 200 - i,
    // Never signed in means both timestamps are null, which is what the `never`
    // filter reads — not a redeemed date with a null last-seen.
    redeemedDaysAgo: never ? null : Math.max(1, 190 - i),
    lastSeenDaysAgo: never ? null : dormant ? 45 + (i % 30) : 1 + (i % 20),
    revokedDaysAgo: revoked ? 3 : null,
    grants: wholeLibrary ? "library" : noGrants ? "none" : ((i % 3) + 1),
  };
}

const people = Array.from({ length: COUNT }, (_, i) => person(i));

// Real slugs, discovered rather than named: which books exist locally depends on
// what has been published on this machine, and a hard-coded slug would create
// grants pointing at nothing.
const slugs = query(
  `SELECT slug FROM content_unit WHERE kind <> 'work' ORDER BY sort_order, title`,
).map((r) => r.slug);

if (slugs.length === 0) {
  console.log("No content units locally — seeding people with sign-in states but no book grants.");
}

const inviteRows = people.map((p) => {
  const first = p.firstName === null ? "NULL" : `'${sq(p.firstName)}'`;
  const last = p.lastName === null ? "NULL" : `'${sq(p.lastName)}'`;
  return `('${sq(p.email)}', '${sq(p.emailRaw)}', '${ACTOR}', ${iso(p.invitedDaysAgo)}, ${first}, ${last},
    ${p.redeemedDaysAgo === null ? "NULL" : iso(p.redeemedDaysAgo)},
    ${p.lastSeenDaysAgo === null ? "NULL" : iso(p.lastSeenDaysAgo)},
    ${p.revokedDaysAgo === null ? "NULL" : iso(p.revokedDaysAgo)})`;
});

// The same UPSERT the application performs, so re-running is a refresh rather
// than a conflict.
d1(`
  INSERT INTO invite (email, email_raw, invited_by, invited_at, first_name, last_name,
                      redeemed_at, last_seen_at, revoked_at)
  VALUES ${inviteRows.join(",\n")}
  ON CONFLICT(email) DO UPDATE SET
    email_raw = excluded.email_raw, invited_at = excluded.invited_at,
    first_name = excluded.first_name, last_name = excluded.last_name,
    redeemed_at = excluded.redeemed_at, last_seen_at = excluded.last_seen_at,
    revoked_at = excluded.revoked_at;
`);

if (slugs.length > 0) {
  /** @type {string[]} */
  const grantRows = [];
  people.forEach((p, i) => {
    if (p.grants === "none") return;
    if (p.grants === "library") {
      grantRows.push(`('${sq(p.email)}', 'library', '*', '${ACTOR}', ${iso(30)})`);
      return;
    }
    for (let n = 0; n < Number(p.grants); n++) {
      const slug = slugs[(i + n * 3) % slugs.length];
      grantRows.push(`('${sq(p.email)}', 'unit', '${sq(slug)}', '${ACTOR}', ${iso(20)})`);
    }
  });

  d1(`
    DELETE FROM access_grant WHERE user_email LIKE '%@${DOMAIN}';
    INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
    VALUES ${grantRows.join(",\n")}
    ON CONFLICT(user_email, scope_type, scope_id) DO UPDATE SET revoked_at = NULL;
  `);
}

const counted = query(`SELECT count(*) AS n FROM invite WHERE email LIKE '%@${DOMAIN}'`);
console.log(
  `Seeded ${counted[0]?.n ?? 0} invented readers at @${DOMAIN} in the LOCAL database only.`,
);
console.log("Remove them with: node scripts/seed-people.mjs --clear");
