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

export const prerender = false;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const book = url.searchParams.get('book');
  const chapter = url.searchParams.get('chapter');
  if (!book || !chapter) {
    return new Response(JSON.stringify({ error: 'Missing book or chapter param' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }
  try {
    const snapshot = getChapterAnnotationSnapshot(book, chapter);
    return new Response(JSON.stringify(snapshot), { headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};

export const PATCH: APIRoute = async ({ request }) => {
  let body: { book: string; chapter: string; paraIdx: number; note: string };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }

  const { book, chapter, paraIdx, note } = body;
  if (!book || !chapter || paraIdx == null || typeof note !== 'string') {
    return new Response(JSON.stringify({ error: 'Missing required fields' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }

  try {
    upsertParagraphNote(book, chapter, paraIdx, note);
    return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { book: string; chapter: string; paraIdx: number; tagId: number; note?: string };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }
  const { book, chapter, paraIdx, tagId, note } = body;
  if (!book || !chapter || paraIdx == null || !tagId) {
    return new Response(JSON.stringify({ error: 'Missing required fields' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }
  try {
    const result = toggleAnnotation(book, chapter, paraIdx, tagId, note);
    return new Response(JSON.stringify(result), { headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
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
      return new Response(JSON.stringify({ ok: true, cleared: true }), { headers: { 'content-type': 'application/json' } });
    }

    if (!id) {
      return new Response(JSON.stringify({ error: 'Missing id param' }), {
        status: 400, headers: { 'content-type': 'application/json' },
      });
    }

    deleteAnnotation(id);
    return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};
