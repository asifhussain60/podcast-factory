/**
 * POST /api/ai/claude — Wave L-8 nuanced editorial tasks (Claude Sonnet).
 *
 * Body: { task, ... }
 *   task="categorise"  { text }                  -> { tag, reason }
 *      Suggests the best content tag for a paragraph:
 *      esoteric | reality | sharia | history | improve | delete.
 *   task="instruct"    { text, instruction }      -> { replacement }
 *      Surgical edit of a paragraph per a natural-language instruction.
 *   task="finalize"    { slug, chapter, paragraphs[] } -> { brief }
 *      Structured markdown handoff brief for Claude Code IDE.
 *
 * Claude (not Gemini) handles these because they need semantic nuance /
 * structured reasoning. Fast tasks (rewrite, summarize) stay on Gemini.
 */
import type { APIRoute } from "astro";
import { claudeComplete } from "../../../lib/ai/claude-client";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";
import { rateLimitCheck } from "../../../lib/reader/gemini-server";

export const prerender = false;

const TAGS = ["esoteric", "reality", "sharia", "history", "improve", "delete"];

const CATEGORISE_SYSTEM = `You classify a single paragraph from an Islamic scholarly text into ONE editorial tag:
- esoteric  — inner/allegorical/spiritual interpretation (ta'wil, batin).
- reality   — metaphysical truths (haqaiq, cosmology, origin & return).
- sharia    — law, ritual practice, hadith-based rulings (zahir).
- history   — biographical or historical material.
- improve   — prose that is weak/unclear and needs an editorial rewrite (not a content category).
- delete    — redundant or off-topic; a candidate for cutting.
Prefer a content tag (esoteric/reality/sharia/history) when the paragraph carries doctrine;
use improve/delete only for editorial-quality calls.
Return ONLY JSON: {"tag":"<one of the six>","reason":"one short sentence"}. No markdown fences.`;

const INSTRUCT_SYSTEM = `You are a careful editor of a scholarly Ismaili text. Apply the user's instruction to the
paragraph and return ONLY the revised paragraph text — no preamble, no quotes, no markdown.
Preserve every transliterated Arabic term and proper noun verbatim. Preserve meaning unless the
instruction explicitly asks otherwise.`;

const FINALIZE_SYSTEM = `You write a concise handoff brief for an engineer continuing work in an IDE.
Given a chapter's edited paragraphs with their tags and comments, produce GitHub-flavored markdown:
  ## Finalize Brief — <chapter>
  ### What was done   (bullet summary: counts of edits + tags)
  ### Tagged paragraphs   (each: **[tag] Para N:** "<=12-word excerpt" + comment if any)
  ### Recommended next steps   (numbered, concrete pipeline actions)
  ### Instruction for Claude Code   (one short paragraph telling the IDE agent what to apply)
Keep it under ~400 words. No fenced code blocks. Return ONLY the markdown.`;

function stripFences(s: string): string {
  let t = s.trim();
  if (t.startsWith("```")) {
    t = t
      .replace(/^```[a-z]*\n?/i, "")
      .replace(/```$/, "")
      .trim();
  }
  return t;
}

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

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const task = String(body.task ?? "").trim();

  try {
    if (task === "categorise") {
      const text = String(body.text ?? "").trim();
      if (!text) return apiError("text is required");
      const out = await claudeComplete(text.slice(0, 4000), {
        system: CATEGORISE_SYSTEM,
        maxTokens: 200,
      });
      let tag = "improve";
      let reason = "";
      try {
        const o = JSON.parse(
          stripFences(out).match(/\{[\s\S]*\}/)?.[0] ?? "{}",
        );
        if (TAGS.includes(String(o.tag))) tag = String(o.tag);
        reason = String(o.reason ?? "");
      } catch {
        /* fall through to default */
      }
      return apiOk({ tag, reason });
    }

    if (task === "instruct") {
      const text = String(body.text ?? "").trim();
      const instruction = String(body.instruction ?? "").trim();
      if (!text || !instruction)
        return apiError("text and instruction are required");
      const prompt = `INSTRUCTION:\n${instruction}\n\nPARAGRAPH:\n${text}`;
      const replacement = await claudeComplete(prompt, {
        system: INSTRUCT_SYSTEM,
        maxTokens: 1024,
      });
      return apiOk({ replacement: stripFences(replacement) });
    }

    if (task === "finalize") {
      const slug = String(body.slug ?? "").trim();
      const chapter = String(body.chapter ?? "").trim();
      const paragraphs = Array.isArray(body.paragraphs) ? body.paragraphs : [];
      if (!slug || !chapter) return apiError("slug and chapter are required");
      const prompt = JSON.stringify({ slug, chapter, paragraphs }).slice(
        0,
        20000,
      );
      const brief = await claudeComplete(prompt, {
        system: FINALIZE_SYSTEM,
        maxTokens: 1500,
      });
      return apiOk({ brief: stripFences(brief) });
    }

    return apiError(`Unknown task "${task}"`);
  } catch (e) {
    return apiServerError(`Claude request failed: ${String(e)}`);
  }
};
