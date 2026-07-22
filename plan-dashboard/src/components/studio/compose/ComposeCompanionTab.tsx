/**
 * ComposeCompanionTab.tsx — thin wrapper mounting the existing CompanionPanel
 * (manual reader notes, e.g. "ANALOGY" cards) inside the Book Composer's
 * Companion drawer surface, docked instead of floating. Reuses the panel's own
 * store and CRUD untouched — this file only adapts Compose's chapter shape and
 * picks the right layout/prose selector.
 *
 * Mounted imperatively (React 19 createRoot) by book-composer.ts, same as
 * ComposeAiTools / ComposeDetailsTab, but ONCE for the page: it passes the
 * CONTROLLED `chapter` prop, so a chapter switch is a re-render with a new value
 * rather than an unmount/remount. That is also what removes the panel's own
 * chapter dropdown here — a second picker for the same thing the page already
 * decides could only ever disagree with it.
 */
import CompanionPanel, {
  type ChapterRef,
} from "../../reader/companion/CompanionPanel";

interface Props {
  slug: string;
  chapters: ChapterRef[];
  /** The chapter open in the Composer. Controlled — the panel follows it. */
  chapter: string;
}

export default function ComposeCompanionTab({
  slug,
  chapters,
  chapter,
}: Props) {
  return (
    <CompanionPanel
      slug={slug}
      chapters={chapters}
      chapter={chapter}
      layout="docked"
      proseSelector=".cx-chapter"
    />
  );
}
