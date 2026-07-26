/**
 * composer-edits.ts — durable Book Composer edits (TS side of the sidecar).
 *
 * TS counterpart of `scripts/podcast/_book_edits.py`. Both sides read and write
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
import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";

export const SIDECAR_NAME = "composer-edits.json";
const SCHEMA = "podcast.composer-edits/v1";

/**
 * The pipeline's per-chapter fingerprint stamp, written by
 * `_book_edits.apply_composer_edits` at the end of every compose.
 *
 * This side does NOT hash anything, and that is the fix. It used to hash the body
 * it read out of the LIVE `book.md`, while the Python replay hashed the composed
 * body several steps earlier — before the edition introduction and the
 * comprehension bridges are injected. The two could never agree for any chapter
 * carrying either, so every such chapter reported a conflict on every compose, and
 * all eight reported on 2026-07-21 were noise. Quoting the pipeline's own number
 * instead of computing a second one retires the whole class: one computation, in
 * one language, read by both sides.
 */
const BASE_STAMP_NAME = "composer-base.json";

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
 * The pipeline's composed fingerprint for one chapter, or "" when this book has
 * not composed since the stamp existed. "" means UNKNOWN, and replay treats an
 * unknown as "no conflict" rather than guessing at one.
 */
export function baseFingerprintFor(
  bookDir: string,
  chapterKey: string,
): string {
  const path = join(bookDir, "_system", BASE_STAMP_NAME);
  if (!existsSync(path)) return "";
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as {
      chapters?: Record<string, string>;
    };
    return String(parsed?.chapters?.[chapterKey] ?? "");
  } catch {
    return "";
  }
}

function sidecarPath(bookDir: string): string {
  return join(bookDir, "_system", SIDECAR_NAME);
}

/**
 * Read the sidecar, THROWING when it exists but cannot be parsed.
 *
 * It used to return an empty list instead, and `recordComposerEdit` then wrote
 * that empty list straight back — so a single unparseable file discarded every
 * edit the author had ever made. Both sides also wrote non-atomically, which is
 * precisely how a crash mid-write manufactures the corrupt file that triggers the
 * wipe. Refusing costs the author one save; guessing cost them the whole sidecar.
 */
function loadSidecar(bookDir: string): Sidecar {
  const path = sidecarPath(bookDir);
  if (!existsSync(path)) return { schema: SCHEMA, edits: [] };
  let parsed: Partial<Sidecar>;
  try {
    parsed = JSON.parse(readFileSync(path, "utf8")) as Partial<Sidecar>;
  } catch (e) {
    throw new Error(
      `${SIDECAR_NAME} is not readable JSON — refusing to overwrite it`,
      { cause: e },
    );
  }
  if (!parsed || !Array.isArray(parsed.edits))
    throw new Error(
      `${SIDECAR_NAME} does not hold a v1 edits list — refusing to overwrite it`,
    );
  return { schema: SCHEMA, edits: parsed.edits as ComposerEdit[] };
}

/** Write via temp file + rename, so a crash cannot leave a half-written sidecar. */
function writeAtomic(path: string, payload: Sidecar): void {
  const tmp = `${path}.tmp`;
  writeFileSync(tmp, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  renameSync(tmp, path);
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
  writeAtomic(path, { schema: SCHEMA, edits: kept });
  return path;
}
