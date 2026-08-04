/**
 * Every button on every view, pressed — does anything happen?
 *
 * The gap this closes is narrow and it has already cost a real bug. `smoke.mjs`
 * proves a page loads without errors and `shots.mjs` shows what it looks like;
 * neither PRESSES anything. So a control can be wired, fire its request, get a
 * 200 — and leave the screen exactly as it was, which is what a delete button
 * looked like on 2026-08-04 when a revalidation rule cancelled the refresh that
 * would have shown the row gone. Every layer said "fine" and the button did not
 * work.
 *
 *   npm run dev        # in another terminal, on :5273
 *   npm run controls
 *   npm run controls -- --only reader
 *
 * A control PASSES when pressing it produces something observable: a navigation,
 * a request to the server, or a change to the page. It FAILS when it produces
 * none of the three — inert.
 *
 * Each press gets a FRESH page. A sweep that clicked twenty controls in one
 * session would be testing the twenty-first against a page nineteen presses from
 * where it started, and the first control that opened a drawer would cover the
 * rest.
 *
 * WHAT IS NOT PRESSED, and why — never silently:
 *   · Anything whose accessible name is in SKIP below. Sign-out ends the session
 *     the sweep runs in; the theme controls are localStorage-only by design.
 *   · A control already in its pressed or selected state. Choosing the tab you
 *     are on is honestly nothing, and counting it as inert would train everyone
 *     to ignore this report.
 *   · Links. An <a href> is not inert by construction; the class of bug this
 *     exists for is a BUTTON that needs code behind it. Their hrefs are checked
 *     for being real rather than "#".
 *
 * It runs against the local database and mutates it — that is the point of
 * pressing Delete. Fixture people are cleaned up; the hundred invented readers
 * are seed data (`npm run seed:people`) and a deleted one is not a loss.
 */
import { execFileSync } from "node:child_process";

import { chromium } from "playwright";

import { cookieFor, ADMIN, query, setUp, tearDown } from "./fixtures.mjs";

const BASE = process.env.LISTENER_URL ?? "http://localhost:5273";

/**
 * LOCAL ONLY, and this refuses rather than trusts.
 *
 * The sweep presses Delete and flips "Open to everyone", which is a privilege
 * bit. Against a deployed site it would hand books to every signed-in reader and
 * remove people, so the address is checked rather than assumed — `LISTENER_URL`
 * is an environment variable and environment variables get set by accident.
 */
if (!/^http:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(BASE)) {
  console.error(`refusing to press buttons at ${BASE} — this sweep is local only.`);
  process.exit(2);
}

/**
 * How many instances of ONE repeated control get pressed.
 *
 * Three, not one: the first can pass for a reason peculiar to being first (the
 * top of a list, the only one above the fold), and a second and third from the
 * middle of the run are what make it a sample rather than an anecdote.
 */
const SAMPLE_PER_FAMILY = 3;

/** Accessible names never pressed, each for a reason worth writing down. */
const SKIP = [
  { match: /^sign out$/i, why: "ends the session this sweep runs in" },
  { match: /^(light|sepia|dark)$/i, why: "writes localStorage only, by design" },
  { match: /^skip to content$/i, why: "moves focus, which is its whole job" },
  { match: /^exit simulation$/i, why: "no simulation is running in this sweep" },
];

const args = process.argv.slice(2);
const only = args.includes("--only") ? args[args.indexOf("--only") + 1] : null;

const fixtures = setUp();
if (fixtures.book === null) {
  console.error("no published book in the local database — nothing to sweep");
  process.exit(2);
}

const { slug } = fixtures.book;
const chapter = encodeURIComponent(fixtures.chapter ?? "");
const episode = fixtures.episode;

/** The surfaces, and how to reach the state worth pressing things in. */
const VIEWS = [
  { label: "library", path: "/" },
  { label: "book", path: `/book/${slug}` },
  { label: "book-notes", path: `/book/${slug}?tab=notes` },
  { label: "reader", path: `/book/${slug}/read/${chapter}` },
  // The player's own controls — the transport, and the two panels — exist only
  // once something is PLAYING, so this view reaches that state before taking
  // inventory. Without `prepare` they were simply outside the sweep: not
  // skipped-with-a-reason, but invisible to it, which is the worse of the two.
  ...(episode === null
    ? []
    : [
        {
          label: "player",
          path: `/book/${slug}?tab=listen`,
          prepare: async (/** @type {import("playwright").Page} */ page) => {
            await page.locator(".pf-row__action").first().click().catch(() => {});
            await page.waitForSelector(".pf-player", { timeout: 3000 }).catch(() => {});
          },
        },
      ]),
  { label: "admin", path: "/admin" },
  { label: "admin-content", path: "/admin/content" },
].filter((v) => only === null || v.label === only);

/**
 * What the sweep is about to change, so it can put it back.
 *
 * "Open to everyone" is the widest switch in the application and pressing it is
 * the only way to know the button works — so it is pressed, and then every book
 * is returned to the value it had. Anything this script cannot restore is named
 * in the closing report instead of being quietly left behind.
 */
const openBefore = query("SELECT slug, open_to_all FROM content_unit");

const browser = await chromium.launch();
const cookie = cookieFor(ADMIN);
const at = cookie.indexOf("=");

let failures = 0;
let pressed = 0;

/** A fresh page carrying the administrator's session.
 *  @param {string} path */
async function open(path) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await context.addCookies([
    { name: cookie.slice(0, at), value: cookie.slice(at + 1), domain: "localhost", path: "/" },
  ]);
  const page = await context.newPage();
  /** @type {string[]} */
  const requests = [];
  page.on("request", (r) => requests.push(r.method()));
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  return { context, page, requests };
}

/** Every button on the page, described well enough to find again and to report.
 *  @param {import("playwright").Page} page */
async function inventory(page) {
  return page.evaluate(() => {
    /** @param {Element} el */
    const name = (el) =>
      (el.getAttribute("aria-label") ?? el.textContent ?? "").replace(/\s+/g, " ").trim() ||
      el.getAttribute("title") ||
      "(unnamed)";

    return [...document.querySelectorAll("button")].map((el, index) => {
      const box = el.getBoundingClientRect();
      const style = getComputedStyle(el);

      return {
        index,
        // The class is the last resort rather than "(unnamed)", so a control
        // this report complains about can actually be found in the source.
        name: name(el) === "(unnamed)" ? `(unnamed .${el.className})` : name(el),
        disabled: el.disabled,
        // Present in the markup and not on the screen — the docked drawer's
        // scrim is `display:none` above 64rem, and a thing nobody can press is
        // not a thing that can be inert.
        visible:
          box.width > 0 && box.height > 0 && style.display !== "none" && style.visibility !== "hidden",
        // A control already in the state it would set. Pressing it is honestly
        // nothing, and calling that a failure teaches everyone to ignore this.
        settled:
          el.getAttribute("aria-pressed") === "true" ||
          el.getAttribute("aria-selected") === "true",
        // A submit button on a form the browser will refuse to send — the invite
        // form with an empty required email is the live example. Doing nothing
        // is the correct behaviour there, and the form itself needs a test that
        // fills it in, which is a different kind of check from this one.
        blocked:
          el.type === "submit" && el.form !== null && !el.form.checkValidity(),
      };
    });
  });
}

for (const view of VIEWS) {
  console.log(`\n\x1b[1m${view.label}\x1b[0m  ${view.path}`);

  const first = await open(view.path);
  if (view.prepare) await first.page.waitForTimeout(400);
  if (view.prepare) await view.prepare(first.page);
  const controls = await inventory(first.page);
  const links = await first.page.evaluate(
    () =>
      [...document.querySelectorAll("a[href]")].filter((a) => {
        const href = a.getAttribute("href");
        return href === null || href === "" || href === "#";
      }).length,
  );
  await first.context.close();

  if (links > 0) {
    failures++;
    console.log(`  FAIL ${links} link(s) with no destination`);
  }

  /* ---- Repeated controls are SAMPLED, not exhausted ----------------------
     A transcript is three hundred buttons: one "play from here" and one "make a
     note here" per spoken line. Pressing every one takes hours, writes a note
     for every line in the episode, and learns nothing after the second — they
     are one control rendered N times from one piece of code, and if the third
     works the two-hundredth does.

     So identical accessible names are capped. The count is printed rather than
     quietly dropped, because a sweep that says "all controls passed" while
     having skipped two hundred of them is the kind of green that hides things.
     Names are normalised on their digits first, so "Play from 4 minutes 12
     seconds" and "Play from 9 minutes 3 seconds" are recognised as the same
     control rather than as three hundred unique ones.                       */
  const seen = new Map();
  const family = (/** @type {string} */ name) => name.replace(/\d+/g, "#");
  const skipped = new Map();

  for (const control of controls) {
    const key = family(control.name);
    const n = (seen.get(key) ?? 0) + 1;
    seen.set(key, n);
    if (n > SAMPLE_PER_FAMILY) {
      skipped.set(key, (skipped.get(key) ?? 0) + 1);
      continue;
    }

    const skip = SKIP.find((s) => s.match.test(control.name));
    if (skip) {
      console.log(`  skip  ${control.name} — ${skip.why}`);
      continue;
    }
    if (control.disabled) {
      console.log(`  skip  ${control.name} — disabled`);
      continue;
    }
    if (!control.visible) {
      console.log(`  skip  ${control.name} — not on screen at this width`);
      continue;
    }
    if (control.blocked) {
      console.log(`  skip  ${control.name} — its form is empty, so the browser blocks the submit`);
      continue;
    }
    if (control.settled) {
      console.log(`  skip  ${control.name} — already the selected state`);
      continue;
    }

    const { context, page } = await open(view.path);
    // The same state the inventory was taken in. Each control gets a FRESH page,
    // so a view whose controls only exist after a setup step has to redo it here
    // or every press lands on a button that is not there.
    if (view.prepare) {
      await page.waitForTimeout(400);
      await view.prepare(page);
    }

    const posts = [];
    page.on("request", (r) => {
      if (r.method() !== "GET") posts.push(r.url());
    });

    const before = {
      url: page.url(),
      html: (await page.content()).length,
    };

    const target = page.locator("button").nth(control.index);
    await target.click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(900);

    const after = { url: page.url(), html: (await page.content()).length };
    const moved = before.url !== after.url;
    const changed = Math.abs(before.html - after.html) > 40;
    const wrote = posts.length > 0;

    pressed++;
    if (moved || changed || wrote) {
      const how = [moved && "navigated", wrote && "wrote", changed && "changed the page"]
        .filter(Boolean)
        .join(", ");
      console.log(`  ok    ${control.name}  (${how})`);
    } else {
      failures++;
      console.log(`  \x1b[31mFAIL  ${control.name} — pressing it did nothing\x1b[0m`);
    }

    await context.close();
  }

  // Named, with its count, so "all controls passed" never quietly means "all the
  // ones I bothered with".
  for (const [key, n] of skipped) {
    console.log(`  skip  ${n} more of "${key}" — one control rendered many times, ${SAMPLE_PER_FAMILY} sampled`);
  }
}

await browser.close();
tearDown();

// Put the privilege bit back exactly as it was found, book by book.
const restore = openBefore
  .map((r) => `UPDATE content_unit SET open_to_all = ${Number(r.open_to_all)} WHERE slug = '${r.slug}';`)
  .join("\n");
if (restore !== "") {
  execFileSync(
    "npx",
    ["wrangler", "d1", "execute", "podcast-listener", "--local", "--command", restore],
    { stdio: "pipe" },
  );
  console.log(`\nrestored "open to everyone" on ${openBefore.length} book(s)`);
}

// Said out loud rather than left to be discovered: pressing Delete on the people
// table deletes invented readers, and this cannot put them back.
console.log("invented readers pressed Delete on are gone — `npm run seed:people` re-seeds them");

console.log(
  failures === 0
    ? `\n${pressed} control(s) pressed, all did something\n`
    : `\n${failures} inert control(s) out of ${pressed} pressed\n`,
);
process.exit(failures === 0 ? 0 : 1);
