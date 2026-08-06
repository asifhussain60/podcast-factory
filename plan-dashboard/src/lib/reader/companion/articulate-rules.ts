/**
 * articulate-rules.ts — the deterministic half of the tightening pass.
 *
 * Split from articulate.server.ts (which talks to Gemini) so the rules that
 * DECIDE things can be tested without a model client, an API key or a network:
 * whether a rewrite is allowed to replace the original, and where a word budget
 * falls. The model half is a call; this half is the contract.
 */

/**
 * What the tightening pass is asked to do. It lives HERE, beside the guards that
 * judge its output, rather than in the module that calls Gemini — two models now
 * run it: Gemini behind the Explain button, and Claude behind the student-reader
 * pass, which reaches it through the Node bridge. A prompt owned by one model's
 * client would have been copied to reach the other.
 */
export const ARTICULATION_PROMPT = `You are tightening a finished explanation. Return the SAME explanation, better articulated.

Do:
- Remove repetition: a point made twice, a heading restated as its section's first sentence, a closing paragraph that summarizes what was just said.
- Cut padding: "it is important to note that", "in other words" where nothing is being put another way.
- Keep the markdown structure — '### ' headings, '- ' and '1. ' lists, blank line between blocks.

Never:
- Never add a fact, a name, a date, a verse or a claim that is not already there.
- Never change, translate, transliterate or drop any Arabic script. Copy every Arabic run exactly.
- Never change or drop a Q|Surah:Verse citation.
- Never make the text longer than it was.

Return ONLY the tightened markdown. No preamble, no fences, no commentary.`;

/** Below this, a card is too short to hold repetition worth a second call. */
export const ARTICULATION_MIN_CHARS = 400;

/** Runs of Arabic script — compared as a set, so reordering is allowed. */
const ARABIC_RUN = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]+/g;
/** The persona's citation form: Q|2:10, Q|2:5-10, with or without a trailing &. */
const CITATION = /Q\|\s*\d+\s*:\s*\d+(?:\s*[-:]\s*\d+)?/g;

function multiset(text: string, re: RegExp): string[] {
  return (text.match(re) ?? []).map((s) => s.replace(/\s+/g, "")).sort();
}

/**
 * True when `after` kept everything it was not allowed to lose.
 *
 * Three gates, each learned from what a "polish" pass can quietly cost:
 *   1. every Arabic run survives — dropping a term removes the scholarship;
 *   2. every Q|Surah:Verse citation survives — dropping one turns a grounded
 *      claim into an unsourced one;
 *   3. the result is not longer — a tightening that grows is not a tightening.
 */
export function articulationGuardsPass(before: string, after: string): boolean {
  if (!after.trim()) return false;
  if (after.length > before.length) return false;
  const arabicAfter = new Set(multiset(after, ARABIC_RUN));
  for (const run of new Set(multiset(before, ARABIC_RUN)))
    if (!arabicAfter.has(run)) return false;
  const citesAfter = new Set(multiset(after, CITATION));
  for (const cite of new Set(multiset(before, CITATION)))
    if (!citesAfter.has(cite)) return false;
  return true;
}

/**
 * Trim to a word budget WITHOUT cutting mid-sentence.
 *
 * Blocks are dropped from the end until the total fits, so what remains is whole:
 * complete sections, complete list items, complete sentences. A hard character
 * slice would leave a card ending in the middle of a clause, which reads as a bug
 * in the reader rather than as a limit in the writer.
 */
export function capWords(markdown: string, maxWords: number): string {
  const words = (text: string) => (text.match(/\S+/g) ?? []).length;
  if (words(markdown) <= maxWords) return markdown;
  const blocks = markdown.split(/\n{2,}/);
  const kept: string[] = [];
  let total = 0;
  for (const block of blocks) {
    const n = words(block);
    if (total + n > maxWords) break;
    kept.push(block);
    total += n;
  }
  // A heading with nothing under it is worse than no heading.
  while (kept.length && /^#{1,6}\s/.test(kept[kept.length - 1])) kept.pop();
  // Never return nothing: a first block over budget is kept whole.
  return (kept.length ? kept : blocks.slice(0, 1)).join("\n\n").trim();
}
