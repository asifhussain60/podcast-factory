import { useEffect } from "react";

import { blocksOf, blockTextsOf, rangesIn, resolveAnchor } from "~/lib/anchor";
import type { Annotation } from "~/lib/marks";

/** What resolving every annotation in a chapter produced. */
export interface Painted {
  /** Ids whose passage could not be found. Listed in the notes, never painted. */
  orphaned: Set<string>;
  /** Ids whose stored offsets were stale and have been corrected. */
  corrected: Map<string, { blockIndex: number; startOffset: number; endOffset: number }>;
}

const MARK_CLASS = "pf-hl";

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
): Painted {
  unpaint(root);

  const blocks = blocksOf(root);
  const texts = blockTextsOf(root);
  const painted: Painted = { orphaned: new Set(), corrected: new Map() };

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

/** Remove every mark this module added, and heal the text nodes it split. */
export function unpaint(root: Element) {
  for (const mark of Array.from(root.querySelectorAll(`mark.${MARK_CLASS}`))) {
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
) {
  useEffect(() => {
    const root = bodyRef.current;
    if (root === null) return;

    const painted = paintHighlights(root, annotations, activeId);
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
  }, [bodyRef, annotations, activeId]);
}
