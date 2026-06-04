/**
 * GET  /api/studio/section-depth?book=<slug>&chapter=<id>
 *   Returns { ok, sections: SectionDepth[] }
 *
 * PATCH /api/studio/section-depth
 *   Body: { book, chapter, ordinal, slug, depth_level, tags? }
 *   Returns { ok, section: SectionDepth }
 *
 * Option A: section-level depth + multi-select tags in one endpoint.
 * Ordinal is the stable key. Source defaults to 'human' on PATCH.
 */

import type { APIRoute } from 'astro';
import { getSectionDepths, upsertSectionDepth } from '../../../lib/db/knowledge';

export const GET: APIRoute = ({ request }) => {
  try {
    const url = new URL(request.url);
    const book = url.searchParams.get('book') ?? '';
    const chapter = url.searchParams.get('chapter') ?? '';
    if (!book || !chapter) {
      return new Response(JSON.stringify({ ok: false, error: 'book and chapter params required' }), {
        status: 400, headers: { 'Content-Type': 'application/json' },
      });
    }
    const sections = getSectionDepths(book, chapter);
    return new Response(JSON.stringify({ ok: true, sections }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: String(e) }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};

export const PATCH: APIRoute = async ({ request }) => {
  try {
    let body: unknown;
    try { body = await request.json(); } catch { return new Response(JSON.stringify({ ok: false, error: 'Invalid JSON' }), { status: 400, headers: { 'Content-Type': 'application/json' } }); }
    const { book, chapter, ordinal, slug, depth_level, tags } = body as Record<string, unknown>;
    if (typeof book !== 'string' || !book) return new Response(JSON.stringify({ ok: false, error: 'book required' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
    if (typeof chapter !== 'string' || !chapter) return new Response(JSON.stringify({ ok: false, error: 'chapter required' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
    if (typeof ordinal !== 'number') return new Response(JSON.stringify({ ok: false, error: 'ordinal (number) required' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
    if (typeof slug !== 'string') return new Response(JSON.stringify({ ok: false, error: 'slug required' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
    if (typeof depth_level !== 'string') return new Response(JSON.stringify({ ok: false, error: 'depth_level required' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
    const tagsArr = Array.isArray(tags) ? (tags as unknown[]).filter((t): t is string => typeof t === 'string') : [];
    const section = upsertSectionDepth(book, chapter, ordinal, slug, depth_level, 'human', tagsArr);
    return new Response(JSON.stringify({ ok: true, section }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: String(e) }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
