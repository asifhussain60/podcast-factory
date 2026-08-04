import { faBookmark, faTrash, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { COLOUR_LABELS, type Annotation, type Bookmark } from "~/lib/marks";

export interface ChapterRef {
  anchorKey: string;
  title: string;
  idx: number;
}

/**
 * Everything a reader has marked in one book, in reading order.
 *
 * ONE component with two hosts: the drawer inside the reader, and the "Notes"
 * tab on the book page. They show the same thing and differ only in whether a
 * row navigates (book page) or scrolls (reader) — passed as `onJump`. Two
 * components would be two answers to what a note looks like.
 *
 * Grouped by chapter and ordered by position within it, because that is the
 * order the reader made them in and the order they will look for them in. Not by
 * date: "what did I mark in chapter three" is the question; "what did I mark on
 * Tuesday" is not.
 */
export function NotesList({
  annotations,
  bookmarks,
  chapters,
  orphaned,
  slug,
  onJump,
  onRemoveAnnotation,
  onRemoveBookmark,
}: {
  annotations: Annotation[];
  bookmarks: Bookmark[];
  chapters: ChapterRef[];
  /**
   * Ids whose passage could not be found in the chapter as it now reads.
   *
   * `ReadonlySet` because this component only ever asks — and because the book
   * page has no chapter rendered to resolve against, so it passes a frozen empty
   * set rather than pretending to know. Only the reader can populate this.
   */
  orphaned: ReadonlySet<string>;
  slug: string;
  /** Given in the reader, where a row scrolls. Absent on the book page, where it links. */
  onJump?: (anchorKey: string, id: string) => void;
  onRemoveAnnotation: (id: string) => void;
  onRemoveBookmark: (id: string) => void;
}) {
  if (annotations.length === 0 && bookmarks.length === 0) {
    return (
      <p className="pf-empty">
        Nothing marked yet. Select a passage while reading to highlight it, or add a note to
        remember why it mattered.
      </p>
    );
  }

  // Chapter order, from the book's own contents — not from the marks. A chapter
  // the reader has marked nothing in is simply absent; a chapter they have
  // marked appears where the book puts it, so the list reads as the book does.
  const byChapter = chapters
    .map((chapter) => ({
      chapter,
      notes: annotations
        .filter((a) => a.anchorKey === chapter.anchorKey)
        .sort((a, b) => a.blockIndex - b.blockIndex || a.startOffset - b.startOffset),
      marks: bookmarks
        .filter((b) => b.anchorKey === chapter.anchorKey)
        .sort((a, b) => a.blockIndex - b.blockIndex),
    }))
    .filter((g) => g.notes.length > 0 || g.marks.length > 0);

  return (
    <div className="pf-notes">
      {byChapter.map(({ chapter, notes, marks }) => (
        <section key={chapter.anchorKey} className="pf-notes__chapter">
          <h3 className="pf-notes__heading">{chapter.title}</h3>

          {marks.map((bookmark) => (
            <div key={bookmark.id} className="pf-mark pf-mark--bookmark">
              <Row
                slug={slug}
                anchorKey={chapter.anchorKey}
                id={bookmark.id}
                onJump={onJump}
                className="pf-mark__body"
              >
                <span className="pf-mark__kind">
                  <Icon icon={faBookmark} title="Bookmark" />
                </span>
                <span className="pf-mark__quote">{bookmark.label}</span>
              </Row>
              <button
                type="button"
                onClick={() => onRemoveBookmark(bookmark.id)}
                aria-label="Remove this bookmark"
                className="pf-mark__remove"
              >
                <Icon icon={faTrash} title="Remove this bookmark" />
              </button>
            </div>
          ))}

          {notes.map((annotation) => (
            <div
              key={annotation.id}
              // `--paper` is what makes it a Post-it: the whole card takes the
              // colour of the highlight rather than wearing it as an edge. Only
              // annotations get it. A bookmark is a place, not a note, and has
              // no colour of its own to be made of.
              className={`pf-mark pf-mark--paper pf-mark--${annotation.colour}${
                orphaned.has(annotation.id) ? " pf-mark--orphaned" : ""
              }`}
            >
              <Row
                slug={slug}
                anchorKey={chapter.anchorKey}
                id={annotation.id}
                onJump={orphaned.has(annotation.id) ? undefined : onJump}
                className="pf-mark__body"
              >
                <span className="sr-only">{COLOUR_LABELS[annotation.colour]} highlight. </span>
                <blockquote className="pf-mark__quote">{annotation.quote}</blockquote>
                {annotation.note ? <p className="pf-mark__text">{annotation.note}</p> : null}
                {/* Said plainly rather than hidden. A highlight whose passage a
                    re-compose has changed still records what the reader marked —
                    the quote is right there — so deleting it would destroy their
                    work, and silently pointing it at a nearby sentence would be
                    worse. It stays, and says what happened. */}
                {orphaned.has(annotation.id) ? (
                  <p className="pf-mark__warning">
                    <Icon icon={faTriangleExclamation} />
                    The wording here has changed since you marked it, so this no longer points at a
                    passage. Your note is kept.
                  </p>
                ) : null}
              </Row>
              <button
                type="button"
                onClick={() => onRemoveAnnotation(annotation.id)}
                aria-label="Remove this highlight"
                className="pf-mark__remove"
              >
                <Icon icon={faTrash} title="Remove this highlight" />
              </button>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}

/**
 * A row that scrolls in the reader and navigates from the book page.
 *
 * The difference is which host is mounting it, not which kind of mark it is, so
 * it is decided once here rather than at every call site. An orphaned mark gets
 * neither — `onJump` undefined and no link — because there is nowhere to go.
 */
function Row({
  slug,
  anchorKey,
  id,
  onJump,
  className,
  children,
}: {
  slug: string;
  anchorKey: string;
  id: string;
  onJump?: (anchorKey: string, id: string) => void;
  className: string;
  children: React.ReactNode;
}) {
  if (onJump !== undefined) {
    return (
      <button type="button" onClick={() => onJump(anchorKey, id)} className={className}>
        {children}
      </button>
    );
  }

  return (
    <Link to={`/book/${slug}/read/${encodeURIComponent(anchorKey)}#mark-${id}`} className={className}>
      {children}
    </Link>
  );
}
