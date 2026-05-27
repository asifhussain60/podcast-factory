/**
 * GET    /api/annotations/tags        — list all tags
 * POST   /api/annotations/tags        — create a new user-defined tag
 * DELETE /api/annotations/tags?id=N  — delete a user-defined tag (non-default only)
 */

import type { APIRoute } from 'astro';
import { getTags, createTag, deleteTag } from '../../../lib/db/annotations';

export const prerender = false;

export const GET: APIRoute = () => {
  try {
    const tags = getTags();
    return new Response(JSON.stringify(tags), { headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { label: string; color: string; icon?: string };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }
  if (!body.label || !body.color) {
    return new Response(JSON.stringify({ error: 'label and color are required' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }
  try {
    const tag = createTag(body.label, body.color, body.icon);
    return new Response(JSON.stringify(tag), {
      status: 201, headers: { 'content-type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};

export const DELETE: APIRoute = ({ request }) => {
  const id = Number(new URL(request.url).searchParams.get('id'));
  if (!id) {
    return new Response(JSON.stringify({ error: 'Missing id param' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }
  try {
    deleteTag(id);
    return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};
