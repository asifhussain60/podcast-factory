/**
 * A book's subject track, shown as the library card's corner ribbon and as a
 * filter chip in the library find row. One place to add a sixth track later —
 * a new entry here, a new `--l-ribbon-*` pair in the stylesheet, nothing else
 * touched.
 */
export type StudyTrack =
  | "theology"
  | "history"
  | "shariah"
  | "esoteric"
  | "reality"
  | "philosophy";

const LABELS: Record<StudyTrack, string> = {
  theology: "Theology",
  history: "History",
  shariah: "Shariah",
  esoteric: "Esoteric",
  reality: "Reality",
  philosophy: "Philosophy",
};

/** Display order for the filter chips — not alphabetical, so a book's own
 * track order (foundational to concrete) reads left to right. */
export const ALL_STUDY_TRACKS: StudyTrack[] = [
  "history",
  "shariah",
  "theology",
  "esoteric",
  "reality",
  "philosophy",
];

export function isStudyTrack(value: string | null): value is StudyTrack {
  return value !== null && value in LABELS;
}

export function studyTrackLabel(track: string | null): string | null {
  return isStudyTrack(track) ? LABELS[track] : null;
}

/**
 * The "Browse by track" filter's choice, kept apart from `StudyTrack` itself
 * so a sixth track never has to teach this file about a sentinel value it
 * does not own.
 *
 * A unit whose `studyTrack` is null or undefined — unclassified, whatever the
 * reason — never matches a specific track choice. It still shows up under
 * "all", which is what makes an unclassified item's disappearance under every
 * other chip a silent taxonomy gap rather than a loud error: nothing here
 * should paper over that by inventing a match. Classify the content instead.
 */
export type TrackChoice = "all" | StudyTrack;

export const inTrack = (
  studyTrack: string | null | undefined,
  choice: TrackChoice,
): boolean => choice === "all" || studyTrack === choice;
