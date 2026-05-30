/**
 * Studio stage-review API (WC8 write-back loop).
 *   GET  /api/studio/review?slug=X&chapter=Y         — read per-stage approval state
 *   POST /api/studio/review  {slug,chapter,stage,approved,notes?} — set a stage's approval
 *
 * The editor calls POST when the reviewer approves a stage; the orchestrator reads the same
 * file to decide whether to resume past that stage's halt.
 */
import type { APIRoute } from 'astro';
import { readReview, setStageReview } from '../../../lib/reader/stage-review';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const slug = url.searchParams.get('slug');
  const chapter = url.searchParams.get('chapter');
  if (!slug || !chapter || !SLUG_RE.test(slug)) return apiError('Missing or invalid slug/chapter');
  try {
    return apiOk(readReview(slug, chapter));
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { slug?: string; chapter?: string; stage?: string; approved?: boolean; notes?: string };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { slug, chapter, stage, approved, notes } = body;
  if (!slug || !chapter || !stage || !SLUG_RE.test(slug)) {
    return apiError('Missing or invalid slug/chapter/stage');
  }
  try {
    return apiOk(setStageReview(slug, chapter, stage, approved !== false, notes));
  } catch (e) {
    return apiServerError(String(e));
  }
};
