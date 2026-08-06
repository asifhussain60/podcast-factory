/**
 * POST /api/ai/gem-explain
 *
 * "Add additional teaching material" — explain a concept in a saved Gem persona's
 * voice (default: the Ismaili Scholar Gem).
 *
 * Three steps, in this order, since 2026-07-26 (Asif):
 *   1. GROUND  — when `ground` is set, the library's own knowledge base is searched
 *      for atoms bearing on the passage and handed to the model as material.
 *   2. EXPLAIN — the persona writes the card, in markdown, with etymology as items.
 *   3. TIGHTEN — a guarded articulation pass removes repetition, then the body is
 *      capped to a word budget on a block boundary.
 *   4. CITE     — `Q|S:V` is resolved to a surah NAME and the cited verse is given
 *      its canonical English rendering from the repo's mushaf mirror.
 * Steps 1 and 3 are best-effort by construction: each returns the input unchanged
 * on any failure, so a card is never lost to an enrichment step.
 *
 * Body: { gem?, concept, context?, bookTitle?, model?, ground?: boolean, maxWords?: number, question?: string }
 *   `question`, when given, is a reader-typed ask ABOUT `concept` (usually the
 *   selected passage) — the answer targets that question instead of generically
 *   explaining `concept`.
 * Returns: { ok, body: string, etymology: string[], grounded: number, source: 'gemini' }
 */

import type { APIRoute } from "astro";
import { rateLimitCheck } from "../../../lib/reader/gemini-server";
import { runGemPrepared } from "../../../lib/reader/gems/engine";
import {
  prepareCard,
  finishCard,
} from "../../../lib/reader/companion/gem-card.server";
import { articulate } from "../../../lib/reader/companion/articulate.server";

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) {
    return new Response(
      JSON.stringify({
        ok: false,
        error: "rate_limited",
        retryMs: limit.retryMs,
      }),
      {
        status: 429,
        headers: { "content-type": "application/json" },
      },
    );
  }

  try {
    const {
      gem,
      concept,
      context,
      chapterContext,
      bookTitle,
      model,
      ground,
      maxWords,
      question,
    } = await request.json();
    const askedQuestion =
      typeof question === "string" && question.trim() ? question.trim() : "";
    if (typeof concept !== "string" || !concept.trim()) {
      return new Response(
        JSON.stringify({ ok: false, error: "missing concept" }),
        { status: 400, headers: { "content-type": "application/json" } },
      );
    }

    // 1. Grounding and the persona's turn, both assembled by the module the
    //    student-reader bridge also calls — see gem-card.server.ts.
    let prepared;
    try {
      prepared = prepareCard({
        gemId: gem,
        concept,
        context,
        chapterContext:
          typeof chapterContext === "string" ? chapterContext : undefined,
        bookTitle,
        question: askedQuestion,
        ground: Boolean(ground),
      });
    } catch (e) {
      const msg = (e as Error).message;
      if (msg.startsWith("unknown_gem:")) {
        return new Response(
          JSON.stringify({ ok: false, error: "unknown gem" }),
          {
            status: 400,
            headers: { "content-type": "application/json" },
          },
        );
      }
      throw e;
    }

    let result;
    try {
      result = await runGemPrepared({
        system: prepared.system,
        user: prepared.user,
        model,
      });
    } catch (e) {
      const msg = (e as Error).message;
      if (msg.startsWith("unknown_gem:")) {
        return new Response(
          JSON.stringify({ ok: false, error: "unknown gem" }),
          { status: 400, headers: { "content-type": "application/json" } },
        );
      }
      throw e;
    }

    if (!result.body) {
      return new Response(
        JSON.stringify({ ok: false, error: "no answer returned" }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }

    // 3. Tighten — the one step that can make a card worse, so it is also the one
    //    step with its own guards, and it falls back to its input on any failure.
    // 4. Cap, resolve citations, veto contradicted etymology. Same module, same
    //    order, as the batch pass — see gem-card.server.ts.
    const finished = finishCard({
      body: await articulate(result.body),
      etymology: result.etymology,
      maxWords,
    });

    return new Response(
      JSON.stringify({
        ok: true,
        body: finished.body,
        etymology: finished.etymology,
        etymologyVetoed: finished.etymologyVetoed,
        grounded: prepared.grounded,
        source: "gemini",
      }),
      {
        status: 200,
        headers: {
          "content-type": "application/json",
          "cache-control": "no-store",
        },
      },
    );
  } catch (e) {
    return new Response(
      JSON.stringify({ ok: false, error: (e as Error).message }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }
};
