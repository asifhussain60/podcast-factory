/**
 * POST /api/ai/etymology
 *
 * Interactive etymology for the Book Composer's Refinement panel. Two-way:
 *   - an English word  → mapped to its Arabic equivalent, then rooted;
 *   - a transliterated Arabic term → rooted directly.
 *
 * Produces TWO outputs from one call:
 *   - `inline`    : the compact reading-edition insert that REPLACES the highlighted
 *                   word in the prose, e.g.
 *                   `gratitude (shukr, from the root sha-ka-ra — also shaakir, mashkoor)`.
 *   - `companion` : a richer, chapter-aware explanation for the Companion Panel —
 *                   the derived-word family PLUS how the root's original meaning fits
 *                   THIS chapter's topic (a teaching note, not a dictionary entry).
 *
 * Accuracy: the local KSESSIONS/KQUR mirror is consulted first (localhost:4390) for
 * an authoritative root; any hit is passed to Gemini as grounding so the model
 * confirms rather than invents. When the term is not in the mirror, Gemini Flash
 * generates and the human reviews the result before it is ever saved.
 *
 * Body: { word: string, context?: string, chapterTitle?: string, book?: string }
 * Returns: { ok, inline, companion, term, arabic, root, rootPhonetic, meaningEn,
 *            derivatives: {term, meaningEn}[], source: 'local+gemini'|'gemini' }
 */
import type { APIRoute } from "astro";
import { apiError, apiOk } from "../../../lib/api-responses";
import { generate, rateLimitCheck } from "../../../lib/reader/gemini-server";
import { fetchLocalTermDef } from "../../../lib/localServerClient";

export const prerender = false;

const SYSTEM = `You are a careful scholar of classical Arabic and the Ismaili/Shi'i tradition, compiling etymology for a study edition. Accuracy is paramount — NEVER invent a root; if you are not confident of a term's classical triliteral Arabic root, set "uncertain": true and do not guess.

You receive a highlighted word (English OR transliterated Arabic), its surrounding sentence, and the chapter's topic. If the word is English, first map it to the Arabic term the passage means; if already Arabic/transliterated, use it directly.

Return ONLY a JSON object with these fields:
  - term: the surface word as it should read in the prose (keep the author's English word if the highlight was English).
  - arabic: the Arabic-script term.
  - root: the triliteral root as separated consonants, e.g. "sh-k-r".
  - rootPhonetic: how to SAY the root aloud, e.g. "sha-ka-ra".
  - meaningEn: the root's core/original meaning, a few words.
  - derivatives: 2-4 objects {term, meaningEn} of words from the SAME root.
  - inline: a MINIMAL parenthetical that will REPLACE the highlighted word inline in reading-edition prose — just the original word followed by its Arabic-script equivalent in parentheses, and NOTHING else. EXACT shape: "<original word> (<arabic-term>)", e.g. "gratitude (شُكْر)". The root, derivatives, meanings and examples do NOT go here — they belong in the companion field. SCRIPT RULE FOR THIS FIELD: the Arabic term MUST be in ARABIC SCRIPT WITH FULL DIACRITICAL MARKS (voweled, e.g. شُكْر) — never Latin transliteration, and NEVER a Latin pronunciation guide (banned in the reading edition).
  - companion: a teaching note for the Companion panel, written in the plain, warm, concrete voice of a spoken lesson (a teacher unpacking a word aloud), NOT a dictionary entry. CRITICAL SCRIPT RULE: in this field write EVERY Arabic term — the root and each derivative — in ARABIC SCRIPT WITH FULL DIACRITICAL MARKS (tashkīl / harakāt: fatḥa, kasra, ḍamma, sukūn, shadda), NOT in Latin transliteration. Write the root with its letters separated by hyphens, e.g. ش-ك-ر, and derivatives fully voweled, e.g. شُكْر، شَاكِر، مَشْكُور. Any example phrase you give must also be in voweled Arabic script. (Latin transliteration is allowed ONLY as a brief parenthetical aid, never as the primary form.) The note MUST:
      (a) give the root (in Arabic script with diacritics) and its core/original meaning in plain words;
      (b) explain EVERY derivative you named in "inline" — write each in Arabic script with diacritics, say what it means, and where it helps add a short voweled-Arabic example of its use;
      (c) THEN draw the specific line from the root's original meaning to what THIS chapter is teaching (use the chapter topic).
    Style to imitate (this is HOW to write it, from real teaching sessions — note the Arabic script): "The word نُطْق means to articulate and to reason. It is also the root of مَنْطِق, meaning logic — so speech sits at the very root of our reasoning." Write 4-7 sentences.
  - uncertain: boolean; true only if you are not confident of the root.
Output ONLY the JSON object, no markdown fences.`;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) {
    return apiError("rate_limited", 429);
  }

  try {
    const { word, context, chapterTitle, book } = await request.json();
    if (!word || typeof word !== "string" || !word.trim()) {
      return apiError("missing word", 400);
    }

    // ── Authoritative root grounding from the local mirror, when available ──
    let grounding = "";
    let source: "local+gemini" | "gemini" = "gemini";
    try {
      const local = await fetchLocalTermDef(word.trim());
      if (
        local &&
        local.found &&
        (local.etymology || (local as { root?: string }).root)
      ) {
        const rootHint = (local as { root?: string }).root ?? "";
        grounding = [
          rootHint
            ? `Confirmed root (authoritative reference): ${rootHint}`
            : "",
          local.etymology ? `Reference etymology: ${local.etymology}` : "",
          local.arabic ? `Arabic: ${local.arabic}` : "",
        ]
          .filter(Boolean)
          .join("\n");
        if (grounding) source = "local+gemini";
      }
    } catch {
      /* mirror down → Gemini only */
    }

    // ── Morphology-corpus grounding: unconditional (local DB, no server hop).
    //    When the word resolves to exactly one root, the model receives the
    //    verified root + real derived family + Lane's meaning as authoritative.
    try {
      const { resolveTermAnyScript } =
        await import("../../../lib/db/morphology.server");
      const rec = resolveTermAnyScript(word.trim());
      if (rec) {
        const fam = rec.family
          .slice(0, 4)
          .map((l) => `${l.lemma_ar} (${l.occurrence_count}x)`)
          .join("; ");
        grounding = [
          grounding,
          `Verified morphology (Quranic Arabic Corpus): root ${rec.root_dashed} (${rec.root_ar}), ` +
            `${rec.occurrences}x in the Quran. Real derived words: ${fam}.` +
            (rec.lane_en ? ` Lane's Lexicon: ${rec.lane_en}` : ""),
        ]
          .filter(Boolean)
          .join("\n");
        source = "local+gemini";
      }
    } catch {
      /* morphology DB absent → prior behavior */
    }

    const user = [
      `Highlighted word: ${word.trim()}`,
      chapterTitle ? `Chapter topic: ${chapterTitle}` : "",
      book ? `Book: ${book}` : "",
      context ? `Surrounding passage: "${String(context).slice(0, 600)}"` : "",
      grounding
        ? `\n${grounding}\nUse the confirmed root; do not contradict it.`
        : "",
    ]
      .filter(Boolean)
      .join("\n");

    const text = await generate({
      model: "flash",
      systemInstruction: SYSTEM,
      contents: [{ role: "user", parts: [{ text: user }] }],
      temperature: 0.2,
      maxOutputTokens: 1400,
      jsonMode: true,
      thinkingBudget: 0, // no thinking tokens — they starve JSON output on Flash
    });

    // Tolerant extraction: strip fences, else grab the outermost JSON object.
    let parsed: Record<string, unknown> = {};
    const cleaned = text.replace(/^```json\s*|\s*```$/g, "").trim();
    const jsonSlice = cleaned.startsWith("{")
      ? cleaned
      : cleaned.slice(cleaned.indexOf("{"), cleaned.lastIndexOf("}") + 1);
    try {
      parsed = JSON.parse(jsonSlice);
    } catch {
      return apiError("model returned unparseable output", 502);
    }

    if (!parsed.inline || !parsed.root) {
      // Deliberate 200: "not found" is a normal outcome, not a server fault.
      return apiError("no etymology found for this word", 200);
    }

    return apiOk({ source, ...parsed }, 200, { "cache-control": "no-store" });
  } catch (e) {
    return apiError((e as Error).message, 500);
  }
};
