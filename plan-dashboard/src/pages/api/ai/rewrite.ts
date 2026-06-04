/**
 * POST /api/ai/rewrite
 *
 * Body: { text: string, mode?: 'clarify'|'tighten'|'simplify'|'formal', context?: string }
 * Returns: { options: string[] }   // 3 rewrite candidates
 *
 * Used by ChapterEditor's AI-assist sparkle button. Gemini Flash returns
 * three short rewrites; the editor renders them as cards and the user
 * accepts one or rejects all.
 */

import type { APIRoute } from 'astro';
import { generate, rateLimitCheck } from '../../../lib/reader/gemini-server';

export const prerender = false;

const MODE_HINTS: Record<string, string> = {
  clarify:   'Rewrite for clarity. Same length or shorter. Preserve every named entity and transliterated Arabic term verbatim.',
  tighten:   'Tighten — remove filler, redundancy, and stock phrasing. Cut word count by 20-30% if possible without losing content.',
  simplify:  'Simplify the vocabulary for a non-specialist reader. Keep technical terms but explain them in-line when natural.',
  formal:    'Raise the register slightly. Scholarly, restrained, no contractions. Same length.',
};

const SYSTEM = (modeHint: string) => `You are a careful editor working on a scholarly Ismaili text.
${modeHint}

Rules:
- Preserve every transliterated Arabic term (Hujjah, Sayyidina, Da'i, etc.) and proper noun verbatim.
- Preserve meaning. If you would need to drop a substantive claim, don't.
- Match the source's voice: formal-but-readable, no marketing tone.

Return ONLY a JSON object: {"options": ["rewrite 1", "rewrite 2", "rewrite 3"]}.
Three DISTINCT alternatives. No prefatory text, no markdown fences.`;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) return new Response(JSON.stringify({ error: 'rate_limited' }), { status: 429 });
  try {
    const { text, mode = 'clarify', context } = await request.json();
    if (!text || typeof text !== 'string') return new Response(JSON.stringify({ error: 'missing text' }), { status: 400 });
    const hint = MODE_HINTS[mode] ?? MODE_HINTS.clarify;
    const user = [
      context ? `Surrounding context (do not rewrite, just orient yourself):\n"""${context}"""` : '',
      'Rewrite this passage three different ways:',
      `"""${text}"""`,
    ].filter(Boolean).join('\n\n');

    const raw = await generate({
      model: 'flash',
      systemInstruction: SYSTEM(hint),
      contents: [{ role: 'user', parts: [{ text: user }] }],
      temperature: 0.7,
      maxOutputTokens: 1500,
      jsonMode: true,
    });

    let parsed: any = {};
    try { parsed = JSON.parse(raw); }
    catch { parsed = { options: [raw] }; }
    if (!Array.isArray(parsed.options)) parsed.options = [String(parsed.options ?? raw)];
    parsed.options = parsed.options.slice(0, 3).map((s: any) => String(s).trim());

    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), { status: 500 });
  }
};
