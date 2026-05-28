/**
 * GET  /api/annotations?book=X&chapter=Y   — list annotations for a chapter
 * POST /api/annotations                    — toggle a tag on a paragraph
 * DELETE /api/annotations?id=N             — remove a specific annotation
 */

import type { APIRoute } from 'astro';
import {
  clearChapterAnnotations,
  getChapterAnnotationSnapshot,
  toggleAnnotation,
  deleteAnnotation,
  upsertParagraphNote,
} from '../../lib/db/annotations';
import { apiError, apiOk, apiServerError } from '../../lib/api-responses';

export const prerender = false;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const book = url.searchParams.get('book');
  const chapter = url.searchParams.get('chapter');
  if (!book || !chapter) {
    return apiError('Missing book or chapter param');
  }
  try {
    const snapshot = getChapterAnnotationSnapshot(book, chapter);
    return apiOk(snapshot);
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const PATCH: APIRoute = async ({ request }) => {
  let body: { book: string; chapter: string; paraIdx: number; note: string };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }

  const { book, chapter, paraIdx, note } = body;
  if (!book || !chapter || paraIdx == null || typeof note !== 'string') {
    return apiError('Missing required fields');
  }

  try {
    upsertParagraphNote(book, chapter, paraIdx, note);
    return apiOk({ ok: true });
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { book: string; chapter: string; paraIdx: number; tagId: number; note?: string };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { book, chapter, paraIdx, tagId, note } = body;
  if (!book || !chapter || paraIdx == null || !tagId) {
    return apiError('Missing required fields');
  }
  try {
    const result = toggleAnnotation(book, chapter, paraIdx, tagId, note);
    return apiOk(result);
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const DELETE: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const book = url.searchParams.get('book');
  const chapter = url.searchParams.get('chapter');
  const id = Number(url.searchParams.get('id'));

  try {
    if (book && chapter) {
      clearChapterAnnotations(book, chapter);
      return apiOk({ cleared: true });
    }

    if (!id) {
      return apiError('Missing id param');
    }

    deleteAnnotation(id);
    return apiOk({ ok: true });
  } catch (e) {
    return apiServerError(String(e));
  }
};
