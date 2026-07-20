/**
 * composer-edits.ts — durable Book Composer edits (TS side of the sidecar).
 *
 * TS mirror of `scripts/podcast/_book_edits.py`. Both sides read and write
 * `_system/composer-edits.json`; keep them in sync IN THE SAME COMMIT when either
 * changes, per the repo's TS<->Python mirror rule.
 *
 * Why this exists: the Composer is the singular path for chapter modifications
 * destined for the PDF, and that only holds if an edit outlives the next pipeline
 * run. `book.md` alone does not — `compose_book_v2` regenerates its layers every
 * run. The Python side replays this sidecar as the final compose step.
 *
 * The route writes; nothing here reads it back at request time. Reading is the
 * pipeline's job.
 */
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export const SIDECAR_NAME = "composer-edits.json";
const SCHEMA = "podcast.composer-edits/v1";

export interface ComposerEdit {
  chapter_key: string;
  body_md: string;
  base_fingerprint: string;
  saved_at: string;
}

interface Sidecar {
  schema: string;
  edits: ComposerEdit[];
}

/**
 * Stable hash of a chapter body, whitespace-normalized. Mirror of `fingerprint`
 * in `scripts/podcast/_book_edits.py`.
 *
 * The character classes are spelled out because the two languages disagree at the
 * edges: JavaScript's `\s` counts the BOM as whitespace and Python's `str.split()`
 * does not, while Python splits on U+0085 and the C0 separators and JavaScript
 * does not. Pasted text is exactly where those arrive. A mismatch is not
 * destructive — the edit still wins on replay — but it reports a conflict against
 * the very base the author edited from, which trains people to ignore conflicts.
 */
export function fingerprintBody(text: string): string {
  const normalized = (text ?? "")
    .replace(/\uFEFF/g, "")
    // The C0 separators are the point: Python's str.split() treats them as
    // whitespace, so this mirror has to as well or the two hashes diverge.
    // eslint-disable-next-line no-control-regex
    .split(/[\s\u0085\u001c-\u001f]+/)
    .filter(Boolean)
    .join(" ");
  return createHash("sha256")
    .update(normalized, "utf8")
    .digest("hex")
    .slice(0, 16);
}

function sidecarPath(bookDir: string): string {
  return join(bookDir, "_system", SIDECAR_NAME);
}

function loadSidecar(bookDir: string): Sidecar {
  const path = sidecarPath(bookDir);
  if (!existsSync(path)) return { schema: SCHEMA, edits: [] };
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as Partial<Sidecar>;
    if (!parsed || !Array.isArray(parsed.edits))
      return { schema: SCHEMA, edits: [] };
    return { schema: SCHEMA, edits: parsed.edits as ComposerEdit[] };
  } catch {
    // A corrupt sidecar must not block a save. Starting fresh loses prior entries,
    // but book.md still holds the current text and git holds the history.
    return { schema: SCHEMA, edits: [] };
  }
}

/** Persist one chapter edit. Last write per chapter wins. */
export function recordComposerEdit(
  bookDir: string,
  edit: {
    chapterKey: string;
    bodyMd: string;
    baseFingerprint: string;
    savedAt: string;
  },
): string {
  const data = loadSidecar(bookDir);
  const kept = data.edits.filter((e) => e.chapter_key !== edit.chapterKey);
  kept.push({
    chapter_key: edit.chapterKey,
    body_md: edit.bodyMd,
    base_fingerprint: edit.baseFingerprint,
    saved_at: edit.savedAt,
  });
  const path = sidecarPath(bookDir);
  mkdirSync(join(bookDir, "_system"), { recursive: true });
  writeFileSync(
    path,
    `${JSON.stringify({ schema: SCHEMA, edits: kept }, null, 2)}\n`,
    "utf8",
  );
  return path;
}
