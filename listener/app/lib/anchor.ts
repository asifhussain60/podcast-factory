/**
 * Where a highlight is, and how to find it again after the book changes.
 *
 * The chapter body is HTML rendered once at publish time by plan-dashboard's
 * `renderMarkdown` — the same function the printed book goes through. It carries
 * no per-paragraph identifiers, and adding some would mean editing that shared
 * renderer and its golden fixture, which would put the print edition's output at
 * risk to serve a screen feature. So a passage is located from the DOM instead.
 *
 * An anchor is four facts, and the redundancy is the whole design:
 *
 *   blockIndex   which top-level child of `.pf-chapter-body` it sits in
 *   start / end  character offsets into that block's text
 *   quote        the exact text that was selected
 *   prefix       up to 48 characters immediately before it
 *
 * Offsets are fast and are tried first, but they are the part that ROTS: a
 * re-compose that adds a word earlier in the paragraph shifts every offset after
 * it. `quote` is therefore the authority — an anchor resolves only when the text
 * at those offsets still equals the quote. When it does not, the quote is
 * searched for; `prefix` is what tells two occurrences of the same sentence
 * apart. A quote that is absent, or present twice with no distinguishing prefix,
 * yields `orphaned` — the annotation is kept and listed, and is NOT painted
 * anywhere. Nothing is ever guessed onto a passage it did not come from.
 *
 * Everything here works on plain text extracted from the DOM, so the same
 * functions run in a browser and in a test with a stub. The only DOM-specific
 * part is `blocksOf` and the range walking at the bottom.
 */

export interface Anchor {
  blockIndex: number;
  startOffset: number;
  endOffset: number;
  quote: string;
  prefix: string;
}

/** Where an anchor landed, and whether it had to move to get there. */
export type Resolution =
  | { status: "exact"; blockIndex: number; startOffset: number; endOffset: number }
  | { status: "moved"; blockIndex: number; startOffset: number; endOffset: number }
  | { status: "orphaned" };

/** How much preceding text is kept. Long enough to separate a repeated line. */
export const PREFIX_LENGTH = 48;

/**
 * Whitespace is normalised before every comparison.
 *
 * HTML collapses runs of whitespace when it renders but keeps them in the source,
 * so `textContent` and what the reader actually saw disagree wherever the
 * markdown wrapped a line. Comparing raw text would make an anchor fail to
 * resolve on a paragraph nobody edited — reported as "the text has changed" when
 * nothing had. Both sides go through this, always.
 */
export const normalizeText = (s: string): string => s.replace(/\s+/g, " ").trim();

/** The same normalisation, but preserving offsets — used for searching in place. */
const flatten = (s: string): string => s.replace(/\s+/g, " ");

/* -------------------------------------------------------------------------- */
/* Resolving — pure, so it is testable without a DOM                           */
/* -------------------------------------------------------------------------- */

/**
 * Find `anchor` among `blocks`, the chapter's block texts in document order.
 *
 * Order of attempts, and each is a strictly wider net than the last:
 *
 *   1. The stored offsets in the stored block. The common case, and O(1).
 *   2. Anywhere in the stored block. Covers an edit elsewhere in the paragraph.
 *   3. Anywhere in the chapter, with `prefix` breaking ties. Covers a paragraph
 *      that moved, split or merged.
 *
 * Step 3 refuses on ambiguity rather than picking the first hit. On a religious
 * text a highlight landing on the wrong sentence is worse than a highlight that
 * says it lost its place, because the first is silent.
 */
export function resolveAnchor(anchor: Anchor, blocks: string[]): Resolution {
  const quote = normalizeText(anchor.quote);
  if (quote === "") return { status: "orphaned" };

  // 1. Exactly where it says it is.
  const home = blocks[anchor.blockIndex];
  if (home !== undefined) {
    const flat = flatten(home);
    if (normalizeText(flat.slice(anchor.startOffset, anchor.endOffset)) === quote) {
      return {
        status: "exact",
        blockIndex: anchor.blockIndex,
        startOffset: anchor.startOffset,
        endOffset: anchor.endOffset,
      };
    }

    // 2. Elsewhere in the same block. Unique-within-block is enough here: the
    //    reader chose this paragraph, so a repeat inside it is still the right
    //    paragraph, and the stored offset picks the nearer occurrence.
    const inHome = occurrences(flat, quote);
    if (inHome.length === 1) {
      return {
        status: "moved",
        blockIndex: anchor.blockIndex,
        startOffset: inHome[0],
        endOffset: inHome[0] + quote.length,
      };
    }
    if (inHome.length > 1) {
      const best = nearest(inHome, anchor.startOffset);
      return {
        status: "moved",
        blockIndex: anchor.blockIndex,
        startOffset: best,
        endOffset: best + quote.length,
      };
    }
  }

  // 3. Anywhere in the chapter.
  const hits: { blockIndex: number; offset: number }[] = [];
  for (let i = 0; i < blocks.length; i++) {
    for (const offset of occurrences(flatten(blocks[i]), quote)) {
      hits.push({ blockIndex: i, offset });
    }
  }

  if (hits.length === 0) return { status: "orphaned" };

  if (hits.length === 1) {
    return {
      status: "moved",
      blockIndex: hits[0].blockIndex,
      startOffset: hits[0].offset,
      endOffset: hits[0].offset + quote.length,
    };
  }

  // Several. The prefix has to settle it, and if it cannot, nothing does.
  const prefix = normalizeText(anchor.prefix);
  if (prefix !== "") {
    const byPrefix = hits.filter((h) => {
      const before = normalizeText(flatten(blocks[h.blockIndex]).slice(0, h.offset));
      return before.endsWith(prefix);
    });
    if (byPrefix.length === 1) {
      return {
        status: "moved",
        blockIndex: byPrefix[0].blockIndex,
        startOffset: byPrefix[0].offset,
        endOffset: byPrefix[0].offset + quote.length,
      };
    }
  }

  return { status: "orphaned" };
}

/** Every index at which `needle` occurs in `haystack`, comparing normalised. */
function occurrences(haystack: string, needle: string): number[] {
  const out: number[] = [];
  if (needle === "") return out;
  let from = 0;
  for (;;) {
    const at = haystack.indexOf(needle, from);
    if (at === -1) return out;
    out.push(at);
    from = at + 1;
  }
}

const nearest = (candidates: number[], to: number): number =>
  candidates.reduce((best, c) => (Math.abs(c - to) < Math.abs(best - to) ? c : best));

/* -------------------------------------------------------------------------- */
/* Reading a selection out of the DOM                                          */
/* -------------------------------------------------------------------------- */

/**
 * The chapter's top-level blocks — the unit `blockIndex` counts.
 *
 * Element children, not text nodes: `renderMarkdown` emits a flat run of
 * `<p>`, `<blockquote>`, `<ul>`, `<hr>` and so on, and a blockquote is ONE block
 * even though it contains paragraphs. Counting elements keeps the index stable
 * against whitespace between tags, which differs between renders.
 */
export const blocksOf = (root: Element): Element[] => Array.from(root.children);

export const blockTextsOf = (root: Element): string[] =>
  blocksOf(root).map((b) => flatten(b.textContent ?? ""));

/**
 * Turn the live selection into an anchor, or null when there is nothing usable.
 *
 * Refuses a selection that spans two blocks. It could be supported by storing a
 * start and an end anchor, but a highlight crossing a paragraph boundary is rare
 * in this corpus and doubles the number of ways re-anchoring can half-succeed —
 * one end found, the other orphaned — with no honest way to render the result.
 * The reader is simply not offered the bar for such a selection.
 */
export function anchorFromSelection(root: Element, selection: Selection): Anchor | null {
  if (selection.isCollapsed || selection.rangeCount === 0) return null;

  const range = selection.getRangeAt(0);
  const blocks = blocksOf(root);

  const blockIndex = blocks.findIndex(
    (b) => b.contains(range.startContainer) && b.contains(range.endContainer),
  );
  if (blockIndex === -1) return null;

  const block = blocks[blockIndex];
  const before = range.cloneRange();
  before.selectNodeContents(block);
  before.setEnd(range.startContainer, range.startOffset);

  const startOffset = flatten(before.toString()).length;
  const quote = flatten(range.toString());
  if (normalizeText(quote) === "") return null;

  const prefixSource = flatten(before.toString());

  return {
    blockIndex,
    startOffset,
    endOffset: startOffset + quote.length,
    quote,
    prefix: prefixSource.slice(Math.max(0, prefixSource.length - PREFIX_LENGTH)),
  };
}

/* -------------------------------------------------------------------------- */
/* Painting                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * The DOM ranges covering `[start, end)` of a block's flattened text.
 *
 * Several, not one: a highlight may cross `<em>` or an inline Arabic span, and
 * `Range.surroundContents` throws on a range with partially-selected non-text
 * nodes. Wrapping each intersecting TEXT node separately is what makes a
 * highlight over mixed inline markup possible at all.
 *
 * Offsets are into the FLATTENED text, and the walk rebuilds that flattening as
 * it goes so the two cannot disagree — the bug this replaces would be a highlight
 * drifting by one character per collapsed line break.
 */
export function rangesIn(block: Element, start: number, end: number): Range[] {
  const doc = block.ownerDocument;
  const walker = doc.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  const out: Range[] = [];

  // ONE pass, with `previousWasSpace` carried ACROSS nodes. That is the whole
  // subtlety: whitespace collapsing does not stop at a node boundary —
  // `<p>a <em>b</em></p>` flattens to `a b`, where the space belongs to the
  // first text node and the `b` to the second. Recomputing the flag per node
  // would emit a second space and put every offset after an inline tag one too
  // high, drifting a highlight further right with each `<em>` it passes.
  //
  // It starts false, not true, because `flatten` does not trim: a block opening
  // with whitespace really does begin with one space in the flattened text.
  let flat = 0;
  let previousWasSpace = false;
  let node: Node | null;

  while ((node = walker.nextNode()) !== null) {
    const raw = node.nodeValue ?? "";
    let rangeStart = -1;
    let rangeEnd = -1;

    for (let i = 0; i < raw.length; i++) {
      const isSpace = /\s/.test(raw[i]);
      if (isSpace && previousWasSpace) continue; // collapsed away, occupies no flat index

      if (flat >= start && flat < end) {
        if (rangeStart === -1) rangeStart = i;
        rangeEnd = i + 1;
      }

      flat++;
      previousWasSpace = isSpace;
    }

    if (rangeStart !== -1) {
      const range = doc.createRange();
      range.setStart(node, rangeStart);
      range.setEnd(node, rangeEnd);
      out.push(range);
    }

    if (flat >= end) break;
  }

  return out;
}
