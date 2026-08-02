/**
 * text-align.server.ts — the disk side of per-paragraph alignment.
 *
 * One file per book, `_system/text-align.json`, keyed by the chapter's
 * `anchorKey` and then by the paragraph's `paraFingerprint` — the same two names
 * the Composer already stores edits, placements and Arabic alignments under, so
 * a chapter and a paragraph each have ONE identity across every sidecar.
 *
 *   { schema, chapters: { "<anchorKey>": { "<paraFingerprint>": "center" } } }
 *
 * Reading it back and applying it is scripts/lib/text-align.mjs, shared with the
 * PDF build. This module only writes.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../content-paths";
import { isStoredAlign } from "./text-align";

export const TEXT_ALIGN_SCHEMA = "book.text-align/v1";

export interface TextAlignDoc {
  schema: string;
  chapters: Record<string, Record<string, string>>;
}

function filePath(slug: string): string | null {
  const dir = findContentDirSync(slug);
  return dir ? join(dir, "_system", "text-align.json") : null;
}

/** Keep only real fingerprints pointing at real alignments. A `left` never
 *  arrives here — the route turns it into a removal — but an unknown value or a
 *  malformed key is dropped rather than written into a class name. */
function clean(paras: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!paras || typeof paras !== "object") return out;
  for (const [key, align] of Object.entries(paras as Record<string, unknown>)) {
    if (/^[a-f0-9]{16}$/.test(key) && isStoredAlign(align)) out[key] = align;
  }
  return out;
}

export function readAlign(slug: string): TextAlignDoc {
  const p = filePath(slug);
  const empty: TextAlignDoc = { schema: TEXT_ALIGN_SCHEMA, chapters: {} };
  if (!p || !existsSync(p)) return empty;
  try {
    const raw = JSON.parse(readFileSync(p, "utf8"));
    const chapters: Record<string, Record<string, string>> = {};
    for (const [k, v] of Object.entries(raw?.chapters ?? {})) {
      const kept = clean(v);
      if (Object.keys(kept).length) chapters[k] = kept;
    }
    return { schema: TEXT_ALIGN_SCHEMA, chapters };
  } catch {
    return empty; // an unreadable sidecar loses alignments, never the chapter
  }
}

/**
 * Replace ONE chapter's alignments. Whole-chapter rather than per-paragraph
 * because the client always holds the chapter's full map (it paints from it),
 * and an empty map removes the chapter's entry rather than leaving `{}` behind —
 * so a book returned to its defaults reads back like one that never left them.
 */
export function writeChapterAlign(
  slug: string,
  chapterKey: string,
  paras: unknown,
): TextAlignDoc {
  const p = filePath(slug);
  if (!p) throw new Error(`Book not found: ${slug}`);
  const doc = readAlign(slug);
  const kept = clean(paras);
  if (Object.keys(kept).length) doc.chapters[chapterKey] = kept;
  else delete doc.chapters[chapterKey];
  mkdirSync(join(p, ".."), { recursive: true });
  writeFileSync(p, JSON.stringify(doc, null, 2) + "\n", "utf8");
  return doc;
}
