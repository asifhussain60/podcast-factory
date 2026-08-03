/**
 * replace-arabic.ts — the Book Composer's "Replace with Arabic" action.
 *
 * POST { slug, chapterKey? } — run scripts/podcast/_book_substitution.py and
 * return { replaced, terms }. Every romanized glossary term in the chapter's
 * prose becomes its Arabic script, and an `amal (عَمَل)` collapses to `عَمَل`.
 *
 * IN-REQUEST, unlike Rearticulate. That action detaches because a long chapter
 * windows into several `claude -p` calls at a 900 s timeout each; this one is
 * deterministic, glossary-driven and finishes in milliseconds, so detaching it
 * would buy a status file and a polling loop for nothing.
 *
 * THE BUTTON IS A FALLBACK. The same function runs as compose step
 * `5a-substitute` over every chapter of every book (see _book_apparatus.py), so
 * a composed book already arrives substituted; this is for a chapter edited by
 * hand afterwards. One code path, so the two can never drift — the same contract
 * Rearticulate has with the automatic fluency pass.
 */
import type { APIRoute } from "astro";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { runPythonJson } from "../../../lib/intake-cli";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const POST: APIRoute = async ({ request }) => {
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
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  if (!existsSync(join(bookDir, "book", "book.md")))
    return apiError("book.md not found", 404);

  try {
    const args = [slug];
    if (chapterKey) args.push("--chapter-key", chapterKey);
    const result = (await runPythonJson("_book_substitution.py", args)) as {
      ok?: boolean;
      error?: string;
      replaced?: number;
      terms?: number;
    };
    if (!result?.ok) return apiError(result?.error ?? "Substitution failed");
    return apiOk({
      slug,
      chapterKey: chapterKey || null,
      replaced: result.replaced ?? 0,
      terms: result.terms ?? 0,
    });
  } catch (e) {
    return apiServerError(`Substitution failed: ${String(e)}`);
  }
};
