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
 */
export function useCorrectionMarks(
  items: Correction[],
  chapterKey: string,
  enabled: boolean,
) {
  useEffect(() => {
    if (!enabled || typeof CSS === "undefined" || !("highlights" in CSS))
      return;
    const root = document.querySelector(".pf-chapter-body");
    if (root === null) return;

    const paint = () => {
      const texts = blockTextsOf(root);
      const blocks = blocksOf(root);
      const ranges: Range[] = [];

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
        if (block !== undefined)
          ranges.push(...rangesIn(block, found.startOffset, found.endOffset));
      }

      CSS.highlights.set(NAME, new Highlight(...ranges));
    };

    paint();

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
      CSS.highlights.delete(NAME);
    };
  }, [items, chapterKey, enabled]);
}
