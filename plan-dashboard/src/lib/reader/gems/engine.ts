/**
 * gems/engine.ts — runs a Gem persona against Gemini for the two capabilities the
 * Companion Panel needs: explaining a concept ("teaching material") and answering
 * a reader's potential question. Both return a GemResult with the persona's prose
 * body separated from its closing Etymology section.
 *
 * JSON-envelope extraction is the primary path (matches every other jsonMode route
 * in api/ai/*); a raw-text regex split is the fallback for parse failures and for
 * the grounded path, which cannot run in jsonMode (generateWithGrounding builds its
 * own request body with no responseMimeType support).
 */
import {
  generate,
  generateWithGrounding,
  type GeminiModel,
} from "../gemini-server";
import { gemDef, DEFAULT_GEM_ID } from "./registry";
import type { GemDef, GemResult } from "./types";

const CONTEXT_TRUNCATE_AT = 80_000;

const JSON_ENVELOPE_ADDENDUM = `

---
Return your ENTIRE response as a single JSON object with exactly two fields:
  - "body": a STRING — the explanation, in markdown: '### ' headings, '- ' and '1. ' lists, blank line between blocks. No etymology here.
  - "etymology": an ARRAY OF STRINGS — one entry per term, each covering exactly one term in at most 60 words. Do NOT include the word "Etymology" as a heading in any entry; the reader supplies that label. Empty array if there is nothing worth saying.
No other fields. No markdown fences around the JSON.`;

function resolveGem(gemId: string | undefined): GemDef {
  const gem = gemDef(gemId ?? DEFAULT_GEM_ID);
  if (!gem) throw new Error(`unknown_gem:${gemId}`);
  return gem;
}

function truncateContext(context: string | undefined): string | undefined {
  if (!context) return context;
  return context.length > CONTEXT_TRUNCATE_AT
    ? context.slice(0, CONTEXT_TRUNCATE_AT) + "\n[...truncated]"
    : context;
}

/** The label a passage-with-a-question turn carries. Exported so the bridge and
 *  the API route ask in the same words. */
export const QUESTION_LABEL = "Answer this question a reader might ask";
/** The label a bare concept/passage turn carries. */
export const CONCEPT_LABEL = "Explain this concept";

export function buildUserTurn(opts: {
  label: string;
  value: string;
  bookTitle?: string;
  context?: string;
  chapterContext?: string;
}): string {
  return [
    opts.bookTitle ? `Book: ${opts.bookTitle}` : "",
    // The WHOLE chapter, when the caller has it. A companion explanation is
    // about a passage inside an argument, and the paragraph around it is not
    // that argument: it cannot say what the Master has already established, what
    // question the boy asked three pages earlier, or which term was defined
    // before being used here. Until 2026-07-27 the Scholar received only the
    // containing paragraph capped at 600 characters — 0.75% of the budget below
    // — while the plain /api/ai/explain route on the same page sent the entire
    // chapter. It is listed BEFORE the passage so the model reads the argument
    // first and the sentence second.
    opts.chapterContext
      ? `The full chapter this passage belongs to, for orientation only — explain the passage, not the chapter:\n"""${truncateContext(opts.chapterContext)}"""`
      : "",
    opts.context
      ? `Surrounding passage: "${truncateContext(opts.context)}"`
      : "",
    `${opts.label}: ${opts.value}`,
  ]
    .filter(Boolean)
    .join("\n");
}

/** Fence-strip + JSON.parse, then brace-extraction fallback (matches arabic-term.ts's extractJson). */
function extractGemJson(
  raw: string,
): { body?: string; etymology?: unknown } | null {
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

/** Defense-in-depth fallback: split raw text on a bare "Etymology" line. */
function splitEtymology(text: string): {
  body: string;
  etymology: string[];
} {
  const m = text.match(/\n\s*#*\s*Etymology\s*\n/i);
  if (!m || m.index === undefined) return { body: text.trim(), etymology: [] };
  // One item per paragraph — the same unit the JSON path returns, so a parse
  // failure degrades to the same shape rather than to a different one.
  const etymology = toItems(text.slice(m.index + m[0].length));
  return { body: text.slice(0, m.index).trim(), etymology };
}

/** Normalize whatever the model returned for `etymology` into discrete items. */
function toItems(value: unknown): string[] {
  const raw = Array.isArray(value)
    ? value.map((v) => String(v ?? ""))
    : String(value ?? "").split(/\n{2,}/);
  return raw
    .map((s) =>
      s
        .replace(/^\s*[-*]\s+/, "")
        .replace(/\s+/g, " ")
        .trim(),
    )
    .filter(Boolean);
}

/** Parse whatever a model returned into a GemResult. Exported because the
 *  student-reader bridge runs the same persona through Claude and must read the
 *  reply with the SAME parser — a second one would disagree about where the
 *  etymology ends on exactly the replies that are hardest to parse. */
export function toResult(raw: string, sources?: string[]): GemResult {
  const parsed = extractGemJson(raw);
  if (parsed && typeof parsed.body === "string") {
    return {
      raw,
      body: parsed.body.trim(),
      etymology: toItems(parsed.etymology),
      ...(sources ? { sources } : {}),
    };
  }
  const split = splitEtymology(raw);
  return { raw, ...split, ...(sources ? { sources } : {}) };
}

// `runGemConcept` was removed 2026-08-06. It built its own user turn and then
// called Gemini, which is exactly what `prepareCard` + `runGemPrepared` now do
// for both writers; its last caller went with them. A second path to the same
// card is a second place for the persona's turn to drift.

/** The persona's system instruction, envelope included — what a caller must send
 *  a model to get a card back. Exported for the bridge, which hands it to Claude
 *  instead of Gemini and so cannot go through `generate` here. */
export function gemSystemInstruction(gemId?: string): string {
  return resolveGem(gemId).systemPrompt + JSON_ENVELOPE_ADDENDUM;
}

/**
 * Run a turn that `prepareCard` already assembled.
 *
 * The narrow seam between the two writers: the Explain button lands here with
 * Gemini, and the student-reader bridge takes the same `system` and `user` to
 * Claude. Everything on either side of this call is shared, so the model is the
 * only thing that differs between a card you press for and a card the pass files.
 */
export async function runGemPrepared(opts: {
  system: string;
  user: string;
  model?: GeminiModel;
}): Promise<GemResult> {
  const raw = await generate({
    model: opts.model ?? "pro",
    systemInstruction: opts.system,
    contents: [{ role: "user", parts: [{ text: opts.user }] }],
    temperature: 0.3,
    maxOutputTokens: 4000,
    jsonMode: true,
  });
  return toResult(raw);
}

export async function runGemQuestion(opts: {
  gemId?: string;
  question: string;
  context?: string;
  chapterContext?: string;
  bookTitle?: string;
  model?: GeminiModel;
  grounded?: boolean;
}): Promise<GemResult> {
  const gem = resolveGem(opts.gemId);
  const user = buildUserTurn({
    label: "Answer this question a reader might ask",
    value: opts.question,
    bookTitle: opts.bookTitle,
    context: opts.context,
    chapterContext: opts.chapterContext,
  });

  if (opts.grounded) {
    const prompt = `${gem.systemPrompt}\n\n---\n\n${user}`;
    const { text, sources } = await generateWithGrounding(prompt, {
      model: opts.model ?? "pro",
      temperature: 0.3,
      maxOutputTokens: 4000,
    });
    return toResult(text, sources);
  }

  const raw = await generate({
    model: opts.model ?? "pro",
    systemInstruction: gem.systemPrompt + JSON_ENVELOPE_ADDENDUM,
    contents: [{ role: "user", parts: [{ text: user }] }],
    temperature: 0.3,
    maxOutputTokens: 4000,
    jsonMode: true,
  });

  return toResult(raw);
}
