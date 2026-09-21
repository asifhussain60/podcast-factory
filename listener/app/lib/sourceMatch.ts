/**
 * Where in a source text a quoted passage most likely sits.
 *
 * Used to highlight the matching span in the EXTRACTED source, which is English like the book.
 * A scan is in the original script and cannot be matched to an English quote, so nothing here is
 * ever asked to guess across languages — the caller simply does not call it for a scan.
 *
 * It says "no match" rather than guessing: a highlight on the wrong sentence would send a
 * moderator to check the wrong words.
 */
export interface Span {
  start: number;
  end: number;
}

interface Token {
  word: string;
  start: number;
  end: number;
}

const tokens = (text: string): Token[] => {
  const out: Token[] = [];
  for (const m of text.matchAll(/[\p{L}\p{N}']+/gu))
    out.push({
      word: m[0].toLowerCase().replace(/^'+|'+$/g, ""),
      start: m.index,
      end: m.index + m[0].length,
    });
  return out.filter((t) => t.word !== "");
};

/** The share of the quote's words found in the best same-sized window; below this, no match. */
const MIN_OVERLAP = 0.65;

export function locateSpan(source: string, quote: string): Span | null {
  const want = tokens(quote);
  if (want.length < 2) return null;

  const have = tokens(source);
  if (have.length < want.length) return null;

  const wanted = new Map<string, number>();
  for (const t of want) wanted.set(t.word, (wanted.get(t.word) ?? 0) + 1);

  const size = want.length;
  let best = { score: 0, at: -1 };

  // A sliding window over the source; the count of wanted words inside it is kept as a running
  // total, so one pass over the text is enough however long the chapter is.
  const inside = new Map<string, number>();
  let score = 0;
  const add = (word: string, by: 1 | -1) => {
    const cap = wanted.get(word) ?? 0;
    if (cap === 0) return;
    const before = inside.get(word) ?? 0;
    const after = before + by;
    inside.set(word, after);
    // Only occurrences up to the quote's own count score, so a repeated word cannot inflate it.
    score += Math.min(after, cap) - Math.min(before, cap);
  };

  for (let i = 0; i < have.length; i++) {
    add(have[i]!.word, 1);
    if (i >= size) add(have[i - size]!.word, -1);
    if (i >= size - 1 && score > best.score) best = { score, at: i - size + 1 };
  }

  if (best.at < 0 || best.score / size < MIN_OVERLAP) return null;
  return { start: have[best.at]!.start, end: have[best.at + size - 1]!.end };
}
