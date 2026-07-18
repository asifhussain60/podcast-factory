/**
 * Companion notes API — the browser↔disk boundary for the reader's private notes.
 *
 *   GET    /api/studio/companion-notes?slug=X&chapter=Y   — read one chapter's notes
 *   GET    /api/studio/companion-notes?slug=X&list=1      — chapters that have notes (+counts)
 *   POST   /api/studio/companion-notes  {slug, chapter, note}
 *                                                         — create (no note.id) or update (note.id)
 *   DELETE /api/studio/companion-notes?slug=X&chapter=Y&id=Z  — remove one note
 *
 * The store writes JSON under _system/companion-notes/ (git-tracked, cross-machine).
 * Mirrors the shape/guards of api/studio/editorial.ts.
 */
import type { APIRoute } from "astro";
import {
  readChapter,
  upsertNote,
  deleteNote,
  listChapters,
} from "../../../lib/reader/companion/store.server";
import { CHAPTER_KEY_RE } from "../../../lib/reader/companion/keys";
import type { CompanionNoteInput } from "../../../lib/reader/companion/types";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const slug = url.searchParams.get("slug");
  if (!slug || !SLUG_RE.test(slug)) return apiError("Missing or invalid slug");
  try {
    if (url.searchParams.get("list") === "1") {
      return apiOk({ slug, chapters: listChapters(slug) });
    }
    const chapter = url.searchParams.get("chapter");
    if (!chapter || !CHAPTER_KEY_RE.test(chapter))
      return apiError("Missing or invalid chapter");
    return apiOk(readChapter(slug, chapter));
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { slug?: string; chapter?: string; note?: CompanionNoteInput };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }
  const { slug, chapter, note } = body;
  if (!slug || !SLUG_RE.test(slug)) return apiError("Missing or invalid slug");
  if (!chapter || !CHAPTER_KEY_RE.test(chapter))
    return apiError("Missing or invalid chapter");
  if (!note || typeof note.body !== "string" || !note.body.trim())
    return apiError("Missing note body");
  if (!note.kind || typeof note.kind !== "string")
    return apiError("Missing note kind");
  try {
    const { note: saved } = upsertNote(slug, chapter, note);
    return apiOk(saved);
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const DELETE: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const slug = url.searchParams.get("slug");
  const chapter = url.searchParams.get("chapter");
  const id = url.searchParams.get("id");
  if (!slug || !SLUG_RE.test(slug)) return apiError("Missing or invalid slug");
  if (!chapter || !CHAPTER_KEY_RE.test(chapter))
    return apiError("Missing or invalid chapter");
  if (!id) return apiError("Missing note id");
  try {
    return apiOk(deleteNote(slug, chapter, id));
  } catch (e) {
    return apiServerError(String(e));
  }
};
