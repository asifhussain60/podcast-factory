/**
 * POST /api/ai/summarize-section
 *
 * Body: { sectionText: string, sectionTitle?: string, bookContext?: string }
 * Returns: { summary: string, keyPoints?: string[] }
 *
 * Two-to-three sentence callout for a single chapter section, plus
 * optional 2-3 key-point bullets. Gemini Flash; cached client-side by
 * SHA-1 hash of sectionText so a stable section is free on re-read.
 */

import type { APIRoute } from 'astro';
import { generate, rateLimitCheck } from '~/lib/gemini-server';

export const prerender = false;

const SYSTEM = `You are summarizing one section of a scholarly Ismaili text for a reader who wants a quick anchor before reading the section in full.
Return ONLY a JSON object:
{
  "summary": "2-3 sentence faithful summary in plain English. Preserve the author's specific argument; do not generalize to 'Islam says X'.",
  "keyPoints": ["3-6 word phrase", "another", "another"]
}
Use the section's own terminology (transliterated terms verbatim). Keep "summary" under 60 words.`;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) return new Response(JSON.stringify({ error: 'rate_limited' }), { status: 429 });
  try {
    const { sectionText, sectionTitle, bookContext } = await request.json();
    if (!sectionText || typeof sectionText !== 'string') {
      return new Response(JSON.stringify({ error: 'missing sectionText' }), { status: 400 });
    }
    const truncated = sectionText.length > 12000 ? sectionText.slice(0, 12000) + '\n[...truncated]' : sectionText;
    const user = [
      bookContext ? `Book: ${bookContext}` : '',
      sectionTitle ? `Section title: ${sectionTitle}` : '',
      'Section text:',
      truncated,
    ].filter(Boolean).join('\n');

    const text = await generate({
      model: 'flash',
      systemInstruction: SYSTEM,
      contents: [{ role: 'user', parts: [{ text: user }] }],
      temperature: 0.3,
      maxOutputTokens: 500,
      jsonMode: true,
    });

    let parsed: any;
    try {
      parsed = JSON.parse(text.replace(/^```json\s*|\s*```$/g, '').trim());
    } catch {
      parsed = { summary: text };
    }
    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), { status: 500 });
  }
};
