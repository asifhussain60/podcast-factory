/**
 * book-md-write.ts — the ONE writer of a chapter body into `book/book.md`.
 *
 * Extracted from the PUT /api/studio/book-md route (2026-07-21) when a second
 * caller appeared: the Arabic vowelling review, which applies accepted diacritics
 * to a chapter. Those marks are PDF-bound, and the repo's locked rule is that the
 * Book Composer is the singular path for PDF-bound chapter changes — a rule that
 * only means anything if there is literally one function doing the writing.
 *
 * Everything the route used to do inline happens here, in the same order and for
 * the same reasons: locate the chapter by its heading key, take a one-time
 * `book.md.bak`, carry the pipeline's machine fences across the edit, rewrite the
 * file, and record the durable sidecar entry that `scripts/podcast/_book_edits.py`
 * replays as the final step of every compose. Skip any one of those and an edit
 * survives only until the next pipeline run.
 */
import { readFileSync, writeFileSync, existsSync, copyFileSync } from "node:fs";
import { join } from "node:path";
import { anchorKey } from "../../../scripts/lib/anchor-key.mjs";
import { preserveFences, editionIntroDelta } from "./book-fences";
import { recordComposerEdit, baseFingerprintFor } from "./composer-edits";

export interface ChapterWriteResult {
  ok: boolean;
  /** Set when the write could not proceed; the caller turns it into a 404/400. */
  error?: string;
  path?: string;
  /** What preserveFences() carried across, for the caller's response envelope. */
  fences?: ReturnType<typeof preserveFences>;
  /** Sidecar outcome. A sidecar failure never fails the write — book.md is
   *  already saved and is what the Composer previews — but it IS reported, because
   *  an edit that did not reach the sidecar will not survive the next compose. */
  sidecar?: { ok: boolean; error?: string };
  /** The body as it stood before this write. Callers that need to reason about
   *  what changed (the vowelling review does) get it without re-reading the file. */
  previousBody?: string;
}

/**
 * Replace ONE chapter's body in book.md, leaving its `## Heading` line and every
 * other chapter untouched.
 *
 * `chapterKey` is the normalized heading key from the shared `anchorKey`;
 * `markdown` is the chapter body only, with no heading line.
 */
export function writeChapterBody(
  bookDir: string,
  chapterKey: string,
  markdown: string,
): ChapterWriteResult {
  const bookMd = join(bookDir, "book", "book.md");
  if (!existsSync(bookMd)) return { ok: false, error: "book.md not found" };

  const lines = readFileSync(bookMd, "utf-8").split("\n");
  // Locate the target chapter's heading and the start of the next chapter. A
  // heading inside an edition-intro span is skipped: that is the edition's front
  // matter, whose `## Introduction` heading lives inside the fenced span, and it
  // is stripped and re-authored on every compose — so an edit addressed to it
  // could never survive, and this writer refuses to record one.
  let start = -1;
  let end = lines.length;
  let introDepth = 0;
  for (let i = 0; i < lines.length; i += 1) {
    introDepth += editionIntroDelta(lines[i]);
    if (introDepth > 0) continue;
    if (!/^##\s+/.test(lines[i])) continue;
    if (start === -1 && anchorKey(lines[i]) === chapterKey) start = i;
    else if (start !== -1) {
      end = i;
      break;
    }
  }
  if (start === -1)
    return { ok: false, error: `Chapter not found: ${chapterKey}` };

  if (!existsSync(`${bookMd}.bak`)) copyFileSync(bookMd, `${bookMd}.bak`);

  const head = lines.slice(0, start + 1); // through the heading line
  const tail = lines.slice(end); // from the next heading (or EOF)

  // Keep the pipeline's machine fences (editorial / bridge / study-summary) alive
  // across this edit. A rich-text round trip cannot carry an HTML comment, so
  // without this the markers are stripped and the Python phases silently stop
  // protecting and stop replacing those asides. See book-fences.ts.
  const previousBody = lines.slice(start + 1, end).join("\n");
  const fences = preserveFences(previousBody, markdown);

  const rebuilt = [...head, "", fences.body, "", ...tail]
    .join("\n")
    .replace(/\n{3,}/g, "\n\n");
  writeFileSync(bookMd, rebuilt.endsWith("\n") ? rebuilt : `${rebuilt}\n`);

  // DURABILITY — the sidecar, written alongside book.md. book.md alone is not
  // durable: compose_book_v2 regenerates its layers (base -> augment -> voice) on
  // every run, so an edit here survives only until anything upstream re-runs, and
  // vanishes with no report. `baseFingerprint` identifies the COMPOSE this edit
  // was made against, so a later replay can tell the author the pipeline moved
  // underneath their edit instead of silently choosing one over the other.
  //
  // It is read from the pipeline's own stamp rather than hashed from
  // `previousBody`. Hashing here was the bug: `previousBody` is the live body,
  // introduction and comprehension bridges included, and the replay compares
  // against the composed body from before either is injected — so the numbers
  // could never match and the conflict warning was permanently on.
  let sidecar: { ok: boolean; error?: string };
  try {
    recordComposerEdit(bookDir, {
      chapterKey,
      bodyMd: fences.body,
      baseFingerprint: baseFingerprintFor(bookDir, chapterKey),
      savedAt: new Date().toISOString(),
    });
    sidecar = { ok: true };
  } catch (e) {
    sidecar = { ok: false, error: String(e) };
  }

  return { ok: true, path: bookMd, fences, sidecar, previousBody };
}
