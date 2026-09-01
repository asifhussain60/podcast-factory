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
 * IT IS OPENED FROM THE ACTION RAIL, and has no tab of its own (Asif,
 * 2026-09-01). This reverses a rule stated twice in this file and once in
 * `ReaderToolbar`, so it is worth saying what changed rather than deleting the
 * old note: the objection was that contents sat in "the row of controls for how
 * this chapter is SET", mixing a way of LEAVING the chapter with the settings
 * that dress it. That row and the rail are now different objects. Appearance —
 * theme, face, size, spacing, width — lives in the toolbar above the page; the
 * rail holds only ways of going somewhere: home, this book, your bookmark. The
 * chapters belong with those three, and the old objection does not reach them
 * there.
 *
 * Passing no `onOpen` is what removes the edge tab; `SidePanel` draws one only
 * for a panel that opens itself. The rail owns the affordance now, so a tab as
 * well would be two controls for one drawer sitting four inches apart.
 *
 * Everything about how the panel closes and looks lives in `SidePanel`, which
 * your marks on the right side use too. This file is only what is IN it: the
 * chapters, and what each one costs to read.
 */
export function ContentsPanel({
  open,
  onClose,
  chapters,
  currentKey,
  slug,
}: {
  open: boolean;
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
              <span className="pf-row__meta">
                {readingMinutes(entry.wordCount)} min
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </SidePanel>
  );
}
