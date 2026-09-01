/**
 * read-along-scroll.ts — put the block being spoken on the reader's eye line.
 *
 * ITS OWN MODULE, and the reason matters: `read-along.ts` beside it is
 * GENERATED. That file is one rule with two surfaces asking it — this reader and
 * the Book Composer — copied in from plan-dashboard by `npm run read-along`, and
 * a test fails the moment the copy drifts. Anything hand-written in there is
 * destroyed by the next sync, silently, whenever somebody changes the rule at
 * its source.
 *
 * This helper is Library-only: it reads the window, the player height and the
 * document, none of which the Composer has. So it lives beside the generated
 * file rather than inside it, and imports the shared arithmetic like any other
 * caller.
 *
 * Moved out of `book.$slug.read.$chapter.tsx` on 2026-09-01, where it sat alone
 * while the function it exists to call was already in the shared module.
 */
import { readAlongTargetScrollY } from "~/lib/read-along";

export function centerReadAlongBlock(block: HTMLElement) {
  if (typeof window === "undefined") return;
  const styles = window.getComputedStyle(document.documentElement);
  const playerHeight = Number.parseFloat(
    styles.getPropertyValue("--pf-player-h"),
  );
  const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
  const top = readAlongTargetScrollY({
    rect: block.getBoundingClientRect(),
    scrollY: window.scrollY,
    viewportHeight,
    playerHeight: Number.isFinite(playerHeight) ? playerHeight : 0,
  });
  window.scrollTo({ top, behavior: "smooth" });
}
