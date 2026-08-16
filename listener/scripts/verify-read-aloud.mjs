/**
 * Every chapter of every published book, checked for a working read-aloud control.
 *
 * The database can say a chapter is narrated while the page still shows nothing —
 * the reader only renders the control when the narration row AND its uploaded
 * audio both survive the join, and a broken media key fails exactly there. So
 * this asks the rendered page, not the database, and it asks about every chapter
 * rather than the one chapter a screenshot happens to show.
 *
 * Local only, and it refuses any other host: it signs in as the administrator to
 * reach every book at once.
 */
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { ADMIN, query } from "./fixtures.mjs";
import { cookieFor } from "./fixtures.mjs";

const BASE = process.env.BASE ?? "http://localhost:5273";
if (!/^http:\/\/localhost:/.test(BASE)) {
  console.error(`refusing to run against ${BASE} — local only`);
  process.exit(2);
}
const OUT = ".read-aloud-check";
mkdirSync(OUT, { recursive: true });

const books = query(`
  SELECT c.slug, c.title,
         (SELECT count(*) FROM chapter WHERE slug = c.slug) AS chapters
    FROM content_unit c
   WHERE c.kind != 'work'
     ${process.env.INCLUDE_DRAFTS === "1" ? "" : "AND c.status = 'published'"}
     AND (SELECT count(*) FROM chapter WHERE slug = c.slug) > 0
   ORDER BY c.title
`);

const cookie = cookieFor(ADMIN);
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
await context.addCookies([
  {
    name: cookie.split("=")[0],
    value: cookie.split("=").slice(1).join("="),
    domain: "localhost",
    path: "/",
  },
]);
const page = await context.newPage();

const summary = [];

for (const book of books) {
  const chapters = query(
    `SELECT anchor_key, title, idx FROM chapter WHERE slug = '${book.slug}' ORDER BY idx`,
  );
  let withControl = 0;
  let unreachable = 0;
  const gaps = [];
  for (const ch of chapters) {
    const url = `${BASE}/book/${book.slug}/read/${encodeURIComponent(ch.anchor_key)}`;
    const response = await page.goto(url, { waitUntil: "domcontentloaded" });
    // A draft book answers 404 for everyone, admin included — status is what
    // makes a book readable at all. Reporting that as "the control is missing"
    // would blame read-aloud for a visibility decision that has nothing to do
    // with it, so the two are counted apart.
    if (response !== null && response.status() === 404) {
      unreachable += 1;
      continue;
    }
    // The button the reader actually renders — and it needs hydration, because
    // it appears only once the client-side player exists. Waiting for the
    // selector rather than counting immediately is the difference between
    // "no read-aloud" and "not hydrated yet".
    const button = page.locator(".pf-reader-listen__button");
    const found = await button
      .first()
      .waitFor({ state: "visible", timeout: 5000 })
      .then(() => true)
      .catch(() => false);
    if (found) withControl += 1;
    else gaps.push(`${ch.idx}. ${ch.title}`);
  }
  summary.push({
    title: book.title,
    slug: book.slug,
    total: chapters.length,
    withControl,
    unreachable,
    gaps,
  });
  // One screenshot per book, on its first chapter, as the visual record.
  if (chapters.length && unreachable < chapters.length) {
    await page.goto(
      `${BASE}/book/${book.slug}/read/${encodeURIComponent(chapters[0].anchor_key)}`,
      { waitUntil: "networkidle" },
    );
    await page.screenshot({ path: `${OUT}/${book.slug}.png` });
  }
}

await browser.close();

console.log("\nread-aloud control, per published book\n");
for (const s of summary) {
  const reachable = s.total - s.unreachable;
  const mark =
    s.unreachable === s.total
      ? "DRFT"
      : s.withControl === reachable && reachable > 0
        ? "OK  "
        : s.withControl === 0
          ? "NONE"
          : "PART";
  const note =
    s.unreachable === s.total ? "  (draft — no reader page for anyone)" : "";
  console.log(
    `${mark}  ${s.title.padEnd(32)} ${s.withControl}/${reachable}${note}`,
  );
  for (const g of s.gaps.slice(0, 5)) console.log(`        missing: ${g}`);
  if (s.gaps.length > 5) console.log(`        …and ${s.gaps.length - 5} more`);
}
const partial = summary.filter(
  (s) => s.withControl > 0 && s.withControl < s.total - s.unreachable,
);
const drafts = summary.filter((s) => s.unreachable === s.total);
const wired = summary.filter(
  (s) => s.unreachable < s.total && s.withControl === s.total - s.unreachable,
);
console.log(
  `\n${wired.length} fully wired, ${partial.length} partial, ` +
    `${summary.length - wired.length - partial.length - drafts.length} with none, ` +
    `${drafts.length} draft (unreadable, so not counted)`,
);
process.exit(partial.length ? 1 : 0);
