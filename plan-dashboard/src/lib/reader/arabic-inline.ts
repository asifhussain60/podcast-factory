/**
 * Arabic script woven into left-to-right prose.
 *
 * Split out of markdown.ts on 2026-08-16, when that file passed its size ratchet.
 * This was the half that could leave cleanly, and it is a genuinely separate
 * concern rather than an arbitrary slice: three cross-language pins already treat
 * it as one — arabic-block.test.mjs, arabic-quote-line.test.mjs and
 * arabic-inline.test.ts each compare a function here against the print renderer's
 * answer to the same question.
 *
 * The renderer imports these; nothing here imports the renderer, so the direction
 * is one-way and there is no cycle to reason about.
 */

/** Arabic-script detection (matches the print renderer's ARABIC_RE). Exported
 *  because markdown.ts decides paragraph direction with the same test, and two
 *  copies of a script range is how a book comes out half right. */
export const ARABIC_SCRIPT_RE =
  /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]/;

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
export function isolateInlineArabic(html: string): string {
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
