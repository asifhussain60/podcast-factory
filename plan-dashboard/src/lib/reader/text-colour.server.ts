/**
 * text-colour.server.ts — the disk side of per-selection text colour.
 *
 * One file per book, `_system/text-colour.json`, keyed by the chapter's
 * `anchorKey` — the same key the Composer already stores edits and figure
 * placements under, so a chapter has ONE identity across every sidecar rather
 * than one per feature.
 *
 *   { schema, chapters: { "<anchorKey>": [ { quote, ink }, ... ] } }
 *
 * Reading it back and painting it is scripts/lib/text-colour.mjs, shared with
 * the PDF build. This module only writes; the two must agree about the shape,
 * and the shape is deliberately the smallest thing that could work — a verbatim
 * quote and a palette id, no offsets. Offsets would be invalidated by the next
 * word anyone types; a quote either still exists or honestly does not.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../content-paths";
import { TEXT_INK_IDS } from "./text-ink";

export const TEXT_COLOUR_SCHEMA = "book.text-colour/v1";

export interface TextColourSpan {
  /** The coloured text, verbatim, as it read when the colour was applied. */
  quote: string;
  ink: string;
}
export interface TextColourDoc {
  schema: string;
  chapters: Record<string, TextColourSpan[]>;
}

/** Below this a quote is not a passage, it is a coincidence — `findPassage`
 *  refuses to match one, so storing it would create a record that can never
 *  apply and can never be explained. */
const MIN_QUOTE = 4;

function filePath(slug: string): string | null {
  const dir = findContentDirSync(slug);
  return dir ? join(dir, "_system", "text-colour.json") : null;
}

function clean(spans: unknown): TextColourSpan[] {
  if (!Array.isArray(spans)) return [];
  const out: TextColourSpan[] = [];
  const seen = new Set<string>();
  for (const s of spans) {
    const quote = typeof s?.quote === "string" ? s.quote.trim() : "";
    const ink = String(s?.ink ?? "");
    if (quote.length < MIN_QUOTE || !TEXT_INK_IDS.includes(ink)) continue;
    // The same passage recorded twice would paint one span inside another's
    // splice at render time. Last write wins, which is what re-colouring a run
    // you already coloured means.
    const key = quote.replace(/\s+/g, " ").toLowerCase();
    if (seen.has(key))
      out.splice(
        out.findIndex(
          (x) => x.quote.replace(/\s+/g, " ").toLowerCase() === key,
        ),
        1,
      );
    seen.add(key);
    out.push({ quote, ink });
  }
  return out;
}

export function readColours(slug: string): TextColourDoc {
  const p = filePath(slug);
  const empty: TextColourDoc = { schema: TEXT_COLOUR_SCHEMA, chapters: {} };
  if (!p || !existsSync(p)) return empty;
  try {
    const raw = JSON.parse(readFileSync(p, "utf8"));
    const chapters: Record<string, TextColourSpan[]> = {};
    for (const [k, v] of Object.entries(raw?.chapters ?? {})) {
      const kept = clean(v);
      if (kept.length) chapters[k] = kept;
    }
    return { schema: TEXT_COLOUR_SCHEMA, chapters };
  } catch {
    return empty; // an unreadable sidecar loses colours, never the chapter
  }
}

/**
 * Replace ONE chapter's spans. Whole-chapter rather than per-span because the
 * client always knows the chapter's full set (it holds them to paint the canvas)
 * and a per-span API would need an id, which a quote already is.
 *
 * An empty array removes the chapter's entry rather than leaving `[]` behind, so
 * a book that has been fully un-coloured reads back exactly like one that never
 * was.
 */
export function writeChapterColours(
  slug: string,
  chapterKey: string,
  spans: unknown,
): TextColourDoc {
  const p = filePath(slug);
  if (!p) throw new Error(`Book not found: ${slug}`);
  const doc = readColours(slug);
  const kept = clean(spans);
  if (kept.length) doc.chapters[chapterKey] = kept;
  else delete doc.chapters[chapterKey];
  mkdirSync(join(p, ".."), { recursive: true });
  writeFileSync(p, JSON.stringify(doc, null, 2) + "\n", "utf8");
  return doc;
}
