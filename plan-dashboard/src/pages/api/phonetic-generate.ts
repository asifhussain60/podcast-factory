/**
 * POST /api/phonetic-generate
 *
 * Given a word in Arabic script OR transliteration, returns ONE house-style
 * respelling following the pronunciation-key convention: lowercase, syllables
 * separated by hyphens, the single stressed syllable in CAPITALS.
 *
 * Body: { word: string }
 * Returns: { phonetic: string }
 *
 * Uses Gemini Flash (cheap, fast). Mirrors the define-term/ask-chapter pattern.
 */

import type { APIRoute } from "astro";
import { generate, rateLimitCheck } from "../../lib/reader/gemini-server";
import { apiOk, apiError, apiServerError } from "../../lib/api-responses";

export const prerender = false;

const SYSTEM = `You produce SPOKEN pronunciation guides for Arabic words, in the exact house style of a podcast pronunciation index:
- ALL LOWERCASE except the ONE stressed syllable (in CAPITALS)
- syllables separated by hyphens
- vowel length from letters: aa=long-a, ee=long-e, oo=long-o, ay=day, ow=now, ah=father
- apostrophe ' for glottal catch (ʿayn/hamza) only when audible; often drop it
- q is rendered as "k" for TTS (so Qurʾān → kur-AAN)
- never include Arabic script in the output
- never spell out individual letters

Examples from the index:
  al-Ghazālī    → al-gha-zaa-LEE
  imām          → ee-MAAM
  Ṣāliḥ         → SAA-lih
  ʿAbd Allāh    → ab-dul-LAH
  quwwa         → QOO-wa
  Qurʾān        → kur-AAN
  al-Khiḍr      → al-KHIDR
  daʿwa         → DAH-wa
  sunna         → SOON-na

Reply with ONLY a JSON object: {"phonetic":"..."} — no markdown fences, no explanation.`;

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

  let word: string;
  try {
    const body = await request.json();
    word = (body.word ?? "").trim();
  } catch {
    return apiError("Invalid JSON");
  }

  if (!word) return apiError("Missing word");
  if (word.length > 120) return apiError("Word too long");

  try {
    const raw = await generate({
      model: "flash",
      systemInstruction: SYSTEM,
      contents: [{ role: "user", parts: [{ text: `Word: ${word}` }] }],
      temperature: 0.1,
      maxOutputTokens: 128,
      jsonMode: true,
      thinkingBudget: 0,
    });

    // Robust extraction: Gemini 2.5 Flash thinking can leak prose even with
    // jsonMode. Try strict parse → extract embedded JSON object → regex fallback.
    let phonetic = "";
    try {
      const parsed = JSON.parse(raw);
      phonetic = (parsed.phonetic ?? "").trim();
    } catch {
      // Try extracting a {...} object from anywhere in the text
      const objMatch = raw.match(/\{[^}]*"phonetic"\s*:\s*"([^"]+)"[^}]*\}/);
      if (objMatch) {
        phonetic = objMatch[1].trim();
      } else {
        // Last resort: strip fences and parse
        try {
          const stripped = raw.replace(/```[a-z]*\n?/gi, "").trim();
          const parsed = JSON.parse(stripped);
          phonetic = (parsed.phonetic ?? "").trim();
        } catch {
          // Give up — surface the raw text as error context
          return apiServerError(
            `Model returned non-JSON: ${raw.slice(0, 120)}`,
          );
        }
      }
    }

    if (!phonetic) return apiServerError("Model returned empty phonetic");
    return apiOk({ phonetic });
  } catch (e) {
    return apiServerError(String(e));
  }
};
