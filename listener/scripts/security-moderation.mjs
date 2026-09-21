/**
 * Runtime security smoke for MODERATION: books held back, and corrections.
 *
 * Its own script, and not more sections of `security-smoke.mjs`, because that file sits at
 * the repo's line ceiling. Same method as its sibling: fire the request as each kind of
 * person and read what actually comes back, with a control beside every denial so a 404 can
 * only ever mean "not yours" and never "no such page".
 *
 *   npm run dev            # in another terminal, on :5273
 *   node scripts/security-moderation.mjs
 *
 * Local only: it mints development sessions against the Miniflare D1 file, and removes every
 * row it made. Exits non-zero on any failure.
 */
import { execFileSync } from "node:child_process";

const BASE = process.env.LISTENER_URL ?? "http://localhost:5273";
const ADMIN = "asifhussain60@gmail.com";
const OUTSIDER = "rdr-smoke-mod@example.com";
const MOD_B = "mdb-smoke-two@example.com";

/** @param {string} sql */
const d1 = (sql) =>
  execFileSync(
    "npx",
    [
      "wrangler",
      "d1",
      "execute",
      "podcast-listener",
      "--local",
      "--command",
      sql,
    ],
    { stdio: "pipe" },
  );

/** @param {string} email */
const cookieFor = (email) => {
  const out = execFileSync("node", ["scripts/session-cookie.mjs", email], {
    encoding: "utf8",
  }).trim();
  if (!out.startsWith("better-auth.session_token=")) {
    throw new Error(
      `could not mint a session for ${email}: got ${JSON.stringify(out)}`,
    );
  }
  return out;
};

/** @param {string} path @param {string} [cookie] */
const get = (path, cookie) =>
  fetch(`${BASE}${path}`, {
    headers: cookie ? { Cookie: cookie } : {},
    redirect: "manual",
  });

/** @param {string} email */
const forged = (email) => `pf-simulate=${encodeURIComponent(email)}`;

let failures = 0;
/** @param {string} name @param {unknown} actual @param {unknown} expected */
const check = (name, actual, expected) => {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(
    `${ok ? "  ok  " : "  FAIL"} ${name}  (${actual}${ok ? "" : `, wanted ${expected}`})`,
  );
};

const admin = cookieFor(ADMIN);
const outsider = cookieFor(OUTSIDER);

// ---------------------------------------------------------------------------
// Books held for moderation (migration 0022). An ordinary reader must not reach one by ANY
// route, however entitled they are otherwise; a moderator must reach one even when it is a
// DRAFT nobody has been granted, which is the ordinary state of a book awaiting moderation.
// Each denial has a control proving the same request succeeds when the book is NOT held, so
// a 404 can never be a page that simply does not exist.
// ---------------------------------------------------------------------------
console.log("\nbooks held for moderation");
const MOD = "mod-smoke-moderator@example.com";
const HELD = "smoke-held";
const HELD_TITLE = "Smoke Held Book";
d1(`
  INSERT INTO invite (email, email_raw, invited_by, invited_at) VALUES
    ('${OUTSIDER}', '${OUTSIDER}', 'smoke', 'now'),
    ('${MOD}', '${MOD}', 'smoke', 'now')
    ON CONFLICT(email) DO UPDATE SET revoked_at = NULL;
  INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at)
    VALUES ('${OUTSIDER}', 'library', '*', 'smoke', 'now')
    ON CONFLICT(user_email, scope_type, scope_id) DO UPDATE SET revoked_at = NULL;
  INSERT INTO moderator (user_email, granted_by, granted_at) VALUES ('${MOD}', 'smoke', 'now')
    ON CONFLICT(user_email) DO UPDATE SET revoked_at = NULL;
  INSERT INTO invite (email, email_raw, invited_by, invited_at) VALUES ('${MOD_B}', '${MOD_B}', 'smoke', 'now')
    ON CONFLICT(email) DO UPDATE SET revoked_at = NULL;
  INSERT INTO moderator (user_email, granted_by, granted_at) VALUES ('${MOD_B}', 'smoke', 'now')
    ON CONFLICT(user_email) DO UPDATE SET revoked_at = NULL;
  DELETE FROM content_unit WHERE slug = '${HELD}';
  INSERT INTO content_unit (slug, bucket, title, kind, sort_order, status, open_to_all, under_moderation)
    VALUES ('${HELD}', 'Islamic', '${HELD_TITLE}', 'book', 999, 'published', 1, 0);
`);
const modCookie = cookieFor(MOD);
const heldPage = `/book/${HELD}`;

// Control first: NOT held, published, open to all — an ordinary reader opens it.
check(
  "control: an ordinary reader opens the book while it is not held",
  (await get(heldPage, outsider)).status,
  200,
);

d1(`UPDATE content_unit SET under_moderation = 1 WHERE slug = '${HELD}'`);
check(
  "held: an ordinary reader gets 404, though it is published, open to all and in their library",
  (await get(heldPage, outsider)).status,
  404,
);
const heldFiltered = await get(
  `${heldPage}.data?_routes=routes%2Fbook.%24slug`,
  outsider,
);
check(
  "held: the _routes loader-skipping request leaks nothing either",
  (await heldFiltered.text()).includes(HELD_TITLE),
  false,
);
check(
  "held: absent from an ordinary reader's shelf",
  (await (await get("/library", outsider)).text()).includes(HELD_TITLE),
  false,
);
check(
  "held: the same 404 as a slug that never existed",
  (await get(heldPage, outsider)).status,
  (await get("/book/no-such-book-exists", outsider)).status,
);

// The moderator holds NO grant and the book is a DRAFT — the ordinary state of a book that
// is waiting for moderation.
d1(
  `UPDATE content_unit SET status = 'draft', open_to_all = 0 WHERE slug = '${HELD}'`,
);
check(
  "held draft: a moderator with no grant opens it",
  (await get(heldPage, modCookie)).status,
  200,
);
check(
  "held draft: an admin opens it",
  (await get(heldPage, admin)).status,
  200,
);
check(
  "held draft: an ordinary reader still cannot",
  (await get(heldPage, outsider)).status,
  404,
);
const modShelf = await (await get("/library", modCookie)).text();
check("held: on a moderator's shelf", modShelf.includes(HELD_TITLE), true);
check("held: and labelled", modShelf.includes("Under Moderation"), true);

// A moderator is not a wider reader and not an admin.
d1(`UPDATE content_unit SET under_moderation = 0 WHERE slug = '${HELD}'`);
check(
  "released draft: a moderator has no special reach into a book that is not held",
  (await get(heldPage, modCookie)).status,
  404,
);
check(
  "a moderator cannot open the admin section (404, not 403)",
  (await get("/admin/moderators", modCookie)).status,
  404,
);
check(
  "an admin can open the moderators screen",
  (await get("/admin/moderators", admin)).status,
  200,
);

// Simulation only ever removes capability.
d1(`UPDATE content_unit SET under_moderation = 1 WHERE slug = '${HELD}'`);
check(
  "simulating a moderator does not hand their view to the admin's session",
  (await get(heldPage, `${admin}; ${forged(OUTSIDER)}`)).status,
  404,
);

// ---------------------------------------------------------------------------
// Corrections (migration 0023) — moderators and admins only, over the SAME book gate. Each
// denial has a control, so a 404 can only mean "you are not a moderator".
// ---------------------------------------------------------------------------
console.log("\ncorrections");
const corrections = `${heldPage}/corrections`;
/** @param {string} cookie @param {Record<string,string>} fields */
const send = (cookie, fields) => {
  const body = new globalThis.FormData();
  for (const [k, v] of Object.entries(fields)) body.set(k, v);
  return fetch(`${BASE}${corrections}`, {
    method: "POST",
    body,
    headers: { Cookie: cookie },
    redirect: "manual",
  });
};
check(
  "control: a moderator reads the list on a held book",
  (await get(corrections, modCookie)).status,
  200,
);
check("control: so does an admin", (await get(corrections, admin)).status, 200);
check(
  "control: a moderator can read the recorded history",
  (await get(`${corrections}?history=all`, modCookie)).status,
  200,
);
check(
  "control: a moderator can read a chapter's source",
  (await get(`${corrections}?source=chapter-1`, modCookie)).status,
  200,
);
check(
  "a moderator cannot open the admin triage screen",
  (await get("/admin/corrections", modCookie)).status,
  404,
);
check("an admin can", (await get("/admin/corrections", admin)).status, 200);
d1(
  `UPDATE content_unit SET under_moderation = 0, open_to_all = 1, status = 'published' WHERE slug = '${HELD}'`,
);
check(
  "an ordinary reader who can open the book still gets 404 here",
  (await get(corrections, outsider)).status,
  404,
);
check(
  "nor read a chapter's source",
  (await get(`${corrections}?source=chapter-1`, outsider)).status,
  404,
);
check(
  "nor read the recorded history",
  (await get(`${corrections}?history=all`, outsider)).status,
  404,
);
check(
  "nor search for other places a passage appears",
  (await get(`${corrections}?occurrences=the+teacher`, outsider)).status,
  404,
);
check(
  "and cannot write either",
  (await send(outsider, { intent: "propose" })).status,
  404,
);
check(
  "simulating a reader removes the admin's access to it",
  (await get(corrections, `${admin}; ${forged(OUTSIDER)}`)).status,
  404,
);
d1(
  `UPDATE content_unit SET under_moderation = 1, open_to_all = 0, status = 'draft' WHERE slug = '${HELD}'`,
);

const proposal = await send(modCookie, {
  intent: "propose",
  anchorKey: "chapter-1",
  blockIndex: "0",
  startOffset: "0",
  endOffset: "12",
  quote: "the teacher said",
  proposedText: "the teacher wrote",
  kind: "meaning",
  rationale: "<script>alert(1)</script>",
});
const proposalBody = await proposal.json();
check("a moderator can raise a correction", proposal.status, 200);
check(
  "a moderator CANNOT accept it, not even their own",
  (
    await send(modCookie, {
      intent: "accept",
      id: proposalBody.id,
      expectedUpdatedAt: "x",
    })
  ).status,
  403,
);
check(
  "an admin's accept with a stale token is refused, not applied",
  (
    await send(admin, {
      intent: "accept",
      id: proposalBody.id,
      expectedUpdatedAt: "stale",
    })
  ).status,
  409,
);
const listed = await (await get(corrections, modCookie)).text();
check(
  "the list carries no address, only a name",
  listed.includes(`${MOD}`),
  false,
);
check("the reason was cleaned on write", listed.includes("<script>"), false);

// ---------------------------------------------------------------------------
// The four rules, fired as each kind of person: a reader, two moderators and the admin.
// ---------------------------------------------------------------------------
console.log("\nwho may do what to a correction");
const modB = cookieFor(MOD_B);
/** @param {string} cookie */
const listAs = async (cookie) =>
  (await (await get(corrections, cookie)).json()).corrections;
const mineId = proposalBody.id; // raised by moderator A above

check(
  "another moderator SEES it",
  (await listAs(modB)).some((/** @type {any} */ c) => c.id === mineId),
  true,
);
check(
  "an admin sees it",
  (await listAs(admin)).some((/** @type {any} */ c) => c.id === mineId),
  true,
);
check(
  "another moderator can COMMENT on it",
  (
    await send(modB, {
      intent: "comment",
      id: mineId,
      body: "This matches page 14.",
    })
  ).status,
  200,
);
check(
  "a reader cannot comment",
  (await send(outsider, { intent: "comment", id: mineId, body: "hi" })).status,
  404,
);
check(
  "another moderator CANNOT edit it",
  (
    await send(modB, {
      intent: "revise",
      id: mineId,
      proposedText: "the teacher wrote to him",
      kind: "meaning",
    })
  ).status,
  403,
);
check(
  "another moderator CANNOT delete it",
  (await send(modB, { intent: "remove", id: mineId })).status,
  403,
);
check(
  "another moderator CANNOT decide it",
  (await send(modB, { intent: "dismiss", id: mineId, expectedUpdatedAt: "x" }))
    .status,
  403,
);
check(
  "its own moderator CAN edit it",
  (
    await send(modCookie, {
      intent: "revise",
      id: mineId,
      proposedText: "the teacher wrote to him",
      kind: "meaning",
    })
  ).status,
  200,
);

const thread = (await listAs(modCookie)).find(
  (/** @type {any} */ c) => c.id === mineId,
).comments;
check("the comment is visible to the correction's owner", thread.length, 1);
check(
  "its owner CANNOT remove somebody else's comment",
  (await send(modCookie, { intent: "uncomment", id: thread[0].id })).status,
  403,
);
check(
  "the commenter can remove their own",
  (await send(modB, { intent: "uncomment", id: thread[0].id })).status,
  200,
);

await send(modB, { intent: "comment", id: mineId, body: "second thought" });
const again = (await listAs(admin)).find(
  (/** @type {any} */ c) => c.id === mineId,
).comments;
check(
  "an admin CAN remove any moderator's comment",
  (await send(admin, { intent: "uncomment", id: again[0].id })).status,
  200,
);
check(
  "an admin CAN edit any moderator's correction",
  (
    await send(admin, {
      intent: "revise",
      id: mineId,
      proposedText: "the teacher wrote unto him",
      kind: "meaning",
    })
  ).status,
  200,
);
check(
  "an admin CAN add their own",
  (
    await send(admin, {
      intent: "propose",
      anchorKey: "chapter-1",
      blockIndex: "1",
      startOffset: "0",
      endOffset: "5",
      quote: "hello",
      proposedText: "hullo",
      kind: "typo",
    })
  ).status,
  200,
);
check(
  "an admin CAN delete any moderator's correction",
  (await send(admin, { intent: "remove", id: mineId })).status,
  200,
);

// ---------------------------------------------------------------------------
// "See as them": the administrator sees a MODERATOR'S whole experience — and can change nothing.
// ---------------------------------------------------------------------------
console.log("\nseeing the site as a moderator");
const asMod = `${admin}; ${forged(MOD)}`;
check(
  "the held book is on the simulated moderator's reach",
  (await get(heldPage, asMod)).status,
  200,
);
check(
  "so is the corrections panel's data",
  (await get(corrections, asMod)).status,
  200,
);
check(
  "but the simulated moderator's shelf shows the held book, labelled",
  (await (await get("/library", asMod)).text()).includes("Under Moderation"),
  true,
);
check(
  "and the admin screens are gone (404), as they would be for her",
  (await get("/admin/corrections", asMod)).status,
  404,
);
check(
  "NOTHING can be saved while simulating: a correction is refused",
  (
    await send(asMod, {
      intent: "propose",
      anchorKey: "chapter-1",
      blockIndex: "0",
      startOffset: "0",
      endOffset: "5",
      quote: "hello",
      proposedText: "hullo",
      kind: "typo",
    })
  ).status,
  403,
);
check(
  "nor a comment",
  (await send(asMod, { intent: "comment", id: "x", body: "hi" })).status,
  403,
);

d1(
  `DELETE FROM correction_comment WHERE slug = '${HELD}'; DELETE FROM correction WHERE slug = '${HELD}'; DELETE FROM access_event WHERE scope_type = 'correction' AND subject = '${HELD}';`,
);

d1(`
  DELETE FROM content_unit WHERE slug = '${HELD}';
  DELETE FROM moderator WHERE user_email IN ('${MOD}', '${MOD_B}');
  DELETE FROM user WHERE email = '${MOD_B}';
  DELETE FROM invite WHERE email = '${MOD_B}';
  DELETE FROM access_grant WHERE user_email = '${OUTSIDER}';
  DELETE FROM access_event WHERE subject = '${MOD}';
  DELETE FROM user   WHERE email = '${MOD}';
  DELETE FROM invite WHERE email = '${MOD}';
`);
d1(`UPDATE invite SET revoked_at = NULL WHERE email = '${OUTSIDER}'`);

// Teardown: only rows this script made.
d1(`
  DELETE FROM user    WHERE email = '${OUTSIDER}';
  DELETE FROM invite  WHERE email = '${OUTSIDER}';
  DELETE FROM access_event WHERE subject = '${OUTSIDER}';
  DELETE FROM session WHERE id = 'sess-dev-${Buffer.from(ADMIN).toString("hex").slice(0, 16)}';
  DELETE FROM user    WHERE id = 'dev-${Buffer.from(ADMIN).toString("hex").slice(0, 16)}'
                        AND NOT EXISTS (SELECT 1 FROM account a WHERE a.userId = user.id);
`);

console.log(
  failures === 0 ? "\nall checks passed\n" : `\n${failures} check(s) failed\n`,
);
process.exit(failures === 0 ? 0 : 1);
