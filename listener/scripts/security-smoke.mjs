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

/** @param {string} path @param {string} [cookie] */
const post = (path, cookie) =>
  fetch(`${BASE}${path}`, {
    method: "POST",
    headers: cookie ? { Cookie: cookie } : {},
    redirect: "manual",
  });

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
// A route that EXISTS and is nested, or the 404 would only prove that nothing
// matched. `/admin/people` served this until the people screen became `/admin`.
check("admin sub-page is 404", (await get("/admin/content", outsider)).status, 404);
check("case-variant admin is 404", (await get("/Admin/content", outsider)).status, 404);

console.log("\nevery surface of a book, not just its front page");
// Each of these is its own route with its own middleware line. A gate added to
// the book page and forgotten on the reading route would leave the prose
// readable by URL while the book itself looked protected — and the chapter keys
// are guessable, because they are the chapter titles.
const CHAPTER = encodeURIComponent("knowledge that will not save you");
check("a chapter is 404", (await get(`/book/ayyuhal-walad/read/${CHAPTER}`, outsider)).status, 404);
check("the slide deck is 404", (await get("/book/ayyuhal-walad/slides", outsider)).status, 404);
check("a media file is 404", (await get("/media/ayyuhal-walad/book.pdf", outsider)).status, 404);
// A key from ANOTHER book must not resolve through this book's slug: the route
// builds `${params.slug}/${rest}`, so the URL's slug always prefixes the key, and
// the row's own slug is compared against it afterwards.
//
// THIS CHECK USED TO BE VACUOUS and is rewritten (2026-08-04). It was
// `/media/ayyuhal-walad/../degrees-of-excellence/book.pdf` — but `fetch` resolves
// `..` in the URL before the request leaves, so what the server actually received
// was `/media/degrees-of-excellence/book.pdf`: a real file the administrator is
// entitled to. It "passed" for as long as it did only because that book had no
// uploaded PDF, and it started FAILING on a correct 200 the day one was published.
// A gate that passes because the target is missing is not testing the gate.
//
// No `..` here, so nothing normalises it away and the request reaches the route
// as written. Asserted as the ADMIN, who holds `library:*` — access is deliberately
// not the variable, so a 404 can only mean the key did not resolve.
check(
  "another book's media does not resolve through this book's slug",
  (await get("/media/ayyuhal-walad/degrees-of-excellence/book.pdf", admin)).status,
  404,
);
// The control the rewrite needs, or the check above passes for the wrong reason:
// that file IS reachable at its own slug, so the 404 is about the key and not
// about the file being absent.
check(
  "control: the same file at its own slug is served",
  (await get("/media/degrees-of-excellence/book.pdf", admin)).status,
  200,
);
// And the access half, which is what the vacuous check was standing in for: an
// invited person with no grant gets nothing, whichever book's media they ask for.
check(
  "an ungranted reader gets 404 for a book they were never given",
  (await get("/media/degrees-of-excellence/book.pdf", outsider)).status,
  404,
);

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

// The same attack against the READING route, which is where the prose is.
const readFiltered =
  `/book/ayyuhal-walad/read/${CHAPTER}.data?_routes=routes%2Fbook.%24slug.read.%24chapter`;
check("denied on the chapter route too", (await get(readFiltered, outsider)).status, 404);
check("control: granted user gets the chapter", (await get(readFiltered, admin)).status, 200);

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

console.log("\nthe Scholar Companion reaches one account");
// A reader who is fully entitled to the book — the case the entitlement checks
// above never cover, because they are all about someone who holds nothing. The
// Companion is not an access question: it is a panel of private teaching notes
// that a perfectly legitimate reader must still never see.
const MARKER = "SMOKE-COMPANION-DO-NOT-SHOW";
d1(`
  INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
    VALUES ('${OUTSIDER}', 'unit', 'ayyuhal-walad', 'smoke', 'now');
  INSERT INTO companion_note (slug, anchor_key, note_id, idx, title, quote, body_html)
    VALUES ('ayyuhal-walad', '${decodeURIComponent(CHAPTER).replaceAll("'", "''")}',
            'smoke-note', 1, 'Smoke', NULL, '<p>${MARKER}</p>')
    ON CONFLICT(slug, note_id) DO UPDATE SET body_html = excluded.body_html;
`);

const asReader = await get(`/book/ayyuhal-walad/read/${CHAPTER}`, outsider);
const readerPage = await asReader.text();
check("the granted reader can read the chapter", asReader.status, 200);
check("and the chapter carries no companion note", readerPage.includes(MARKER), false);
// Not only the note — the PANEL. What this reader gets on that edge is their own
// notes drawer, and only that: an empty Companion offered to someone it is not
// for would still be a surface that should not exist for them.
// Addressed by the tab's accessible name rather than by the bare word
// "Companion": the reading route imports the panel either way, so the module's
// FILENAME is in every page's preload list. A check on the word alone fails on a
// build artefact and would have to be weakened until it proved nothing.
check("their right-hand drawer is their own notes", readerPage.includes("Open your notes"), true);
check("and no Companion panel is rendered", readerPage.includes("Open companion"), false);

// Control. Without it, the checks above pass just as happily when the note was
// never written, when the chapter key was wrong, or when the page 500s — none of
// which prove anything was withheld from anybody.
const asAdmin = await get(`/book/ayyuhal-walad/read/${CHAPTER}`, admin);
const adminPage = await asAdmin.text();
check("control: the administrator's copy of the same page carries it", adminPage.includes(MARKER), true);
check("control: and their drawer is the Companion", adminPage.includes("Open companion"), true);
check("control: which REPLACES the notes drawer, not joins it", adminPage.includes("Open your notes"), false);

console.log("\nseeing the site as somebody else");
// The cookie is read ONLY when the real session is the administrator's, so in
// anyone else's browser it is inert. That is the entire gate, and it is a claim
// about how a request is dispatched — only firing one can prove it.
/** @param {string} email */
const forged = (email) => `pf-simulate=${encodeURIComponent(email)}`;

check(
  "a forged cookie naming the admin gets a reader nothing",
  (await get("/admin", `${outsider}; ${forged(ADMIN)}`)).status,
  404,
);
check(
  "and it does not even reach a book they were never given",
  (await get("/book/degrees-of-excellence", `${outsider}; ${forged(ADMIN)}`)).status,
  404,
);

// The same cookie in the ADMINISTRATOR's browser is the feature, and what it
// does is take capability AWAY. Both halves are checked: the admin screens close
// behind them, and the Companion — which is `viewer.isAdmin` and nothing else —
// stops being served on a page that was serving it a moment ago.
const asThem = `${admin}; ${forged(OUTSIDER)}`;
check("the administrator simulating loses the admin screens", (await get("/admin", asThem)).status, 404);

const simulated = await get(`/book/ayyuhal-walad/read/${CHAPTER}`, asThem);
check("still reads the book the simulated reader holds", simulated.status, 200);
check("but is no longer shown the companion", (await simulated.text()).includes(MARKER), false);

// The way out cannot be behind the gate the simulation just closed.
check("stopping is reachable while simulating", (await post("/stop-simulating", asThem)).status, 302);

d1(`
  DELETE FROM companion_note WHERE note_id = 'smoke-note';
  DELETE FROM access_grant WHERE user_email = '${OUTSIDER}';
  DELETE FROM access_event WHERE subject IN ('${OUTSIDER}', '${STRANGER}');
`);

console.log("\none reader's marks are their own");
// The most private thing this application stores. The unit tests in
// test/marks-isolation.test.ts prove the SQL; this proves the ROUTE, as one
// signed-in person actually reaching for another's rows over HTTP.
const OWNED = "44444444-4444-4444-8444-444444444444";
d1(`
  INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
    VALUES ('${OUTSIDER}', 'unit', 'ayyuhal-walad', 'smoke', 'now');
  DELETE FROM annotation WHERE id = '${OWNED}';
  INSERT INTO annotation
    (id, user_email, slug, anchor_key, block_index, start_offset, end_offset,
     quote, prefix, colour, note, created_at, updated_at)
    VALUES ('${OWNED}', '${ADMIN}', 'ayyuhal-walad', '${decodeURIComponent(CHAPTER).replaceAll("'", "''")}',
            1, 0, 5, 'mine', '', 'gold', 'SMOKE-PRIVATE-NOTE', 'now', 'now');
`);

const theirMarks = await get("/book/ayyuhal-walad/marks", outsider);
check("a granted reader can load their own marks", theirMarks.status, 200);
check(
  "and the other reader's note is not in them",
  (await theirMarks.text()).includes("SMOKE-PRIVATE-NOTE"),
  false,
);

// Now the write. Ids are client-generated, so knowing one is the whole attack:
// until 2026-08-04 this rewrote the row, in a book the caller need not hold.
await fetch(`${BASE}/book/ayyuhal-walad/marks`, {
  method: "POST",
  headers: { Cookie: outsider, "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({
    intent: "annotate",
    id: OWNED,
    anchorKey: decodeURIComponent(CHAPTER),
    blockIndex: "9",
    startOffset: "0",
    endOffset: "9",
    quote: "vandalised",
    colour: "rose",
    note: "VANDALISED",
  }),
});

const after = JSON.parse(
  (() => {
    const out = String(
      execFileSync(
        "npx",
        [
          "wrangler", "d1", "execute", "podcast-listener", "--local", "--json",
          "--command", `SELECT note, quote, user_email FROM annotation WHERE id = '${OWNED}'`,
        ],
        { encoding: "utf8" },
      ),
    );
    return out.slice(out.indexOf("["));
  })(),
)[0].results[0];

check("their note is untouched", after.note, "SMOKE-PRIVATE-NOTE");
check("their quote is untouched", after.quote, "mine");
check("and it still belongs to them", after.user_email, ADMIN);

d1(`
  DELETE FROM annotation WHERE id = '${OWNED}';
  DELETE FROM access_grant WHERE user_email = '${OUTSIDER}';
`);

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
