/**
 * text-colour.mjs — read a book's per-selection text colours, and paint them
 * into rendered HTML.
 *
 * WHY A SIDECAR, and not markup in book.md. Colour has no markdown syntax, and
 * the print renderer escapes raw HTML, so a coloured span written into the file
 * would print as literal `&lt;span&gt;`. Inventing a syntax was the other option
 * and is the dangerous one: every Python phase in the pipeline reads book.md as
 * text — the Arabic audit matches its runs against it BYTE FOR BYTE, and the
 * vowelling, glossary-overlay and inline-Arabic passes all regex over it. New
 * delimiters landing inside an Arabic run would break the provenance guarantees
 * that are the most protected thing in this repo.
 *
 * So book.md is never touched. `_system/text-colour.json` records what was
 * coloured, quoted verbatim, and the colour is re-found and applied at RENDER
 * time — the same shape `_book_bridges` and the Composer-edit replay already
 * use, and the same quoted-passage anchoring the Companion notes use.
 *
 * The failure mode is honest: edit the words and the quote no longer matches, so
 * the colour simply does not apply. Nothing is guessed into a neighbouring
 * sentence, and nothing is silently written back into the source.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { flatten, findPassage } from "./passage-match.mjs";

/** Mirrors TEXT_INK_IDS in src/lib/reader/text-ink.ts — ids only, because a
 *  plain .mjs cannot import the TypeScript and the display names are of no use
 *  here. An unknown id is dropped rather than trusted into a class name. */
export const TEXT_INK_IDS = ["maroon", "ink", "indigo", "forest", "brown"];

/**
 * `_system/text-colour.json` → { chapterKey: [{ quote, ink }, ...] }.
 *
 * `bookDir` is the book's root (the folder holding `_system/` and `book/`).
 * Anything unreadable, absent or malformed yields {} — an edition renders
 * uncoloured rather than failing to render.
 */
export function readTextColours(bookDir) {
  const p = path.join(bookDir, "_system", "text-colour.json");
  if (!existsSync(p)) return {};
  try {
    const raw = JSON.parse(readFileSync(p, "utf-8"));
    const out = {};
    for (const [key, spans] of Object.entries(raw?.chapters ?? {})) {
      if (!Array.isArray(spans)) continue;
      const kept = spans.filter(
        (s) =>
          s &&
          typeof s.quote === "string" &&
          s.quote.trim().length >= 4 &&
          TEXT_INK_IDS.includes(s.ink),
      );
      if (kept.length) out[key] = kept;
    }
    return out;
  } catch {
    return {};
  }
}

/** Text segments of an HTML string, with their offsets — never the inside of a
 *  tag. Same split `renderInline`'s Arabic isolation uses, for the same reason:
 *  a match must never land in an attribute. */
function htmlChunks(html) {
  const chunks = [];
  const re = /<[^>]+>|[^<]+/g;
  let m;
  while ((m = re.exec(html))) {
    if (m[0].startsWith("<")) continue;
    chunks.push({ text: m[0], at: m.index });
  }
  return chunks;
}

/**
 * Wrap every recorded passage of one chapter in `<span class="ink-NAME">`.
 *
 * Splices back to front so an earlier span's offsets stay valid. A passage that
 * crosses inline markup comes back as one range PER text segment, so it is
 * wrapped as several spans that each sit inside one element — never one span
 * across a tag boundary, which would be crossed markup in a printed book.
 */
export function applyTextColours(html, spans) {
  if (!spans?.length || !html) return html;
  /** @type {{from: number, to: number, ink: string}[]} */
  const edits = [];
  for (const s of spans) {
    // Defence in depth: readTextColours already drops an unknown ink, but this
    // is the function that interpolates one into a class name.
    if (!TEXT_INK_IDS.includes(s?.ink)) continue;
    // `to` is EXCLUSIVE (passage-match builds `to: last + 1`), the same
    // convention the DOM and ProseMirror callers rely on. Adding one here
    // reached a character past the text segment, which for a passage crossing
    // inline markup was the "<" of the next tag — and spliced a span across it,
    // producing crossed markup in a printed book.
    for (const r of findPassage(flatten(htmlChunks(html)), s.quote)) {
      if (r.to > r.from) edits.push({ from: r.from, to: r.to, ink: s.ink });
    }
  }
  // Overlaps would nest one span inside another's splice and corrupt both. The
  // first colour applied to a stretch of text wins; a later one covering the
  // same characters is dropped, which is what "the last thing I coloured it"
  // means once the sidecar is read in order.
  edits.sort((a, b) => a.from - b.from);
  const kept = [];
  let guard = -1;
  for (const e of edits) {
    if (e.from < guard) continue;
    kept.push(e);
    guard = e.to;
  }
  let out = html;
  for (const e of [...kept].reverse()) {
    out =
      out.slice(0, e.from) +
      `<span class="ink-${e.ink}">` +
      out.slice(e.from, e.to) +
      "</span>" +
      out.slice(e.to);
  }
  return out;
}
