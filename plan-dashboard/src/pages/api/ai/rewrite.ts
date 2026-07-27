/**
 * POST /api/ai/rewrite
 *
 * Body: { text: string, mode?: 'clarify'|'tighten'|'simplify'|'formal', context?: string }
 * Returns: { options: string[] }   // 3 rewrite candidates
 *
 * Used by ChapterEditor's AI-assist sparkle button. Gemini Flash returns
 * three short rewrites; the editor renders them as cards and the user
 * accepts one or rejects all.
 */

import type { APIRoute } from "astro";
import { generate, rateLimitCheck } from "../../../lib/reader/gemini-server";

export const prerender = false;

const MODE_HINTS: Record<string, string> = {
  clarify:
    "Rewrite for clarity. Same length or shorter. Preserve every named entity and transliterated Arabic term verbatim.",
  tighten:
    "Tighten — remove filler, redundancy, and stock phrasing. Cut word count by 20-30% if possible without losing content.",
  simplify:
    "Simplify the vocabulary for a non-specialist reader. Keep technical terms but explain them in-line when natural.",
  expand:
    "Expand — add helpful detail, unpack implicit reasoning, and gloss difficult terms in-line. Grow the passage ~20-40% WITHOUT inventing facts, doctrine, names, or citations not already implied. Preserve every named entity and transliterated Arabic term verbatim.",
  formal:
    "Raise the register slightly. Scholarly, restrained, no contractions. Same length.",
};

const SYSTEM = (
  modeHint: string,
) => `You are a careful editor working on a scholarly Ismaili text.
${modeHint}

Rules:
- Preserve every transliterated Arabic term (Hujjah, Sayyidina, Da'i, etc.) and proper noun verbatim.
- Preserve meaning. If you would need to drop a substantive claim, don't.
- Match the source's voice: formal-but-readable, no marketing tone.

Return ONLY a JSON object: {"options": ["rewrite 1", "rewrite 2", "rewrite 3"]}.
Three DISTINCT alternatives. No prefatory text, no markdown fences.`;

/** Does this string look like the envelope rather than a rewrite? */
function looksLikeEnvelope(s: string): boolean {
  const t = s.trimStart();
  return t.startsWith("{") && t.includes('"options"');
}

/**
 * Never hand a caller an "option" that is actually the envelope.
 *
 * The two parses above fail together in one real case: the model's JSON arrives
 * TRUNCATED — `{"options": ["done", "also done", "half a th` — so there is no
 * closing brace for the regex to find and no valid document for JSON.parse. The
 * fallback then wraps the whole fragment as options[0], and a caller that trusts
 * the contract offers a literal `{"options": [...]}` blob as a rewrite. On
 * 2026-07-27 that reached a book: the Composer showed the JSON as its one
 * suggestion, one click from pasting it into the prose. The edit surface carried
 * a private re-parse of its own and survived; the Composer had none, and a guard
 * only one of two callers holds is not a guard.
 *
 * Truncation is recoverable, because the rewrites that finished are complete JSON
 * string literals — only the last one is cut. So salvage those and drop the
 * fragment: two good rewrites beat one blob, and beat an error the user cannot
 * act on. If nothing survives, return nothing, which makes the caller say "no
 * suggestions returned" instead of rendering machinery as prose.
 */
export function salvage(options: string[]): string[] {
  const clean = options.filter((s) => s && !looksLikeEnvelope(s));
  if (clean.length) return clean;

  const blob = options.find(looksLikeEnvelope);
  if (!blob) return [];

  try {
    const inner = JSON.parse(blob);
    if (Array.isArray(inner.options))
      return inner.options
        .map((s: unknown) => String(s).trim())
        .filter(Boolean)
        .slice(0, 3);
  } catch {
    // Unterminated. Pull out every COMPLETE string literal after `"options"`,
    // which is exactly the set of rewrites the model finished writing.
    const arrayStart = blob.indexOf("[", blob.indexOf('"options"'));
    if (arrayStart === -1) return [];
    const rescued: string[] = [];
    const literal = /"((?:[^"\\]|\\.)*)"/g;
    literal.lastIndex = arrayStart;
    for (let m = literal.exec(blob); m; m = literal.exec(blob)) {
      try {
        const s = JSON.parse(`"${m[1]}"`).trim();
        if (s) rescued.push(s);
      } catch {
        /* skip a literal that will not unescape */
      }
    }
    return rescued.slice(0, 3);
  }
  return [];
}

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok)
    return new Response(JSON.stringify({ error: "rate_limited" }), {
      status: 429,
    });
  try {
    const { text, mode = "clarify", context } = await request.json();
    if (!text || typeof text !== "string")
      return new Response(JSON.stringify({ error: "missing text" }), {
        status: 400,
      });
    const hint = MODE_HINTS[mode] ?? MODE_HINTS.clarify;
    const user = [
      context
        ? `Surrounding context (do not rewrite, just orient yourself):\n"""${context}"""`
        : "",
      "Rewrite this passage three different ways:",
      `"""${text}"""`,
    ]
      .filter(Boolean)
      .join("\n\n");

    const raw = await generate({
      model: "flash",
      systemInstruction: SYSTEM(hint),
      contents: [{ role: "user", parts: [{ text: user }] }],
      temperature: 0.7,
      maxOutputTokens: 1500,
      jsonMode: true,
    });

    let parsed: any = {};
    // Tolerate a code fence or stray prose around the JSON (some model turns wrap it).
    const jsonText = (raw.match(/\{[\s\S]*\}/) ?? [raw])[0];
    try {
      parsed = JSON.parse(jsonText);
    } catch {
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = { options: [raw] };
      }
    }
    if (!Array.isArray(parsed.options))
      parsed.options = [String(parsed.options ?? raw)];
    parsed.options = parsed.options
      .slice(0, 3)
      .map((s: any) => String(s).trim());

    parsed.options = salvage(parsed.options);

    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "cache-control": "no-store",
      },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), {
      status: 500,
    });
  }
};
