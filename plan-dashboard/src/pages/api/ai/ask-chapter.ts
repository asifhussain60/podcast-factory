/**
 * POST /api/ai/ask-chapter (streaming)
 *
 * Body: { chapterText: string, chapterTitle: string, bookContext?: string,
 *         history: {role: 'user'|'model', text: string}[], question: string }
 * Returns: text/event-stream — SSE tokens as the model generates.
 *
 * Gemini Pro for long context + nuance. Streams via the Gemini SSE API.
 */

import type { APIRoute } from 'astro';
import { generateStream, rateLimitCheck } from '../../../lib/reader/gemini-server';

export const prerender = false;

const SYSTEM_TEMPLATE = (title: string, book: string | undefined, chapterText: string) => `You are a focused reading companion answering questions about ONE chapter the user is currently reading.

Book: ${book ?? 'unknown'}
Chapter: ${title}

GROUND TRUTH (the only authoritative source for this conversation — do not import outside facts unless the user explicitly asks for context):
"""
${chapterText}
"""

Rules:
- Answer ONLY using the chapter above. If the answer is not in the chapter, say so plainly and offer the closest related point that IS in the chapter.
- Quote selectively — short phrases, not paragraphs.
- When you cite, add a marker like 【¶12】 or 【"Outer of the call"】 so the reader can find it. Be precise about which heading the point sits under when possible.
- Preserve the author's specific terminology (transliterated Arabic terms verbatim).
- Be concise. 1-3 short paragraphs unless the question genuinely needs more.
- Markdown allowed (lists, bold). No headings.`;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) return new Response('rate_limited', { status: 429 });
  try {
    const { chapterText, chapterTitle, bookContext, history = [], question } = await request.json();
    if (!chapterText || !question) return new Response('missing chapterText or question', { status: 400 });

    const truncated = chapterText.length > 80_000 ? chapterText.slice(0, 80_000) + '\n[...truncated for length]' : chapterText;
    const contents = [
      ...history.map((h: any) => ({ role: h.role === 'model' ? 'model' as const : 'user' as const, parts: [{ text: String(h.text) }] })),
      { role: 'user' as const, parts: [{ text: question }] },
    ];

    const stream = generateStream({
      model: 'pro',
      systemInstruction: SYSTEM_TEMPLATE(chapterTitle ?? 'this chapter', bookContext, truncated),
      contents,
      temperature: 0.4,
      maxOutputTokens: 1800,
    });

    const encoder = new TextEncoder();
    const sseStream = new ReadableStream({
      async start(controller) {
        try {
          for await (const chunk of stream) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text: chunk })}\n\n`));
          }
          controller.enqueue(encoder.encode(`event: done\ndata: {}\n\n`));
        } catch (e) {
          controller.enqueue(encoder.encode(`event: error\ndata: ${JSON.stringify({ error: (e as Error).message })}\n\n`));
        } finally {
          controller.close();
        }
      },
    });

    return new Response(sseStream, {
      status: 200,
      headers: {
        'content-type': 'text/event-stream',
        'cache-control': 'no-store',
        'connection': 'keep-alive',
      },
    });
  } catch (e) {
    return new Response(`error: ${(e as Error).message}`, { status: 500 });
  }
};
