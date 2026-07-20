/**
 * ComposeCompanionTab.tsx — thin wrapper mounting the existing CompanionPanel
 * (manual reader notes, e.g. "ANALOGY" cards) inside Compose's first
 * inspector tab, docked instead of floating. Reuses the panel's own store and
 * CRUD untouched — this file only adapts Compose's chapter shape and picks
 * the right layout/prose selector.
 *
 * Mounted imperatively (React 19 createRoot) by book-composer.ts, same as
 * ComposeAiTools / ComposeDetailsTab, and re-mounted on every chapter switch
 * with a fresh `initialChapter` — otherwise the panel's own chapter selector
 * (and the notes it shows) stay pinned to whichever chapter was active when
 * it first mounted, going stale the moment the main Chapter dropdown moves
 * to a different one.
 */
import CompanionPanel, {
  type ChapterRef,
} from "../../reader/companion/CompanionPanel";

interface Props {
  slug: string;
  chapters: ChapterRef[];
  initialChapter?: string;
}

export default function ComposeCompanionTab({
  slug,
  chapters,
  initialChapter,
}: Props) {
  return (
    <CompanionPanel
      slug={slug}
      chapters={chapters}
      initialChapter={initialChapter}
      layout="docked"
      proseSelector=".cx-chapter"
    />
  );
}
