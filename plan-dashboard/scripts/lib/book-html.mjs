/**
 * book-html.mjs — the SINGLE HTML-assembly source for a book's reading edition.
 *
 * Extracted from render-book-pdf.mjs (studio-composer REQ-SC-022) so the printed
 * PDF and the in-browser Preview (Studio redesign Phase 3) consume identical
 * markup instead of two hand-synced renderers. Pure — no Playwright, no
 * process.argv, no filesystem writes; every function here only reads book
 * content and returns strings.
 *
 * Callers:
 *   - scripts/render-book-pdf.mjs — wraps buildBookHtml() output in a full
 *     <html> document + print CSS, serves it locally, and screenshots it to
 *     PDF via Playwright.
 *   - src/pages/studio/[slug]/preview.astro — INDIRECTLY. It calls
 *     ensurePreviewPageImages() (scripts/lib/preview-pages.mjs), which shells out
 *     to render-book-pdf.mjs into a scratch PDF, rasterizes it with pdftoppm, and
 *     stacks the page images. So the Preview shows the PDF renderer's own output
 *     rather than a second pagination of the same markup.
 *
 * Corrected 2026-07-20. This docstring claimed for two design revisions that the
 * preview "calls buildBookHtml() directly … and paginates the result client-side
 * with vendored Paged.js". None of that is true: there is no Paged.js dependency
 * in this repo, and the preview route's own header records why — live in-browser
 * pagination hung this environment's Chromium on a two-paragraph, zero-stylesheet
 * document, so the approach was abandoned for rasterization.
 *
 * The correction matters beyond tidiness. A stale docstring here is what made
 * "the two surfaces are two engines that can disagree" look true, and an agent
 * existed for two design revisions to police a divergence that cannot occur while
 * the Preview is a rasterizer. It is deleted; this note is what stops it coming
 * back.
 */
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { readTextColours, applyTextColours } from "./text-colour.mjs";
import { anchorKey } from "./anchor-key.mjs";
import { loadLayout, applyLayout } from "../visual-layout.mjs";

const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
const ARABIC_INLINE_RE = /[﴿«]?[\s؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+[﴾»]?/g;
const NUMBER_WORDS = [
  "",
  "One",
  "Two",
  "Three",
  "Four",
  "Five",
  "Six",
  "Seven",
  "Eight",
  "Nine",
  "Ten",
  "Eleven",
  "Twelve",
  "Thirteen",
  "Fourteen",
  "Fifteen",
  "Sixteen",
  "Seventeen",
  "Eighteen",
  "Nineteen",
  "Twenty",
  "Twenty-One",
  "Twenty-Two",
  "Twenty-Three",
  "Twenty-Four",
  "Twenty-Five",
  "Twenty-Six",
  "Twenty-Seven",
  "Twenty-Eight",
  "Twenty-Nine",
  "Thirty",
];

/**
 * Is this paragraph an Arabic QUOTATION, rather than English containing Arabic?
 *
 * Proportional: an English sentence carrying a glossary term (`the bab (بَاب)`)
 * is English; a quotation carrying a footnote digit is Arabic. Two thirds of the
 * letters decides it.
 *
 * It matters because such a paragraph gets a DISPLAY treatment — centered, at the
 * quotation size, with the leading the vowel marks need. Without the class it is
 * a plain `<p>` at the body's 1.62 leading, and `.ar-inline` pins the runs inside
 * it to that same line-height to stop one Arabic word inflating a Latin line. That
 * is right for a word in a sentence and wrong for a whole paragraph of it — and
 * once every run carried its marks the stacks had nowhere to go, which is how it
 * came to look oversized and cramped at once (Asif, 2026-07-30).
 *
 * THREE-WAY MIRROR, pinned by `arabic-block.fixtures.json`:
 *   - here (the PDF and the Composer's Read view),
 *   - `isArabicOnlyParagraph` in src/lib/reader/markdown.ts (the reader; it is
 *     client-bundled and cannot import this Node-only module),
 *   - `_book_mirror.is_arabic_block` in Python (the paragraph merge).
 * A copy that drifts does not throw — it silently gives one surface a display
 * block the others render as running prose.
 */
export function isArabicOnlyParagraph(s) {
  const arabic = (s.match(/[ؠ-يٱ-ۓ]/g) || []).length;
  const latin = (s.match(/[A-Za-z]/g) || []).length;
  return arabic > 20 && arabic > 2 * latin;
}

export function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
export function renderInline(text) {
  let s = escapeHtml(text);
  s = s.replace(ARABIC_INLINE_RE, (match) => {
    if (!ARABIC_RE.test(match)) return match;
    const leading = match.match(/^\s*/)?.[0] || "";
    const trailing = match.match(/\s*$/)?.[0] || "";
    const body = match.slice(leading.length, match.length - trailing.length);
    return `${leading}<span class="ar-inline" dir="rtl" lang="ar">${body}</span>${trailing}`;
  });
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  return s;
}

export function extractToc(md) {
  const items = [];
  const headingRe = /^##\s+(.+)$/gm;
  let match;
  let sawNumbered = false;
  while ((match = headingRe.exec(md)) !== null) {
    const raw = match[1].trim();
    const numbered = raw.match(/^(\d+)\.\s+(.+)$/);
    if (numbered) {
      sawNumbered = true;
      items.push({ label: numbered[1], title: numbered[2].trim() });
    } else if (!sawNumbered && items.length === 0) {
      items.push({ label: items.length === 0 ? "Preface" : "", title: raw });
    }
  }
  return items;
}

export function renderToc(items) {
  if (!items.length) return "";
  const rows = items
    .map((item) => {
      const label = item.label
        ? `<span class="toc-label">${escapeHtml(item.label)}</span>`
        : "";
      return `<li>${label}<span class="toc-title">${renderInline(item.title)}</span></li>`;
    })
    .join("");
  return `<section class="toc-page"><p class="toc-eyebrow">Contents</p><h2>Contents</h2><ol>${rows}</ol></section>`;
}
/** ASCII-fold a display name (meta.yml authors carry diacritics). */
export function asciiFold(s) {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[ʻʿ‘’ʼ]/g, "'");
}
/** Read the author display name from the book's meta.yml (best effort). */
export function readAuthor(bookContentDir) {
  const metaPath = path.join(bookContentDir, "meta.yml");
  if (!existsSync(metaPath)) return "";
  const line = readFileSync(metaPath, "utf-8")
    .split(/\r?\n/)
    .find((l) => /^\s*author:\s*/.test(l));
  if (!line) return "";
  let value = line.replace(/^\s*author:\s*/, "").trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return asciiFold(value.trim());
}
/** The style families and translation faces a book may choose. Duplicated as
 *  typed constants in the API route (citation-style.ts) because this is a
 *  plain-.mjs module the Astro route cannot import types from; the two lists must
 *  change together. `plain` leads because it is the default (locked 2026-07-21). */
export const CITATION_FAMILIES = ["plain", "scholarly", "elegant"];
export const TRANSLATION_FONTS = [
  "eb-garamond",
  "cormorant-garamond",
  "crimson-pro",
  "lora",
];
/** The NON-Qur'anic Arabic face. Scripture is not in this list and never will
 *  be: a run the audit resolved against the canonical mushaf is set in the KFGQPC
 *  Uthmanic script because that is the orthography the text is written in, which
 *  is a correctness rule, not a preference. This choice covers everything else —
 *  hadith, sayings, poetry, the book's own Arabic phrases. */
export const ARABIC_FONTS = [
  "scheherazade-new",
  "amiri",
  // Three modern faces added 2026-08-02. Declaring one here is only a third of
  // the job: it must also carry an @font-face in BOTH book-print.css and
  // theme-tokens.css, and a `.ar-<id>` stack in quote-typography.css.
  "cairo",
  "tajawal",
  "ibm-plex-sans-arabic",
];

/** How large the book sets its Arabic — display quotations AND terms woven into
 *  prose, which move together (quote-typography.css `.ars-*`). `standard` is the
 *  default and stamps no class: it IS the :root value, so an unset book and one
 *  explicitly set to standard render through the same declaration. */
export const ARABIC_SIZES = ["compact", "standard", "large", "generous"];
export const DEFAULT_ARABIC_SIZE = "standard";

/** The colour Arabic is set in (quote-typography.css `.ari-*`). `maroon` is the
 *  default and stamps no class, for the same reason `standard` does not. Every
 *  option is measured to clear WCAG AA on all three papers — see that file. */
export const ARABIC_INKS = ["maroon", "ink", "indigo", "forest", "brown"];
export const DEFAULT_ARABIC_INK = "maroon";

/**
 * The pipeline's machine fence kinds — comment markers that delimit spans the
 * Python phases own (`0book-augment` asides, `_book_bridges` bridges, the
 * self-study summary layer, `_book_frontmatter`'s edition introduction). They
 * are load-bearing in book.md and must NEVER render as visible text.
 *
 * MIRRORS `FENCE_KINDS` in src/lib/reader/book-fences.ts, which is the
 * contract's declaration; the two are pinned in agreement by a test rather than
 * trusted, because this renderer also runs under plain node for the PDF build
 * and so cannot import the TypeScript side.
 */
export const MACHINE_FENCE_KINDS = [
  "editorial",
  "study-summary",
  "bridge",
  "edition-intro",
];

/** An ordered-list item. MIRRORS `OL_ITEM_RE` in src/lib/reader/markdown.ts —
 *  the reader and the printed page must agree on what a list is, and on the
 *  ordinal each item states. Pinned by the cross-renderer test in
 *  book-html.test.mjs. */
const OL_ITEM_RE = /^(\d+)\.\s+(.+)$/;
const UL_ITEM_RE = /^\s*[-*]\s+(.+)$/;

/** Does an open list continue past the blank line at `from`? Same contract as
 *  `continuesList` in markdown.ts: a blank line between items does NOT end a
 *  list, so a loose `1. / 2. / 3.` stays one list with its ordinals intact. */
function listContinues(lines, from, kind) {
  for (let j = from; j < lines.length; j += 1) {
    const next = lines[j].trim();
    if (next.length === 0) continue;
    return kind === "ol" ? OL_ITEM_RE.test(next) : UL_ITEM_RE.test(next);
  }
  return false;
}

const MACHINE_FENCE_RE = new RegExp(
  `^<!--\\s*(?:${MACHINE_FENCE_KINDS.join("|")}):(?:begin|end)\\s*-->$`,
);

/** Read the per-book citation-style family from book/citation-style.json.
 *  Returns 'plain' | 'scholarly' | 'elegant', or '' when the file is absent or
 *  the value is unknown (renderer then leaves the body unstyled = default look). */
export function readCitationFamily(bookDir) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const family = JSON.parse(readFileSync(p, "utf-8"))?.family;
    return CITATION_FAMILIES.includes(family) ? family : "";
  } catch {
    return "";
  }
}
/** Read the per-book translation face from the same file. The field is OPTIONAL
 *  and was added after the first books shipped, so an absent or unknown value
 *  reads as '' and every consumer falls back to the --q-tr-face default (EB
 *  Garamond) — an older book gains the face without its artifact being rewritten. */
export function readTranslationFont(bookDir) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const font = JSON.parse(readFileSync(p, "utf-8"))?.translation_font;
    return TRANSLATION_FONTS.includes(font) ? font : "";
  } catch {
    return "";
  }
}
/** The book's non-Qur'anic Arabic face, from the same file. Optional in exactly
 *  the way translation_font is: absent or unknown reads as '' and every surface
 *  falls back to the --q-ar-face default (Scheherazade New), so no shipped book's
 *  artifact needed rewriting to gain the setting. */
export function readArabicFont(bookDir) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const font = JSON.parse(readFileSync(p, "utf-8"))?.arabic_font;
    return ARABIC_FONTS.includes(font) ? font : "";
  } catch {
    return "";
  }
}
/** The book's Arabic size and ink, from the same file.
 *
 *  Both return '' for the DEFAULT as well as for absent/unknown, and that is
 *  deliberate rather than lossy: the default is the `:root` declaration in
 *  quote-typography.css, so stamping `.ars-standard` would mean maintaining a
 *  second declaration that has to agree with it forever. '' means "the class is
 *  not needed", which is the truth. */
export function readArabicSize(bookDir) {
  return readOptionalChoice(
    bookDir,
    "arabic_size",
    ARABIC_SIZES,
    DEFAULT_ARABIC_SIZE,
  );
}
export function readArabicInk(bookDir) {
  return readOptionalChoice(
    bookDir,
    "arabic_ink",
    ARABIC_INKS,
    DEFAULT_ARABIC_INK,
  );
}
function readOptionalChoice(bookDir, key, allowed, fallback) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const v = JSON.parse(readFileSync(p, "utf-8"))?.[key];
    return allowed.includes(v) && v !== fallback ? v : "";
  } catch {
    return "";
  }
}
/** The Arabic runs this book has resolved against the CANONICAL MUSHAF, as a set
 *  of their exact text.
 *
 *  Why exact text rather than a recomputed skeleton: the classification lives in
 *  `_system/book-arabic-audit.json`, written by the Python audit, and the only
 *  honest way to recompute it here would be a JavaScript mirror of
 *  `_arabic_coverage.normalize_arabic` — a fold table that must then be kept in
 *  step with the Python forever, with a silent misclassification as the failure
 *  mode. The audit already stores each run's verbatim text, and all 52 runs of
 *  this book match `book.md` byte-for-byte, so a plain string set is both simpler
 *  and impossible to drift.
 *
 *  Consumers use it to pick the Arabic FACE: scripture is set in the Uthmanic
 *  face, everything else in Scheherazade New. An absent or stale audit yields an
 *  empty set, and every run then renders in the non-Qur'anic face — the
 *  conservative direction, since it never dresses ordinary prose as scripture. */
export function readQuranicRuns(bookContentDir) {
  const p = path.join(bookContentDir, "_system", "book-arabic-audit.json");
  const set = new Set();
  if (!existsSync(p)) return set;
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    for (const ch of data?.chapters || []) {
      for (const run of ch?.runs || []) {
        if (run?.resolution === "canonical-mushaf" && run?.text)
          set.add(String(run.text).trim());
      }
    }
  } catch {
    /* tolerant: a bad audit just means everything reads as non-Qur'anic */
  }
  return set;
}

/** Map visual_id -> { src, embeddedTitle } from book/visuals/index.json (v2).
 *  Absent index (today's state) yields an empty map — the layout applier then
 *  no-ops, so rendering is unchanged. */
export function readVisualAssets(bookContentDir) {
  const p = path.join(bookContentDir, "book", "visuals", "index.json");
  const map = new Map();
  if (!existsSync(p)) return map;
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    for (const v of data?.visuals || []) {
      if (!v?.id || !v?.file) continue;
      map.set(String(v.id), {
        src: `/book/visuals/${v.file}`,
        embeddedTitle: String(v.embedded_title || ""),
      });
    }
  } catch {
    /* tolerant: a bad index just means no contract-driven figures */
  }
  return map;
}

/**
 * Read the source crosswalk. Accepts BOTH the `{schema, book, chapters}` object
 * and a bare array of chapter rows.
 *
 * The strict-and-silent version of this cost a whole apparatus page. A
 * regeneration wrote the rows as a top-level array, this returned `[]`, the
 * crosswalk page rendered as an empty string, the same empty map starved the
 * per-chapter "Arabic source pp." lines, and the book printed one page shorter
 * with no error anywhere in the pipeline. Nothing but a human reading the PDF
 * caught it.
 *
 * So: tolerate the shape, and refuse to be silent. A crosswalk file that exists
 * but yields no rows is a broken artifact, not an absent one, and it throws —
 * an empty return here is reserved for "there is no crosswalk", which is a
 * legitimate state for the companion route.
 */
export function readCrosswalk(bookContentDir) {
  const p = path.join(bookContentDir, "book", "source-crosswalk.json");
  if (!existsSync(p)) return [];
  let data;
  try {
    data = JSON.parse(readFileSync(p, "utf-8"));
  } catch (err) {
    throw new Error(`source-crosswalk.json is not valid JSON (${p})`, {
      cause: err,
    });
  }
  const rows = Array.isArray(data)
    ? data
    : Array.isArray(data?.chapters)
      ? data.chapters
      : null;
  if (!rows || rows.length === 0) {
    throw new Error(
      `source-crosswalk.json yielded no chapter rows (${p}) — expected an object with a ` +
        "`chapters` array, or a bare array. Refusing to render a book that silently drops its " +
        "Source Crosswalk page and every per-chapter provenance line.",
    );
  }
  return rows;
}

/**
 * Cut to at most `max` characters at a word boundary, ellipsis when cut.
 *
 * The cell — not the generator — is what decides how much text fits in a table
 * column, so the cut belongs here. The generator trims too, at a much larger
 * budget for other consumers; a hard `.slice(0, 140)` here re-cut that trimmed
 * text mid-word and printed "was struck by t" in every row of the Source
 * Crosswalk, 280 characters before the generator's own ellipsis could appear.
 */
export function trimToWord(text, max) {
  const s = String(text || "").trim();
  if (s.length <= max) return s;
  const cut = s.slice(0, max);
  const boundary = cut.lastIndexOf(" ");
  return (
    (boundary > max / 2 ? cut.slice(0, boundary) : cut).replace(
      /[ ,;:.]+$/,
      "",
    ) + "…"
  );
}

export function renderSourceCrosswalk(items) {
  if (!items.length) return "";
  const rows = items
    .map((item) => {
      const n = item.index ? String(item.index) : "";
      const range =
        item.arabic_source_page_range || item.source_page_range || "";
      // One code path for every row. This used to prefer `source_headings` when
      // the chapter had any, which gave exactly one row of eight a different
      // provenance AND a different formatter — the headings branch was joined
      // raw, so it carried no section number, no ellipsis, and no length bound
      // at all. That row looked wrong in three consecutive renders for three
      // different reasons, and a book with three long headings would have run
      // the column off the page. The column header promises "Source signal";
      // the excerpt is what that is.
      const heads = trimToWord(item.source_excerpt || "", 140);
      return (
        `<tr><td>${escapeHtml(n)}</td><td>${renderInline(item.title || "")}</td>` +
        `<td>${escapeHtml(range)}</td><td>${renderInline(heads || "")}</td></tr>`
      );
    })
    .join("");
  return (
    '<section class="crosswalk-page"><p class="toc-eyebrow">Source Crosswalk</p>' +
    "<h2>Source Crosswalk</h2>" +
    "<table><thead><tr><th>Ch.</th><th>Chapter</th><th>Arabic pages</th><th>Source signal</th></tr></thead>" +
    `<tbody>${rows}</tbody></table></section>`
  );
}

/** Minimal renderer matching markdown.ts behaviour for book.md (headings,
 *  paragraphs, blockquotes, and raw HTML blocks like <figure class="book-diagram">). */
/**
 * Group each chapter's blocks under one wrapper so a named page can cover it.
 *
 * A running head that names the CHAPTER needs `@page` rules scoped per chapter,
 * and `page:` is inherited — so the whole chapter has to sit inside one element,
 * not just its opening section. Tagging the `.chapter-open` alone was tried and
 * cost six pages: the body after it reverts to the default page, and a named-page
 * CHANGE forces a break, so every chapter opening was stranded on a page of its
 * own.
 *
 * Done as a post-pass over the finished block list rather than inside the line
 * loop, so no per-line branch changes and the blocks themselves are untouched.
 * Anything before the first chapter opening (there is nothing today) stays
 * outside, unwrapped.
 *
 * OPT-IN, and only the PDF asks for it. `composer.ts` renders chapter by chapter
 * for the on-screen Composer, and a test pins those two paths to byte equality —
 * the guarantee that the Composer shows what the PDF shows. Wrapping unavoidably
 * breaks that at a seam: rendering one chapter in isolation must close its
 * wrapper at the end of its own chunk, while the whole-book render keeps a
 * trailing unnumbered heading inside the chapter it belongs to. Same blocks, same
 * order, different close point. Since only the print path needs the named pages,
 * the print path is the only one that wraps.
 */
export function wrapChapters(blocks) {
  const isOpen = (b) => b.startsWith('<section class="chapter-open');
  if (!blocks.some(isOpen)) return blocks;
  const out = [];
  let current = null;
  let n = 0;
  const flush = () => {
    if (!current) return;
    out.push(
      `<section class="chapter ch-page-${n}">`,
      ...current,
      "</section>",
    );
    current = null;
  };
  for (const block of blocks) {
    if (isOpen(block)) {
      flush();
      // The chapter's OWN number, carried on the block by the heading branch —
      // not a counter over this call. Rendering one chapter in isolation (the
      // per-chapter path, which exists and is tested) would otherwise label every
      // chapter `ch-page-1` and give it the wrong running head.
      n = Number(block.match(/ data-ch="(\d+)"/)?.[1] ?? 0);
      current = [block];
      continue;
    }
    if (current) current.push(block);
    else out.push(block);
  }
  flush();
  return out;
}

export function renderMd(md, crosswalkByIndex = new Map(), opts = {}) {
  // selfStudy (opt-in): the render-time self-study layer. When false (default)
  // every branch below is skipped, so the reading-edition render is byte-for-byte
  // unchanged. When true it additionally parses markdown bullet lists into <ul>
  // and turns the source-grounded editorial fences (produced by 0book-augment,
  // <!-- editorial:begin -->…<!-- editorial:end -->) into distinctly-styled
  // Contextual-Note / Study-summary asides instead of plain blockquotes.
  const selfStudy = opts.selfStudy === true;
  // quranicRuns (opt-in): the Set from readQuranicRuns(). Runs it contains are
  // marked `is-quranic`, which switches the Arabic FACE to the Uthmanic script;
  // everything else stays in Scheherazade New. Omitted (the default) means no run
  // is marked, so a caller that does not pass it renders exactly as before.
  //
  // The class name is deliberate: `blockquote.quran` has ALWAYS meant "this block
  // contains Arabic", not "this is scripture" (see the emit below — it fires on
  // ARABIC_RE). Nothing in the markup distinguished a verse from a hadith until
  // now, which is why the face could not be split without this.
  const quranicRuns = opts.quranicRuns instanceof Set ? opts.quranicRuns : null;
  const arClass = (text) =>
    quranicRuns && quranicRuns.has(String(text).trim())
      ? "ar is-quranic"
      : "ar";
  // sawH2 (opt-in): seed the "have we already opened a chapter?" state. Whole-book
  // callers (buildBookHtml) leave it false, so their output is byte-for-byte
  // unchanged. A caller rendering ONE chapter in isolation (the Book Composer's
  // read mode) passes true for every chapter after the first, so an unnumbered
  // later heading renders as an in-flow section heading rather than being
  // mistaken for the preface. sawH2 is the ONLY state renderMd carries ACROSS a
  // "## " boundary — every other accumulator (para/quote/list/aside) is flushed
  // by the heading branch — which is exactly why seeding it is sufficient to make
  // per-chapter rendering identical to the whole-book render of that chapter.
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let para = [];
  let quote = [];
  let list = [];
  let listKind = null; // 'ol' | 'ul'
  let inHtmlBlock = false;
  let chapterJustOpened = false;
  let sawH2 = opts.sawH2 === true;
  // Self-study editorial-aside capture state.
  let aside = null; // { kind: 'note' | 'summary', body: string[] }

  const ASIDE_META = {
    note: { cls: "study-note", label: "Contextual note" },
    summary: { cls: "study-summary", label: "Study summary" },
  };
  const flushList = () => {
    if (!list.length) {
      listKind = null;
      return;
    }
    // `value` carries the ordinal the SOURCE states, exactly as markdown.ts
    // does, so the printed page cannot renumber a list that starts at 3 — the
    // faked numbering REQ-015 forbids. Bulleted items never get it.
    if (listKind === "ol") {
      out.push(
        `<ol class="book-list">${list
          .map(
            (it) =>
              `<li${it.value === undefined ? "" : ` value="${it.value}"`}>${renderInline(it.text)}</li>`,
          )
          .join("")}</ol>`,
      );
    } else {
      out.push(
        `<ul class="study-list">${list.map((it) => `<li>${renderInline(it.text)}</li>`).join("")}</ul>`,
      );
    }
    list = [];
    listKind = null;
  };
  const flushAside = () => {
    if (!aside) return;
    const meta = ASIDE_META[aside.kind];
    const paras = [];
    let cur = [];
    for (const l of aside.body) {
      if (l.trim() === "") {
        if (cur.length) {
          paras.push(cur.join(" "));
          cur = [];
        }
      } else cur.push(l);
    }
    if (cur.length) paras.push(cur.join(" "));
    const inner =
      paras.map((p) => `<p>${renderInline(p)}</p>`).join("") || "<p></p>";
    out.push(
      `<aside class="${meta.cls}"><p class="study-aside-label">${meta.label}</p>${inner}</aside>`,
    );
    aside = null;
  };

  const flushPara = () => {
    if (!para.length) return;
    const text = para.join(" ");
    const names = [];
    if (chapterJustOpened) names.push("ch-first");
    if (isArabicOnlyParagraph(text)) names.push("ar-block");
    chapterJustOpened = false;
    const cls = names.length ? ` class="${names.join(" ")}"` : "";
    out.push(`<p${cls}>${renderInline(text)}</p>`);
    para = [];
  };
  const flushQuote = () => {
    if (!quote.length) return;
    const paras = [];
    let cur = [];
    for (const l of quote) {
      if (l.trim() === "") {
        if (cur.length) {
          paras.push(cur.join(" "));
          cur = [];
        }
      } else cur.push(l);
    }
    if (cur.length) paras.push(cur.join(" "));
    const hasArabic = paras.some((p) => ARABIC_RE.test(p));
    if (hasArabic) {
      // Mushaf treatment: Arabic lines RTL + Amiri, translations centered below.
      const inner = [];
      paras.forEach((p, i) => {
        if (ARABIC_RE.test(p)) {
          // Strip a stray trailing ASCII period — Latin punctuation has no
          // place at the end of an Arabic line (bidi renders it mid-air).
          const cleaned = p.trim().replace(/\.\s*$/, "");
          inner.push(
            `<p class="${arClass(cleaned)}" dir="rtl" lang="ar">${renderInline(cleaned)}</p>`,
          );
          if (i < paras.length - 1) inner.push('<hr class="quran-divider">');
        } else {
          inner.push(`<p class="tr">${renderInline(p)}</p>`);
        }
      });
      out.push(`<blockquote class="quran">${inner.join("")}</blockquote>`);
    } else {
      out.push(
        `<blockquote>${paras.map((p) => `<p>${renderInline(p)}</p>`).join("") || "<p></p>"}</blockquote>`,
      );
    }
    quote = [];
  };

  // Indexed rather than for-of: the blank-line handler below needs to look
  // AHEAD to decide whether an open list continues past it. `ln` (not `i`) to
  // avoid shadowing anything in this long body.
  for (let ln = 0; ln < lines.length; ln += 1) {
    const line = lines[ln];
    // Raw HTML block pass-through: <figure class="book-diagram">...</figure>
    if (inHtmlBlock) {
      out.push(line);
      if (line.trimEnd().toLowerCase() === "</figure>") inHtmlBlock = false;
      continue;
    }
    // Self-study: capture the source-grounded editorial fences (0book-augment)
    // and study-summary fences into distinctly-styled asides. Outside self-study
    // these fall through untouched (comment lines are invisible; the > lines
    // render as an ordinary blockquote — the reading edition is unchanged).
    if (selfStudy) {
      if (aside) {
        if (/<!--\s*(?:editorial|study-summary):end\s*-->/.test(line)) {
          flushAside();
          continue;
        }
        const body = line.replace(/^>\s?/, "");
        if (!/^\*\*.+\*\*\s*$/.test(body.trim())) aside.body.push(body); // drop the bold label line
        continue;
      }
      const beginSummary = /<!--\s*study-summary:begin\s*-->/.test(line);
      const beginNote = /<!--\s*editorial:begin\s*-->/.test(line);
      if (beginSummary || beginNote) {
        flushPara();
        flushQuote();
        flushList();
        aside = { kind: beginSummary ? "summary" : "note", body: [] };
        continue;
      }
    }
    // The pipeline's fences are machine markers, never visible text. Self-study
    // consumes editorial/study-summary into styled asides (above); every other
    // case skips the marker line so it never renders as escaped <!-- --> text —
    // the fenced content's own lines render as ordinary prose.
    //
    // Driven off MACHINE_FENCE_KINDS rather than an inline alternation. The
    // alternation listed three of the four kinds and missed `edition-intro`
    // (added to the contract 2026-07-21), so on a book whose front matter opens
    // the first chapter the Composer showed `<!-- edition-intro:begin -->` as
    // the chapter's first line, with the `<!` taking the drop-cap. One list, so
    // the next kind added cannot be missed here; the list is pinned against
    // FENCE_KINDS by book-html.test.mjs.
    if (MACHINE_FENCE_RE.test(line.trim())) {
      continue;
    }
    if (line.trimStart().toLowerCase().startsWith("<figure")) {
      flushPara();
      flushQuote();
      flushList();
      out.push(line);
      inHtmlBlock = !line.includes("</figure>");
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) {
      flushPara();
      flushQuote();
      flushList();
      const level = h[1].length;
      const text = h[2].trim();
      if (level === 2) {
        // Book-style chapter opening. "N. Title" → CHAPTER N eyebrow + bare
        // title; the unnumbered first h2 is the preface. Later unnumbered H2s
        // are internal source headings and must stay in the prose flow.
        const isFirstH2 = !sawH2;
        const numbered = text.match(/^(\d+)\.\s+(.+)$/);
        let eyebrow;
        let title;
        if (numbered) {
          const n = parseInt(numbered[1], 10);
          eyebrow = `Chapter ${NUMBER_WORDS[n] || numbered[1]}`;
          title = numbered[2];
        } else {
          eyebrow = sawH2 ? "" : "Preface";
          title = text;
        }
        if (numbered || isFirstH2) {
          const sourceRange = numbered
            ? crosswalkByIndex.get(parseInt(numbered[1], 10))
                ?.arabic_source_page_range ||
              crosswalkByIndex.get(parseInt(numbered[1], 10))
                ?.source_page_range ||
              ""
            : "";
          sawH2 = true;
          chapterJustOpened = true;
          out.push(
            `<section class="chapter-open${isFirstH2 ? " first-chapter-open" : ""}"` +
              ` data-ch="${numbered ? parseInt(numbered[1], 10) : 0}">` +
              (eyebrow
                ? `<p class="ch-eyebrow">${escapeHtml(eyebrow)}</p>`
                : "") +
              `<h2>${renderInline(title)}</h2>` +
              (sourceRange
                ? `<p class="ch-source">Arabic source ${escapeHtml(sourceRange)}</p>`
                : "") +
              '<hr class="ch-rule">' +
              "</section>",
          );
        } else {
          out.push(`<h3 class="section-heading">${renderInline(text)}</h3>`);
        }
      } else {
        out.push(`<h${level}>${renderInline(text)}</h${level}>`);
      }
      continue;
    }
    // Ordered lists, in EVERY render. This one is not opt-in: `renderMd` builds
    // the printed edition, and with no ordered-list parser a real enumeration
    // came out as one run-together paragraph with "1." "2." "3." as literal text
    // — faked numbering in the publication deliverable, and disagreeing with the
    // reader, which renders the same source as a real <ol>.
    const oli = line.match(OL_ITEM_RE);
    if (oli) {
      flushPara();
      flushQuote();
      if (listKind !== "ol") {
        flushList();
        listKind = "ol";
      }
      list.push({ text: oli[2], value: Number(oli[1]) });
      continue;
    }
    // Self-study: markdown bullet lists → <ul>. Still opt-in — no book.md in the
    // corpus uses '- ' bullets, so turning them on for print would be a change
    // with nothing to render and no way to see it was right.
    if (selfStudy) {
      const li = line.match(UL_ITEM_RE);
      if (li) {
        flushPara();
        flushQuote();
        if (listKind !== "ul") {
          flushList();
          listKind = "ul";
        }
        list.push({ text: li[1] });
        continue;
      }
    }
    // Any other CONTENT ends the list — but a blank line is not content, and
    // flushing here would split a loose list before the blank-line handler
    // below ever got its lookahead.
    if (list.length && line.trim() !== "") flushList();
    // `(?:>\s?)+`, not `>` — flatten a nested marker rather than print it. The
    // markers are space-separated (`> > text`), so a `>+` character class only
    // eats the first. Mirrors src/lib/reader/markdown.ts; see the note there for
    // the failure this fixes (an augment double-prefix printed as a literal ">").
    const q = line.match(/^(?:>\s?)+(.*)$/);
    if (q) {
      flushPara();
      flushList();
      quote.push(q[1]);
      continue;
    }
    if (quote.length) flushQuote();
    if (line.trim() === "") {
      flushPara();
      if (listKind !== null && !listContinues(lines, ln + 1, listKind))
        flushList();
      continue;
    }
    para.push(line);
  }
  flushPara();
  flushQuote();
  flushList();
  flushAside();
  return (opts.wrapChapters ? wrapChapters(out) : out).join("\n");
}

export function themeRoot(css) {
  const m = css.match(/:root\s*\{([^}]*)\}/);
  return m ? m[1] : "";
}

/**
 * buildBookHtml(mdPath, { v2 }) — the single HTML-assembly entry point.
 *
 * Reads book.md (at mdPath) plus its sibling contract files (meta.yml,
 * citation-style.json, source-crosswalk.json, and — when v2 is true —
 * visual-layout.json + visuals/index.json) and returns every markup fragment
 * a caller needs to build a full document: cover, title page, TOC, source
 * crosswalk, and the chapter body (with v2 figure placement already applied).
 * Callers own their own document shell (doctype/head/print-CSS for the PDF
 * path, the Astro page shell + Paged.js for Preview) — this function only
 * ever returns body-level HTML fragments, never a full <html> document.
 */
export function buildBookHtml(mdPath, { v2 = false, selfStudy = false } = {}) {
  const md = readFileSync(mdPath, "utf-8");
  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch
    ? titleMatch[1].trim()
    : path.basename(mdPath, ".md");
  const body = md.replace(/^#\s+.+$\n?/m, "");
  const tocItems = extractToc(body);

  // Static-asset root: the book's content dir (parent of book/), so markdown
  // can reference e.g. <img src="slide-deck/_pages/page-02.png">.
  const assetRoot = path.resolve(path.dirname(mdPath), "..");
  const author = readAuthor(assetRoot);
  const crosswalk = readCrosswalk(assetRoot);
  const crosswalkByIndex = new Map(
    crosswalk.map((item) => [Number(item.index), item]),
  );
  const coverPath = path.join(path.dirname(mdPath), "cover.png");
  const hasCover = existsSync(coverPath);

  const coverHtml = hasCover
    ? `<section class="cover"><img src="/book/cover.png" alt="">` +
      `<div class="cover-panel"><h1>${escapeHtml(title)}</h1>` +
      (author ? `<p class="cover-author">${escapeHtml(author)}</p>` : "") +
      `</div></section>`
    : "";
  const titlePage =
    `<section class="title-page"><p class="eyebrow">Reading edition</p>` +
    `<h1>${escapeHtml(title)}</h1>` +
    (author ? `<p class="title-author">${escapeHtml(author)}</p>` : "") +
    `<hr class="title-rule">` +
    `<div class="disclaimer-panel">Generated using podcast-factory AI. Verify content; AI can make mistakes.</div>` +
    `</section>`;

  // v2: honor the human-curated visual-layout.json contract. Figures are placed
  // ONLY from the contract (book.md stays diagram-free). Absent/partial contract
  // is tolerated — applyLayout no-ops when there are no placements or assets.
  let bodyHtml = renderMd(body, crosswalkByIndex, {
    selfStudy,
    wrapChapters: true,
    // Scripture gets the Uthmanic face, the rest Scheherazade New. Sourced from
    // the Arabic audit's own provenance rather than re-derived here.
    quranicRuns: readQuranicRuns(assetRoot),
  });
  // Per-selection text colours (_system/text-colour.json). Applied per CHAPTER
  // rather than to the whole body: a stored quote is matched by its text, and
  // `findPassage` takes the first occurrence, so a short phrase recorded in
  // chapter 2 would otherwise be free to colour an identical phrase in chapter 9.
  // The wrapper `wrapChapters` already emits carries the chapter's own number, so
  // splitting on it is enough to keep each chapter's colours inside it.
  bodyHtml = applyColoursPerChapter(bodyHtml, assetRoot, tocItems);

  const bodyClasses = [];
  if (selfStudy) bodyClasses.push("book-self-study");
  if (v2) {
    bodyClasses.push("book-v2");
    const { placements, warnings } = loadLayout(assetRoot);
    if (warnings.length)
      warnings.forEach((w) => console.error(`  [visual-layout] ${w}`));
    if (placements.length) {
      bodyHtml = applyLayout(bodyHtml, placements, readVisualAssets(assetRoot));
    }
  }
  // Citation & quote family (book/citation-style.json) — global per-book choice
  // made in the Composer's Citations tab. Applies regardless of the v2 flag;
  // absent file or unknown value falls back to the unstyled default. Adds a
  // body.style-<family> hook that book-print.css reskins passage blocks with,
  // and a body.tr-<font> hook that sets --q-tr-face (quote-typography.css) for
  // the English rendering under an Arabic quotation.
  const bookDir = path.dirname(mdPath);
  const family = readCitationFamily(bookDir);
  if (family) bodyClasses.push(`style-${family}`);
  const trFont = readTranslationFont(bookDir);
  if (trFont) bodyClasses.push(`tr-${trFont}`);
  // ...and a body.ar-<font> hook for the NON-Qur'anic Arabic face. Scripture is
  // unaffected: .is-quranic re-declares --q-ar-face on the run itself, and a
  // declaration on the element beats one inherited from <body>.
  const arFont = readArabicFont(bookDir);
  if (arFont) bodyClasses.push(`ar-${arFont}`);
  // ...and body.ars-<size> / body.ari-<ink>, which move --q-ar-size,
  // --q-ar-inline-size and --q-maroon. Absent for the default value on purpose:
  // see readArabicSize.
  const arSize = readArabicSize(bookDir);
  if (arSize) bodyClasses.push(`ars-${arSize}`);
  const arInk = readArabicInk(bookDir);
  if (arInk) bodyClasses.push(`ari-${arInk}`);
  const bodyClass = bodyClasses.join(" ");

  return {
    title,
    author,
    // Chapter labels+titles for the per-chapter running heads. Same array the
    // Contents is built from, so the head can never name a chapter the Contents
    // does not list.
    chapters: tocItems,
    assetRoot,
    coverHtml,
    titlePage,
    tocHtml: renderToc(tocItems),
    crosswalkHtml: renderSourceCrosswalk(crosswalk),
    bodyHtml,
    bodyClass,
  };
}

/**
 * Apply each chapter's recorded text colours to its own slice of the body.
 *
 * The sidecar is keyed by `anchorKey` (the same key the Composer stores edits and
 * placements under); the rendered body is divided by `ch-page-N` wrappers. The
 * bridge between them is the Contents, which this renderer has already built from
 * the same headings — so the mapping is derived from one source rather than
 * recomputed from the HTML.
 *
 * Anything unmatched is left alone. A chapter with no colours, a colour whose
 * words have since been edited, a book with no sidecar at all: each renders
 * exactly as it did before this existed.
 */
function applyColoursPerChapter(bodyHtml, bookDir, tocItems) {
  const colours = readTextColours(bookDir);
  if (!Object.keys(colours).length) return bodyHtml;
  const keyByNumber = new Map();
  for (const item of tocItems || []) {
    const n = /^\d+$/.test(String(item.label || "")) ? Number(item.label) : 0;
    if (n) keyByNumber.set(n, anchorKey(`${n}. ${item.title || ""}`));
  }

  // Split on the OPENING wrapper only. A chapter contains a nested
  // `<section class="chapter-open">`, so pairing each opening tag with a
  // `</section>` closes on the wrong one: lazily at the chapter-open's own close
  // (which truncated every chapter to its title block and matched nothing),
  // greedily at the last close in the book. A chapter's text is simply
  // everything up to the next chapter's opening tag.
  const OPEN = /<section class="chapter ch-page-(\d+)">/g;
  const marks = [];
  let m;
  while ((m = OPEN.exec(bodyHtml))) {
    marks.push({ at: m.index, after: m.index + m[0].length, n: Number(m[1]) });
  }
  if (!marks.length) return bodyHtml;

  let out = "";
  let cursor = 0;
  marks.forEach((mark, i) => {
    const endAt = i + 1 < marks.length ? marks[i + 1].at : bodyHtml.length;
    out += bodyHtml.slice(cursor, mark.after);
    const inner = bodyHtml.slice(mark.after, endAt);
    const spans = colours[keyByNumber.get(mark.n) ?? ""];
    out += spans?.length ? applyTextColours(inner, spans) : inner;
    cursor = endAt;
  });
  return out + bodyHtml.slice(cursor);
}
