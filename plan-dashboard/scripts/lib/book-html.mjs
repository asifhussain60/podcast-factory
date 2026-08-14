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
import { readTextAlign, flattenAlign } from "./text-align.mjs";
import {
  readQuoteKind,
  flattenQuoteKind,
  quoteKindKey,
  QUOTE_KIND_LABEL,
  speakerFor,
} from "./quote-kind.mjs";
import {
  readQuoteGroups,
  flattenQuoteGroups,
  collectGroupRuns,
  groupKey,
} from "./quote-groups.mjs";
import { readImageLayout, flattenImageLayout } from "./image-layout.mjs";
import { paraFingerprint } from "./para-blocks.mjs";
import { loadLayout, applyLayout } from "../visual-layout.mjs";
// Book-level display settings (author, citation family, translation/Arabic
// face/size/ink) — split out (DR-005, 2026-08-14) as a pure settings-reader
// cluster with no markdown-parsing dependency. Re-exported below so every
// existing import path into book-html.mjs is unchanged.
import {
  asciiFold,
  readAuthor,
  CITATION_FAMILIES,
  TRANSLATION_FONTS,
  ARABIC_FONTS,
  ARABIC_SIZES,
  DEFAULT_ARABIC_SIZE,
  ARABIC_INKS,
  DEFAULT_ARABIC_INK,
  readCitationFamily,
  readTranslationFont,
  readArabicFont,
  readArabicSize,
  readArabicInk,
} from "./book-style-settings.mjs";
export {
  asciiFold,
  readAuthor,
  CITATION_FAMILIES,
  TRANSLATION_FONTS,
  ARABIC_FONTS,
  ARABIC_SIZES,
  DEFAULT_ARABIC_SIZE,
  ARABIC_INKS,
  DEFAULT_ARABIC_INK,
  readCitationFamily,
  readTranslationFont,
  readArabicFont,
  readArabicSize,
  readArabicInk,
};

const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
const ARABIC_INLINE_RE = /[﴿«]?[\s؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+[﴾»]?/g;
// The same class, global, for COUNTING rather than testing. Kept beside its source
// so the two can never describe different alphabets; `ARABIC_RE` must stay non-global
// because a global regex carries `lastIndex` between `.test()` calls.
const ARABIC_COUNT_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/g;
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

/**
 * Is this line of a quotation block ARABIC, or is it the translation beside it?
 *
 * The rule is which script the line is MOSTLY in. Until 2026-08-09 it was
 * `ARABIC_RE.test(p)` — true on a single Arabic character — so an English
 * translation carrying the `(ع)` honorific after Ali's name was emitted as
 * `<p class="ar" dir="rtl" lang="ar">` and set in the Arabic face, right to left,
 * with its quotation marks thrown to the wrong ends of the line. The worst cases
 * were whole editorial notes: 626 Latin characters flipped by three Arabic ones
 * naming a root like `ح-س-ن`.
 *
 * NOT `isArabicOnlyParagraph`, which needs more than twenty Arabic characters and
 * would demote a short quotation — `> بَاب` is three — to a translation. Inside a
 * quotation block the question is only which script wins.
 *
 * MIRROR, pinned by `arabic-quote-line.fixtures.json`:
 *   - here (the PDF and the Composer's Read view),
 *   - `isArabicQuoteLine` in src/lib/reader/markdown.ts (the reader; it is
 *     client-bundled and cannot import this Node-only module),
 *   - `english_set_right_to_left` in scripts/podcast/tests/test_book_articulation_defects.py.
 * Neither renderer was pinned to the other before this: a one-sided change would
 * have given the printed page and the on-screen reader different directions for the
 * same paragraph, which is the one divergence no gate here could see.
 */
export function isArabicQuoteLine(s) {
  const arabic = (s.match(ARABIC_COUNT_RE) || []).length;
  if (arabic === 0) return false;
  const latin = (s.match(/[A-Za-z]/g) || []).length;
  return arabic > latin;
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
      // Label-less, for the same reason the eyebrow is: the section's own title
      // is the label, and "Preface — Introduction to the Book" reads as two names
      // for one thing.
      items.push({ label: "", title: raw });
    }
  }
  return items;
}

export function renderToc(items) {
  if (!items.length) return "";
  const rows = items
    .map((item) => {
      // The label span is ALWAYS emitted, even empty, for a label-less entry
      // (the unnumbered "Introduction to the Book" row). `.toc-page li` is a
      // two-column CSS grid (`3.2rem 1fr`); a `<li>` with only one child places
      // that lone child in the FIRST (3.2rem) track, not the 1fr title track —
      // there is nothing to push it into the second column. The title then
      // wraps three words deep inside a number-column's width, which both looks
      // wrong on its own page and, by costing two extra list-item lines, was
      // exactly enough to overflow the Contents page: the last chapter row
      // spilled onto its own near-blank page, and the Source Crosswalk that
      // follows it lost its whole page in turn (BR-BLANK-PAGE on pages 4-5).
      const label = `<span class="toc-label">${item.label ? escapeHtml(item.label) : ""}</span>`;
      return `<li>${label}<span class="toc-title">${renderInline(item.title)}</span></li>`;
    })
    .join("");
  return `<section class="toc-page"><p class="toc-eyebrow">Contents</p><h2>Contents</h2><ol>${rows}</ol></section>`;
}
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
/** The same marker, with its kind and side captured — so a renderer can know
 *  WHICH span it is inside rather than merely that a marker went past. */
const MACHINE_FENCE_PARTS = new RegExp(
  `^<!--\\s*(${MACHINE_FENCE_KINDS.join("|")}):(begin|end)\\s*-->$`,
);

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
/** Each mushaf-resolved run's printable citation — `"Al-Ahzab: 6"` — by the run's
 *  exact text, from the same audit file and the same `runs` array readQuranicRuns
 *  walks. The label is FORMATTED IN PYTHON (`_mushaf.mushaf_reference_label`),
 *  where the surah names already live, so no JavaScript copy of that table has to
 *  be kept in step for the sake of a header line.
 *
 *  A Qur'an card has no state without one: the reference always shows (Asif,
 *  2026-08-09). An audit written before this field existed yields an empty map
 *  and the band falls back to its ornament alone — which is why
 *  `provenance_drift` reports a scripture run with no reference as drift, so
 *  `--refresh-provenance` fills it. */
export function readQuranicRefs(bookContentDir) {
  const p = path.join(bookContentDir, "_system", "book-arabic-audit.json");
  const map = {};
  if (!existsSync(p)) return map;
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    for (const ch of data?.chapters || []) {
      for (const run of ch?.runs || []) {
        if (
          run?.resolution === "canonical-mushaf" &&
          run?.text &&
          run?.reference
        )
          map[String(run.text).trim()] = String(run.reference);
      }
    }
  } catch {
    /* tolerant: no reference just means the band shows its mark alone */
  }
  return map;
}

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
  // alignByPara (opt-in): fingerprint -> "center" | "right", from
  // _system/text-align.json. Omitted (the default) leaves every paragraph
  // exactly as it rendered before this existed.
  const alignByPara = opts.alignByPara ?? null;
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
  // quoteKinds (opt-in): first-line -> "hadith" | "poem" | "quote", from
  // _system/quote-kind.json. It answers the question `quranicRuns` cannot: a
  // block holding Arabic the mushaf does not carry is a hadith, a saying or a
  // line of verse, and only a person knows which. A block the map does not
  // mention takes the default card, so a caller that never passes this renders
  // exactly as it did before the map existed.
  //
  // Scripture always wins: a block whose Arabic the audit resolved is a Qur'an
  // card whatever the map says, because the mushaf is not a matter of opinion.
  const quoteKinds = opts.quoteKinds ?? null;
  // quoteGroups (opt-in): { quote: {firstLine: groupId}, gloss: {fingerprint:
  // groupId} }, from _system/quote-groups.json. Omitted (the default, and
  // every book today) means blockMeta below stays empty and the merge pass
  // at the end is a no-op — output is byte-for-byte unchanged. See
  // quote-groups.mjs's header for the whole mechanism.
  const quoteGroups = opts.quoteGroups ?? null;
  // Parallel to `out`, sparse: blockMeta[i] is set only for a block whose key
  // is found in quoteGroups, at the SAME index `out[i]` was just pushed to.
  // Never touches what gets pushed to `out` itself — the merge pass at the
  // end reads this to decide what to collapse, so every existing push site
  // that ISN'T a group member needs no change at all.
  const blockMeta = [];
  // imageLayout (opt-in): src -> {height_px?, align?}, from
  // _system/image-layout.json. Omitted (the default, and every book before
  // this existed) means no image carries a height/align override, which is
  // exactly what rendered before this option existed.
  const imageLayout = opts.imageLayout ?? null;
  // quranicRefs (opt-in): run text -> "Al-Ahzab: 6". Only the Qur'an card names
  // itself from the text; the other three take a fixed word, because "which
  // hadith" is a question the audit cannot answer and a person has not been
  // asked.
  const quranicRefs = opts.quranicRefs ?? null;
  // bands (opt-in, default ON): the header strip. The Composer's EDIT seed turns
  // it OFF, and that is load-bearing rather than cosmetic — TipTap would hold the
  // band as content and `docToMarkdown` writes a blockquote from its CONTENT, so
  // a band inside the editor could be serialised into book.md on the next
  // autosave. Read mode and the PDF, which never round-trip, get it.
  const bands = opts.bands !== false;
  const band = (kind, paras) => {
    if (!bands || !kind) return "";
    let label = QUOTE_KIND_LABEL[kind] ?? "";
    if (kind === "quran") {
      const line = paras.find((x) => isArabicQuoteLine(x));
      label = (line && quranicRefs?.[line.trim().replace(/\.\s*$/, "")]) || "";
    }
    const by = speakerFor(quoteKinds, paras, kind);
    return (
      `<span class="q-band q-band--${kind}">` +
      '<span class="q-orn" aria-hidden="true"></span>' +
      (label ? `<span class="q-kind">${escapeHtml(label)}</span>` : "") +
      (by ? `<span class="q-by" dir="auto">${escapeHtml(by)}</span>` : "") +
      "</span>"
    );
  };
  // A CARD NEEDS AN ARABIC LINE, not merely Arabic somewhere: a blockquote whose
  // English glosses one term has no quotation to draw, and the default card
  // would put a tinted plate around an ordinary note. An aside is never a card.
  // `lines` are the block's RAW lines and `paras` are those lines joined. The
  // declaration is filed under the first LINE, so the two cannot be conflated —
  // see quoteKindKey.
  const kindClass = (lines, paras, hasScripture, isAside) => {
    if (isAside) return "";
    if (hasScripture) return " k-quran";
    const kind = quoteKinds?.[quoteKindKey(lines)]?.kind;
    if (kind) return ` k-${kind}`;
    return paras.some(isArabicQuoteLine) ? " k-quote" : "";
  };
  const arClass = (text) =>
    quranicRuns && quranicRuns.has(String(text).trim())
      ? "ar is-quranic"
      : "ar";
  // A declared poem's Arabic, set as the two-column grid printed diwans use: one
  // bayt is a sadr on the right and an ajuz on the left, and the gutter running
  // straight down the block is what makes the shape read as verse to someone who
  // cannot read the words. Mirrors `verseGrid` in src/lib/reader/markdown.ts.
  //
  // ` * ` is the hemistich separator, and splitting on it is safe HERE and
  // nowhere else: the same character separates a Qur'anic verse from its own
  // reference five times in ayyuhal-walad (`… * الحجرات: ٥`), so the rule runs
  // only inside a block a person marked as verse.
  // IT TAKES THE RAW LINES, not the paragraphs, and that is what lets it work at
  // all: one bayt is one LINE, and every other quotation here joins its lines
  // into paragraphs first. Three abyat joined into `A * B C * D E * F` cannot be
  // divided back into hemistichs by any rule — the boundaries are gone.
  const verseGrid = (lines) => {
    const parts = [];
    let cells = [];
    let prose = [];
    const flushCells = () => {
      if (cells.length === 0) return;
      parts.push(`<div class="q-verse">${cells.join("")}</div>`);
      cells = [];
    };
    const flushProse = () => {
      const text = prose.join(" ").trim();
      prose = [];
      if (text) parts.push(`<p class="tr">${renderInline(text)}</p>`);
    };
    for (const raw of lines) {
      const line = raw.trim();
      if (!line) {
        flushProse();
        continue;
      }
      if (isArabicQuoteLine(line)) {
        flushProse();
        const halves = line.replace(/\.\s*$/, "").split(/\s+\*\s+/);
        // A line with no second hemistich spans both columns — alone in one it
        // reads as a missing line rather than a whole one.
        const solo = halves.length < 2 ? " bayt-solo" : "";
        for (const half of halves) {
          cells.push(
            `<p class="ar${solo}" dir="rtl" lang="ar">${renderInline(half)}</p>`,
          );
        }
      } else {
        flushCells();
        prose.push(line);
      }
    }
    flushCells();
    flushProse();
    return parts.join("");
  };
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
    // Human-chosen alignment. `text` is the block with its line breaks joined by
    // spaces, and `paraFingerprint` collapses whitespace before hashing — so this
    // is the same name the raw block carries in _system/, and the same one the
    // Composer stored it under.
    if (alignByPara) {
      const align = alignByPara[paraFingerprint(text)];
      if (align) names.push(`align-${align}`);
    }
    chapterJustOpened = false;
    const cls = names.length ? ` class="${names.join(" ")}"` : "";
    out.push(`<p${cls}>${renderInline(text)}</p>`);
    // A gloss member for the merge pass — the tight translation of an
    // adjacent declared quote fragment, never the author's own commentary,
    // which is why this only fires when a person explicitly tagged THIS
    // paragraph's own fingerprint, not by proximity or shape.
    const glossGroup = quoteGroups?.gloss?.[groupKey(para)];
    if (glossGroup)
      blockMeta[out.length - 1] = { type: "gloss", groupId: glossGroup, text };
    para = [];
  };
  // The pipeline fence currently open, so a blockquote written INSIDE an
  // editorial/bridge/study-summary span can say so. Tracked independently of
  // `selfStudy` (2026-08-05): the reading edition renders these as blockquotes
  // whether or not the self-study layer is on, and an apparatus note that draws
  // exactly like the book's own words is the one thing it must not do. Only a
  // CLASS is added — the markup is otherwise byte-identical, so any surface that
  // does not style `.aside` renders exactly as before.
  let openFence = null;
  const ASIDE_KINDS = new Set(["editorial", "study-summary", "bridge"]);
  const asideCls = () =>
    openFence && ASIDE_KINDS.has(openFence) ? ` aside ${openFence}` : "";

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
    // The BLOCK decision stays "contains Arabic": it chooses the mushaf CARD, and a
    // quotation whose one line runs Arabic straight into its English gloss is still a
    // scripture quotation. Only the per-line direction below weighs proportion — that
    // is where the defect was.
    const hasArabic = paras.some((p) => ARABIC_RE.test(p));
    if (hasArabic) {
      const scripture = paras.some(
        (p) =>
          isArabicQuoteLine(p) &&
          arClass(p.trim().replace(/\.\s*$/, "")).includes("is-quranic"),
      );
      // The kind is decided BEFORE the markup because verse is SET differently,
      // not merely coloured differently: a poem's lines are grid cells and every
      // other kind's are paragraphs. Asked once rather than the three times this
      // line used to ask it.
      const kind = kindClass(quote, paras, scripture, !!asideCls())
        .trim()
        .replace(/^k-/, "");
      // Mushaf treatment: Arabic lines RTL + Amiri, translations centered below.
      const inner = [];
      if (kind === "poem") {
        inner.push(verseGrid(quote));
      } else {
        paras.forEach((p, i) => {
          if (isArabicQuoteLine(p)) {
            // Strip a stray trailing ASCII period — Latin punctuation has no
            // place at the end of an Arabic line (bidi renders it mid-air).
            const cleaned = p.trim().replace(/\.\s*$/, "");
            inner.push(
              `<p class="${arClass(cleaned)}" dir="rtl" lang="ar">${renderInline(cleaned)}</p>`,
            );
            // Between two Arabic RUNS, which is what the divider is for — never
            // between a run and its English rendering. "Not the last paragraph"
            // used to stand in for that, and it was true while a card's rendering
            // lived outside it as body prose. Folding the rendering back in
            // (`translation-outside-card`, 2026-08-09) made the two differ, and
            // the divider landed between the verse and its translation on every
            // repaired card. It was invisible — a legacy `.quran` descendant rule
            // hides it on both surfaces that see it — but invisible-by-accident is
            // not the same as absent, and the approved specimen has none there.
            if (isArabicQuoteLine(paras[i + 1] ?? ""))
              inner.push('<hr class="quran-divider">');
          } else {
            inner.push(`<p class="tr">${renderInline(p)}</p>`);
          }
        });
      }
      out.push(
        `<blockquote class="quran${kind ? ` k-${kind}` : ""}${asideCls()}">${band(kind, quote)}${inner.join("")}</blockquote>`,
      );
      const quoteGroupId = quoteGroups?.quote?.[quoteKindKey(quote)];
      if (quoteGroupId && kind && kind !== "quran")
        blockMeta[out.length - 1] = {
          type: "quote",
          groupId: quoteGroupId,
          kind,
          bandHtml: band(kind, quote),
          innerHtml: inner.join(""),
        };
    } else {
      // No Arabic, so no `quran` class — that word has always meant "this block
      // contains Arabic". A kind still applies when a person declared one: verse
      // reaches the page in English alone (Imam al-Shafii's lines in Spiritual
      // Ethos), and it is a poem whichever language it arrives in. An undeclared
      // English blockquote gets nothing, exactly as before.
      const dec = asideCls() ? null : quoteKinds?.[quoteKindKey(quote)];
      const cls = `${dec ? `k-${dec.kind}` : ""}${asideCls()}`.trim();
      const innerHtml =
        paras.map((p) => `<p>${renderInline(p)}</p>`).join("") || "<p></p>";
      out.push(
        `<blockquote${cls ? ` class="${cls}"` : ""}>${band(dec?.kind, quote)}${innerHtml}</blockquote>`,
      );
      const quoteGroupId = quoteGroups?.quote?.[quoteKindKey(quote)];
      if (quoteGroupId && dec?.kind)
        blockMeta[out.length - 1] = {
          type: "quote",
          groupId: quoteGroupId,
          kind: dec.kind,
          bandHtml: band(dec.kind, quote),
          innerHtml,
        };
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
      // Flush BEFORE clearing on `end`: the fenced blockquote is still sitting
      // in the buffer at that moment, and it is the marker that says what kind
      // of aside it is. Clear first and the class is lost on the very block it
      // describes.
      const parts = line.trim().match(MACHINE_FENCE_PARTS);
      if (parts) {
        flushPara();
        flushQuote();
        flushList();
        openFence = parts[2] === "begin" ? parts[1] : null;
      }
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
    // A markdown image alone on its line — `![alt](src)`.
    //
    // NOT opt-in, for the reason the ordered-list branch above is not: this
    // builds the printed edition and the Book Composer's read mode, and with no
    // image rule at all a Sessions chapter printed the literal characters
    // `![](images/213/….jpg)` where a diagram belongs. Sixty-three of them in
    // Surah Al-Fateha, two in Love Of The Prophet — every illustration in the
    // collection, on the one surface Asif reviews a book on.
    //
    // A FIGURE rather than an inline `<img>`, and only when the line is nothing
    // but the image: these are plates the prose points at, and an `![…]`
    // mid-sentence would open a block element inside a `<p>`, which the browser
    // closes for you somewhere you did not choose. Mirrors the identical rule in
    // src/lib/reader/markdown.ts and is pinned against it by a parity fixture —
    // the printed page and the reader must not disagree about what a figure is.
    //
    // The src is written through UNTOUCHED. Relative to `book/` is correct here:
    // that is the directory the PDF is built in. The Composer serves the same
    // HTML over HTTP, where it is not, and rewrites it there — the same split
    // the listener already makes, and for the same reason.
    const mdImage = /^!\[([^\]]*)\]\(([^)\s]+)\)$/.exec(line.trim());
    if (mdImage) {
      flushPara();
      flushQuote();
      flushList();
      const src = mdImage[2].replace(/&/g, "&amp;").replace(/"/g, "&quot;");
      const alt = mdImage[1].replace(/&/g, "&amp;").replace(/"/g, "&quot;");
      const layout = imageLayout?.[mdImage[2]];
      const figAttrs = layout?.align ? ` data-align="${layout.align}"` : "";
      const imgStyle = layout?.height_px
        ? ` style="--img-h:${layout.height_px}px"`
        : "";
      out.push(
        `<figure class="md-figure"${figAttrs}><img src="${src}" alt="${alt}" loading="lazy"${imgStyle} />` +
          (mdImage[1]
            ? `<figcaption>${renderInline(mdImage[1])}</figcaption>`
            : "") +
          `</figure>`,
      );
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
          // No eyebrow. A numbered chapter needs one because "The Pole and
          // Foundation of Religion" does not say it is chapter one; an unnumbered
          // front-matter section names itself. Since 2026-08-03 that section is
          // titled "Introduction to the Book", so the hardcoded label printed
          //     Preface
          //     Introduction to the Book
          // one line above the other — a stale word arguing with the heading
          // under it, on the reader's first page.
          eyebrow = "";
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
  // Collapse declared groups into one merged card each. blockMeta is empty
  // for every book with no quote-groups.json (the default), so this is a
  // no-op there — `merged` becomes `out` unchanged, same array contents.
  let merged = out;
  if (quoteGroups && blockMeta.some(Boolean)) {
    const blocksForRuns = out.map((_, i) =>
      blockMeta[i]
        ? {
            groupId: blockMeta[i].groupId,
            type: blockMeta[i].type,
            kind: blockMeta[i].kind,
          }
        : { groupId: null },
    );
    const runOf = collectGroupRuns(blocksForRuns);
    merged = [];
    let i = 0;
    while (i < out.length) {
      let j = i;
      while (j + 1 < out.length && runOf[j + 1] === runOf[i]) j++;
      if (j > i && blockMeta[i]) {
        // A genuine multi-member merge: one card, the first quote member's
        // band, every member's own inner content in document order.
        const members = [];
        for (let k = i; k <= j; k++) members.push(blockMeta[k]);
        const firstQuote = members.find((m) => m.type === "quote");
        const bandHtml = firstQuote?.bandHtml ?? "";
        const kind = firstQuote?.kind ?? "quote";
        const inner = members
          .map((m) =>
            m.type === "gloss"
              ? `<p class="tr">${renderInline(m.text)}</p>`
              : m.innerHtml,
          )
          .join("");
        merged.push(
          `<blockquote class="quran k-${kind} is-group">${bandHtml}${inner}</blockquote>`,
        );
      } else {
        merged.push(out[i]);
      }
      i = j + 1;
    }
  }
  return (opts.wrapChapters ? wrapChapters(merged) : merged).join("\n");
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
    // Flat, not per chapter: this render walks the whole book at once, and a
    // fingerprint is of the paragraph's own text — see flattenAlign.
    alignByPara: flattenAlign(readTextAlign(assetRoot)),
    // Scripture gets the Uthmanic face, the rest Scheherazade New. Sourced from
    // the Arabic audit's own provenance rather than re-derived here.
    quranicRuns: readQuranicRuns(assetRoot),
    // Which card a non-scriptural quotation is drawn in. Flat for the same
    // reason alignByPara is: this render walks the whole book at once and the
    // key is the quotation's own text — see flattenQuoteKind.
    quoteKinds: flattenQuoteKind(readQuoteKind(assetRoot)),
    // Which declared quote+gloss fragments merge into one card. Flat for the
    // same reason quoteKinds is — see flattenQuoteGroups.
    quoteGroups: flattenQuoteGroups(readQuoteGroups(assetRoot)),
    // Per-image resize/align a person set in the Composer.
    imageLayout: flattenImageLayout(readImageLayout(assetRoot)),
    // The chapter and verse each Qur'an card is headed by.
    quranicRefs: readQuranicRefs(assetRoot),
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
