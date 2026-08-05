import { faListUl } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { SidePanel } from "~/components/reader/SidePanel";
import { readingMinutes } from "~/lib/reading";

export interface ChapterEntry {
  anchorKey: string;
  title: string;
  wordCount: number;
}

/**
 * The book's contents, in the panel on the left.
 *
 * It is NOT in the toolbar. It was — first as the book's own title doubling as
 * the toggle, then as a "Contents" button — and both put a way of LEAVING this
 * chapter in the row of controls for how this chapter is SET. They are different
 * kinds of thing, and the row was the longer for holding both.
 *
 * Everything about how the panel opens, closes and looks lives in `SidePanel`,
 * which your marks on the right side use too. This file is only what is IN it:
 * the chapters, and what each one costs to read.
 */
export function ContentsPanel({
  open,
  onOpen,
  onClose,
  chapters,
  currentKey,
  slug,
}: {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  chapters: ChapterEntry[];
  currentKey: string;
  slug: string;
}) {
  return (
    <SidePanel
      side="start"
      as="nav"
      open={open}
      onOpen={onOpen}
      onClose={onClose}
      label="Contents"
      icon={faListUl}
    >
      <ol className="pf-toc__list">
        {chapters.map((entry) => (
          <li key={entry.anchorKey}>
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(entry.anchorKey)}`}
              onClick={onClose}
              aria-current={entry.anchorKey === currentKey ? "page" : undefined}
              className="pf-row pf-toc__row"
            >
              <span className="pf-row__main">{entry.title}</span>
              <span className="pf-row__meta">{readingMinutes(entry.wordCount)} min</span>
            </Link>
          </li>
        ))}
      </ol>
    </SidePanel>
  );
}
