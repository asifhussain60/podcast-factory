/**
 * passage-match.ts — find a note's VERBATIM passage inside rendered prose.
 *
 * One matcher, three callers: the LIVE Session reader, the Composer's read view,
 * and the Composer's TipTap edit canvas. They disagree about coordinates — the
 * first two want a DOM text node and an offset, the third wants a ProseMirror
 * document position — so the core works in a caller-supplied coordinate space and
 * each side maps back into its own.
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
export function normalizeQuote(s: string): string {
  return String(s ?? "")
    .replace(/\s+/g, " ")
    .trim();
}

/** One piece of source text, in the caller's own coordinate space. */
export interface PassageChunk {
  text: string;
  /** Coordinate of `text[0]`. Chunks must be given in document order. */
  at: number;
  /** True when this chunk opens a new block (paragraph, list item, heading).
   *  A block boundary reads as a space, so the end of one paragraph can never
   *  fuse with the start of the next into a match that isn't really there. */
  blockStart?: boolean;
}

/** The normalized projection, with every character mapped back to its source. */
export interface FlatText {
  /** Lowercased, single-spaced. */
  text: string;
  /** `pos[i]` — caller coordinate of `text[i]`. */
  pos: number[];
  /** `chunk[i]` — index of the chunk `text[i]` came from. */
  chunk: number[];
}

/** A contiguous slice of ONE chunk, in caller coordinates; `to` is exclusive. */
export interface PassageRange {
  chunk: number;
  from: number;
  to: number;
}

export function flatten(chunks: PassageChunk[]): FlatText {
  const chars: string[] = [];
  const pos: number[] = [];
  const chunkOf: number[] = [];
  chunks.forEach((c, idx) => {
    if (c.blockStart && chars.length && chars[chars.length - 1] !== " ") {
      chars.push(" ");
      pos.push(c.at);
      chunkOf.push(idx);
    }
    for (let i = 0; i < c.text.length; i++) {
      const ch = c.text[i];
      const space = /\s/.test(ch);
      if (space && chars[chars.length - 1] === " ") continue; // collapse runs
      chars.push(space ? " " : ch.toLowerCase());
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
export function findPassage(flat: FlatText, quote: string): PassageRange[] {
  const needle = normalizeQuote(quote).toLowerCase();
  if (needle.length < 4) return []; // too short to be a passage; never guess
  const start = flat.text.indexOf(needle);
  if (start < 0) return [];
  const end = start + needle.length - 1; // inclusive

  const ranges: PassageRange[] = [];
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

const BLOCK_SEL = "p, li, blockquote, h1, h2, h3, h4, td, dd, dt, figcaption";

interface DomChunks {
  nodes: Text[];
  chunks: PassageChunk[];
}

function domChunks(root: HTMLElement): DomChunks {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  const chunks: PassageChunk[] = [];
  let prevBlock: Element | null = null;
  let at = 0;
  let node: Node | null;
  while ((node = walker.nextNode())) {
    const t = node as Text;
    const text = t.textContent ?? "";
    if (!text) continue;
    const block = t.parentElement?.closest(BLOCK_SEL) ?? null;
    chunks.push({ text, at, blockStart: block !== prevBlock });
    prevBlock = block;
    nodes.push(t);
    at += text.length + 1; // +1 gap so consecutive nodes are never contiguous
  }
  return { nodes, chunks };
}

/**
 * Wrap each passage in `<span class=...>` elements so it can be tinted.
 *
 * Returns the spans per note id. The DOM is re-read for EVERY note, because
 * wrapping splits the text nodes an earlier index described. Passages are few and
 * chapters are small, so the cost is nothing next to the class of bug it avoids.
 */
export function markPassages(
  root: HTMLElement,
  notes: { id: string; quote?: string }[],
  className: string,
): Map<string, HTMLElement[]> {
  const marked = new Map<string, HTMLElement[]>();
  for (const note of notes) {
    if (!note.quote) continue;
    const { nodes, chunks } = domChunks(root);
    const ranges = findPassage(flatten(chunks), note.quote);
    if (!ranges.length) continue;

    // Back to front: surroundContents splits the node it wraps, so working from
    // the end keeps every earlier range's offsets valid.
    const spans: HTMLElement[] = [];
    for (const r of [...ranges].reverse()) {
      const node = nodes[r.chunk];
      const base = chunks[r.chunk].at;
      const range = document.createRange();
      try {
        range.setStart(node, r.from - base);
        range.setEnd(node, Math.min(r.to - base, node.length));
      } catch {
        continue;
      }
      const span = document.createElement("span");
      span.className = className;
      span.dataset.note = note.id;
      try {
        range.surroundContents(span);
        spans.unshift(span);
      } catch {
        /* fragment sits inside another note's mark — leave it unwrapped */
      }
    }
    if (spans.length) marked.set(note.id, spans);
  }
  return marked;
}
