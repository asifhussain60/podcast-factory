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
  reanchorNote,
  acceptNote,
  deleteNote,
  listChapters,
} from "../../../lib/reader/companion/store.server";
import { CHAPTER_KEY_RE } from "../../../lib/reader/companion/keys";
import type {
  CompanionNote,
  CompanionNoteInput,
} from "../../../lib/reader/companion/types";
import { morphologyForEtymology } from "../../../lib/db/morphology.server";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** Attach the verified morphology block per etymology row — computed fresh
 *  from the Quranic morphology DB on every read, never persisted, and never
 *  accepted from a client (upsertNote does not know the field). */
const withMorphology = (note: CompanionNote): CompanionNote =>
  note.etymology?.length
    ? { ...note, morphology: morphologyForEtymology(note.etymology) }
    : note;

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
    const doc = readChapter(slug, chapter);
    return apiOk({ ...doc, notes: doc.notes.map(withMorphology) });
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
  if (
    note.etymology !== undefined &&
    (!Array.isArray(note.etymology) ||
      note.etymology.some((e) => typeof e !== "string"))
  )
    return apiError("etymology must be an array of strings");
  try {
    const { note: saved } = upsertNote(slug, chapter, note);
    return apiOk(withMorphology(saved));
  } catch (e) {
    return apiServerError(String(e));
  }
};

/** Re-point a note at the wording its passage now carries. Quote only — the
 *  Composer's write-back after an explained sentence is edited and saved. */
export const PATCH: APIRoute = async ({ request }) => {
  let body: {
    slug?: string;
    chapter?: string;
    id?: string;
    quote?: string;
    review?: string;
  };
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON");
  }
  const { slug, chapter, id, quote, review } = body;
  if (!slug || !SLUG_RE.test(slug)) return apiError("Missing or invalid slug");
  if (!chapter || !CHAPTER_KEY_RE.test(chapter))
    return apiError("Missing or invalid chapter");
  if (!id || typeof id !== "string") return apiError("Missing note id");
  // Accepting shares PATCH with re-anchoring because both are the same kind of
  // request -- one field of one known note -- and both go through a write that
  // touches only that field. `review` is the only accepted value: "kept" is a
  // judgement a person makes, and there is deliberately no route back to
  // "proposed", which only the pass that filed the note may set.
  if (review !== undefined) {
    if (review !== "kept") return apiError("review may only be set to 'kept'");
    try {
      const accepted = acceptNote(slug, chapter, id);
      if (!accepted) return apiError("Unknown note id");
      return apiOk(withMorphology(accepted));
    } catch (e) {
      return apiServerError(String(e));
    }
  }
  if (typeof quote !== "string") return apiError("Missing quote");
  try {
    const saved = reanchorNote(slug, chapter, id, quote);
    if (!saved) return apiError("Unknown note id");
    return apiOk(withMorphology(saved));
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
