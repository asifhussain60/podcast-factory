/**
 * Every surface, at every width, in every theme — as PNGs to look at.
 *
 * The deterministic half of the quality gate is `smoke.mjs`, which fails on
 * things a machine can decide: a status, a console error, a page that scrolls
 * sideways. This is the other half. Nothing here passes or fails; it produces
 * images, and a person or an agent judges them. That division is deliberate — a
 * screenshot differ would fail on every legitimate change to a stylesheet whose
 * whole purpose is to be changed.
 *
 *   npm run dev      # in another terminal, on :5273
 *   npm run shots
 *   npm run shots -- --only reader --theme dark --width phone
 *
 * Writes to `.visual-qa/`, which is gitignored and is deleted by `--clean`. The
 * shots are throwaway by design: they describe one moment of one branch, and a
 * committed baseline would be a second definition of what the site looks like.
 */
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { chromium } from "playwright";

import { BOOK_ROUTES, OPTIONAL_ROUTES, STATIC_ROUTES, THEMES, WIDTHS } from "./routes.mjs";
import { fill, setUp, tearDown } from "./fixtures.mjs";

const BASE = process.env.LISTENER_URL ?? "http://localhost:5273";
const OUT = ".visual-qa";

const args = process.argv.slice(2);
/** @param {string} name */
const flag = (name) => {
  const at = args.indexOf(`--${name}`);
  return at === -1 ? null : args[at + 1];
};

if (args.includes("--clean")) {
  rmSync(OUT, { recursive: true, force: true });
  console.log(`removed ${OUT}`);
  process.exit(0);
}

const onlyRoute = flag("only");
const onlyTheme = flag("theme");
const onlyWidth = flag("width");

const themes = THEMES.filter((t) => onlyTheme === null || t === onlyTheme);
const widths = WIDTHS.filter((w) => onlyWidth === null || w.name === onlyWidth);

/**
 * The reader's own states, which no URL reaches.
 *
 * A chapter with the contents drawer open, with a highlight on the page, with
 * the notes drawer open — these are the views most likely to be wrong and the
 * least likely to be looked at, because getting to them by hand takes six
 * actions. Each one is a script run against the rendered page.
 */
/** @type {Record<string, { name: string, act: (page: import("playwright").Page) => Promise<void> }[]>} */
const STATES = {
  reader: [
    { name: "plain", act: async () => {} },
    {
      name: "contents-open",
      act: async (page) => {
        await page.click(".pf-edge-tab--start");
        await page.waitForSelector(".pf-drawer--start", { timeout: 2000 });
      },
    },
    { name: "selection", act: (page) => raiseSelectionBar(page, 60) },
    {
      name: "highlighted",
      act: async (page) => {
        await applyHighlight(page);
      },
    },
    {
      // The composer, open and empty. Its own state because it is the largest
      // surface the reader ever sees floating over the text, and the only one
      // whose size is a judgment rather than a measurement.
      name: "note-writing",
      act: async (page) => {
        await applyHighlight(page);
        await openComposer(page);
      },
    },
    {
      name: "notes-open",
      act: async (page) => {
        await applyHighlight(page);
        // WITH a note on it. A highlight alone photographs half the entry, and
        // the half it leaves out is the reader's own words.
        await writeNote(page, "The debt of gratitude is the hinge of the whole passage.");
        // The tab on the right edge, which is where the notes live now. It was
        // a button in the toolbar addressed by its accessible name; the tab is
        // addressed by its side, because that is the only thing about it that
        // distinguishes it from the contents tab facing it.
        await page.click(".pf-edge-tab--end").catch(() => {});
        await page.waitForSelector(".pf-drawer--end", { timeout: 2000 }).catch(() => {});
      },
    },
  ],
  "admin-people": [
    { name: "plain", act: async () => {} },
    {
      name: "person-open",
      act: async (page) => {
        await page.click(".pf-person").catch(() => {});
        await page.waitForSelector(".pf-facts", { timeout: 3000 }).catch(() => {});
      },
    },
  ],
  "admin-content": [
    { name: "plain", act: async () => {} },
    {
      name: "book-open",
      act: async (page) => {
        await page.click("text=Who has this").catch(() => {});
        await page.waitForSelector(".pf-grant", { timeout: 3000 }).catch(() => {});
      },
    },
  ],
};

/**
 * Select a passage and raise the bar over it, through the real code path.
 *
 * The selection is made with a Range and the bar is woken with a `pointerup`
 * DISPATCHED ON THE CHAPTER BODY — not by moving the mouse to a coordinate. The
 * first version drove the real mouse to (200, 400), which is a different element
 * on every page, at every width, in every state; in one shot it landed on a row
 * of the open contents drawer and navigated to chapter six, and the picture that
 * came out looked like a layout bug in a toolbar that was in fact fine.
 * Targeting the element means the gesture means the same thing everywhere.
 */
/** @param {import("playwright").Page} page @param {number} length */
async function raiseSelectionBar(page, length = 90) {
  await page.evaluate((n) => {
    const p = document.querySelector(".pf-chapter-body > p");
    if (p === null) return;
    const text = p.firstChild;
    const sel = window.getSelection();
    if (text === null || text.textContent === null || sel === null) return;
    const range = document.createRange();
    range.setStart(text, 0);
    range.setEnd(text, Math.min(n, text.textContent.length));
    sel.removeAllRanges();
    sel.addRange(range);
    p.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
  }, length);
  await page.waitForSelector(".pf-selbar", { timeout: 2000 }).catch(() => {});
}

/**
 * Put a real highlight on the page.
 *
 * Not by injecting a `<mark>`: that would photograph markup this application
 * does not produce. This presses a real colour in the real bar and lets the
 * store, the optimistic paint and the POST all run — so the picture is of the
 * feature, not of a mock-up of it.
 */
/** @param {import("playwright").Page} page */
async function applyHighlight(page) {
  await raiseSelectionBar(page);
  await page.click(".pf-selbar__colour--gold").catch(() => {});
  await page.waitForSelector("mark.pf-hl", { timeout: 2000 }).catch(() => {});
}

/**
 * Reopen the bar on the highlight just made and start writing on it.
 *
 * Through the mark, not through a fresh selection: that is the path a reader
 * takes to annotate something they have already coloured, and it is the one that
 * exercises the composer's edit branch.
 */
/** @param {import("playwright").Page} page */
async function openComposer(page) {
  await page.click("mark.pf-hl").catch(() => {});
  await page.click('[title="Add note"]').catch(() => {});
  await page.waitForSelector("#pf-note-draft", { timeout: 2000 }).catch(() => {});
}

/** @param {import("playwright").Page} page @param {string} text */
async function writeNote(page, text) {
  await openComposer(page);
  await page.fill("#pf-note-draft", text).catch(() => {});
  await page.click("text=Save note").catch(() => {});
  await page.waitForSelector(".pf-selbar", { state: "detached", timeout: 2000 }).catch(() => {});
}

/* -------------------------------------------------------------------------- */

console.log("setting up fixtures");
const { book, chapter, cookies } = setUp();
if (book === null) console.log("  !     no published book — book and reader surfaces skipped");

const routes = [
  ...STATIC_ROUTES.filter((r) => r.expect === 200),
  ...(book === null ? [] : BOOK_ROUTES.filter((r) => r.expect === 200 && !r.path.endsWith("/marks"))),
  ...(book === null ? [] : OPTIONAL_ROUTES.filter((r) => r.needs !== "deck" || book.hasDeck)),
].filter((r) => onlyRoute === null || r.label === onlyRoute);

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const written = [];

try {
  for (const width of widths) {
    for (const theme of themes) {
      for (const route of routes) {
        const cookie = cookies[route.who] ?? null;
        const context = await browser.newContext({
          viewport: { width: width.width, height: width.height },
          deviceScaleFactor: 2,
          ...(cookie === null ? {} : { extraHTTPHeaders: { Cookie: cookie } }),
        });

        // Stamped BEFORE any navigation, so the very first paint is in the
        // right theme — the pre-paint script reads this key and would otherwise
        // photograph the default while resolving.
        await context.addInitScript(`localStorage.setItem("pf-theme", ${JSON.stringify(theme)})`);

        const page = await context.newPage();

        const url = BASE + fill(route.path, book, chapter);

        for (const state of STATES[route.label] ?? [{ name: "plain", act: async () => {} }]) {
          // A FRESH page per state. Running them in sequence on one page made
          // each shot the sum of every state before it — the contents drawer
          // stayed open under the selection bar, and one synthetic click landed
          // inside it and navigated to another chapter entirely. Every picture
          // after that was of a page nobody asked for.
          await page.goto(url, { waitUntil: "networkidle" });
          await state.act(page);
          // One frame for the transition to settle. `--pf-motion` is 160ms.
          await page.waitForTimeout(250);

          const name = `${route.label}--${state.name}--${theme}--${width.name}.png`;
          await page.screenshot({
            path: `${OUT}/${name}`,
            // The viewport, not the full page. A chapter's full-page PNG is tens
            // of thousands of pixels tall; scaled to fit, nothing in it can be
            // judged. The states above are what reach the parts further down.
            fullPage: false,
          });
          written.push(name);
          console.log(`  ${name}`);
        }

        await context.close();
      }
    }
  }
} finally {
  await browser.close();
  tearDown();
}

writeFileSync(`${OUT}/index.txt`, written.join("\n") + "\n");
console.log(`\n${written.length} shots in ${OUT}/ — review, fix, re-shoot, then \`npm run shots -- --clean\`\n`);
