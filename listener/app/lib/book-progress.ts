import type { Progress } from "~/server/marks.server";

/**
 * Whole chapters finished plus how far into the current one, so a reader on
 * chapter 4 of 9 reads about 40%, not 11% because one chapter is "done".
 * Clamped to 1-99 so rounding never claims 0% or 100%. Null when there's
 * nothing to measure — a percentage of zero chapters, or a book never
 * opened, is a lie.
 *
 * The one formula the card and the library's list row both read from, so
 * they can never disagree about how far into a book the same reader is.
 */
export function percentRead(
  chapters: number,
  progress: Progress | null,
): number | null {
  if (progress === null || chapters === 0) return null;
  return Math.min(
    99,
    Math.max(
      1,
      Math.round(
        ((progress.chaptersDone + progress.fraction) / chapters) * 100,
      ),
    ),
  );
}
