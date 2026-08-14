/**
 * A book's subject track, shown as the library card's corner ribbon and as a
 * filter chip in the library find row. One place to add a sixth track later —
 * a new entry here, a new `--l-ribbon-*` pair in the stylesheet, nothing else
 * touched.
 */
export type StudyTrack = "theology" | "history" | "shariah" | "esoteric" | "reality";

const LABELS: Record<StudyTrack, string> = {
  theology: "Theology",
  history: "History",
  shariah: "Shariah",
  esoteric: "Esoteric",
  reality: "Reality",
};

/** Display order for the filter chips — not alphabetical, so a book's own
 * track order (foundational to concrete) reads left to right. */
export const ALL_STUDY_TRACKS: StudyTrack[] = [
  "theology",
  "shariah",
  "esoteric",
  "history",
  "reality",
];

export function isStudyTrack(value: string | null): value is StudyTrack {
  return value !== null && value in LABELS;
}

export function studyTrackLabel(track: string | null): string | null {
  return isStudyTrack(track) ? LABELS[track] : null;
}
