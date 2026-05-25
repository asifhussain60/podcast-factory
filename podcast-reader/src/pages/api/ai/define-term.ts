/**
 * POST /api/ai/define-term
 *
 * Body: { phonetic: string, transliteration?: string, arabic?: string, context?: string, book?: string }
 * Returns: { definition: string, etymology?: string, related?: string[] }
 *
 * Uses Gemini Flash. The client caches the response in localStorage so
 * repeat hovers cost nothing. Context is the surrounding sentence so
 * the model can disambiguate (e.g. "Hujjah" the rank vs the proof).
 */

import type { APIRoute } from 'astro';
import { generate, rateLimitCheck } from '~/lib/gemini-server';

export const prerender = false;

const SYSTEM = `You are a careful scholar of Ismaili and broader Islamic tradition. When given an Arabic/transliterated term, return a JSON object with:
  - definition: ONE crisp sentence (max 28 words) explaining the term in the context provided.
  - etymology: optional, ONE short clause on root letters or origin (omit if unknown).
  - related: optional, up to 3 closely-related terms a reader might also want to know.
Stay specific to the Ismaili/Shi'i context when the surrounding text is clearly in that tradition. Do NOT pad with disclaimers. Output ONLY the JSON object, no markdown fences.`;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) {
    return new Response(JSON.stringify({ error: 'rate_limited', retryMs: limit.retryMs }), {
      status: 429, headers: { 'content-type': 'application/json' },
    });
  }
  try {
    const { phonetic, transliteration, arabic, context, book } = await request.json();
    if (!phonetic) return new Response(JSON.stringify({ error: 'missing phonetic' }), { status: 400 });

    const user = [
      `Term: ${phonetic}`,
      transliteration && transliteration !== phonetic ? `Transliteration: ${transliteration}` : '',
      arabic ? `Arabic script: ${arabic}` : '',
      book ? `Book context: ${book}` : '',
      context ? `Surrounding sentence: "${context}"` : '',
    ].filter(Boolean).join('\n');

    const text = await generate({
      model: 'flash',
      systemInstruction: SYSTEM,
      contents: [{ role: 'user', parts: [{ text: user }] }],
      temperature: 0.2,
      maxOutputTokens: 400,
      jsonMode: true,
    });

    // Best-effort JSON parse; strip code fences if model included them.
    let parsed: any = {};
    try {
      const cleaned = text.replace(/^```json\s*|\s*```$/g, '').trim();
      parsed = JSON.parse(cleaned);
    } catch {
      parsed = { definition: text };
    }
    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), { status: 500 });
  }
};
