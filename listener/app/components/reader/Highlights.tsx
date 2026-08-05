import { useEffect } from "react";

import { blocksOf, blockTextsOf, rangesIn, resolveAnchor } from "~/lib/anchor";
import type { Annotation } from "~/lib/marks";

/** A Scholar Companion card's sentence, as the card names it. */
export interface Passage {
  id: string;
  quote: string;
}

/** What resolving every annotation in a chapter produced. */
export interface Painted {
  /** Ids whose passage could not be found. Listed in the notes, never painted. */
  orphaned: Set<string>;
  /** Ids whose stored offsets were stale and have been corrected. */
  corrected: Map<string, { blockIndex: number; startOffset: number; endOffset: number }>;
  /** Companion cards whose sentence is not in the chapter as it now reads. */
  unplaced: Set<string>;
}

const MARK_CLASS = "pf-hl";

/**
 * The Companion tint. A second class in the SAME pass, not a second pass.
 *
 * Two independent painters over one chapter would each start by stripping "what
 * the previous run added" and take the other's marks off with it, and the second
 * to run would wrap ranges the first had already split. Everything about owning
 * this DOM — the strip, the backwards ordering, the healing `normalize()` — has
 * to be one function or it is not owned at all.
 */
const COMPANION_CLASS = "pf-cp";

/**
 * Paint stored highlights into the chapter HTML, after it has rendered.
 *
 * Done in an effect and never on the server, for a reason that is not
 * performance: `chapter.html` is injected with `dangerouslySetInnerHTML`, and
 * React will not reconcile inside it. Marking up the string before injection
 * would mean re-injecting the whole chapter on every highlight — losing the
 * scroll position and any text the reader had selected — so the marks are added
 * to the live DOM instead, and removed the same way.
 *
 * Every run starts by stripping what the previous run added. Wrapping is not
 * idempotent: painting twice would nest a `<mark>` inside a `<mark>` and the
 * second pass would compute its offsets against text that already contains the
 * first pass's elements. `normalize()` afterwards re-joins the text nodes the
 * unwrap left adjacent, so offsets are measured against the same shape every
 * time.
 */
export function paintHighlights(
  root: Element,
  annotations: Annotation[],
  activeId: string | null,
  passages: Passage[] = [],
): Painted {
  unpaint(root);

  const blocks = blocksOf(root);
  const texts = blockTextsOf(root);
  const painted: Painted = { orphaned: new Set(), corrected: new Map(), unplaced: new Set() };

  // The Companion FIRST, so a reader's own highlight over the same sentence is
  // wrapped inside the tint rather than around it — their mark is the one they
  // put there, and it should be the one they see and the one they tap.
  //
  // Painting it first is safe for the same reason painting anything is: offsets
  // are read from `texts`, which is `textContent` and cannot see an inline
  // element, and `rangesIn` emits one range per TEXT node — so a highlight
  // crossing a tint's boundary comes back as two ranges that each wrap cleanly,
  // exactly as one crossing an `<em>` already did.
  paintPassages(root, blocks, texts, passages, painted);

  // Later blocks first, and later offsets before earlier ones within a block.
  //
  // Wrapping a range splits the text node it lands in, which invalidates offsets
  // AFTER it in the same block. Working backwards means every range is measured
  // against text no earlier wrap has touched yet.
  const ordered = [...annotations].sort(
    (a, b) => b.blockIndex - a.blockIndex || b.startOffset - a.startOffset,
  );

  for (const annotation of ordered) {
    const resolution = resolveAnchor(annotation, texts);

    if (resolution.status === "orphaned") {
      painted.orphaned.add(annotation.id);
      continue;
    }

    if (resolution.status === "moved") {
      painted.corrected.set(annotation.id, {
        blockIndex: resolution.blockIndex,
        startOffset: resolution.startOffset,
        endOffset: resolution.endOffset,
      });
    }

    const block = blocks[resolution.blockIndex];
    if (block === undefined) {
      painted.orphaned.add(annotation.id);
      continue;
    }

    const ranges = rangesIn(block, resolution.startOffset, resolution.endOffset);
    if (ranges.length === 0) {
      painted.orphaned.add(annotation.id);
      continue;
    }

    for (const range of ranges) {
      const mark = root.ownerDocument.createElement("mark");
      mark.className =
        `${MARK_CLASS} ${MARK_CLASS}--${annotation.colour}` +
        (annotation.note ? ` ${MARK_CLASS}--noted` : "") +
        (annotation.id === activeId ? ` ${MARK_CLASS}--active` : "");
      mark.dataset.markId = annotation.id;
      // The note travels ON the element so the selection bar can open with its
      // existing text already in the field, without looking the annotation up
      // again by id. A highlight with no note carries no attribute at all —
      // `dataset.note` then reads `undefined`, which is the distinction the bar
      // uses to say "Add note" rather than "Edit note".
      if (annotation.note !== null) mark.dataset.note = annotation.note;
      // A highlight is a control — it opens its note — so it must be reachable
      // without a pointer. `tabindex` rather than a <button>, because a button
      // inside a paragraph changes how the sentence is announced and cannot
      // legally contain the block-level markup a quotation sometimes carries.
      mark.tabIndex = 0;
      mark.setAttribute("role", "button");
      mark.setAttribute(
        "aria-label",
        annotation.note ? `Highlighted, with a note: ${annotation.quote}` : `Highlighted: ${annotation.quote}`,
      );

      try {
        range.surroundContents(mark);
      } catch {
        // `surroundContents` throws when a range partially selects a non-text
        // node. `rangesIn` only ever produces ranges inside a single text node,
        // so this is unreachable — but a thrown exception here would blank the
        // chapter, and one unpainted highlight is a far smaller failure.
        painted.orphaned.add(annotation.id);
      }
    }
  }

  return painted;
}

/**
 * Tint the sentences the Scholar Companion explains.
 *
 * A companion card carries only its `quote` — no block index, no offsets, no
 * prefix — so it is resolved by the SAME function a highlight is, with the
 * offsets it does not have left at zero. `resolveAnchor` then falls straight
 * through to its whole-chapter search, which is what makes this work at all, and
 * REFUSES ON AMBIGUITY: a sentence that appears twice with nothing to tell the
 * two apart is left unpainted and the card says so. On a religious text an
 * explanation attached to the wrong passage is worse than one that admits it
 * lost its place, because the first is silent.
 */
function paintPassages(
  root: Element,
  blocks: Element[],
  texts: string[],
  passages: Passage[],
  painted: Painted,
) {
  // Resolve every one before painting any: the resolutions are read from `texts`,
  // which was captured before this ran, so the order they are PAINTED in is the
  // only thing that has to go backwards.
  const placed = passages
    .map((passage) => ({
      passage,
      at: resolveAnchor(
        { blockIndex: -1, startOffset: 0, endOffset: 0, quote: passage.quote, prefix: "" },
        texts,
      ),
    }))
    .filter((entry) => {
      if (entry.at.status === "orphaned") {
        painted.unplaced.add(entry.passage.id);
        return false;
      }
      return true;
    })
    .sort((a, b) =>
      a.at.status === "orphaned" || b.at.status === "orphaned"
        ? 0
        : b.at.blockIndex - a.at.blockIndex || b.at.startOffset - a.at.startOffset,
    );

  for (const { passage, at } of placed) {
    if (at.status === "orphaned") continue;

    const block = blocks[at.blockIndex];
    if (block === undefined) {
      painted.unplaced.add(passage.id);
      continue;
    }

    const ranges = rangesIn(block, at.startOffset, at.endOffset);
    if (ranges.length === 0) {
      painted.unplaced.add(passage.id);
      continue;
    }

    for (const range of ranges) {
      const mark = root.ownerDocument.createElement("mark");
      mark.className = COMPANION_CLASS;
      mark.dataset.companionId = passage.id;
      // A control, like a highlight is: tapping it opens the card that explains
      // it. `tabindex` rather than a <button> for the reason given below — a
      // button inside a paragraph changes how the sentence is announced.
      mark.tabIndex = 0;
      mark.setAttribute("role", "button");
      mark.setAttribute("aria-label", `Explained by the Companion: ${passage.quote}`);

      try {
        range.surroundContents(mark);
      } catch {
        // Unreachable for the same reason it is below — `rangesIn` never returns
        // a range that straddles a node. A tint that fails to paint is a tint
        // missing, never a blanked chapter.
        painted.unplaced.add(passage.id);
      }
    }
  }
}

/** Remove every mark this module added, and heal the text nodes it split. */
export function unpaint(root: Element) {
  for (const mark of Array.from(
    root.querySelectorAll(`mark.${MARK_CLASS}, mark.${COMPANION_CLASS}`),
  )) {
    const parent = mark.parentNode;
    if (parent === null) continue;
    while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
    parent.removeChild(mark);
  }
  root.normalize();
}

/**
 * Keep the chapter's highlights in step with the store.
 *
 * `corrected` goes back to the caller rather than being written from here: this
 * component knows a passage moved, but saving that correction is a WRITE, and
 * writes belong to the route that owns the fetcher. Painting and persisting are
 * separate so a render can never post.
 */
export function useHighlights(
  bodyRef: React.RefObject<HTMLElement | null>,
  annotations: Annotation[],
  activeId: string | null,
  onResolved: (painted: Painted) => void,
  passages: Passage[] = EMPTY_PASSAGES,
) {
  useEffect(() => {
    const root = bodyRef.current;
    if (root === null) return;

    const painted = paintHighlights(root, annotations, activeId, passages);
    onResolved(painted);

    return () => {
      // The chapter body survives a store update but NOT a chapter change, and
      // React tears the old one down before this runs. Guarding on the node
      // still being attached keeps the cleanup from working on a detached tree.
      if (root.isConnected) unpaint(root);
    };
    // `onResolved` is deliberately absent: the caller re-creates it every render,
    // and depending on it would repaint the chapter on every keystroke in a note.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bodyRef, annotations, activeId, passages]);
}

/** A stable identity for "no companion", so the default cannot drive a repaint. */
const EMPTY_PASSAGES: Passage[] = [];
