/**
 * POST /api/ai/english-term
 *
 * Suggests the natural English a narrator would SPEAK in place of an Arabic term,
 * for the Arabic-review panel's "Replace · English" action (when a term should be
 * said in plain English rather than recited in Arabic). The per-book glossary has
 * no English field, so this fills the replacement box with an editable suggestion
 * instead of making the curator type it.
 *
 * Body: { text: string, arabic?: string, bookTitle?: string }
 *   text    — the transliterated term (e.g. "hadith", "riyadh al-hadrah")
 *   arabic  — its Arabic script, for disambiguation
 * Returns: { ok, english: string, gloss: string, source: 'gemini' }
 */

import type { APIRoute } from "astro";
import { generate, rateLimitCheck } from "../../../lib/reader/gemini-server";

export const prerender = false;

const SYSTEM = `You render an Arabic term from an Ismaili / broader Islamic scholarly text into the natural ENGLISH a careful narrator would SAY when speaking it aloud in plain English (not reciting the Arabic).

Rules:
  - Return the established English word or short phrase a reader of this tradition expects — a common loanword stays itself ("hadith" -> "hadith", "Imam" -> "Imam", "Quran" -> "the Quran"); a descriptive term gets its plain-English equivalent ("riyadh al-hadrah" -> "the gardens of the Presence", "hijab al-khas" -> "the special veil").
  - Keep it concise and speakable — the words a narrator would actually voice, not a dictionary definition.
  - Stay faithful to the term's meaning and the Ismaili/Shi'i register when context implies it. Introduce no new doctrine.

Return a JSON object ONLY (no markdown fences) with:
  - english: the spoken English rendering (max ~8 words).
  - gloss: ONE short clause (max 12 words) confirming the sense, so the curator can verify it.`;

function extractJson(raw: string): { english?: string; gloss?: string } | null {
  if (!raw) return null;
  const cleaned = raw.replace(/^```json\s*|\s*```$/g, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    const m = cleaned.match(/\{[\s\S]*\}/);
    if (m) {
      try {
        return JSON.parse(m[0]);
      } catch {
        return null;
      }
    }
    return null;
  }
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

  try {
    const { text, arabic, bookTitle } = await request.json();
    if (typeof text !== "string" || !text.trim()) {
      return new Response(
        JSON.stringify({ ok: false, error: "missing text" }),
        { status: 400, headers: { "content-type": "application/json" } },
      );
    }

    const user = [
      `Arabic term (transliterated): "${text.trim()}"`,
      typeof arabic === "string" && arabic.trim()
        ? `Arabic script: ${arabic.trim()}`
        : "",
      bookTitle ? `Book: ${bookTitle}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    const raw = await generate({
      model: "flash",
      systemInstruction: SYSTEM,
      contents: [{ role: "user", parts: [{ text: user }] }],
      temperature: 0.2,
      maxOutputTokens: 200,
      jsonMode: true,
      // Disable Flash thinking so the small token budget feeds the JSON answer.
      thinkingBudget: 0,
    });

    const parsed = extractJson(raw);
    if (!parsed || !parsed.english || !parsed.english.trim()) {
      return new Response(
        JSON.stringify({ ok: false, error: "no English returned" }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }

    return new Response(
      JSON.stringify({
        ok: true,
        english: parsed.english.trim(),
        gloss: (parsed.gloss ?? "").trim(),
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
