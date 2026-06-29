/**
 * POST /api/ai/explain
 *
 * Rewrite a highlighted excerpt so it is clearer and more fully explained, while
 * staying strictly within the meaning, voice, and tradition of the chapter it
 * came from. The full chapter is passed as context so the expansion never drifts
 * outside what the chapter actually says.
 *
 * Body: { text: string, chapter?: string, bookTitle?: string }
 *   text     — the highlighted excerpt to clarify
 *   chapter  — the full chapter plain text (context; may be long)
 *   bookTitle
 * Returns: { ok, text: string, source: 'gemini' }
 */

import type { APIRoute } from 'astro';
import { generate, rateLimitCheck } from '../../../lib/reader/gemini-server';

export const prerender = false;

const SYSTEM = `You are a careful editor clarifying a passage from a scholarly book, often in the Ismaili / broader Islamic tradition.

You are given the FULL CHAPTER as context and a single HIGHLIGHTED EXCERPT taken verbatim from it. Rewrite ONLY the highlighted excerpt so it is clearer and more fully explained for a thoughtful lay reader:
  - unpack implicit ideas and make the reasoning explicit,
  - gloss difficult or technical terms inline,
  - smooth awkward or compressed phrasing,
  - keep the original's register and reverence.

Hard rules:
  - Stay strictly faithful to the chapter's meaning, voice, and tradition. Use the surrounding chapter to disambiguate — never contradict it.
  - Do NOT introduce new doctrine, claims, names, citations, or facts that are not already supported by the chapter.
  - Do NOT explain or restate anything outside the highlighted excerpt.
  - Preserve Arabic-script terms and phrases in Arabic script only. Do NOT add English transliteration beside Arabic script, and do NOT rewrite Arabic terms as romanized Arabic in parentheses.
  - Expand only as much as clarity needs; this should read as a fuller version of the same passage, not a commentary on it.

Output ONLY the rewritten excerpt as plain prose — no preamble, no labels, no surrounding quotation marks.`;

function stripArabicTransliterationPairs(value: string): string {
  const arabic = String.raw`[\p{Script=Arabic}\s]+`;
  const roman = String.raw`[A-Za-zāēīōūĀĒĪŌŪṣṢḍḌṭṬẓẒḥḤʿʾ'’\-\s]+`;
  const romanizedArabicTerm = String.raw`(?:al-[A-Za-zāēīōūĀĒĪŌŪṣṢḍḌṭṬẓẒḥḤʿʾ'’-]+(?:\s+al-[A-Za-zāēīōūĀĒĪŌŪṣṢḍḌṭṬẓẒḥḤʿʾ'’-]+)*|[A-Za-z'’\-]*[āēīōūṣḍṭẓḥʿʾ][A-Za-zāēīōūṣḍṭẓḥʿʾ'’\-\s]*)`;

  return value
    .replace(new RegExp(String.raw`\*${roman}\*\s*\((${arabic})\)`, 'gu'), '$1')
    .replace(new RegExp(String.raw`${romanizedArabicTerm}\s*\((${arabic})\)`, 'gu'), '$1')
    .replace(new RegExp(String.raw`(${arabic})\s*\(\*?(?=[^)]*(?:al-|ā|ē|ī|ō|ū|ṣ|ḍ|ṭ|ẓ|ḥ|ʿ|ʾ))${roman}\*?\)`, 'gu'), '$1');
}

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) {
    return new Response(JSON.stringify({ ok: false, error: 'rate_limited', retryMs: limit.retryMs }), {
      status: 429, headers: { 'content-type': 'application/json' },
    });
  }

  try {
    const { text, chapter, bookTitle } = await request.json();
    if (typeof text !== 'string' || !text.trim()) {
      return new Response(JSON.stringify({ ok: false, error: 'missing text' }), { status: 400, headers: { 'content-type': 'application/json' } });
    }

    const ctx = typeof chapter === 'string' ? chapter.trim() : '';
    const user = [
      bookTitle ? `Book: ${bookTitle}` : '',
      ctx ? `Full chapter (context):\n"""\n${ctx}\n"""` : '',
      `Highlighted excerpt to clarify:\n"""\n${text.trim()}\n"""`,
    ].filter(Boolean).join('\n\n');

    const out = await generate({
      model: 'flash',
      systemInstruction: SYSTEM,
      contents: [{ role: 'user', parts: [{ text: user }] }],
      temperature: 0.4,
      maxOutputTokens: 1024,
      // Disable Flash's default thinking so the token budget goes to the answer.
      thinkingBudget: 0,
    });

    const clarified = stripArabicTransliterationPairs((out ?? '').trim().replace(/^["“”]+|["“”]+$/g, '').trim());
    if (!clarified) {
      return new Response(JSON.stringify({ ok: false, error: 'no explanation returned' }), { status: 502, headers: { 'content-type': 'application/json' } });
    }

    return new Response(JSON.stringify({ ok: true, text: clarified, source: 'gemini' }), {
      status: 200, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: (e as Error).message }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
};
