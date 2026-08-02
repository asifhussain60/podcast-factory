/**
 * passage-match.mjs — find a stored VERBATIM passage inside rendered prose.
 *
 * One matcher, FOUR callers: the LIVE Session reader, the Composer's read view,
 * the Composer's TipTap edit canvas, and the PDF renderer. They disagree about
 * coordinates — the
 * first two want a DOM text node and an offset, the third a ProseMirror document
 * position, the fourth an offset into an HTML string — so the core works in a
 * caller-supplied coordinate space and each side maps back into its own.
 *
 * Plain .mjs, and that is the point: the PDF build runs under bare node and
 * cannot import the TypeScript side, exactly as with anchor-key.mjs and
 * para-blocks.mjs. The TS module of the same name re-exports every symbol here
 * and adds the DOM-only helpers, so no caller had to learn a new import path and
 * there is only ever ONE implementation of the matching.
 *
 * Two properties matter, both learned from the bugs this replaced:
 *
 *   1. Matching is done on a whitespace-NORMALIZED projection of the text, so a
 *      quote captured from a selection still matches prose that wraps differently
 *      or carries a line break where the quote has a space.
 *   2. A passage may cross inline markup. A sentence containing an italicized
 *      term lives in three text nodes; matching one node at a time silently found
 *      nothing, which excluded exactly the sentences most worth annotating. The
 *      match therefore spans chunks and comes back as one run per chunk.
 */

/** Collapse every run of whitespace to one space and trim. */
export function normalizeQuote(s) {
  return String(s ?? "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Fold one character to what BOTH renderers agree on, or to nothing.
 *
 * The same source sentence reaches the two surfaces spelled differently. The
 * Composer shows the PDF's rendering, which keeps scholarly transliteration
 * (ẓāhir, bāṭin); the LIVE reader folds it to plain English (zahir, batin) — see
 * `simplifyTransliteration` in lib/translit.ts. A quote captured in one therefore
 * could not be found in the other, and a card that appeared beside the prose in
 * the Composer vanished in the reader. Vowelled Arabic has the same problem: the
 * diacritics are combining marks, so the same word matched only if it carried the
 * same vowelling.
 *
 * So matching happens on a folded skeleton: combining marks and the modifier
 * letters (ʾ ʿ and their curly-quote spellings) fold to NOTHING, everything else
 * to its base character, lowercased. Positions survive because the flattener maps
 * every EMITTED character back to the source index it came from — a character
 * that folds away simply contributes no entry.
 */
export function foldChar(ch) {
  if (/[\u02BE\u02BF\u2018\u2019\u02B9\u02BC']/.test(ch)) return "";
  const base = ch
    .normalize("NFD")
    .replace(/[\u0300-\u036f\u064B-\u0652\u0670]/g, "");
  return base.slice(0, 1).toLowerCase();
}

/** The whole string, folded — used for the needle. */
export function foldText(s) {
  let out = "";
  for (const ch of String(s ?? "")) out += foldChar(ch);
  return out;
}

/** One piece of source text, in the caller's own coordinate space. */

/** The normalized projection, with every character mapped back to its source. */

/** A contiguous slice of ONE chunk, in caller coordinates; `to` is exclusive. */

export function flatten(chunks) {
  const chars = [];
  const pos = [];
  const chunkOf = [];
  chunks.forEach((c, idx) => {
    if (c.blockStart && chars.length && chars[chars.length - 1] !== " ") {
      chars.push(" ");
      pos.push(c.at);
      chunkOf.push(idx);
    }
    for (let i = 0; i < c.text.length; i++) {
      const ch = c.text[i];
      if (/\s/.test(ch)) {
        if (chars[chars.length - 1] === " ") continue; // collapse runs
        chars.push(" ");
      } else {
        const folded = foldChar(ch);
        if (!folded) continue; // a mark the other surface does not print
        chars.push(folded);
      }
      pos.push(c.at + i);
      chunkOf.push(idx);
    }
  });
  return { text: chars.join(""), pos, chunk: chunkOf };
}

/**
 * Locate `quote` in a flattened projection.
 *
 * Returns one range per chunk the passage crosses (empty when it isn't there).
 * A range covers everything between its first and last matched character, so
 * whitespace collapsed inside the match is included rather than left behind.
 */
export function findPassage(flat, quote) {
  const needle = foldText(normalizeQuote(quote));
  if (needle.length < 4) return []; // too short to be a passage; never guess
  const start = flat.text.indexOf(needle);
  if (start < 0) return [];
  const end = start + needle.length - 1; // inclusive

  const ranges = [];
  let i = start;
  while (i <= end) {
    const chunk = flat.chunk[i];
    const from = flat.pos[i];
    let last = from;
    while (i <= end && flat.chunk[i] === chunk) {
      last = flat.pos[i];
      i++;
    }
    ranges.push({ chunk, from, to: last + 1 });
  }
  return ranges;
}

// ── DOM binding ────────────────────────────────────────────────────────────
// Each text node gets its own coordinate block, so a match always breaks at node
// boundaries and every range can be wrapped with a single-node Range.
