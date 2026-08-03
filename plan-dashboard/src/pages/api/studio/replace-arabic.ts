/**
 * replace-arabic.ts — the Book Composer's "Replace with Arabic" action.
 *
 * POST { slug, text } — a PURE TRANSFORM. Returns { text, replaced, unavailable }
 * and writes nothing. The Composer applies the result to the live editor and its
 * own autosave persists it, exactly as the Diacritics action does.
 *
 * It used to write book.md server-side and reload the page. That is the RCA-002
 * shape — a file write underneath a live editor — and it is also what made the
 * button feel broken: the page bounced, and on a book whose glossary cannot
 * reach the words on screen, nothing changed and nothing said why.
 *
 * `unavailable` is what says why: the terms the passage sets as foreign that
 * this book has no Arabic for. On `al-anwaar-al-lateefah` that is most of the
 * page, because it has no Arabic scan to fill a glossary from.
 *
 * POST { slug } with no text runs the whole book through the file-writing pass —
 * the same function compose step 5a-substitute calls, kept for scripting.
 */
import type { APIRoute } from "astro";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { findContentDirSync } from "../../../lib/content-paths";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { runPythonJson } from "../../../lib/intake-cli";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
/** A chapter of a long book, with headroom. Guards the spawn, not the prose. */
const MAX_TEXT = 200_000;

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }
  const slug = String(body.slug ?? "").trim();
  const text = typeof body.text === "string" ? body.text : "";
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (text.length > MAX_TEXT) return apiError("Passage too long");

  const bookDir = findContentDirSync(slug);
  if (!bookDir) return apiError(`Book not found: ${slug}`, 404);
  if (!existsSync(join(bookDir, "book", "book.md")))
    return apiError("book.md not found", 404);

  try {
    const result = (await runPythonJson(
      "_book_substitution.py",
      text ? [slug, "--stdin"] : [slug],
      text || undefined,
    )) as {
      ok?: boolean;
      error?: string;
      text?: string;
      replaced?: number;
      unavailable?: string[];
    };
    if (!result?.ok) return apiError(result?.error ?? "Substitution failed");
    return apiOk({
      slug,
      text: result.text ?? "",
      replaced: result.replaced ?? 0,
      unavailable: result.unavailable ?? [],
    });
  } catch (e) {
    return apiServerError(`Substitution failed: ${String(e)}`);
  }
};
