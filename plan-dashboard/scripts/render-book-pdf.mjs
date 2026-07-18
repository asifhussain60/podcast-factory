/**
 * render-book-pdf.mjs — render a book's book.md into a print PDF.
 *
 * Reuses the site's Playwright chromium (the same one render-mermaid.mjs uses)
 * and the editorial theme tokens, but lays the book out as a clean single-column
 * print document (no nav sidebar). Arabic scripture renders above its English
 * translation, matching the on-screen reader.
 *
 * Book-craft layer (2026-06-11):
 *   - cover page from <book>/book/cover.png when present (full bleed, panel
 *     with title + author from the book's meta.yml);
 *   - chapter-opening pages: numbered "## N. Title" headings become a fresh
 *     page with a "CHAPTER N" eyebrow, the bare title, a hairline rule, and a
 *     drop cap on the opening paragraph; the unnumbered first heading is
 *     treated as the preface;
 *   - Quranic treatment: blockquote paragraphs containing Arabic script get
 *     dir="rtl" + the mushaf styling from book-print.css (Amiri Quran face,
 *     centered, golden frame), translations centered beneath;
 *   - all print CSS lives in src/styles/book-print.css (external single
 *     source of truth), with :root tokens injected from theme.css.
 *
 * HTML assembly (2026-07-15, studio-composer REQ-SC-022): the cover/title/TOC/
 * crosswalk/body markup is built by the shared scripts/lib/book-html.mjs
 * (buildBookHtml) — the SAME module the Studio Preview route calls — so this
 * PDF and the on-screen Preview can never silently disagree. This file now
 * owns only the PDF-specific wrapping: the document shell, the local static
 * server, and the Playwright print-to-PDF step.
 *
 *   node scripts/render-book-pdf.mjs <book.md> <out.pdf> [theme.css]
 *
 * Exit 0 on success; exit 3 if the chromium binary is missing (actionable
 * message — run `npx playwright install chromium`); exit 1 on other errors.
 */
import { chromium } from "playwright";
import { readFileSync, mkdirSync, existsSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";

import { buildBookHtml, themeRoot } from "./lib/book-html.mjs";

const [, , MD_PATH, OUT_PATH, THEME_PATH, FLAG_V2, FLAG_SELF_STUDY] =
  process.argv;
// The renderer honors book/visual-layout.json and enables the unified
// pagination CSS (scoped under body.book-v2). Callers always pass "1".
const V2 = String(FLAG_V2 || "").trim() === "1";
// Opt-in self-study layer (body.book-self-study): renders labeled Contextual-note
// and Study-summary asides + bullet lists. Off unless the caller passes "1".
const SELF_STUDY = String(FLAG_SELF_STUDY || "").trim() === "1";
if (!MD_PATH || !OUT_PATH) {
  console.error("usage: render-book-pdf.mjs <book.md> <out.pdf> [theme.css]");
  process.exit(2);
}
const themePath =
  THEME_PATH ||
  path.resolve(import.meta.dirname, "..", "src", "styles", "theme.css");
const printCssPath = path.resolve(
  import.meta.dirname,
  "..",
  "src",
  "styles",
  "book-print.css",
);
const fontRoot = path.resolve(import.meta.dirname, "..", "public", "fonts");

async function main() {
  const rootTokens = existsSync(themePath)
    ? themeRoot(readFileSync(themePath, "utf-8"))
    : "";
  const printCss = readFileSync(printCssPath, "utf-8");

  const {
    assetRoot,
    coverHtml,
    titlePage,
    tocHtml,
    crosswalkHtml,
    bodyHtml,
    bodyClass,
  } = buildBookHtml(MD_PATH, { v2: V2, selfStudy: SELF_STUDY });
  const bodyClassAttr = bodyClass ? ` class="${bodyClass}"` : "";

  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    :root {${rootTokens}}
${printCss}
  </style></head><body${bodyClassAttr}>
    ${coverHtml}
    ${titlePage}
    ${tocHtml}
    ${crosswalkHtml}
    ${bodyHtml}
  </body></html>`;

  const MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".woff2": "font/woff2",
  };
  const server = createServer((req, res) => {
    const reqPath = decodeURIComponent((req.url || "/").split("?")[0]);
    if (reqPath === "/" || reqPath === "") {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(html);
      return;
    }
    // Font route: /fonts/** → plan-dashboard/public/fonts/**
    const root = reqPath.startsWith("/fonts/")
      ? path.dirname(fontRoot)
      : assetRoot;
    const resolved = path.resolve(root, "." + reqPath);
    const type = MIME[path.extname(resolved).toLowerCase()];
    // Traversal guard: only files under the allowed root, known types only.
    if (
      !resolved.startsWith(root + path.sep) ||
      !type ||
      !existsSync(resolved)
    ) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    res.writeHead(200, { "Content-Type": type });
    res.end(readFileSync(resolved));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const { port } = server.address();

  let browser;
  try {
    browser = await chromium.launch();
  } catch (err) {
    server.close();
    const first = String(err.message || err).split("\n")[0];
    console.error(`book-pdf: chromium unavailable — ${first}`);
    console.error(
      "  Run `npx playwright install chromium` in plan-dashboard/, then retry.",
    );
    process.exit(3);
  }
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => console.error("  [pageerror]", e.message));
    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
    // Wait for ALL @font-face fonts (self-hosted Source Serif 4 + Amiri) to finish
    // loading before paginating. Without this, font-display:swap can paginate with
    // a fallback font and swap after — making page/line breaks non-deterministic.
    await page.evaluate(() => document.fonts.ready);
    mkdirSync(path.dirname(OUT_PATH), { recursive: true });
    await page.pdf({
      path: OUT_PATH,
      format: "A4",
      printBackground: true,
      margin: { top: "0", right: "0", bottom: "0", left: "0" },
    });
    console.log(`book-pdf: wrote ${OUT_PATH}`);
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((e) => {
  console.error("book-pdf: " + (e?.stack || e));
  process.exit(1);
});
