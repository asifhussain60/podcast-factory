/**
 * POST /api/studio/quote-kind-suggest
 *
 * Gemini SUGGESTS a card kind for a selected quotation — it never writes one.
 * The Book Composer's card-type control (book-composer.ts, runSuggestQuoteKind)
 * shows the suggestion as a status line; the human still has to click Saying /
 * Verse / Prophetic tradition themselves, which POSTs to /api/studio/quote-kind
 * and is the only route that ever writes `_system/quote-kind.json`. Keeps the
 * rule quote-kind.mjs states in its own header: nothing in this app decides a
 * quotation's kind from its text alone, a person always does.
 *
 * Body: { slug, text }
 * Returns: { ok, kind: "hadith"|"poem"|"quote", reason }
 */
import type { APIRoute } from "astro";
import { apiError, apiOk } from "../../../lib/api-responses";
import { generate, rateLimitCheck } from "../../../lib/reader/gemini-server";

export const prerender = false;

const SYSTEM = `You classify a single Arabic quotation from an Islamic scholarly book into exactly one of three kinds, for a human editor to confirm — you are a SUGGESTION, never a final answer.

- "hadith": a prophetic tradition — words attributed to the Prophet or explicitly narrated as his saying.
- "poem": a line of classical verse or metered/rhymed composition (often introduced as "the poet says").
- "quote": anything else quoted — a maxim, a narrated exchange or dialogue, a scholar's own words, rhymed prose (saj') that is not attributed as either scripture-adjacent tradition or metered verse.

Return ONLY a JSON object: { "kind": "hadith"|"poem"|"quote", "reason": "one short clause, under 15 words" }. If genuinely unsure between two, pick the more likely one — the human reviewing your answer will correct it if wrong. Never return anything but one of these three ids.`;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) return apiError("rate_limited", 429);

  try {
    const { text } = await request.json();
    if (!text || typeof text !== "string" || !text.trim())
      return apiError("missing text", 400);

    const out = await generate({
      model: "flash",
      systemInstruction: SYSTEM,
      contents: [
        { role: "user", parts: [{ text: text.trim().slice(0, 800) }] },
      ],
      temperature: 0.1,
      maxOutputTokens: 200,
      jsonMode: true,
      thinkingBudget: 0,
    });

    const cleaned = out.replace(/^```json\s*|\s*```$/g, "").trim();
    const jsonSlice = cleaned.startsWith("{")
      ? cleaned
      : cleaned.slice(cleaned.indexOf("{"), cleaned.lastIndexOf("}") + 1);
    let parsed: { kind?: string; reason?: string } = {};
    try {
      parsed = JSON.parse(jsonSlice);
    } catch {
      return apiError("model returned unparseable output", 502);
    }
    if (!["hadith", "poem", "quote"].includes(String(parsed.kind)))
      return apiError("model returned an invalid kind", 502);

    return apiOk(
      { kind: parsed.kind, reason: String(parsed.reason ?? "") },
      200,
      { "cache-control": "no-store" },
    );
  } catch (e) {
    return apiError((e as Error).message, 500);
  }
};
