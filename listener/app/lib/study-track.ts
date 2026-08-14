/**
 * A book's doctrinal advancement level, shown as the library card's corner
 * ribbon. One place to add a fourth track later — a new key here, a new
 * `--l-ribbon-*` pair in the stylesheet, nothing else touched.
 */
export type StudyTrack = "theology" | "esoterics" | "history";

const LABELS: Record<StudyTrack, string> = {
  theology: "Theology",
  esoterics: "Esoterics",
  history: "History",
};

export function isStudyTrack(value: string | null): value is StudyTrack {
  return value !== null && value in LABELS;
}

export function studyTrackLabel(track: string | null): string | null {
  return isStudyTrack(track) ? LABELS[track] : null;
}
