/**
 * arabic-source.ts — the Arabic behind a chapter, addressed by paragraph number.
 *
 * The critical edition numbers its paragraphs and the OCR kept those numbers, so a
 * line beginning `(١)` opens paragraph 1 and runs to the next such line. The
 * refined English carries the SAME numbering, which is what makes an English
 * paragraph addressable in Arabic at all. `_system/arabic-alignment.json` (written
 * by scripts/podcast/align_arabic_paragraphs.py) says which source paragraphs each
 * composed paragraph came from; this module turns those numbers into text.
 *
 * THE STALENESS CHECK IS THE POINT OF THE PORT. `raw-extract.vowelled.md` is a
 * vowelling OF a particular OCR. Re-running Phase 0a rewrites the OCR, and a
 * sibling left from the previous one is then the marked-up text of a document that
 * no longer exists. Python guards this in `_vowelled_source.is_current`; nothing on
 * this side knew the sibling could go stale, so a route that opened it directly
 * would serve that ghost silently. Same sha256-against-the-report rule here, with
 * the raw scan as the fallback.
 */
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/** Arabic-Indic digits → ASCII, for reading a paragraph number. */
const ARABIC_INDIC: Record<string, string> = {
  "٠": "0",
  "١": "1",
  "٢": "2",
  "٣": "3",
  "٤": "4",
  "٥": "5",
  "٦": "6",
  "٧": "7",
  "٨": "8",
  "٩": "9",
};

/**
 * A paragraph marker: parenthesised Arabic-Indic digits at column 0. The anchor is
 * load-bearing — footnote references in this scan are bare, unparenthesised digits
 * welded to the preceding letter (`وَلَا٢`), and a looser pattern would read every
 * one of them as a paragraph break and shred the text.
 */
const MARKER_RE = /^\(([٠-٩]+)\)/;
const PAGE_RE = /^\s*<!--\s*page\s+\d+\s*-->\s*$/;

/**
 * A footnote reference: 1-2 Arabic-Indic digits welded to a letter. The letter is
 * captured and restored rather than matched behind, because the source is vowelled
 * and the character before the digit is usually a combining mark, not the letter.
 */
const FOOTNOTE_REF_RE = /([ؠ-ي][ً-ْٰ]*)[٠-٩]{1,2}/g;

/** The number whose marker the scan lost; its text lives in the block before it. */
export const MERGED_INTO: Record<number, number> = { 511: 510 };

export interface ArabicParagraph {
  number: number;
  text: string;
  merged?: boolean;
}

export interface AlignmentPair {
  fp: string;
  source_paras: number[];
  confidence: "verified" | "bracketed";
  anchored?: boolean;
  pinned?: boolean;
  repaired?: boolean;
}

function toInt(arabicDigits: string): number {
  return Number([...arabicDigits].map((c) => ARABIC_INDIC[c] ?? c).join(""));
}

/**
 * Is the vowelled sibling still the vowelling of THIS OCR?
 *
 * The TypeScript mirror of `_vowelled_source.is_current`. Fails closed: a missing
 * or unreadable report means "nothing is known to be current", which sends every
 * read to the raw scan rather than to a text of unknown provenance.
 */
export function vowelledSourceIsCurrent(bookDir: string): boolean {
  const raw = join(bookDir, "_system", "source", "ocr", "raw-extract.md");
  const sibling = join(bookDir, "_system", "source", "ocr", "raw-extract.vowelled.md");
  if (!existsSync(raw) || !existsSync(sibling)) return false;
  try {
    const report = JSON.parse(
      readFileSync(join(bookDir, "_system", "source-vowelling.json"), "utf8"),
    );
    const entry = report?.streams?.["_system/source/ocr/raw-extract.md"];
    if (!entry?.source_sha256) return false;
    const actual = createHash("sha256").update(readFileSync(raw)).digest("hex");
    return actual === entry.source_sha256;
  } catch {
    return false;
  }
}

/** The Arabic source to read — vowelled when that copy is current, else the scan. */
export function resolveArabicSource(bookDir: string): string | null {
  const raw = join(bookDir, "_system", "source", "ocr", "raw-extract.md");
  if (!existsSync(raw)) return null;
  return vowelledSourceIsCurrent(bookDir)
    ? join(bookDir, "_system", "source", "ocr", "raw-extract.vowelled.md")
    : raw;
}

/**
 * Map every paragraph number to its Arabic text.
 *
 * A block is its marker line plus everything up to the next marker, with page
 * markers dropped — they are scan furniture, and 48 of this book's 95 land
 * mid-paragraph, so keeping them would cut sentences in half.
 */
export function parseBlocks(
  text: string,
  opts: { stripFootnoteRefs?: boolean } = {},
): Map<number, ArabicParagraph> {
  const blocks = new Map<number, ArabicParagraph>();
  let current: number | null = null;
  let buf: string[] = [];

  const flush = () => {
    if (current === null) return;
    let body = buf.join("\n").trim();
    // The marker itself is scan furniture, dropped like the page comments above.
    // It opened the block only so this parser could find the boundary; the number
    // survives on `.number`, and every consumer states it in its own words
    // ("Source paragraph 29") rather than printing the Arabic-Indic original into
    // the middle of the text. MARKER_RE is start-anchored and unflagged, so this
    // takes the opening marker and nothing else.
    body = body.replace(MARKER_RE, "").trimStart();
    if (opts.stripFootnoteRefs) body = body.replace(FOOTNOTE_REF_RE, "$1");
    blocks.set(current, { number: current, text: body });
  };

  for (const line of String(text ?? "").split("\n")) {
    if (PAGE_RE.test(line)) continue;
    const m = MARKER_RE.exec(line);
    if (m) {
      flush();
      current = toInt(m[1]);
      buf = [line];
    } else if (current !== null) {
      buf.push(line);
    }
  }
  flush();

  for (const [missing, host] of Object.entries(MERGED_INTO)) {
    const n = Number(missing);
    const h = blocks.get(host);
    if (!blocks.has(n) && h) blocks.set(n, { number: n, text: h.text, merged: true });
  }
  return blocks;
}

/**
 * The Arabic for a list of paragraph numbers, in reading order.
 *
 * A number that merged into an earlier block is emitted once — asking for both 510
 * and 511 must not print the same paragraph to the reader twice.
 */
export function joinParagraphs(
  blocks: Map<number, ArabicParagraph>,
  numbers: number[],
): { number: number; text: string; merged: boolean }[] {
  const seen = new Set<string>();
  const out: { number: number; text: string; merged: boolean }[] = [];
  for (const n of [...new Set(numbers)].sort((a, b) => a - b)) {
    const p = blocks.get(n);
    if (!p || seen.has(p.text)) continue;
    seen.add(p.text);
    out.push({ number: n, text: p.text, merged: Boolean(p.merged) });
  }
  return out;
}

/** The alignment sidecar, keyed by chapter. Absent means the feature is simply off. */
export function loadAlignment(
  bookDir: string,
): Map<string, { pairs: AlignmentPair[]; sourceParaRange: number[] }> {
  const out = new Map<string, { pairs: AlignmentPair[]; sourceParaRange: number[] }>();
  const path = join(bookDir, "_system", "arabic-alignment.json");
  if (!existsSync(path)) return out;
  try {
    const doc = JSON.parse(readFileSync(path, "utf8"));
    for (const ch of doc?.chapters ?? []) {
      out.set(ch.chapter_key, {
        pairs: ch.pairs ?? [],
        sourceParaRange: ch.source_para_range ?? [],
      });
    }
  } catch {
    return new Map();
  }
  return out;
}

/**
 * Which runs in this book are canonical scripture.
 *
 * The same provenance the PDF and the live reader use — `book-arabic-audit.json`
 * rows resolved to the mushaf — so a verse in the reveal is set in the Uthmanic
 * face by the same rule that sets it on the printed page.
 */
export function quranicSkeletons(bookDir: string): Set<string> {
  const path = join(bookDir, "_system", "book-arabic-audit.json");
  if (!existsSync(path)) return new Set();
  try {
    const doc = JSON.parse(readFileSync(path, "utf8"));
    const rows = doc?.runs ?? doc?.findings ?? [];
    return new Set(
      rows
        .filter((r: { resolution?: string }) => r?.resolution === "canonical-mushaf")
        .map((r: { skeleton?: string; text?: string }) => r.skeleton ?? r.text ?? "")
        .filter(Boolean),
    );
  } catch {
    return new Set();
  }
}
