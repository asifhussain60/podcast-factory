/**
 * Studio editorial-decisions API (WC8 Slice 5b).
 *   GET  /api/studio/editorial?slug=X&scope=book              — read a scope's stored cards
 *   GET  /api/studio/editorial?slug=X&chapter=Y&resolve=1     — effective (override||book) for a chapter
 *   POST /api/studio/editorial  {slug, scope, card, value|null} — set/clear one card at a scope
 *
 * `scope` is 'book' or a chapter slug. The cockpit POSTs when the editor edits a card; the
 * Slice-6 orchestrator reads the same JSON to steer stage advancement.
 */
import type { APIRoute } from 'astro';
import {
  readEditorial,
  setEditorialCard,
  resolveEffective,
  chaptersWithOverrides,
  CARD_IDS,
  type CardId,
  type CardValue,
} from '../../../lib/reader/editorial';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const GET: APIRoute = ({ request }) => {
  const url = new URL(request.url);
  const slug = url.searchParams.get('slug');
  if (!slug || !SLUG_RE.test(slug)) return apiError('Missing or invalid slug');
  try {
    const chapter = url.searchParams.get('chapter');
    if (url.searchParams.get('resolve') === '1' && chapter) {
      return apiOk({ slug, chapter, resolved: resolveEffective(slug, chapter) });
    }
    const scope = url.searchParams.get('scope') ?? 'book';
    return apiOk({ ...readEditorial(slug, scope), overriddenChapters: chaptersWithOverrides(slug) });
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: { slug?: string; scope?: string; card?: string; value?: CardValue | null };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { slug, scope, card } = body;
  if (!slug || !SLUG_RE.test(slug) || !scope) return apiError('Missing or invalid slug/scope');
  if (!card || !CARD_IDS.includes(card as CardId)) return apiError('Missing or invalid card');
  try {
    const value = body.value === undefined ? null : body.value;
    return apiOk(setEditorialCard(slug, scope, card as CardId, value));
  } catch (e) {
    return apiServerError(String(e));
  }
};
