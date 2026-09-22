import { useEffect } from "react";

import { blocksOf, blockTextsOf, rangesIn, resolveAnchor } from "~/lib/anchor";
import type { Correction } from "~/lib/corrections";

const NAME = "pf-correction";

/**
 * Whether a correction is still unsettled and so still earns the underline. Pulled out as its own
 * function, rather than left inline in the DOM-walking code below, purely so this one decision —
 * the thing a bug report would actually be about — has a name and a unit test that needs no DOM.
 */
export const needsUnderline = (status: Correction["status"]): boolean =>
  status === "open" || status === "suggested";

/** Whether a point falls inside a client rect, which is what a click's coordinates are. */
const hits = (rect: DOMRect, x: number, y: number): boolean =>
  x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;

/**
 * Which underlined correction, if any, a click at this point landed on.
 *
 * A registered Highlight Range is not a DOM node, so it cannot carry a click handler of its own —
 * this is the other half of that: hit-test the click's coordinates against the SAME ranges the
 * underline was just painted from. `getClientRects()`, not `getBoundingClientRect()`, because a
 * passage that wraps onto a second line has a bounding box that also covers the gap between the
 * lines; a real click in that gap would otherwise be answered as a hit on whichever line is
 * larger. Exported bare of the DOM walk around it, so the one-point-in-many-rectangles question
 * has a test that needs no browser.
 */
export function correctionAt(
  x: number,
  y: number,
  marked: { id: string; range: Range }[],
): string | null {
  for (const { id, range } of marked) {
    for (const rect of range.getClientRects()) {
      if (hits(rect, x, y)) return id;
    }
  }
  return null;
}

/**
 * Underline, in the proofreader's red, every passage of this chapter that still has a correction
 * WAITING for a decision — so a moderator sees at a glance where the book has been questioned.
 * The underline is what marks a passage as unsettled: once an admin accepts or dismisses it, the
 * question is answered and the mark comes off immediately, before the accepted wording has even
 * reached the book on the next republish. Left on until then, an accepted passage would still
 * look like an open question — the one thing the underline is supposed to tell a moderator.
 *
 * Done with the browser's CSS Custom Highlight API and NOT by wrapping text in elements, and that
 * is the whole reason this is a separate mechanism from the reader's own highlights. Those are
 * painted by rewriting the chapter's DOM (see `paintHighlights`, which warns that two painters over
 * one DOM strip each other's marks). A registered highlight range marks text WITHOUT touching it, so
 * this can run beside them and can never damage what a reader has marked.
 *
 * Where the API does not exist the underline is simply absent; nothing else depends on it. A
 * passage the reader cannot find is not marked — the same refusal to guess `resolveAnchor` makes.
 *
 * TAPPING the underline opens its card, given `onOpen` — the same idea as tapping a Companion
 * card's tinted sentence, and by the same route: nothing here is a DOM element a browser click
 * can target directly, so a plain click on the chapter is hit-tested against the ranges just
 * painted (`correctionAt`, above) rather than answered by an element's own listener. Mouse and
 * touch only; a registered Highlight Range has no place in the tab order, so a passage a keyboard
 * reader cannot see cannot be reached this way either — the card is always still reachable by
 * scrolling the panel itself.
 */
export function useCorrectionMarks(
  items: Correction[],
  chapterKey: string,
  enabled: boolean,
  onOpen?: (id: string) => void,
) {
  useEffect(() => {
    if (!enabled || typeof CSS === "undefined" || !("highlights" in CSS))
      return;
    const root = document.querySelector(".pf-chapter-body");
    if (root === null) return;

    // Read by the click handler below; kept outside `paint` so a click always tests against
    // whatever was painted most recently rather than a stale closure from the first run.
    let marked: { id: string; range: Range }[] = [];

    const paint = () => {
      const texts = blockTextsOf(root);
      const blocks = blocksOf(root);
      const ranges: Range[] = [];
      marked = [];

      for (const c of items) {
        if (c.anchorKey !== chapterKey) continue;
        if (!needsUnderline(c.status)) continue;

        const found = resolveAnchor(
          {
            blockIndex: c.blockIndex,
            startOffset: c.startOffset,
            endOffset: c.endOffset,
            quote: c.quote,
            prefix: c.prefix,
          },
          texts,
        );
        if (found.status === "orphaned") continue;
        const block = blocks[found.blockIndex];
        if (block === undefined) continue;
        const found_ranges = rangesIn(
          block,
          found.startOffset,
          found.endOffset,
        );
        ranges.push(...found_ranges);
        for (const range of found_ranges) marked.push({ id: c.id, range });
      }

      CSS.highlights.set(NAME, new Highlight(...ranges));
    };

    paint();

    const onClick = (event: MouseEvent) => {
      if (onOpen === undefined) return;
      const target = event.target as HTMLElement | null;
      // A tap that lands on the reader's own highlight, an explained sentence, or a real control
      // (the source citation's link, say) belongs to whatever already owns it.
      if (target?.closest("mark.pf-hl, mark.pf-cp, a, button")) return;
      // A drag that leaves a selection behind is the reader raising a NEW correction, not opening
      // an existing one — `SelectionBar` answers that, and must not be pre-empted here.
      if ((window.getSelection()?.toString() ?? "") !== "") return;
      const id = correctionAt(event.clientX, event.clientY, marked);
      if (id !== null) onOpen(id);
    };
    root.addEventListener("click", onClick);

    // The reader repaints its own highlights by rewriting this DOM, which leaves our ranges
    // pointing at removed nodes. Repaint after any such change, debounced.
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(paint, 150);
    });
    observer.observe(root, { childList: true, subtree: true });

    return () => {
      clearTimeout(timer);
      observer.disconnect();
      root.removeEventListener("click", onClick);
      CSS.highlights.delete(NAME);
    };
  }, [items, chapterKey, enabled, onOpen]);
}
