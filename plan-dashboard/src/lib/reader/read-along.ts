/**
 * read-along.ts — which paragraph is being spoken, right now.
 *
 * THE ONE OWNER of that question. Two surfaces ask it: the Podcast Factory
 * Library, where a reader follows the recording through a published chapter, and
 * the Book Composer, where Asif follows it through the chapter he is editing.
 * Two implementations would be free to disagree about the same second of the
 * same audio, and the disagreement would show as the wrong sentence lit up in
 * one of them — the precise failure the timing gate exists to prevent.
 *
 * It lives HERE, in the admin site, for the same reason `renderMarkdown` and
 * `sectionKeyFromHeading` do: the Library takes what this side already owns
 * rather than growing its own answer. The two apps share nothing at runtime, so
 * the Library's copy is GENERATED — `listener/scripts/sync-read-along.mjs`
 * writes it and `--check` fails on drift, the same arrangement as the study-track
 * colours and the quote inks. Change a rule HERE, then run the sync.
 *
 * Pure and DOM-free on purpose: it is imported by a ProseMirror plugin, a React
 * route and a test runner, and takes numbers rather than elements so all three
 * can ask the same function.
 */

export interface ReadAlongCue {
  startS: number;
  endS: number;
  text?: string;
  /** Which block of the chapter this cue belongs to; defaults to its own index. */
  blockIndex?: number;
}

/**
 * The index of the cue being spoken at `position` seconds, or -1 before the first.
 *
 * Binary search rather than a scan: this is asked on every frame of playback —
 * many times a second — against a chapter that can carry hundreds of cues, and a
 * linear pass there is a hundred thousand comparisons a minute for an answer
 * that changes twice.
 *
 * BETWEEN cues — a pause, a breath, the gap where nothing was said — it returns
 * the cue that just FINISHED rather than nothing. The alternative makes the
 * highlight blink out in every gap, which reads as the page losing its place.
 */
export function cueAt(cues: ReadAlongCue[], position: number): number {
  let low = 0;
  let high = cues.length - 1;
  let found = -1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (cues[mid].startS <= position) {
      found = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return found;
}

/**
 * The block to light up, or -1 for none.
 *
 * -1 is a real answer and every caller must render it as "nothing highlighted":
 * before the first cue, on a chapter published without timings, and whenever the
 * position is not a number a clock could produce. Guessing a block in any of
 * those cases lights a paragraph while a different one is being spoken.
 */
export function readAlongBlockIndex(
  active: boolean,
  cues: ReadAlongCue[] | null | undefined,
  position: number,
): number {
  if (!active || cues === null || cues === undefined || cues.length === 0)
    return -1;
  if (!Number.isFinite(position)) return -1;
  const cueIndex = cueAt(cues, Math.max(0, position));
  if (cueIndex < 0) return -1;
  const blockIndex = cues[cueIndex].blockIndex ?? cueIndex;
  return Number.isInteger(blockIndex) && blockIndex >= 0 ? blockIndex : -1;
}

export interface ReadAlongRect {
  top: number;
  height: number;
}

/**
 * Where to scroll so the spoken paragraph sits in the middle of what can be seen.
 *
 * `playerHeight` is subtracted because the transport sits over the page:
 * centring in the viewport would centre it behind the controls.
 */
export function readAlongTargetScrollY({
  rect,
  scrollY,
  viewportHeight,
  playerHeight,
}: {
  rect: ReadAlongRect;
  scrollY: number;
  viewportHeight: number;
  playerHeight: number;
}): number {
  const visibleHeight = Math.max(1, viewportHeight - Math.max(0, playerHeight));
  const centerOffset = Math.max(0, (visibleHeight - rect.height) / 2);
  return Math.max(0, scrollY + rect.top - centerOffset);
}
