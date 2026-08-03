/**
 * Runtime security smoke test — the checks that cannot be made as unit tests
 * because they depend on how React Router actually dispatches a request.
 *
 * The headline case is the `_routes` bypass. `filterMatchesToLoad`
 * (single-fetch.js:79-84) lets a caller name which LOADERS run, so a gate
 * written as a parent loader is defeated by one query parameter. Middleware sits
 * outside that filter. No amount of reading the code proves which one we built —
 * only firing the request does.
 *
 *   npm run dev            # in another terminal, on :5273
 *   node scripts/security-smoke.mjs
 *
 * Local only: it mints development sessions against the Miniflare D1 file.
 * Exits non-zero on any failure.
 */
import { execFileSync } from "node:child_process";

const BASE = process.env.LISTENER_URL ?? "http://localhost:5273";
const ADMIN = "asifhussain60@gmail.com";
const OUTSIDER = "smoke-outsider@example.com";
const STRANGER = "smoke-stranger@example.com";

/** @param {string} sql */
const d1 = (sql) =>
  execFileSync("npx", ["wrangler", "d1", "execute", "podcast-listener", "--local", "--command", sql], {
    stdio: "pipe",
  });

/** @param {string} email @returns {string} */
const cookieFor = (email) => {
  const out = execFileSync("node", ["scripts/session-cookie.mjs", email], { encoding: "utf8" })
    .trim()
    .split("\n")
    .pop();

  // An empty cookie would make every "is this denied?" check pass for entirely
  // the wrong reason, so it has to be loud rather than falsy.
  if (!out?.startsWith("better-auth.session_token=")) {
    throw new Error(`could not mint a session for ${email}: got ${JSON.stringify(out)}`);
  }
  return out;
};

/** @param {string} path @param {string} [cookie] */
const get = (path, cookie) =>
  fetch(`${BASE}${path}`, { headers: cookie ? { Cookie: cookie } : {}, redirect: "manual" });

let failures = 0;
/** @param {string} name @param {unknown} actual @param {unknown} expected */
const check = (name, actual, expected) => {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(`${ok ? "  ok  " : "  FAIL"} ${name}  (${actual}${ok ? "" : `, wanted ${expected}`})`);
};

// OUTSIDER is invited but holds nothing. STRANGER is not invited at all.
d1(`
  INSERT INTO invite (email, email_raw, invited_by, invited_at)
    VALUES ('${OUTSIDER}', '${OUTSIDER}', 'smoke', 'now')
    ON CONFLICT(email) DO UPDATE SET revoked_at = NULL;
  DELETE FROM invite WHERE email = '${STRANGER}';
  DELETE FROM access_grant WHERE user_email = '${OUTSIDER}';
`);

const admin = cookieFor(ADMIN);
const outsider = cookieFor(OUTSIDER);
const stranger = cookieFor(STRANGER);

console.log("\nsigned out");
check("protected page redirects, does not 404", (await get("/")).status, 302);
check("a book link redirects so the recipient can sign in", (await get("/book/ayyuhal-walad")).status, 302);
check("admin redirects too", (await get("/admin")).status, 302);
check("sign-in is reachable", (await get("/sign-in")).status, 200);

console.log("\nunmatched path (middleware never runs here)");
check("renders a 404 rather than throwing 500", (await get("/nonexistent")).status, 404);
check("still 404 with a session", (await get("/nonexistent", admin)).status, 404);

console.log("\nsigned in, not invited");
check("sent to no-access", (await get("/", stranger)).status, 302);

console.log("\ninvited, granted nothing");
check("library loads", (await get("/", outsider)).status, 200);
check("a real book is 404", (await get("/book/ayyuhal-walad", outsider)).status, 404);
check("admin is 404, not 403", (await get("/admin", outsider)).status, 404);
check("admin sub-page is 404", (await get("/admin/people", outsider)).status, 404);
check("case-variant admin is 404", (await get("/Admin/people", outsider)).status, 404);

console.log("\nTHE BYPASS — _routes filter on the single-fetch endpoint");
const filtered = "/book/ayyuhal-walad.data?_routes=routes%2Fbook.%24slug";
check("denied for someone without the grant", (await get(filtered, outsider)).status, 404);
// Control: the SAME request by someone who is granted must succeed, or the 404
// above proves nothing — it could just be a malformed route id.
const control = await get(filtered, admin);
check("control: granted user gets data", control.status, 200);
const body = await control.text();
check(
  "control: the filter really was applied (child route only)",
  body.includes("routes/book.$slug") && !body.includes("routes/_authed"),
  true,
);

console.log("\nthe two 404s are indistinguishable");
const denied = await get("/book/ayyuhal-walad", outsider);
const missing = await get("/book/no-such-book-exists", outsider);
check("same status", denied.status, missing.status);
/** @param {string} t @param {string} p */
const strip = (t, p) => t.replaceAll(p, "SLUG");
check(
  "same body once the echoed path is normalised",
  strip(await denied.text(), "ayyuhal-walad") === strip(await missing.text(), "no-such-book-exists"),
  true,
);

console.log("\nrevocation takes effect on the next request");
d1(`UPDATE invite SET revoked_at = 'now' WHERE email = '${OUTSIDER}'`);
check("revoked person is sent to no-access", (await get("/", outsider)).status, 302);

// Teardown. A test that leaves its fixtures behind shows two invented people in
// the admin People list and a forged session for each, which then has to be
// explained every time someone opens that screen. It removes only rows it made:
// the two @example.com identities and the dev session minted for the admin.
d1(`
  DELETE FROM user    WHERE email IN ('${OUTSIDER}', '${STRANGER}');
  DELETE FROM invite  WHERE email IN ('${OUTSIDER}', '${STRANGER}');
  DELETE FROM session WHERE id = 'sess-dev-${Buffer.from(ADMIN).toString("hex").slice(0, 16)}';
  DELETE FROM user    WHERE id = 'dev-${Buffer.from(ADMIN).toString("hex").slice(0, 16)}'
                        AND NOT EXISTS (SELECT 1 FROM account a WHERE a.userId = user.id);
`);

console.log(failures === 0 ? "\nall checks passed\n" : `\n${failures} check(s) failed\n`);
process.exit(failures === 0 ? 0 : 1);
