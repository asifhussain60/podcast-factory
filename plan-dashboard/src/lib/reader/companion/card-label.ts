/**
 * card-label.ts — the title a filed Companion card carries.
 *
 * Its own module, and client-safe, because two callers need the SAME answer from
 * different runtimes: the Gem panel in the browser, which files a card when you
 * press Explain, and the Node bridge behind the student-reader pass, which files
 * one without a browser. A second copy in either place would let two cards
 * explaining the same sentence show different titles.
 *
 * Deliberately the passage itself rather than a paraphrase of it: the card's job
 * is to say which sentence it belongs to, and a summarized title makes that a
 * guess.
 */

/** Longest title kept whole. Past this the passage is elided rather than reworded. */
export const LABEL_MAX_CHARS = 72;

/** A short card title for a filed note — the passage, not a paraphrase of it. */
export function labelFor(text: string): string {
  const trimmed = (text ?? "").trim();
  return trimmed.length <= LABEL_MAX_CHARS
    ? trimmed
    : `${trimmed.slice(0, LABEL_MAX_CHARS - 3).trimEnd()}…`;
}
