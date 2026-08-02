/**
 * text-align.mjs — read a book's per-paragraph alignment.
 *
 * Same reasoning as text-colour.mjs, and the same promise: book.md is never
 * touched. Markdown has no alignment syntax, the print renderer escapes raw
 * HTML, and inventing a syntax would put new delimiters into the file every
 * Python phase reads as text. So the choice lives in `_system/text-align.json`
 * and is applied at RENDER time.
 *
 * The KEY is different from text-colour's, and deliberately. A colour lands on
 * a run the human highlighted, so it is anchored by the quoted words. Alignment
 * lands on a whole PARAGRAPH, which already has a stable name: the fingerprint
 * in para-blocks.mjs, whitespace-collapsed so a re-wrap does not rename it, and
 * mirrored into Python so the aligner and the Composer cannot disagree about
 * which paragraph is which. Re-using it means alignment is keyed by the same
 * name the Arabic reveal already uses, rather than by a second idea of what a
 * paragraph is.
 *
 * `left` is never stored: it is what a paragraph does with no class at all, so
 * recording it would be a second declaration that has to agree with the first.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/** Mirrors TEXT_ALIGNMENTS in src/lib/reader/text-align.ts — ids only, because
 *  a plain .mjs cannot import the TypeScript. `left` is absent on purpose: see
 *  the header. An unknown value is dropped rather than trusted into a class. */
export const ALIGN_IDS = ["center", "right"];

/**
 * `_system/text-align.json` → { chapterKey: { paraFingerprint: align } }.
 *
 * `bookDir` is the book's root (the folder holding `_system/` and `book/`).
 * Anything unreadable, absent or malformed yields {} — an edition renders with
 * its default alignment rather than failing to render.
 */
export function readTextAlign(bookDir) {
  const p = path.join(bookDir, "_system", "text-align.json");
  if (!existsSync(p)) return {};
  try {
    const raw = JSON.parse(readFileSync(p, "utf-8"));
    const out = {};
    for (const [chapter, paras] of Object.entries(raw?.chapters ?? {})) {
      if (!paras || typeof paras !== "object") continue;
      const kept = {};
      for (const [key, align] of Object.entries(paras)) {
        if (ALIGN_IDS.includes(align)) kept[key] = align;
      }
      if (Object.keys(kept).length) out[chapter] = kept;
    }
    return out;
  } catch {
    return {};
  }
}

/** Every chapter's alignments flattened into ONE fingerprint -> align map.
 *
 *  The print renderer walks the whole book in one pass and sees paragraphs, not
 *  chapters, at the point it decides a paragraph's classes. Flattening is safe
 *  where keying by text would not be: a fingerprint is of the paragraph's own
 *  content, so two chapters can only collide by containing a byte-identical
 *  paragraph — in which case they are the same paragraph and want the same
 *  alignment. */
export function flattenAlign(byChapter) {
  const flat = {};
  for (const paras of Object.values(byChapter ?? {}))
    Object.assign(flat, paras);
  return flat;
}
