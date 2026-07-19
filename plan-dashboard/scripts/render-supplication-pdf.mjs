/**
 * render-supplication-pdf.mjs — render a supplication's units.json into a
 * facing-column print PDF (English left │ original script right).
 *
 * A SIBLING of render-book-pdf.mjs, deliberately not a branch inside it: the
 * supplication lane is standalone and PDF-only (no episodes, audio, slides, or
 * video), and render-book-pdf.mjs + book-print.css govern every existing
 * reading edition and must stay untouched. This file mirrors that renderer's
 * proven mechanics — local static server, /fonts/** route, Playwright chromium,
 * and `document.fonts.ready` BEFORE paginating so page breaks are deterministic
 * — but assembles its own HTML and inlines its own stylesheet.
 *
 * All print CSS lives in src/styles/supplication-print.css (external single
 * source of truth); never style inside this script.
 *
 *   node scripts/render-supplication-pdf.mjs <units.json> <out.pdf> [theme.css]
 *
 * Input shape (see scripts/podcast/supplication/schema.py for the authority):
 *   {
 *     "slug": "dua-kumayl",
 *     "source_language": "ar" | "ur",
 *     "title_en": "...", "title_src": "...",
 *     "meta": { "type": "...", "attributed_to": "...", "occasion": "...",
 *               "purpose": "...", "place": "..." },
 *     "preamble_en": "paragraph\n\nparagraph",
 *     "units": [ { "n": 1, "source": "...", "english": "...",
 *                  "refrain": false } ]
 *   }
 *
 * Exit 0 on success; 2 on usage/validation error; 3 if the chromium binary is
 * missing (actionable — run `npx playwright install chromium`); 1 otherwise.
 */
import { chromium } from "playwright";
import { readFileSync, mkdirSync, existsSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { themeRoot } from "./lib/book-html.mjs";

const [, , UNITS_PATH, OUT_PATH, THEME_PATH] = process.argv;

const themePath =
  THEME_PATH ||
  path.resolve(import.meta.dirname, "..", "src", "styles", "theme.css");
const printCssPath = path.resolve(
  import.meta.dirname,
  "..",
  "src",
  "styles",
  "supplication-print.css",
);
const fontRoot = path.resolve(import.meta.dirname, "..", "public", "fonts");

export const SCRIPT_LANGS = new Set(["ar", "ur"]);

export const esc = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/** Metadata rows, in the fixed reading order the content model defines. */
export const META_FIELDS = [
  ["type", "Type"],
  ["attributed_to", "Attributed to"],
  ["occasion", "Recommended occasion"],
  ["purpose", "Purpose"],
  ["place", "Place"],
];

export function buildTitleBlock(doc) {
  const meta = doc.meta || {};
  const rows = META_FIELDS.filter(([k]) => meta[k])
    .map(([k, label]) => `<dt>${esc(label)}</dt><dd>${esc(meta[k])}</dd>`)
    .join("\n      ");
  const lang = doc.source_language;
  const titleSrc = doc.title_src
    ? `<p class="sup-title-src sup-src" dir="rtl" lang="${esc(lang)}">${esc(doc.title_src)}</p>`
    : "";
  const preamble = (doc.preamble_en || "")
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${esc(p)}</p>`)
    .join("\n      ");
  return `<header class="sup-titleblock">
      <p class="sup-eyebrow">Supplication</p>
      <h1>${esc(doc.title_en || doc.slug || "")}</h1>
      ${titleSrc}
      ${rows ? `<dl class="sup-meta">\n      ${rows}\n      </dl>` : ""}
      ${preamble ? `<div class="sup-preamble">\n      ${preamble}\n      </div>` : ""}
    </header>`;
}

export function buildUnitsTable(doc) {
  const lang = doc.source_language;
  // Unit numbers are NOT printed. `n` stays in units.json and in the review CLI
  // (it is how a human refers to a unit), but a devotional text is not a
  // numbered reference edition, so the page carries no unit chrome.
  const rows = doc.units
    .map((u) => {
      const cls = u.refrain ? ' class="sup-refrain"' : "";
      return `      <tr${cls}>
        <td class="sup-en">${esc(u.english)}</td>
        <td class="sup-src" dir="rtl" lang="${esc(lang)}">${esc(u.source)}</td>
      </tr>`;
    })
    .join("\n");
  // No <thead>: the columns are self-evident and a repeating header would
  // consume vertical space on every page of a long litany.
  return `<table class="sup-units">\n<tbody>\n${rows}\n</tbody>\n</table>`;
}

export function validate(doc) {
  const errs = [];
  if (!SCRIPT_LANGS.has(doc.source_language))
    errs.push(
      `source_language must be one of ${[...SCRIPT_LANGS].join("|")} (got ${JSON.stringify(doc.source_language)}) — it selects the script face and must never be inferred`,
    );
  if (!Array.isArray(doc.units) || doc.units.length === 0)
    errs.push("units must be a non-empty array");
  else
    doc.units.forEach((u, i) => {
      if (!u || typeof u.source !== "string" || !u.source.trim())
        errs.push(`unit ${i}: missing 'source'`);
      if (!u || typeof u.english !== "string" || !u.english.trim())
        errs.push(`unit ${i}: missing 'english'`);
    });
  return errs;
}

async function main() {
  const doc = JSON.parse(readFileSync(UNITS_PATH, "utf-8"));
  const errs = validate(doc);
  if (errs.length) {
    console.error("supplication-pdf: invalid units.json");
    for (const e of errs) console.error(`  - ${e}`);
    process.exit(2);
  }

  const rootTokens = existsSync(themePath)
    ? themeRoot(readFileSync(themePath, "utf-8"))
    : "";
  const printCss = readFileSync(printCssPath, "utf-8");

  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${esc(doc.title_en || doc.slug || "Supplication")}</title><style>
    :root {${rootTokens}}
${printCss}
  </style></head><body>
    ${buildTitleBlock(doc)}
    ${buildUnitsTable(doc)}
    <p class="sup-colophon">${esc(doc.units.length)} units · source preserved verbatim from OCR</p>
  </body></html>`;

  const MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
  };
  const server = createServer((req, res) => {
    const reqPath = decodeURIComponent((req.url || "/").split("?")[0]);
    if (reqPath === "/" || reqPath === "") {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(html);
      return;
    }
    // Only the font route exists: a supplication PDF has no images or other
    // per-book assets, so there is no second asset root to expose.
    const root = path.dirname(fontRoot);
    const resolved = path.resolve(root, "." + reqPath);
    const type = MIME[path.extname(resolved).toLowerCase()];
    if (
      !reqPath.startsWith("/fonts/") ||
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
    console.error(`supplication-pdf: chromium unavailable — ${first}`);
    console.error(
      "  Run `npx playwright install chromium` in plan-dashboard/, then retry.",
    );
    process.exit(3);
  }
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => console.error("  [pageerror]", e.message));
    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
    // Wait for the self-hosted Naskh/Nastaliq/Source Serif faces to finish
    // loading BEFORE paginating. Without this, font-display:swap can paginate
    // against a fallback face and swap after — which would make row heights
    // (and therefore page breaks) non-deterministic. This is the single most
    // important line for reproducible output.
    await page.evaluate(() => document.fonts.ready);
    mkdirSync(path.dirname(path.resolve(OUT_PATH)), { recursive: true });
    await page.pdf({
      path: OUT_PATH,
      format: "A4",
      printBackground: true,
      margin: { top: "0", right: "0", bottom: "0", left: "0" },
    });
    console.log(`supplication-pdf: wrote ${OUT_PATH}`);
  } finally {
    await browser.close();
    server.close();
  }
}

// Only run when invoked directly — importing this module (e.g. from its test)
// must not launch a browser or read argv.
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  if (!UNITS_PATH || !OUT_PATH) {
    console.error(
      "usage: render-supplication-pdf.mjs <units.json> <out.pdf> [theme.css]",
    );
    process.exit(2);
  }
  main().catch((err) => {
    console.error("supplication-pdf:", err?.stack || err);
    process.exit(1);
  });
}
