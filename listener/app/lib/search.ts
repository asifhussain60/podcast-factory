/**
 * The parts of search that BOTH sides need.
 *
 * This module exists because of a real failure rather than for tidiness. The
 * results page renders snippets while the reader is looking at them, so
 * `snippetOf` runs in the browser — but it started life beside the queries in
 * `search.server.ts`, and importing it from the route pulled that whole module,
 * `VISIBLE_SQL` and all, toward the client bundle. React Router refuses to build
 * that (`Server-only module referenced by client`), which is the right answer:
 * the alternative is a bundler quietly shipping the entitlement SQL to the page.
 *
 * So the split is by WHERE THE CODE RUNS, not by subject. Anything that touches
 * the database stays in `search.server.ts`. The shapes it returns, and the pure
 * function that turns a passage into a snippet, live here where both may import
 * them. Types are erased at build time and were never the problem; the function
 * was.
 */

import { fold } from "./search-fold";

/** Which indexed field the query is aimed at. Never which rows may come back. */
export type Scope = "all" | "titles" | "content" | "verses";

export interface Hit {
  id: number;
  slug: string;
  bookTitle: string;
  bucket: string;
  kind: string;
  anchorKey: string | null;
  heading: string | null;
  ordinal: number;
  episodeNumber: number | null;
  quote: string;
  arabic: string | null;
  label: string | null;
  surah: number | null;
  ayah: number | null;
  /** Where clicking it goes. Built on the server so the two callers agree. */
  href: string;
}

export interface Facet {
  value: string;
  label: string;
  passages: number;
  books: number;
}

export interface Segment {
  text: string;
  hit: boolean;
}

/**
 * The words around the first match, with the matching words marked.
 *
 * FTS5 has its own `snippet()` and it is deliberately not used. That function
 * returns the text of the INDEXED column, which here is the folded form: no
 * capitals, no punctuation, and Arabic stripped of the vowels this whole library
 * is careful to print. Showing it would mean the results quoted these books in a
 * spelling the books do not use.
 *
 * So the snippet is built from `quote` — the real text — by folding each word as
 * it goes and asking whether any query term begins it. Word by word rather than
 * by offset, because folding does not preserve them: `al-Kirmani` is one word
 * before it and two after.
 */
export function snippetOf(quote: string, terms: string[], radius = 14): Segment[] {
  const words = quote.split(/\s+/).filter(Boolean);
  if (words.length === 0 || terms.length === 0) {
    return [{ text: quote, hit: false }];
  }

  const isHit = words.map((w) => {
    const parts = fold(w).split(" ").filter(Boolean);
    return parts.some((p) => terms.some((t) => p.startsWith(t)));
  });

  const first = isHit.indexOf(true);
  // No word matched — a prefix match inside the index that the word-wise test
  // cannot see. Show the opening rather than nothing.
  const centre = first === -1 ? 0 : first;
  const start = Math.max(0, centre - radius);
  const end = Math.min(words.length, centre + radius + 1);

  const segments: Segment[] = [];
  /** Append, merging into the previous segment when it is the same kind. */
  const push = (text: string, hit: boolean) => {
    if (text === "") return;
    const last = segments[segments.length - 1];
    if (last !== undefined && last.hit === hit) last.text += text;
    else segments.push({ text, hit });
  };

  if (start > 0) push("… ", false);

  for (let i = start; i < end; i++) {
    if (i > start) push(" ", false);
    if (!isHit[i]) {
      push(words[i], false);
      continue;
    }
    // Only the WORD is marked, not the punctuation stuck to it. Marking the
    // whole whitespace-delimited token put the comma inside the highlight —
    // `Allah,` — which reads as though the search had matched the punctuation
    // and makes a paragraph of hits look careless. An apostrophe INSIDE a word
    // is not stripped: `Allah's` is one word and is marked as one.
    //
    // `\p{M}` — combining marks — is in the KEPT class alongside letters and
    // digits, and on this corpus that is not a detail. A shadda or a kasra is
    // not a letter, so a class of only `\p{L}\p{N}` reads the trailing `ّ` of
    // `اَلْكِرْمَانِيّ` as punctuation and tears it off the word it belongs to.
    // That is mangling Arabic, not tidying punctuation.
    const [, lead = "", core = "", tail = ""] =
      /^([^\p{L}\p{N}\p{M}]*)(.*?)([^\p{L}\p{N}\p{M}]*)$/u.exec(words[i]) ?? [];
    push(lead, false);
    push(core, true);
    push(tail, false);
  }

  if (end < words.length) push(" …", false);

  return segments;
}
