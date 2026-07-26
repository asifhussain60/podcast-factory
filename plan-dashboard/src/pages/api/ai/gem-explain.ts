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
 * Body: { gem?, concept, context?, bookTitle?, model?, ground?: boolean, maxWords?: number }
 * Returns: { ok, body: string, etymology: string[], grounded: number, source: 'gemini' }
 */

import type { APIRoute } from "astro";
import { rateLimitCheck } from "../../../lib/reader/gemini-server";
import { runGemConcept } from "../../../lib/reader/gems/engine";
import {
  groundingFor,
  groundingBlock,
} from "../../../lib/reader/companion/corpus-grounding.server";
import { articulate } from "../../../lib/reader/companion/articulate.server";
import { capWords } from "../../../lib/reader/companion/articulate-rules";
import { resolveQuranCitations } from "../../../lib/reader/companion/quran-citation.server";

/** The body budget. ~400 words is about half of what an ungoverned card ran to. */
const DEFAULT_MAX_WORDS = 400;
/** Per etymology item, mirroring the persona's own "at most 60 words" rule. */
const ETYMOLOGY_MAX_WORDS = 60;

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
    const { gem, concept, context, bookTitle, model, ground, maxWords } =
      await request.json();
    if (typeof concept !== "string" || !concept.trim()) {
      return new Response(
        JSON.stringify({ ok: false, error: "missing concept" }),
        { status: 400, headers: { "content-type": "application/json" } },
      );
    }

    // 1. The corpus first, so the model writes WITH it rather than being corrected
    //    by it afterwards. Empty when nothing in the library bears on the passage.
    const atoms = ground ? groundingFor(`${concept} ${context ?? ""}`) : [];
    const grounded = atoms.length
      ? [context ?? "", groundingBlock(atoms)].filter(Boolean).join("\n\n")
      : context;

    let result;
    try {
      result = await runGemConcept({
        gemId: gem,
        concept: concept.trim(),
        context: grounded,
        bookTitle,
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

    // 3. Tighten, then bound. Both fall back to their input on any failure.
    const budget =
      typeof maxWords === "number" && maxWords > 50
        ? Math.min(maxWords, 2000)
        : DEFAULT_MAX_WORDS;
    // 4. Citations last, so the cap can never cut a verse away from its
    //    rendering: `Q|18:65` becomes `Al-Kahf 18:65`, and a cited verse gets its
    //    canonical English from the mushaf mirror rather than from the model.
    const tightened = resolveQuranCitations(
      capWords(await articulate(result.body), budget),
    );

    return new Response(
      JSON.stringify({
        ok: true,
        body: tightened,
        etymology: result.etymology.map((e) =>
          capWords(e, ETYMOLOGY_MAX_WORDS),
        ),
        grounded: atoms.length,
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
