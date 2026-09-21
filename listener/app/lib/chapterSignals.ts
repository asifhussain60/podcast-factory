/**
 * What is in each chapter, for the badges on the book page's chapter list.
 *
 * Pure and client-safe: the page already holds every input, so nothing is fetched to draw a
 * badge. Corrections are passed as `null` for anyone who may not see them, and `null` yields
 * zeros — the gate is the corrections route, which answers a non-moderator with a 404 and so
 * never produces a list to count; this function only declines to invent one.
 */
import type { Correction } from "./corrections";
import type { Annotation, Bookmark, Progress } from "./marks";

export interface ChapterSignal {
  bookmarks: number;
  /** A highlight with no text of its own. */
  highlights: number;
  /** A highlight that carries a note. */
  notes: number;
  /** Corrections still waiting for a decision — everyone's, not only yours. */
  open: number;
  decided: number;
  state: "done" | "part" | "none";
}

const undecided = (c: Correction) =>
  c.status === "open" || c.status === "suggested";

export function chapterSignals(
  chapters: { anchorKey: string }[],
  marks: {
    annotations: Pick<Annotation, "anchorKey" | "note">[];
    bookmarks: Pick<Bookmark, "anchorKey">[];
  },
  corrections: Pick<Correction, "anchorKey" | "status">[] | null,
  progress: Pick<Progress, "anchorKey" | "fraction" | "chaptersDone"> | null,
): Map<string, ChapterSignal> {
  const out = new Map<string, ChapterSignal>();
  chapters.forEach((chapter, index) => {
    out.set(chapter.anchorKey, {
      bookmarks: 0,
      highlights: 0,
      notes: 0,
      open: 0,
      decided: 0,
      // `chaptersDone` counts the chapters finished BEFORE the one being read, and the reader
      // writes it as that chapter's position in this same list.
      state:
        progress === null
          ? "none"
          : progress.anchorKey === chapter.anchorKey
            ? progress.fraction > 0
              ? "part"
              : "none"
            : index < progress.chaptersDone
              ? "done"
              : "none",
    });
  });

  for (const b of marks.bookmarks) {
    const s = out.get(b.anchorKey);
    if (s !== undefined) s.bookmarks += 1;
  }
  for (const a of marks.annotations) {
    const s = out.get(a.anchorKey);
    if (s === undefined) continue;
    if ((a.note ?? "").trim() === "") s.highlights += 1;
    else s.notes += 1;
  }
  for (const c of corrections ?? []) {
    const s = out.get(c.anchorKey);
    if (s === undefined) continue;
    if (undecided(c)) s.open += 1;
    else s.decided += 1;
  }
  return out;
}
