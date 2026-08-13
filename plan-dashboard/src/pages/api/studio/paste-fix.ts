/**
 * paste-fix.ts — the Book Composer's "Paste & Fix Chapter" action.
 *
 * A Sessions-lane chapter Asif copies out, edits somewhere else, and pastes
 * back in loses the things a hand-off rewrite already loses through
 * pf-compose-articulator: the chapter's inline lecture-slide images (plain
 * text carries no image reference forward), the book's house citation/
 * heading style, paragraph shape, and sometimes the connective explanation
 * a student needs. This route runs the SAME engine that skill uses — nothing
 * reimplemented — against text pasted into a dedicated box, never against
 * the live rich-text editor, so a broken paste can never reach book.md
 * through autosave before it has been fixed.
 *
 * POST { slug, chapterKey, chapterTitle, pastedMarkdown }
 *   Check only — never writes. Shells out to
 *   `compose_articulate.py <slug> <chapterTitle> --json --stdin`, the exact
 *   CLI pf-compose-articulator uses, fed the pasted text over stdin instead
 *   of a hand-off file. The Compose button opts into the gated Scholar
 *   continuity pass and the student-reader readability lens because the user
 *   is reviewing the result before Apply. The student-reader pass is dry-run
 *   only: it writes no Companion cards.
 *   Returns the engine's own result: restored images, paragraph repairs,
 *   formatting changes, Scholar continuity outcome, student-reader questions,
 *   the fidelity-gate findings, and the fixed body.
 *   `chapterTitle` (not `chapterKey`) is what the Python side resolves by —
 *   see compose_articulate.resolve_chapter, which matches book.md's own
 *   heading text. Refuses (404) on any book that is not Sessions-lane,
 *   exactly as the CLI itself refuses.
 *
 * PUT { slug, chapterKey, markdown }
 *   Apply — writes the ALREADY-FIXED body (what the POST step returned,
 *   after the human reviewed it) through writeChapterBody, the same writer
 *   book-md.ts uses for every other Compose save. Then re-runs the book's
 *   Arabic audit so a restored citation's gold chapter-and-verse header is
 *   correct the moment the page reloads — book-md.ts's route is generic and
 *   does neither the Sessions-lane resolution nor the audit re-run, which is
 *   why this stays its own route rather than becoming a second caller of it.
 */
import type { APIRoute } from "astro";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { runPythonJson } from "../../../lib/intake-cli";
import { writeChapterBody } from "../../../lib/reader/book-md-write";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function requireSessionsLane(bookDir: string): boolean {
  return existsSync(join(bookDir, "_system", "sessions-articulation.json"));
}

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  const chapterTitle = String(body.chapterTitle ?? "").trim();
  const pastedMarkdown = String(body.pastedMarkdown ?? "");

  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!chapterTitle) return apiError("Missing chapterTitle");
  if (!pastedMarkdown.trim())
    return apiError("Nothing pasted — paste the edited chapter first");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  if (!requireSessionsLane(bookDir)) {
    return apiError(
      "Paste & Fix only applies to Sessions-lane books (a lecture transcript) — " +
        "this book has a real source to stay faithful to instead.",
      404,
    );
  }

  try {
    const result = await runPythonJson(
      "compose_articulate.py",
      [
        slug,
        chapterTitle,
        "--json",
        "--stdin",
        "--scholar-continuity",
        "--student-readability",
      ],
      pastedMarkdown,
    );
    return apiOk(result);
  } catch (e) {
    return apiServerError(`Check failed: ${String((e as Error).message ?? e)}`);
  }
};

export const PUT: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  const chapterKey = String(body.chapterKey ?? "")
    .trim()
    .toLowerCase();
  const markdown = String(body.markdown ?? "").trim();

  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!chapterKey) return apiError("Missing chapterKey");
  if (!markdown) return apiError("Nothing to save");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  if (!requireSessionsLane(bookDir))
    return apiError("Not a Sessions-lane book", 404);

  try {
    const res = writeChapterBody(bookDir, chapterKey, markdown);
    if (!res.ok) return apiError(res.error ?? "Save failed", 404);

    // Best-effort: a citation's gold header stays correct as of the LAST
    // audit if this fails, which is a stale label, never a broken page —
    // the save above already succeeded and is what matters most.
    let audited = true;
    try {
      await runPythonJson("_book_arabic_audit.py", [bookDir, "--json"]);
    } catch {
      audited = false;
    }

    return apiOk({ slug, chapterKey, audited });
  } catch (e) {
    return apiServerError(`Save failed: ${String(e)}`);
  }
};
