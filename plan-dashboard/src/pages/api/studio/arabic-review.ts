/**
 * Arabic-curation API — human review of a book's Arabic terms before audio.
 *   GET  /api/studio/arabic-review?slug=X
 *        — every glossary term (phonetic, transliteration, arabic_script, decision)
 *   POST /api/studio/arabic-review
 *        {slug, phonetic, decision, corrected_phonetic?, corrected_arabic?,
 *         english_override?}
 *        — persist a keep / fix_phonetic / correct_arabic / replace_english
 *          decision INTO _system/glossary.yml (schema v2).
 *
 * Single source of truth: the decision written here drives BOTH the spoken audio
 * (pronunciation_compiler.resolve_curation) and the on-page overlay
 * (glossary.ts resolveCuration). The model never authors Arabic — the human
 * curates the verified overlay.
 */
import type { APIRoute } from 'astro';
import {
  loadGlossaryAll,
  writeGlossaryDecision,
  type GlossaryDecision,
} from '../../../lib/reader/glossary';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const DECISIONS: GlossaryDecision[] = [
  'keep', 'fix_phonetic', 'correct_arabic', 'replace_english',
];

export const GET: APIRoute = async ({ request }) => {
  const url = new URL(request.url);
  const slug = url.searchParams.get('slug');
  if (!slug || !SLUG_RE.test(slug)) return apiError('Missing or invalid slug');
  try {
    return apiOk({ slug, entries: await loadGlossaryAll(slug) });
  } catch (e) {
    return apiServerError(String(e));
  }
};

export const POST: APIRoute = async ({ request }) => {
  let body: {
    slug?: string;
    phonetic?: string;
    arabic_script?: string;
    decision?: GlossaryDecision;
    corrected_phonetic?: string;
    corrected_arabic?: string;
    english_override?: string;
    decided_by?: string;
  };
  try {
    body = await request.json();
  } catch {
    return apiError('Invalid JSON');
  }
  const { slug, phonetic, decision } = body;
  if (!slug || !SLUG_RE.test(slug)) return apiError('Missing or invalid slug');
  if (!phonetic) return apiError('Missing phonetic (term key)');
  if (!decision || !DECISIONS.includes(decision)) {
    return apiError(`Invalid decision; expected one of ${DECISIONS.join(', ')}`);
  }
  try {
    const updated = await writeGlossaryDecision(slug, phonetic, {
      decision,
      corrected_phonetic: body.corrected_phonetic,
      corrected_arabic: body.corrected_arabic,
      english_override: body.english_override,
      decided_by: body.decided_by,
    }, body.arabic_script);
    if (!updated) return apiError(`Term not found in glossary: ${phonetic}`, 404);
    return apiOk(updated);
  } catch (e) {
    return apiServerError(String(e));
  }
};
