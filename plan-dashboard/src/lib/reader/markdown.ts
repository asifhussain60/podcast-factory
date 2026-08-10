/**
 * Minimal markdown → HTML converter for podcast-factory prose content — the
 * ONE renderer behind both surfaces (R2 of the clean-code hardening plan
 * merged the former source-render.ts into this module):
 *
 *   - Book/chapter prose (default options): paragraphs, headers with anchor
 *     ids, bold/italic/inline code, links, ul/ol lists, Arabic-aware
 *     blockquotes (.ar/.tr + `quran` class), md-comment divs.
 *   - Source-extractor bundles (`renderSourceMarkdown`): ⟪ar:…⟫ / ⟪ar-quote:…⟫
 *     inline Arabic + ⟪quran X:Y⟫ citation chips, section-comment dividers,
 *     pipe tables, [diagram]/[image] blocks — no heading ids, no lists, no
 *     transliteration folding.
 *
 * We don't need full CommonMark, and shipping a dependency that does is
 * overkill. IMPORTANT: emphasis spans are preserved as `<em>`/`<strong>` so
 * the highlight-renderer can wrap them in ref-category spans without
 * re-parsing.
 */

import { FENCE_KINDS } from "./book-fences";
import { sectionKeyFromHeading } from "./companion/keys";
import { simplifyTransliteration } from "../translit";

/** A pipeline fence marker line. Built from the contract in book-fences.ts —
 *  imported, not copied, because this module is TypeScript in the same directory
 *  and a fourth hand-kept list is a fourth chance to miss a kind (which is
 *  exactly how `edition-intro` came to render as visible text). */
const MACHINE_FENCE_LINE_RE = new RegExp(
  `^<!--\\s*(${FENCE_KINDS.join("|")}):(begin|end)\\s*-->$`,
);

/** Fence kinds whose span is an EDITORIAL ASIDE — the pipeline talking to the
 *  reader about the text — as opposed to the text itself. They render as
 *  blockquotes, exactly like a scripture citation does, and until 2026-07-28
 *  nothing in the markup told them apart: `blockquote p:first-child` in
 *  book-reader.css sizes the first line of a verse block at 1.45rem/1.9 for the
 *  Arabic, and it was hitting these instead, so a 220-word editorial note
 *  rendered as 28px centred display type against 20px justified body. Tagging
 *  the aside lets that rule stay exactly as it is for verses and skip these.
 *  `edition-intro` is deliberately absent — it is plain prose, never a quote. */
const ASIDE_FENCE_KINDS = new Set(["editorial", "study-summary", "bridge"]);

/** A list item, by marker. Declared once: the parse below and the blank-line
 *  lookahead in renderMarkdown must agree on what counts as an item, and two
 *  copies of these would be two chances to disagree. A marker needs trailing
 *  whitespace, which is what keeps an italic line (`*Three Thanks…*`) prose. */
const UL_ITEM_RE = /^[-*+]\s+(.+)$/;
const OL_ITEM_RE = /^(\d+)\.\s+(.+)$/;

/** Arabic-script detection (matches the print renderer's ARABIC_RE). */
const ARABIC_SCRIPT_RE = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/;

export interface RenderOptions {
  /** Add slug ids to headings for in-chapter anchoring. Default true. */
  headingIds?: boolean;
  /** Parse `-`/`*`/`+` and `1.` lists. Default true. */
  lists?: boolean;
  /** Parse pipe tables (header + separator + body). Default false. */
  tables?: boolean;
  /** Parse ⟪ar:…⟫ / ⟪quran X:Y⟫ inline markers; disables code/links. Default false. */
  angleMarkers?: boolean;
  /** Render `<!-- section N (id=…) -->` comments as .se-section-marker dividers. Default false. */
  sectionMarkers?: boolean;
  /** Tag Arabic blockquote lines .ar/.tr + `quran` class. Default true. */
  arabicBlockquotes?: boolean;
  /** Render [diagram:…]/[image:…] lines as .se-image-block paragraphs. Default false. */
  imageBlocks?: boolean;
  /** Fold scholarly transliteration to plain English first. Default true. */
  simplifyTranslit?: boolean;
  /** Render pipeline fence markers as visible `.md-comment` chips instead of
   *  skipping them. Default false — they are machine markers, never prose. Only
   *  the Composer's EDIT seed sets this, where the marker text must survive into
   *  the editor for `preserveFences` to restore it after a save. */
  keepMachineFences?: boolean;
  /** Arabic runs the book's audit resolved against the CANONICAL MUSHAF, by their
   *  exact text. A run in this set is tagged `is-quranic`, which switches the
   *  Arabic face to the Uthmanic script; every other run keeps Scheherazade New.
   *  Mirrors the `quranicRuns` option of renderMd (scripts/lib/book-html.mjs) —
   *  same set, same class, so the reader and the printed page agree. Omitted
   *  means nothing is tagged, which renders exactly as before. */
  quranicRuns?: Set<string>;
  /** Which CARD a non-scriptural quotation is drawn in, keyed by the quotation's
   *  own first line. Answers what `quranicRuns` cannot: a block holding Arabic
   *  the mushaf does not carry is a hadith, a saying or a line of verse, and only
   *  a person knows which — so the map is written by hand, never inferred.
   *  Mirrors the `quoteKinds` option of renderMd (scripts/lib/book-html.mjs).
   *  Omitted means every quotation takes the default card, exactly as before. */
  quoteKinds?: Record<string, "hadith" | "poem" | "quote">;
  /** Each mushaf-resolved run's printable citation, by the run's exact text. The
   *  Qur'an card is headed by its chapter and verse and has no state without one.
   *  Formatted in Python where the surah names already live. */
  quranicRefs?: Record<string, string>;
  /** Emit the card's header strip. Default true. The Composer's EDIT seed turns
   *  it OFF, and that is load-bearing rather than cosmetic: TipTap would hold the
   *  band as content and `docToMarkdown` writes a blockquote from its CONTENT, so
   *  a band inside the editor could be serialised into book.md on the next
   *  autosave. Read mode and the PDF, which never round-trip, get it. */
  quoteBands?: boolean;
  /** Set a declared poem's Arabic as the two-column verse grid. Default true.
   *  The Composer's EDIT seed turns it OFF, and for a harder reason than the
   *  band above: the grid is not decoration around the text, it RESTRUCTURES it.
   *  One source line — one bayt — becomes two paragraphs inside a `<div>`, and a
   *  blockquote in the editor is a list of paragraphs that `docToMarkdown`
   *  writes back one per line. Seeding the editor with the grid would therefore
   *  offer to save a poem whose every bayt had been cut in half, and would ask
   *  TipTap to hold a `<div>` it has no node for. The editor shows the source:
   *  one line per bayt, exactly as book.md holds it. */
  quoteVerseGrid?: boolean;
}

/** The key one quotation is stored under: its first non-empty line, trimmed.
 *  Mirrors `quoteKindKey` in scripts/lib/quote-kind.mjs — a plain string rather
 *  than a hash, so the two renderers cannot drift on it. */
const QUOTE_BAND_LABEL: Record<string, string> = {
  hadith: "Prophetic tradition",
  poem: "Verse",
  quote: "Saying",
};

/** The card's header strip. Mirrors `band` in scripts/lib/book-html.mjs. Only the
 *  Qur'an card names itself from the text; the other three take a fixed word,
 *  because "which hadith" is a question the audit cannot answer. */
function quoteBand(kind: string, lines: string[], opts: RenderOptions): string {
  if (kind === "" || opts.quoteBands === false) return "";
  let label = QUOTE_BAND_LABEL[kind] ?? "";
  if (kind === "quran") {
    const line = lines.find((x) => isArabicQuoteLine(x));
    label = (line && opts.quranicRefs?.[line.trim()]) || "";
  }
  return (
    `<span class="q-band q-band--${kind}">` +
    '<span class="q-orn" aria-hidden="true"></span>' +
    (label ? `<span>${escapeHtml(label)}</span>` : "") +
    "</span>"
  );
}

/** THE BLOCK'S OWN FIRST LINE, and it must be given the RAW LINES rather than
 *  the paragraphs. A quotation's paragraphs are its lines JOINED — three abyat
 *  with no blank line between them are one paragraph — so keying on a paragraph
 *  asked for a string no human wrote and no store holds. The three-line poem in
 *  `ayyuhal-walad` was declared verse and rendered as a saying for exactly that
 *  reason: the declaration was filed under its first line, and the renderer
 *  looked up all three joined together. */
function quoteKindKey(lines: string[]): string {
  for (const p of lines) {
    const line = p.trim();
    if (line) return line;
  }
  return "";
}

/** ` * ` inside a line of DECLARED VERSE separates the two hemistichs of one
 *  bayt — the sadr, which is set on the right, and the ajuz on the left.
 *
 *  Splitting on it is safe here and nowhere else. In `ayyuhal-walad` the same
 *  character separates a Qur'anic verse from its own reference five times
 *  (`… * الحجرات: ٥`), so a renderer that split every Arabic line would tear
 *  those citations in half and print a surah name as a second hemistich. It runs
 *  only inside a block a person marked as verse. */
const HEMISTICH = /\s+\*\s+/;

/** A declared poem's Arabic set as a two-column grid, the arrangement printed
 *  diwans use. Mirrors `verseGrid` in scripts/lib/book-html.mjs.
 *
 *  IT TAKES THE RAW LINES, not the paragraphs, and that is the whole reason it
 *  can work: one bayt is one LINE, and every other quotation in this renderer
 *  joins its lines into paragraphs before anything looks at them. Three abyat
 *  joined into `A * B C * D E * F` cannot be divided back into hemistichs by any
 *  rule — the bayt boundaries are gone.
 *
 *  Arabic lines accumulate into one grid however many blank lines fall between
 *  them, so the gutter runs unbroken down the block; the English closes the grid
 *  and is set beneath it as prose. Document order is preserved either way, so a
 *  book that translates each bayt reads the same as one that translates them all
 *  at once. */
function verseGrid(lines: string[], opts: RenderOptions): string {
  const out: string[] = [];
  let cells: string[] = [];
  let prose: string[] = [];
  const flushCells = () => {
    if (cells.length === 0) return;
    out.push(`<div class="q-verse">${cells.join("")}</div>`);
    cells = [];
  };
  const flushProse = () => {
    const text = prose.join(" ").trim();
    prose = [];
    if (text) out.push(`<p class="tr">${renderInline(text, opts)}</p>`);
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushProse();
      continue;
    }
    if (isArabicQuoteLine(line)) {
      flushProse();
      const halves = line.split(HEMISTICH);
      // A line with no second hemistich spans both columns. Left in one column
      // it would sit against the gutter as a half-empty row, which reads as a
      // missing line rather than as a whole one.
      const solo = halves.length < 2 ? " bayt-solo" : "";
      for (const half of halves) {
        cells.push(
          `<p class="ar${solo}" dir="rtl" lang="ar">${renderInline(half, opts)}</p>`,
        );
      }
    } else {
      flushCells();
      prose.push(line);
    }
  }
  flushCells();
  flushProse();
  return out.join("");
}

/**
 * Does the list currently open continue after the blank line at `from`?
 *
 * Skips further blank lines, then reports whether the next line with content is
 * an item of the SAME kind. Anything else — prose, a heading, a rule, a table,
 * end of input — ends the list.
 *
 * The `kind` comparison is DEFENSIVE rather than load-bearing: when the marker
 * kind changes, keeping the list open here would make no difference, because the
 * item branch in the main loop flushes on a kind switch anyway. It is checked
 * here so the decision "does this list continue" is answerable from this
 * function alone, instead of being correct only by virtue of what happens next.
 */
function continuesList(
  lines: string[],
  from: number,
  kind: "ul" | "ol",
): boolean {
  for (let j = from; j < lines.length; j++) {
    const next = lines[j].trim();
    if (next.length === 0) continue;
    return kind === "ul" ? UL_ITEM_RE.test(next) : OL_ITEM_RE.test(next);
  }
  return false;
}

/** The source-extractor bundle profile (the former source-render.ts). */
const SOURCE_PROFILE: RenderOptions = {
  headingIds: false,
  // Real enumerations render as real lists (2026-07-26). This was `false`, which
  // flattened a numbered list into one run-together paragraph with the numbering
  // as literal text — visible in the chapter viewer, the Urdu bilingual view and
  // the Composer's podcast lane, and it made enumeration survival (a
  // narrative-frame rule) unreviewable on the surfaces a human actually reads.
  // Turning it on required fixing the shared list handling FIRST: a blank line
  // used to split a loose list, and the ordinal came from the `<ol>` counter
  // rather than the source. See flushList + continuesList, pinned by
  // markdown.test.ts.
  lists: true,
  tables: true,
  angleMarkers: true,
  sectionMarkers: true,
  arabicBlockquotes: false,
  imageBlocks: true,
  simplifyTranslit: false,
};

function escapeHtml(s: string): string {
  // Don't escape apostrophes — they're safe in HTML text content and inside
  // double-quoted attributes. Escaping them as &#39; breaks downstream
  // pattern matching (e.g. "Abu Ya'qub" → "Abu Ya&#39;qub" which the Arabic
  // detector can't see through). Only escape what's actually unsafe.
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** ⟪…⟫ marker pass: escape text OUTSIDE markers, emit marker tags directly. */
function renderAngleMarkers(text: string): string {
  const markerRe = /⟪([a-z-]+):([^⟪⟫]*)⟫|⟪quran (\d+):(\d+)(?:-(\d+))?⟫/g;
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = markerRe.exec(text)) !== null) {
    out += escapeHtml(text.slice(last, m.index));
    if (m[3] !== undefined) {
      const surah = m[3];
      const start = m[4];
      const end = m[5];
      const ref = end
        ? `Quran ${surah}:${start}–${end}`
        : `Quran ${surah}:${start}`;
      out += `<span class="quran-cite" dir="ltr">${ref}</span>`;
    } else {
      const kind = m[1]; // "ar", "ar-quote", or arbitrary "ar-*"
      const cls = kind === "ar-quote" ? "ar-quote" : "ar";
      const trimmed = m[2].trim();
      out += `<span class="${cls}" lang="ar" dir="rtl">${escapeHtml(trimmed)}</span>`;
    }
    last = m.index + m[0].length;
  }
  return out + escapeHtml(text.slice(last));
}

function renderInline(text: string, opts: RenderOptions): string {
  let s: string;
  if (opts.angleMarkers) {
    // Source flavor: markers first (escaping around them), then emphasis only.
    s = renderAngleMarkers(text);
  } else {
    s = escapeHtml(text);
    // inline code (must come before emphasis so backticks don't interleave)
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    // links: [text](url) — URL is escaped already because we ran escapeHtml first
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, label, url) => {
      const safeUrl = url.replace(/"/g, "&quot;");
      return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });
  }
  // bold: **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // italic: *text* (single asterisks, not part of bold)
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  return isolateInlineArabic(s);
}

/** An Arabic run woven into left-to-right prose, with the bracketing glyphs the
 *  print renderer also absorbs. Mirror of `ARABIC_INLINE_RE` in
 *  plan-dashboard/scripts/lib/book-html.mjs — keep the two in step. */
const ARABIC_INLINE_RE = /[﴿«]?[\s؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+[﴾»]?/g;

/**
 * Is this paragraph an Arabic QUOTATION, rather than English containing Arabic?
 *
 * Deliberately duplicated rather than imported: the canonical copy lives in
 * scripts/lib/book-html.mjs, which reads the filesystem and so cannot be pulled
 * into this client-bundled module. The two, plus `_book_mirror.is_arabic_block`
 * on the Python side, are pinned against each other by `arabic-block.fixtures.json`
 * — see the canonical copy's own note for what drift costs.
 */
export function isArabicOnlyParagraph(s: string): boolean {
  const arabic = (s.match(/[ؠ-يٱ-ۓ]/g) || []).length;
  const latin = (s.match(/[A-Za-z]/g) || []).length;
  return arabic > 20 && arabic > 2 * latin;
}

/**
 * Is this line of a quotation block ARABIC, or the translation beside it?
 *
 * MIRROR of `isArabicQuoteLine` in scripts/lib/book-html.mjs, pinned by
 * `arabic-quote-line.fixtures.json`. Deliberately duplicated for the same reason
 * `isArabicOnlyParagraph` above is: the canonical copy reads the filesystem and
 * cannot be pulled into this client-bundled module.
 *
 * The rule is which script the line is MOSTLY in. Until 2026-08-09 both copies
 * asked only whether the line CONTAINED Arabic, so an English translation carrying
 * the `(ع)` honorific was set right-to-left in the Arabic face. Drift here is the
 * one divergence no gate could see: the printed page and this reader would give the
 * same paragraph different directions.
 */
export function isArabicQuoteLine(s: string): boolean {
  const arabic = (s.match(/[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/g) || []).length;
  if (arabic === 0) return false;
  const latin = (s.match(/[A-Za-z]/g) || []).length;
  return arabic > latin;
}

/**
 * Every inline Arabic run in a chunk of plain text (no tags — the caller has
 * already split those out), as `[start, end)` character offsets with the
 * bracketing whitespace trimmed off each end.
 *
 * Factored out of `isolateInlineArabic` so the live Book Composer editor can
 * find the SAME runs over ProseMirror text nodes that this function finds over
 * an HTML string — see `arabic-decos.ts`'s header for why that decoration
 * exists and why it has to match this, not a second regex of its own.
 */
export function findArabicRuns(
  text: string,
): Array<{ start: number; end: number }> {
  if (!ARABIC_SCRIPT_RE.test(text)) return [];
  const runs: Array<{ start: number; end: number }> = [];
  for (const m of text.matchAll(ARABIC_INLINE_RE)) {
    if (!ARABIC_SCRIPT_RE.test(m[0])) continue;
    const leading = m[0].match(/^\s*/)?.[0] ?? "";
    const trailing = m[0].match(/\s*$/)?.[0] ?? "";
    const start = m.index + leading.length;
    const end = m.index + m[0].length - trailing.length;
    if (end > start) runs.push({ start, end });
  }
  return runs;
}

/**
 * Wrap each inline Arabic run in the same `.ar-inline` span the PRINT renderer
 * emits (book-html.mjs `renderInline`).
 *
 * Block-level Arabic already gets `dir="rtl" lang="ar"`, but an Arabic run
 * sitting INSIDE an English sentence had no wrapper at all on the reader path.
 * The bidi algorithm then pulls the neighbouring brackets into the
 * right-to-left run, so `… al-Yaman (جعفر بن منصور اليمن) and …` renders with
 * its closing parenthesis stranded at the start of the next line. The PDF never
 * had the bug because `.ar-inline` carries `unicode-bidi: isolate`; this brings
 * the on-screen render to the same markup, which also gives it the same Arabic
 * face for free.
 *
 * Applied last, so it cannot wrap the HTML tags the passes above emit.
 */
function isolateInlineArabic(html: string): string {
  if (!ARABIC_SCRIPT_RE.test(html)) return html;
  // Only rewrite text, never the inside of a tag.
  return html.replace(/<[^>]+>|[^<]+/g, (chunk) => {
    if (chunk.startsWith("<")) return chunk;
    const runs = findArabicRuns(chunk);
    if (!runs.length) return chunk;
    let out = "";
    let last = 0;
    for (const r of runs) {
      out += chunk.slice(last, r.start);
      out += `<span class="ar-inline" dir="rtl" lang="ar">${chunk.slice(r.start, r.end)}</span>`;
      last = r.end;
    }
    out += chunk.slice(last);
    return out;
  });
}

/** Split accumulated blockquote lines into paragraphs on blank lines. */
function quoteParagraphs(quoteBuffer: string[]): string[] {
  const paras: string[] = [];
  let cur: string[] = [];
  for (const l of quoteBuffer) {
    if (l.trim() === "") {
      if (cur.length) {
        paras.push(cur.join(" "));
        cur = [];
      }
    } else cur.push(l);
  }
  if (cur.length) paras.push(cur.join(" "));
  return paras;
}

/**
 * Pipe-separated table row → array of cell texts. Handles surrounding
 * whitespace and one optional leading/trailing pipe.
 */
function parseTableRow(line: string): string[] {
  let t = line.trim();
  if (t.startsWith("|")) t = t.slice(1);
  if (t.endsWith("|")) t = t.slice(0, -1);
  return t.split("|").map((c) => c.trim());
}

function isTableSeparator(line: string): boolean {
  const t = line.trim();
  if (!t.startsWith("|") && !t.includes("|")) return false;
  // a separator row has only -, :, |, spaces
  return /^\|?\s*:?-{2,}:?(\s*\|\s*:?-{2,}:?)+\s*\|?$/.test(t);
}

const SECTION_COMMENT_RE =
  /^<!--\s*section\s+(\d+)\s*\(id=(\d+),\s*raw_sort=(\d+)\):\s*(.*?)\s*-->$/;

type ListKind = "ul" | "ol" | null;

export function renderMarkdown(
  input: string,
  options: RenderOptions = {},
): string {
  const opts: RenderOptions = {
    headingIds: true,
    lists: true,
    arabicBlockquotes: true,
    simplifyTranslit: true,
    ...options,
  };

  // Fold scholarly Arabic transliteration to plain English for display
  // (Kīmiyāʾ al-Saʿāda → Kimiya al-Sa'ada). Arabic script is left untouched.
  const source = opts.simplifyTranslit ? simplifyTransliteration(input) : input;
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let paraBuffer: string[] = [];
  let quoteBuffer: string[] = [];
  /** The pipeline fence currently open, so a blockquote inside an aside span can
   *  be told apart from a scripture citation. See ASIDE_FENCE_KINDS. */
  let openFence: string | null = null;
  let listKind: ListKind = null;
  /** Open list items. `value` carries the SOURCE ordinal for an ordered item —
   *  see flushList on why the `<ol>` counter is not trusted. */
  let listItems: { text: string; value?: number }[] = [];

  const flushPara = () => {
    if (paraBuffer.length === 0) return;
    const text = paraBuffer.join(" ").trim();
    if (text) {
      // A standalone Arabic quotation is a DISPLAY block, not a sentence with a
      // term in it. The reader used to emit a bare <p> for one while the PDF and
      // the Composer's Read view (both renderMd) emitted `.ar-block` — so the same
      // paragraph was a centered display quotation in two surfaces and left-aligned
      // running prose at body leading in the third.
      const cls = isArabicOnlyParagraph(text) ? ' class="ar-block"' : "";
      out.push(`<p${cls}>${renderInline(text, opts)}</p>`);
    }
    paraBuffer = [];
  };

  const flushQuote = () => {
    if (quoteBuffer.length === 0) return;
    const paras = quoteParagraphs(quoteBuffer);
    // An aside keeps its fence kind as a second class, so a stylesheet can reach
    // `.aside` for all of them or `.editorial` / `.bridge` for one.
    const asideCls =
      openFence && ASIDE_FENCE_KINDS.has(openFence)
        ? ` aside ${openFence}`
        : "";
    if (opts.arabicBlockquotes) {
      // Tag Arabic-script lines as `.ar` and their translations as `.tr` (only
      // when the block actually contains Arabic) so the reader can style verses
      // like the print renderer does — body-ink Arabic at body scale, no box.
      // Emission stays one line so the Composer's paragraph mirror
      // (`:scope > p`) is unaffected.
      // The BLOCK decision stays "contains Arabic" (it chooses the mushaf card); only
      // the per-line direction below weighs proportion. See `isArabicQuoteLine`.
      const hasArabic = paras.some((p) => ARABIC_SCRIPT_RE.test(p));
      // Scripture always wins the card: a block whose Arabic the audit resolved
      // is a Qur'an card whatever the map says, because the mushaf is not a
      // matter of opinion. Everything else takes the declared kind, or the
      // default when nobody declared one.
      // A CARD NEEDS AN ARABIC LINE, not merely Arabic somewhere. A blockquote
      // whose English glosses one term — `<span class="ar-inline">` inside a
      // translation paragraph — has no quotation to draw, and giving it the
      // default card would put a tinted plate around an ordinary note. And an
      // editorial or bridge aside is never a quotation card whatever it holds.
      const hasArabicLine =
        hasArabic && paras.some((p) => isArabicQuoteLine(p));
      const scripture =
        hasArabicLine &&
        paras.some(
          (p) => isArabicQuoteLine(p) && opts.quranicRuns?.has(p.trim()),
        );
      const kind = asideCls
        ? ""
        : scripture
          ? "quran"
          : (opts.quoteKinds?.[quoteKindKey(quoteBuffer)] ??
            (hasArabicLine ? "quote" : ""));
      // The kind is decided BEFORE the markup because verse is SET differently,
      // not merely coloured differently: a poem's lines are grid cells, and every
      // other kind's are paragraphs.
      const inner =
        paras.length === 0
          ? "<p></p>"
          : kind === "poem" && hasArabicLine && opts.quoteVerseGrid !== false
            ? verseGrid(quoteBuffer, opts)
            : paras
                .map((p) => {
                  if (!hasArabic) return `<p>${renderInline(p, opts)}</p>`;
                  return isArabicQuoteLine(p)
                    ? `<p class="${opts.quranicRuns?.has(p.trim()) ? "ar is-quranic" : "ar"}" dir="rtl" lang="ar">${renderInline(p, opts)}</p>`
                    : `<p class="tr">${renderInline(p, opts)}</p>`;
                })
                .join("");
      const cls =
        `${hasArabic ? "quran" : ""}${kind ? ` k-${kind}` : ""}${asideCls}`.trim();
      out.push(
        `<blockquote${cls ? ` class="${cls}"` : ""}>${quoteBand(kind, quoteBuffer, opts)}${inner}</blockquote>`,
      );
    } else {
      const inner = paras
        .map((p) => {
          const t = p.trim();
          return t ? `<p>${renderInline(t, opts)}</p>` : "";
        })
        .join("");
      // No Arabic, so no `quran` class. A kind still applies when a person
      // declared one — verse reaches the page in English alone, and it is a poem
      // whichever language it arrives in. An undeclared English blockquote gets
      // nothing, exactly as before.
      const declared = asideCls
        ? undefined
        : opts.quoteKinds?.[quoteKindKey(quoteBuffer)];
      const cls = `${declared ? `k-${declared}` : ""}${asideCls}`.trim();
      out.push(
        `<blockquote${cls ? ` class="${cls}"` : ""}>${quoteBand(declared ?? "", quoteBuffer, opts)}${inner}</blockquote>`,
      );
    }
    quoteBuffer = [];
  };

  /**
   * Close the open list.
   *
   * An ordered item carries `value="N"` from the SOURCE rather than leaning on
   * `<ol>`'s own counter. The counter is not trustworthy for this corpus: a list
   * legitimately starting at 3 rendered as 1, and an author style that repeats
   * "1." per item was silently rewritten to 1,2,3. Both are the faked numbering
   * the view standard forbids (REQ-015), and `value` makes the rendered number
   * equal the number the source actually states — whatever it states.
   *
   * `value` is only valid on an `<ol>`'s items, so a bulleted list never gets it.
   */
  const flushList = () => {
    if (listKind === null || listItems.length === 0) {
      listKind = null;
      listItems = [];
      return;
    }
    out.push(`<${listKind}>`);
    for (const item of listItems) {
      const attr =
        listKind === "ol" && item.value !== undefined
          ? ` value="${item.value}"`
          : "";
      out.push(`<li${attr}>${renderInline(item.text, opts)}</li>`);
    }
    out.push(`</${listKind}>`);
    listKind = null;
    listItems = [];
  };

  const flushAll = () => {
    flushPara();
    flushQuote();
    flushList();
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i].replace(/\t/g, "  ").trimEnd();
    const trimmed = line.trim();

    if (trimmed.length === 0) {
      flushPara();
      flushQuote();
      // A blank line does NOT end a list whose next content is another item of
      // the same kind. Loose lists are the dominant enumeration style in this
      // corpus, and flushing here split one `1. / 2. / 3.` into three separate
      // lists — each of which then restarted its own numbering.
      if (listKind !== null && !continuesList(lines, i + 1, listKind))
        flushList();
      i++;
      continue;
    }

    // horizontal rule
    if (/^(---+|\*\*\*+)$/.test(trimmed)) {
      flushAll();
      out.push("<hr />");
      i++;
      continue;
    }

    // headings
    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushAll();
      const level = hMatch[1].length;
      const inner = renderInline(hMatch[2], opts);
      if (opts.headingIds) {
        // slug for in-chapter anchoring (mini-TOC) — and, because the LIVE Session
        // keys Companion notes by this id, the one rule both sides import.
        const plain = sectionKeyFromHeading(hMatch[2]);
        out.push(`<h${level} id="${plain}">${inner}</h${level}>`);
      } else {
        out.push(`<h${level}>${inner}</h${level}>`);
      }
      i++;
      continue;
    }

    // blockquote. `(?:>\s?)+` rather than `>`: a NESTED marker is flattened to one
    // level instead of surviving into the reader as a literal ">" character.
    // Nothing in this corpus quotes inside a quote — the single occurrence ever
    // found was an authoring accident, where the augment pass wrapped model
    // prose that had already opened its own blockquote, and it printed as
    // `Editorial note (tradition-grounded). > A clarified term…` mid-sentence.
    // `_book_augment.format_editorial_block` no longer emits it; this keeps the
    // already-composed books readable without re-composing them, and mirrors
    // scripts/lib/book-html.mjs, which renders the same markdown for print.
    const qMatch = line.match(/^(?:>\s?)+(.*)$/);
    if (qMatch) {
      flushPara();
      flushList();
      quoteBuffer.push(qMatch[1]);
      i++;
      continue;
    } else if (quoteBuffer.length > 0) {
      flushQuote();
    }

    if (opts.lists) {
      // unordered list
      const ulMatch = line.match(UL_ITEM_RE);
      if (ulMatch) {
        flushPara();
        flushQuote();
        if (listKind !== "ul") {
          flushList();
          listKind = "ul";
        }
        listItems.push({ text: ulMatch[1] });
        i++;
        continue;
      }

      // ordered list
      const olMatch = line.match(OL_ITEM_RE);
      if (olMatch) {
        flushPara();
        flushQuote();
        if (listKind !== "ol") {
          flushList();
          listKind = "ol";
        }
        // The stated ordinal, carried through to `value` — see flushList.
        listItems.push({ text: olMatch[2], value: Number(olMatch[1]) });
        i++;
        continue;
      } else if (listKind !== null) {
        flushList();
      }
    }

    // Table: header row + separator + body (source flavor)
    if (
      opts.tables &&
      trimmed.startsWith("|") &&
      i + 1 < lines.length &&
      isTableSeparator(lines[i + 1])
    ) {
      flushAll();
      const header = parseTableRow(trimmed);
      i += 2; // skip header + separator
      const body: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        body.push(parseTableRow(lines[i]));
        i++;
      }
      const headHtml = header
        .map((c) => `<th>${renderInline(c, opts)}</th>`)
        .join("");
      const bodyHtml = body
        .map(
          (row) =>
            `<tr>${row.map((c) => `<td>${renderInline(c, opts)}</td>`).join("")}</tr>`,
        )
        .join("");
      out.push(
        `<table><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`,
      );
      continue;
    }

    // HTML comments
    if (opts.sectionMarkers) {
      // Section-marker comment: `<!-- section N (id=…, raw_sort=…): label -->`
      const sm = trimmed.match(SECTION_COMMENT_RE);
      if (sm) {
        flushAll();
        const pos = sm[1];
        const id = sm[2];
        const label = sm[4];
        out.push(
          `<div class="se-section-marker" dir="ltr">` +
            `<span>§ ${pos} · id ${id}</span>` +
            (label
              ? `  <span dir="rtl" class="se-urdu-label">— ${escapeHtml(label)}</span>`
              : "") +
            `</div>`,
        );
        i++;
        continue;
      }
      if (trimmed.startsWith("<!--") && trimmed.endsWith("-->")) {
        flushAll();
        const inner = trimmed.replace(/^<!--\s*/, "").replace(/\s*-->$/, "");
        out.push(
          `<div class="se-section-marker" dir="ltr">${escapeHtml(inner)}</div>`,
        );
        i++;
        continue;
      }
    } else if (trimmed.startsWith("<!--")) {
      // Book flavor: comment line (used in transcripts: `<!-- page 1 -->`).
      //
      // A PIPELINE FENCE is not that kind of comment. It delimits a span the
      // Python phases own, and rendering it as a visible chip put 16 grey
      // `editorial:begin` / `edition-intro:begin` labels into the rendered
      // reading view. Skipped by default; the EDIT seed opts back in via
      // `keepMachineFences`, because there the marker text is load-bearing —
      // `preserveFences` reads it back to restore the comment form after a save,
      // and dropping it from the seed would strip the fence on the first save.
      const fence = trimmed.match(MACHINE_FENCE_LINE_RE);
      if (fence) {
        // Flush FIRST, then move the marker: on `begin` that closes whatever
        // preceded the span, and on `end` it emits the aside's own blockquote
        // while the kind is still open — which is what carries the class.
        //
        // Unconditional since 2026-08-05. It used to be skipped under
        // `keepMachineFences`, which is the EDIT seed — so there the marker was
        // cleared first and the flush at the bottom of this branch emitted the
        // note with no class at all. Read mode drew a plain blockquote and Edit
        // drew a plain blockquote between two grey marker strips, which is the
        // shape Asif reported. The flush is safe here either way: a marker line
        // is never itself prose, so closing the buffer at it cannot join two
        // paragraphs that belong apart.
        flushAll();
        openFence = fence[2] === "begin" ? fence[1] : null;
      }
      if (!opts.keepMachineFences && fence) {
        i++;
        continue;
      }
      flushAll();
      const inner = trimmed.replace(/^<!--\s*/, "").replace(/\s*-->$/, "");
      out.push(
        `<div class="md-comment" data-md-comment="${escapeHtml(inner)}">${escapeHtml(inner)}</div>`,
      );
      i++;
      continue;
    }

    // Image-block markers from the source-extractor finalize stage.
    if (
      opts.imageBlocks &&
      (trimmed.startsWith("[diagram") || trimmed.startsWith("[image"))
    ) {
      flushPara();
      out.push(`<p class="se-image-block">${renderInline(trimmed, opts)}</p>`);
      i++;
      continue;
    }

    // Default — accumulate prose. Source flavor accumulates the trimmed line
    // (its inputs are machine-generated, column-0 text); book flavor keeps the
    // line as-is minus trailing whitespace.
    paraBuffer.push(opts.angleMarkers ? trimmed : line);
    i++;
  }
  flushAll();

  return out.join("\n");
}

/**
 * Render a source-extractor raw-extract.md into HTML for the review view —
 * the former source-render.ts entry point, now a profile of renderMarkdown.
 * Deliberately scoped to the source-extractor view (.se-prose).
 */
export function renderSourceMarkdown(input: string): string {
  return renderMarkdown(input, SOURCE_PROFILE);
}

/**
 * The Book Composer's EDIT-mode seed — the byte-faithful profile.
 *
 * Everything this render loses, the next autosave writes into book.md, so no
 * display-only transform may run here. The one the default profile applies —
 * simplifyTransliteration — treats a straight apostrophe as a probable
 * ayn/hamza and folds it away unless it is verifiably English, which ate the
 * OPENING quote of "(صالح, 'the righteous')" (space before it → dropped;
 * the closing one follows an `s` → kept). Seeding the editor from that fold
 * corrupted the round trip before the author typed a single character.
 * Display surfaces keep folding; the editor sees the file's actual bytes.
 */
export function renderEditSeed(
  input: string,
  quranicRuns?: Set<string> | null,
  quoteKinds?: Record<string, "hadith" | "poem" | "quote"> | null,
): string {
  // keepMachineFences: the editor MUST receive the fence marker lines. TipTap
  // has no comment node, so they arrive as bare text, which is exactly what
  // `preserveFences` step 1 reads to put the comment form back on save. Skipping
  // them here would strip every fence on the first save of that chapter.
  //
  // quranicRuns (optional, added 2026-08-09): the same provenance set Read mode
  // and the PDF are already given. Without it the edit canvas could not tell
  // scripture from a saying AT ALL — every Arabic run arrived unmarked, so the
  // face split locked on 2026-07-21 was invisible on the one surface the printed
  // book is verified on, and any treatment keyed to provenance would have dressed
  // every verse as somebody's words. Omitted (the default, and what every test
  // caller passes) renders exactly as it did before.
  //
  // The class cannot reach book.md: `docToMarkdown` writes the blockquote from
  // its CONTENT and names no class, which is the same reason `quran`/`ar`/`tr`
  // are safe to carry here.
  // quoteKinds rides along for the same reason: without it the edit canvas
  // would draw every non-scriptural quotation in the default card while Read
  // mode and the PDF drew three different ones, and the Composer is the surface
  // the printed book is verified on.
  return renderMarkdown(input, {
    simplifyTranslit: false,
    keepMachineFences: true,
    quranicRuns: quranicRuns ?? undefined,
    quoteKinds: quoteKinds ?? undefined,
    // NEVER in the edit seed — see the option's own note. The card's plate and
    // ink still show, because those come from the class; only the header strip,
    // which is markup TipTap would hold as content, is withheld.
    quoteBands: false,
    // Also NEVER in the edit seed, and this one is not cosmetic at all: the
    // grid splits one source line into two paragraphs, and the editor writes a
    // blockquote back one paragraph per line. Seeding it would offer to save a
    // poem with every bayt cut in half.
    quoteVerseGrid: false,
  });
}

/**
 * Render a YAML-folded scalar as a single paragraph or as paragraphs.
 * YAML's `>` folding collapses newlines into spaces, so we typically
 * get one paragraph back. We still run renderInline so emphasis works.
 */
export function renderProse(text: string): string {
  return renderMarkdown(text);
}
