/**
 * A quotation card's header strip, and the group runs that merge adjacent cards.
 *
 * Split out of markdown.ts on 2026-08-16, when that file passed its size ratchet.
 * The cut stops before `verseGrid`, deliberately: that function calls back into
 * the renderer's own inline pass, so moving it would trade a long file for a
 * circular import — a worse problem wearing a better number.
 */

import { escapeHtml } from "../html-escape";
import { isArabicQuoteLine } from "./arabic-inline";
import type { RenderOptions } from "./markdown";

/** The key one quotation is stored under: its first non-empty line, trimmed.
 *  Mirrors `quoteKindKey` in scripts/lib/quote-kind.mjs — a plain string rather
 *  than a hash, so the two renderers cannot drift on it. */
/** What each kind is called on its header. A COPY of `QUOTE_KIND_LABEL` in
 *  scripts/lib/quote-kind.mjs, which is its home, and copied rather than
 *  imported for a reason that is not laziness: that module reads the filesystem,
 *  and this one is bundled into the browser by the Studio editor's client
 *  scripts (arabic-decos.ts, compose-lane.ts). Importing it would put `node:fs`
 *  in a browser bundle. The golden fixture in listener/test pins the rendered
 *  words, so a divergence between the two fails a test rather than shipping. */
const QUOTE_KIND_LABEL: Record<string, string> = {
  hadith: "Prophetic tradition",
  poem: "Verse",
  quote: "Saying",
};

/** The card's header strip. Mirrors `band` in scripts/lib/book-html.mjs. Only the
 *  Qur'an card names itself from the text; the other three take a fixed word,
 *  because "which hadith" is a question the audit cannot answer.
 *
 *  WHO SAID IT sits beside the kind in that centred header when a person
 *  recorded it, and only then — an attribution nobody wrote is a claim nobody
 *  made. TWO KINDS never name one: scripture's header carries the surah and
 *  verse the audit resolved, and a prophetic tradition is already the claim
 *  that the Prophet said it (Asif, 2026-08-11). */
export function quoteLabel(
  kind: string,
  lines: string[],
  opts: RenderOptions,
): string {
  if (kind === "") return "";
  let label = QUOTE_KIND_LABEL[kind] ?? "";
  if (kind === "quran") {
    const line = lines.find((x) => isArabicQuoteLine(x));
    label = (line && opts.quranicRefs?.[line.trim()]) || "";
  }
  return label;
}

export function quoteLabelAttribute(
  kind: string,
  lines: string[],
  opts: RenderOptions,
): string {
  if (!opts.quoteLabelAttributes) return "";
  const label = quoteLabel(kind, lines, opts);
  return label
    ? ` data-q-label="${escapeHtml(label).replace(/"/g, "&quot;")}"`
    : "";
}

export function quoteBand(
  kind: string,
  lines: string[],
  opts: RenderOptions,
): string {
  if (kind === "" || opts.quoteBands === false) return "";
  const label = quoteLabel(kind, lines, opts);
  const anon = kind === "quran" || kind === "hadith";
  const by = anon ? "" : opts.quoteKinds?.[quoteKindKey(lines)]?.by;
  return (
    `<span class="q-band q-band--${kind}">` +
    '<span class="q-orn" aria-hidden="true"></span>' +
    (label ? `<span class="q-kind">${escapeHtml(label)}</span>` : "") +
    (by ? `<span class="q-by" dir="auto">${escapeHtml(by)}</span>` : "") +
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
export function quoteKindKey(lines: string[]): string {
  for (const p of lines) {
    const line = p.trim();
    if (line) return line;
  }
  return "";
}

/** A block's group membership + the pieces needed to build a merged card
 *  from it, recorded in parallel to `out` at the same index — never changing
 *  what gets pushed there. Mirrors blockMeta in scripts/lib/book-html.mjs. */
export interface QuoteGroupMeta {
  type: "quote" | "gloss";
  groupId: string;
  kind?: string;
  bandHtml?: string;
  innerHtml?: string;
  text?: string;
}

/** Collect a linear list of `{groupId, type, kind}` markers (one per rendered
 *  block, `groupId: null` for anything undeclared) into merge-run indices —
 *  `runOf[i] === runOf[j]` means blocks i and j belong to the same card. A
 *  run of DECLARED same-group blocks collapses only when it has 2+ members
 *  AND every `type: "quote"` member shares one effective kind; otherwise
 *  every member of that would-be run gets its own singleton run, i.e.
 *  renders exactly as if ungrouped.
 *
 *  COPY-MIRRORED from `collectGroupRuns` in scripts/lib/quote-groups.mjs, not
 *  imported — this file is bundled into the browser and that one touches
 *  `node:fs`. `quote-groups.fixtures.json` pins the two against drifting.
 *  Keep the two functions byte-for-byte the same shape if you change either. */
export function collectGroupRuns(
  blocks: { groupId: string | null; type?: string; kind?: string }[],
): number[] {
  const runOf = new Array(blocks.length).fill(-1);
  let nextRun = 0;
  let i = 0;
  while (i < blocks.length) {
    const gid = blocks[i].groupId;
    if (!gid) {
      runOf[i] = nextRun++;
      i++;
      continue;
    }
    let j = i;
    while (j < blocks.length && blocks[j].groupId === gid) j++;
    const run = blocks.slice(i, j);
    const kinds = new Set(
      run.filter((b) => b.type !== "gloss" && b.kind).map((b) => b.kind),
    );
    const mergeable = run.length >= 2 && kinds.size <= 1;
    if (mergeable) {
      const id = nextRun++;
      for (let k = i; k < j; k++) runOf[k] = id;
    } else {
      for (let k = i; k < j; k++) runOf[k] = nextRun++;
    }
    i = j;
  }
  return runOf;
}
