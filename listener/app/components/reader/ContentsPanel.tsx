import { faListUl, faXmark } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { readingMinutes } from "~/lib/reading";

export interface ChapterEntry {
  anchorKey: string;
  title: string;
  wordCount: number;
}

/**
 * The book's contents, as a panel on the left that collapses to a tab.
 *
 * It is NOT in the toolbar. It was — first as the book's own title doubling as
 * the toggle, then as a "Contents" button — and both put a way of LEAVING this
 * chapter in the row of controls for how this chapter is SET. They are different
 * kinds of thing, and the row was the longer for holding both.
 *
 * Collapsed, the panel is a tab against the left edge: the affordance is the
 * panel's own, so nothing else on the page has to carry it. Expanded, it is the
 * same drawer component the notes use, mirrored — one behaviour to learn, with
 * the book's structure on the left and your own marks on it to the right.
 *
 * Fixed rather than in the flow, so opening it never moves the paragraph being
 * read. On a phone it covers the page and the scrim dims what it covers; on a
 * wide screen it takes a column of its own beside the text.
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
  if (!open) {
    return (
      <button
        type="button"
        onClick={onOpen}
        aria-expanded={false}
        aria-label="Open the contents"
        title="Contents"
        className="pf-contents-tab"
      >
        <Icon icon={faListUl} />
        {/* Written out, not left to the icon. The control this replaced said
            "Contents" in words; an unlabelled glyph alone in the margin is easy
            to miss entirely, which would make the panel harder to reach than it
            was in the toolbar. Hidden on the phone layout, where the tab is a
            round button with no room for it — the accessible name on the button
            carries it there. */}
        <span className="pf-contents-tab__label">Contents</span>
      </button>
    );
  }

  return (
    <>
      {/* Click-away. Not focusable and hidden from assistive tech — Escape and
          the close button are the keyboard routes out, and a scrim in the tab
          order is a stop that announces nothing. */}
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        onClick={onClose}
        className="pf-drawer__scrim"
      />

      <nav aria-label="Table of contents" className="pf-drawer pf-drawer--left">
        <div className="pf-drawer__head">
          <h2 className="pf-drawer__title">Contents</h2>
          <button
            type="button"
            onClick={onClose}
            aria-expanded={true}
            aria-label="Close the contents"
            className="pf-tool"
          >
            <Icon icon={faXmark} title="Close the contents" />
          </button>
        </div>

        <div className="pf-drawer__body">
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
        </div>
      </nav>
    </>
  );
}
