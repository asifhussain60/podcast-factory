/**
 * POST /api/ai/gem-answer
 *
 * "Augment answers to potential questions" — answer a reader's question in a saved
 * Gem persona's voice (default: the Ismaili Scholar Gem). Backend generation only;
 * the Companion Panel UI that will call this is designed in a later pass.
 *
 * Body: { gem?: string, question: string, context?: string, bookTitle?: string, model?: 'flash'|'pro', grounded?: boolean }
 * Returns: { ok, body: string, etymology: string|null, source: 'gemini', sources?: string[] }
 *
 * grounded:true uses Gemini's Google Search grounding (draws on other online
 * Ismaili/Islamic sources, per the Gem's own instructions) but cannot run in JSON
 * mode, so its body/etymology split uses the raw-text fallback rather than the
 * JSON envelope the non-grounded path gets — a known, deliberate limitation.
 */

import type { APIRoute } from 'astro';
import { rateLimitCheck } from '../../../lib/reader/gemini-server';
import { runGemQuestion } from '../../../lib/reader/gems/engine';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) {
    return new Response(JSON.stringify({ ok: false, error: 'rate_limited', retryMs: limit.retryMs }), {
      status: 429, headers: { 'content-type': 'application/json' },
    });
  }

  try {
    const { gem, question, context, bookTitle, model, grounded } = await request.json();
    if (typeof question !== 'string' || !question.trim()) {
      return new Response(JSON.stringify({ ok: false, error: 'missing question' }), { status: 400, headers: { 'content-type': 'application/json' } });
    }

    let result;
    try {
      result = await runGemQuestion({ gemId: gem, question: question.trim(), context, bookTitle, model, grounded: Boolean(grounded) });
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
      ...(result.sources ? { sources: result.sources } : {}),
    }), { status: 200, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: (e as Error).message }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
};
