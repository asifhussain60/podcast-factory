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
 *   is reviewing the result before Apply. The student-reader pass prepares
 *   proposed Companion cards but writes none during this check step.
 *   Returns the engine's own result: restored images, paragraph repairs,
 *   formatting changes, Scholar continuity outcome, proposed Companion cards,
 *   the fidelity-gate findings, and the fixed body.
 *   `chapterTitle` (not `chapterKey`) is what the Python side resolves by —
 *   see compose_articulate.resolve_chapter, which matches book.md's own
 *   heading text. Refuses (404) on any book that is not Sessions-lane,
 *   exactly as the CLI itself refuses.
 *
 * PUT { slug, chapterKey, markdown, companionNotes? }
 *   Apply — writes the ALREADY-FIXED body (what the POST step returned,
 *   after the human reviewed it) through writeChapterBody, the same writer
 *   book-md.ts uses for every other Compose save. Then re-runs the book's
 *   Arabic audit so a restored citation's gold chapter-and-verse header is
 *   correct the moment the page reloads — book-md.ts's route is generic and
 *   does neither the Sessions-lane resolution nor the audit re-run, which is
 *   why this stays its own route rather than becoming a second caller of it.
 */
import type { APIRoute } from "astro";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { runPythonJson } from "../../../lib/intake-cli";
import { writeChapterBody } from "../../../lib/reader/book-md-write";
import { upsertNote } from "../../../lib/reader/companion/store.server";
import type { CompanionNoteInput } from "../../../lib/reader/companion/types";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const STUDENT_NOTE_ID_RE = /^student:[0-9a-f]{16}$/;

function requireSessionsLane(bookDir: string): boolean {
  return existsSync(join(bookDir, "_system", "sessions-articulation.json"));
}

function applyQuoteKindDeclarations(
  bookDir: string,
  chapterKey: string,
  declarations: unknown,
): number {
  if (!Array.isArray(declarations) || declarations.length === 0) return 0;
  const kept: Record<string, "hadith" | "poem" | "quote"> = {};
  for (const declaration of declarations) {
    if (!declaration || typeof declaration !== "object") continue;
    const firstLine = String(
      (declaration as { first_line?: unknown }).first_line ?? "",
    ).trim();
    const kind = String((declaration as { kind?: unknown }).kind ?? "").trim();
    if (!firstLine || !["hadith", "poem", "quote"].includes(kind)) continue;
    kept[firstLine] = kind as "hadith" | "poem" | "quote";
  }
  if (Object.keys(kept).length === 0) return 0;

  const path = join(bookDir, "_system", "quote-kind.json");
  let raw: {
    schema?: string;
    chapters?: Record<string, Record<string, unknown>>;
  };
  try {
    raw = existsSync(path)
      ? JSON.parse(readFileSync(path, "utf-8"))
      : { schema: "book.quote-kind/v1", chapters: {} };
  } catch {
    raw = { schema: "book.quote-kind/v1", chapters: {} };
  }
  raw.schema = "book.quote-kind/v1";
  raw.chapters =
    raw.chapters && typeof raw.chapters === "object" ? raw.chapters : {};
  const chapter = raw.chapters[chapterKey] ?? {};
  raw.chapters[chapterKey] = { ...chapter, ...kept };
  writeFileSync(path, `${JSON.stringify(raw, null, 2)}\n`, "utf-8");
  return Object.keys(kept).length;
}

function applyCompanionNotes(
  slug: string,
  chapterKey: string,
  markdown: string,
  notes: unknown,
): number {
  if (!Array.isArray(notes) || notes.length === 0) return 0;
  let filed = 0;
  for (const raw of notes) {
    if (!raw || typeof raw !== "object") continue;
    const note = raw as Record<string, unknown>;
    const id = String(note.id ?? "").trim();
    const body = String(note.body ?? "").trim();
    const quote = String(note.quote ?? "").trim();
    if (!STUDENT_NOTE_ID_RE.test(id) || !body || !quote) continue;
    if (!markdown.includes(quote)) continue;
    const etymology = Array.isArray(note.etymology)
      ? note.etymology.filter((e): e is string => typeof e === "string")
      : undefined;
    const ref =
      note.source &&
      typeof note.source === "object" &&
      typeof (note.source as { ref?: unknown }).ref === "string"
        ? (note.source as { ref: string }).ref
        : undefined;
    const input: CompanionNoteInput = {
      id,
      kind: "explanation",
      body,
      anchor: String(note.anchor ?? "").trim() || undefined,
      quote,
      etymology,
      review: "proposed",
      source: {
        provider: "scholar",
        label: "Ismaili Scholar",
        ref,
      },
    };
    upsertNote(slug, chapterKey, input);
    filed += 1;
  }
  return filed;
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
    const quoteKindDeclarations = applyQuoteKindDeclarations(
      bookDir,
      chapterKey,
      body.quoteKindDeclarations,
    );
    const companionNotes = applyCompanionNotes(
      slug,
      chapterKey,
      markdown,
      body.companionNotes,
    );

    // Best-effort: a citation's gold header stays correct as of the LAST
    // audit if this fails, which is a stale label, never a broken page —
    // the save above already succeeded and is what matters most.
    let audited = true;
    try {
      await runPythonJson("_book_arabic_audit.py", [bookDir, "--json"]);
    } catch {
      audited = false;
    }

    return apiOk({
      slug,
      chapterKey,
      audited,
      quoteKindDeclarations,
      companionNotes,
    });
  } catch (e) {
    return apiServerError(`Save failed: ${String(e)}`);
  }
};
