/**
 * POST /api/ai/arabic-term
 *
 * Context-aware Arabic rendering for a highlighted word/phrase in the Studio editor.
 * Primary use: replace an ENGLISH term with the correct Arabic term a scholar would
 * use in this passage (e.g. "Divine Light" → نور, "Night Journey" → ليلة الإسراء).
 * Auto-detects: if the input is already a transliterated Arabic term, returns its
 * Arabic script instead of an English-style translation.
 *
 * Body: { text: string, context?: string, bookTitle?: string }
 * Returns: { ok, arabic: string, gloss: string, kind: 'translation'|'script', source: 'gemini' }
 */

import type { APIRoute } from "astro";
import { generate, rateLimitCheck } from "../../../lib/reader/gemini-server";

export const prerender = false;

const SYSTEM = `You are a careful scholar of Ismaili and broader Islamic tradition rendering a highlighted term from an English scholarly text into Arabic, for inline display.

Decide which case applies and act accordingly:
  - ENGLISH word/phrase (e.g. "Divine Light", "Night Journey", "the Covenant"): return the established Arabic TERM a scholar of this tradition would use in THIS context — not a literal word-for-word gloss. ("Night Journey" → ليلة الإسراء, "Divine Light" → نور.) Set kind to "translation".
  - Already a TRANSLITERATED Arabic term (e.g. "fitra", "Sayyidina", "Da'wah"): return its correct Arabic SCRIPT. Set kind to "script".

Return a JSON object ONLY (no markdown fences) with:
  - arabic: the Arabic script, fully voweled only if natural; correct orthography is critical.
  - gloss: ONE short clause (max 12 words) confirming what the Arabic means, so the editor can verify it.
  - kind: "translation" or "script".

Use the surrounding sentence to disambiguate. Stay specific to the Ismaili/Shi'i register when the context is clearly that tradition. Output ONLY the JSON object.`;

/**
 * Parse the model's JSON reply. Strips markdown fences (same convention as
 * define-term.ts) and, as a last resort, grabs the first {...} block. Returns
 * null when nothing parseable is found so the caller can 502.
 */
function extractJson(
  raw: string,
): { arabic?: string; gloss?: string; kind?: string } | null {
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
    const { text, context, bookTitle } = await request.json();
    if (typeof text !== "string" || !text.trim()) {
      return new Response(
        JSON.stringify({ ok: false, error: "missing text" }),
        { status: 400, headers: { "content-type": "application/json" } },
      );
    }

    const user = [
      `Highlighted term: "${text.trim()}"`,
      bookTitle ? `Book: ${bookTitle}` : "",
      context ? `Surrounding sentence: "${context}"` : "",
    ]
      .filter(Boolean)
      .join("\n");

    const raw = await generate({
      model: "flash",
      systemInstruction: SYSTEM,
      contents: [{ role: "user", parts: [{ text: user }] }],
      temperature: 0.2,
      maxOutputTokens: 300,
      jsonMode: true,
      // Disable Flash's default thinking: this is a deterministic term-rendering
      // task, and with thinking ON the token budget can be spent reasoning, leaving
      // the JSON answer empty (intermittent "could not parse model output").
      thinkingBudget: 0,
    });

    const parsed = extractJson(raw);
    if (!parsed) {
      return new Response(
        JSON.stringify({ ok: false, error: "could not parse model output" }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }
    if (!parsed.arabic || !parsed.arabic.trim()) {
      return new Response(
        JSON.stringify({ ok: false, error: "no Arabic returned" }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }

    return new Response(
      JSON.stringify({
        ok: true,
        arabic: parsed.arabic.trim(),
        gloss: (parsed.gloss ?? "").trim(),
        kind: parsed.kind === "script" ? "script" : "translation",
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
