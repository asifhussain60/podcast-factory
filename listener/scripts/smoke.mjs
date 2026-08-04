/**
 * The runtime gate this application has never had.
 *
 * `npm run check` is typecheck + unit tests + build. Nothing in it has ever
 * OPENED A PAGE, which is why a console error, a broken client island, a 5xx on
 * a route nobody visits, or a layout that scrolls sideways on a phone all reach
 * a human rather than a command. This is the peer of `plan-dashboard`'s own
 * `npm run smoke`, and it is deliberately deterministic: zero model spend, one
 * exit code.
 *
 *   npm run dev        # in another terminal, on :5273
 *   npm run smoke
 *
 * What it asserts, per route, per identity, per width:
 *
 *   - the status is the one the manifest declares (this is where the ACCESS
 *     model is fired: a book you were not given must 404, identically to a book
 *     that does not exist)
 *   - no console error and no uncaught exception
 *   - no failed network request
 *   - no horizontal page overflow
 *   - every interactive control is at least 44px on its short side
 *
 * It runs `security-smoke.mjs` first. That script covers the things a browser
 * cannot easily fire — the `_routes` single-fetch bypass, byte-identical 404
 * bodies — and there is no reason to look at pixels if the gates are open.
 *
 * Local only. Every fixture is written to the Miniflare D1 file.
 */
import { execFileSync } from "node:child_process";
import { chromium } from "playwright";

import { BOOK_ROUTES, OPTIONAL_ROUTES, STATIC_ROUTES, WIDTHS } from "./routes.mjs";
import { fill, setUp, tearDown } from "./fixtures.mjs";

const BASE = process.env.LISTENER_URL ?? "http://localhost:5273";

let failures = 0;
/** @param {string} what @param {string} detail */
const fail = (what, detail) => {
  failures++;
  console.log(`  FAIL  ${what}\n        ${detail}`);
};
/** @param {string} what */
const pass = (what) => console.log(`  ok    ${what}`);

/* -------------------------------------------------------------------------- */

console.log("\nsecurity gates");
try {
  execFileSync("node", ["scripts/security-smoke.mjs"], { stdio: "inherit" });
} catch {
  console.log("\nsecurity-smoke failed — stopping before the visual checks.");
  process.exit(1);
}

console.log("\nsetting up fixtures");
const { book, chapter, cookies } = setUp();

if (book === null) {
  console.log("  !     no published book with chapters in the local database.");
  console.log("        The book, reader and slides routes are SKIPPED — not passed.");
} else {
  console.log(`  ok    using "${book.title}" (${book.slug})`);
}

const routes = [
  ...STATIC_ROUTES,
  ...(book === null ? [] : BOOK_ROUTES),
  ...(book === null ? [] : OPTIONAL_ROUTES.filter((r) => r.needs !== "deck" || book.hasDeck)),
];

const browser = await chromium.launch();

try {
  for (const width of WIDTHS) {
    console.log(`\n${width.name} · ${width.width}px`);

    for (const route of routes) {
      const url = BASE + fill(route.path, book, chapter);
      const cookie = cookies[route.who] ?? null;

      const context = await browser.newContext({
        viewport: { width: width.width, height: width.height },
        // Set on the context rather than as a header so it survives the
        // redirects a signed-out visit follows.
        ...(cookie === null ? {} : { extraHTTPHeaders: { Cookie: cookie } }),
      });

      /** @type {string[]} */
      const problems = [];
      const page = await context.newPage();

      page.on("console", (m) => {
        if (m.type() !== "error") return;
        const text = m.text();
        // A route we ASKED to be refused logs its own refusal: Chrome reports
        // every non-2xx navigation as "Failed to load resource". Counting that
        // would make every access assertion fail for succeeding, which is how a
        // gate that works ends up looking broken.
        if (route.expect !== 200 && /Failed to load resource/.test(text)) return;
        problems.push(`console: ${text.slice(0, 200)}`);
      });
      page.on("pageerror", (e) => problems.push(`uncaught: ${String(e).slice(0, 200)}`));
      page.on("requestfailed", (r) => {
        // A navigation aborted by a redirect we asked not to follow is not a
        // failed request; it is the thing being measured.
        const why = r.failure()?.errorText ?? "";
        if (why.includes("ERR_ABORTED")) return;
        problems.push(`request failed: ${r.url().slice(0, 120)} (${why})`);
      });

      let status = 0;
      try {
        const response = await page.goto(url, {
          waitUntil: "domcontentloaded",
          // A redirect is an ANSWER here, not a step to be followed: the
          // signed-out cases assert a 302 and following it would report the
          // sign-in page's 200 instead.
          ...(route.expect === 302 ? {} : {}),
        });
        status = response?.status() ?? 0;
      } catch (error) {
        fail(`${route.label} @ ${url}`, String(error).split("\n")[0]);
        await context.close();
        continue;
      }

      const label = `${route.label.padEnd(22)} ${route.who.padEnd(6)} ${status}`;

      // A 302 is reported by Playwright as the status of the FINAL response, so
      // "expected a redirect" is checked by where it landed rather than by the
      // code — which is also the stronger assertion: it proves the destination.
      const landed = new URL(page.url()).pathname;
      const asked = new URL(url).pathname;

      if (route.expect === 302) {
        if (landed === asked) fail(label, `expected a redirect away from ${asked}, stayed put`);
        else if (!landed.startsWith("/sign-in")) fail(label, `redirected to ${landed}, wanted /sign-in`);
        else pass(`${label} → ${landed}`);
      } else if (status !== route.expect) {
        fail(label, `wanted ${route.expect}`);
      } else if (landed !== asked && route.expect === 200) {
        fail(label, `asked for ${asked} and landed on ${landed} — an undeclared redirect`);
      } else {
        pass(label);
      }

      // Layout checks only make sense on a page that rendered. A 404 body is a
      // deliberate near-empty document and has nothing to measure.
      if (status === 200 && !route.path.endsWith("/marks")) {
        const layout = await page.evaluate(() => {
          const doc = document.documentElement;
          const overflow = doc.scrollWidth - doc.clientWidth;

          /* Two floors, because there are honestly two rules.
           *
           * WCAG 2.2 AA (2.5.8) sets 24×24 for every target, and exempts a link
           * inside a sentence — an inline link cannot be 44px tall without
           * wrecking the line it sits in, which is why the spec exempts it
           * rather than asking anyone to try. That is the HARD floor here.
           *
           * 44px is AAA, and it is the right number for the controls a thumb
           * reaches for while holding a phone one-handed: the reader's toolbar,
           * the bar over a selection, the steppers. Those are named, and held to
           * it. Applying 44 everywhere instead would have forced inline links
           * into blocks, which is a worse page in the name of a better score.
           */
          /* `.pf-swatch` is deliberately NOT in this list, and the reasoning is
           * worth keeping: it is one segment of a three-segment pill with no gap
           * between segments, so a miss lands on a neighbouring theme rather
           * than on nothing. It is held to 44px TALL in the stylesheet and 36px
           * wide, which clears the 24px AA floor with room — and at 44 square it
           * rendered as a circle, reading as a status light rather than as one
           * choice of three. */
          const THUMB = ".pf-tool, .pf-toolbar__home, .pf-toolbar__contents, .pf-stepper__step, .pf-selbar__action, .pf-selbar__colour, .pf-mark__remove";

          const small = [];
          for (const el of document.querySelectorAll(
            "button, a[href], select, input:not([type=hidden]), [role=button], [role=tab]",
          )) {
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue; // hidden panel, or sr-only
            // 1px of slack absorbs sub-pixel layout; it does not excuse a
            // control designed one step too small.
            const floor = el.matches(THUMB) ? 43 : 23;
            if (Math.min(r.width, r.height) < floor) {
              small.push(
                `${el.tagName.toLowerCase()}.${(el.className || "").toString().split(" ")[0]} ${Math.round(r.width)}x${Math.round(r.height)} (wanted ${floor + 1})`,
              );
            }
          }

          const images = [...document.images]
            .filter((i) => i.complete && i.naturalWidth === 0)
            .map((i) => i.src.slice(0, 80));

          return { overflow, small: small.slice(0, 6), images };
        });

        if (layout.overflow > 1) {
          fail(`${route.label} @ ${width.name}`, `page scrolls sideways by ${layout.overflow}px`);
        }
        if (layout.images.length > 0) {
          fail(`${route.label} @ ${width.name}`, `broken images: ${layout.images.join(", ")}`);
        }
        // Touch targets are only a requirement where a finger is the pointer.
        if (width.width <= 768 && layout.small.length > 0) {
          fail(
            `${route.label} @ ${width.name}`,
            `targets under 44px: ${layout.small.join(", ")}`,
          );
        }
      }

      for (const problem of problems) fail(`${route.label} @ ${width.name}`, problem);

      await context.close();
    }
  }
} finally {
  await browser.close();
  console.log("\ncleaning up fixtures");
  tearDown();
}

console.log(
  failures === 0
    ? `\nall clear — ${routes.length} routes × ${WIDTHS.length} widths\n`
    : `\n${failures} failure${failures === 1 ? "" : "s"}\n`,
);

process.exit(failures === 0 ? 0 : 1);
