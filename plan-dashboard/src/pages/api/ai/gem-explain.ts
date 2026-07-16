/**
 * POST /api/ai/gem-explain
 *
 * "Add additional teaching material" — explain a concept in a saved Gem persona's
 * voice (default: the Ismaili Scholar Gem). Backend generation only; the Companion
 * Panel UI that will call this is designed in a later pass.
 *
 * Body: { gem?: string, concept: string, context?: string, bookTitle?: string, model?: 'flash'|'pro' }
 * Returns: { ok, body: string, etymology: string|null, source: 'gemini' }
 */

import type { APIRoute } from 'astro';
import { rateLimitCheck } from '../../../lib/reader/gemini-server';
import { runGemConcept } from '../../../lib/reader/gems/engine';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) {
    return new Response(JSON.stringify({ ok: false, error: 'rate_limited', retryMs: limit.retryMs }), {
      status: 429, headers: { 'content-type': 'application/json' },
    });
  }

  try {
    const { gem, concept, context, bookTitle, model } = await request.json();
    if (typeof concept !== 'string' || !concept.trim()) {
      return new Response(JSON.stringify({ ok: false, error: 'missing concept' }), { status: 400, headers: { 'content-type': 'application/json' } });
    }

    let result;
    try {
      result = await runGemConcept({ gemId: gem, concept: concept.trim(), context, bookTitle, model });
    } catch (e) {
      const msg = (e as Error).message;
      if (msg.startsWith('unknown_gem:')) {
        return new Response(JSON.stringify({ ok: false, error: 'unknown gem' }), { status: 400, headers: { 'content-type': 'application/json' } });
      }
      throw e;
    }

    if (!result.body) {
      return new Response(JSON.stringify({ ok: false, error: 'no answer returned' }), { status: 502, headers: { 'content-type': 'application/json' } });
    }

    return new Response(JSON.stringify({
      ok: true,
      body: result.body,
      etymology: result.etymology,
      source: 'gemini',
    }), { status: 200, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: (e as Error).message }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
};
