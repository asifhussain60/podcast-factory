/**
 * passage-match.ts — the DOM half of the passage matcher, over the shared core.
 *
 * The matching itself moved to scripts/lib/passage-match.mjs on 2026-08-02 so the
 * PDF renderer (plain node, no DOM, cannot import TypeScript) could use the same
 * implementation the three browser surfaces already did. This module re-exports
 * every core symbol under its original name, so every existing import kept
 * working unchanged, and adds the two helpers that genuinely need a document.
 */
export {
  normalizeQuote,
  foldChar,
  foldText,
  flatten,
  findPassage,
} from "../../../../scripts/lib/passage-match.mjs";
import {
  flatten,
  findPassage,
} from "../../../../scripts/lib/passage-match.mjs";

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

/** The elements that count as a block boundary when walking a rendered chapter.
 *  A DOM selector, so it stays on this side of the split rather than in the
 *  document-free core. */
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
