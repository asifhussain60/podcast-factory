/**
 * GET  /api/annotations?book=X&chapter=Y   — list annotations for a chapter
 * POST /api/annotations                    — toggle a tag on a paragraph
 * DELETE /api/annotations?id=N             — remove a specific annotation
 */

import type { APIRoute } from 'astro';
import { getAnnotations, toggleAnnotation, deleteAnnotation } from '../../lib/db/annotations';

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
    const rows = getAnnotations(book, chapter);
    return new Response(JSON.stringify(rows), { headers: { 'content-type': 'application/json' } });
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
  const id = Number(url.searchParams.get('id'));
  if (!id) {
    return new Response(JSON.stringify({ error: 'Missing id param' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }
  try {
    deleteAnnotation(id);
    return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};
