import { useEffect, useState } from "react";
import {
  faBookOpen,
  faBookmark,
  faHeadphones,
  faPen,
  faTrash,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { RichNoteEditor } from "~/components/notes/RichNoteEditor";
import { count } from "~/lib/plural";
import { renderNote } from "~/lib/richNote";
import {
  COLOUR_LABELS,
  PRE_ROLL_S,
  type Annotation,
  type Bookmark,
  type EpisodeNote,
} from "~/lib/marks";

export interface ChapterRef {
  anchorKey: string;
  title: string;
  idx: number;
}

export interface EpisodeRef {
  number: number;
  title: string;
}

/**
 * Everything a reader has marked in one book, in the order the book runs.
 *
 * ONE component with three hosts now: the drawer inside the reader, the "Notes"
 * tab on the book page, and the drawer on an episode page. They show the same
 * thing and differ only in what they can act on — a row scrolls in the reader,
 * navigates from the book page, seeks in an episode.
 *
 * WHAT EACH HOST PASSES, and why it is a data difference rather than a mode:
 * a host supplies the lists it can DO something with. The reader has no episode
 * loaded, so it passes no episodes and the podcast group does not appear; an
 * episode page passes no chapters for the same reason. Nothing here branches on
 * who is mounting it — that is the same rule `orphaned` already follows, where
 * only the reader can populate the set and the book page passes a frozen empty
 * one. Editing follows the same rule: a host that cannot resubmit a note (none
 * today) simply omits `onEditAnnotation`/`onEditEpisodeNote`, and the row's Edit
 * button does not appear — the same optionality `onRemoveEpisodeNote` already
 * has.
 *
 * Grouped by chapter, then by episode, and ordered by position within each —
 * that is the order the marks were made in and the order they will be looked for
 * in. Not by date: "what did I mark in chapter three" is the question; "what did
 * I mark on Tuesday" is not.
 */
export function NotesList({
  annotations,
  bookmarks,
  chapters,
  episodes = [],
  episodeNotes = [],
  orphaned,
  slug,
  onJump,
  onPlay,
  onRemoveAnnotation,
  onRemoveBookmark,
  onRemoveEpisodeNote,
  onEditAnnotation,
  onEditEpisodeNote,
}: {
  annotations: Annotation[];
  bookmarks: Bookmark[];
  chapters: ChapterRef[];
  /** The podcast, when this host can reach it. Empty in the reader. */
  episodes?: EpisodeRef[];
  episodeNotes?: EpisodeNote[];
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
  /** Play an episode from a moment. Absent where there is no player to command. */
  onPlay?: (number: number, seconds: number) => void;
  onRemoveAnnotation: (id: string) => void;
  onRemoveBookmark: (id: string) => void;
  onRemoveEpisodeNote?: (id: string) => void;
  /** Resubmit a highlight's note with new text. Absent where a host cannot write. */
  onEditAnnotation?: (id: string, note: string) => void;
  /** Resubmit a moment's note with new text. Absent where a host cannot write. */
  onEditEpisodeNote?: (id: string, note: string) => void;
}) {
  // One editor open at a time, across annotations AND episode notes — ids are
  // unique across both, so there is never a collision, and a reader editing one
  // note while another sits mid-edit unsaved is not a case worth supporting.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");

  const startEdit = (id: string, note: string | null) => {
    setEditingId(id);
    setEditDraft(note ?? "");
  };
  const cancelEdit = () => {
    setEditingId(null);
    setEditDraft("");
  };
  const saveAnnotationEdit = (id: string) => {
    onEditAnnotation?.(id, editDraft);
    cancelEdit();
  };
  const saveEpisodeNoteEdit = (id: string) => {
    onEditEpisodeNote?.(id, editDraft);
    cancelEdit();
  };

  /* Go to the group the reader asked for.
     The episode list's note count links to `?tab=notes#ep-N`, and the browser's
     own hash handling cannot serve it: this list appears because a TAB changed,
     which is a search-param navigation with no document load and nothing for the
     browser to scroll to — by the time these sections exist, the moment it would
     have acted on has passed. So the move is made here, once, when the list that
     owns the target has rendered. Silent when the hash names nothing. */
  useEffect(() => {
    const hash = location.hash.slice(1);
    if (hash === "") return;
    document.getElementById(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
    // Deliberately not depending on the hash: the reader may scroll away and
    // switch tabs back, and yanking them to an anchor they have already read is
    // the sort of help nobody asked for. One move, on the render that follows
    // the link.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (annotations.length === 0 && bookmarks.length === 0 && episodeNotes.length === 0) {
    return (
      <EmptyState>
        Nothing marked yet. Select a passage while reading to highlight it, or mark a moment while
        listening to come back to it.
      </EmptyState>
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

  // The podcast, on the same principle: episode order from the book, and an
  // episode with nothing marked in it simply absent.
  const byEpisode = episodes
    .map((episode) => ({
      episode,
      moments: episodeNotes
        .filter((n) => n.number === episode.number)
        .sort((a, b) => a.seconds - b.seconds),
    }))
    .filter((g) => g.moments.length > 0);

  return (
    <div className="pf-notes">
      {byChapter.map(({ chapter, notes, marks }) => (
        <section key={chapter.anchorKey} className="pf-notes__chapter">
          <h3 className="pf-notes__heading">
            <span className="pf-notes__heading-main">
              <Icon icon={faBookOpen} />
              {chapter.title}
            </span>
            <span className="pf-notes__count">{count(notes.length + marks.length, "mark")}</span>
          </h3>

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

          {notes.map((annotation) =>
            editingId === annotation.id ? (
              <div
                key={annotation.id}
                className={`pf-mark pf-mark--paper pf-mark--${annotation.colour}`}
              >
                <div className="pf-mark__body">
                  <blockquote className="pf-mark__quote">{annotation.quote}</blockquote>
                  <RichNoteEditor
                    initialValue={editDraft}
                    onChange={setEditDraft}
                    placeholder="What matters about this passage?"
                    autoFocus
                    ariaLabel="Your note on this passage"
                  />
                  <div className="pf-mark__edit-actions">
                    <button
                      type="button"
                      onClick={cancelEdit}
                      className="pf-button pf-button--sm pf-button--ghost"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => saveAnnotationEdit(annotation.id)}
                      className="pf-button pf-button--sm pf-button--primary"
                    >
                      Save
                    </button>
                  </div>
                </div>
              </div>
            ) : (
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
                  {annotation.note ? (
                    <div className="pf-mark__text">{renderNote(annotation.note)}</div>
                  ) : null}
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
                {onEditAnnotation === undefined ? null : (
                  <button
                    type="button"
                    onClick={() => startEdit(annotation.id, annotation.note)}
                    aria-label={annotation.note ? "Edit this note" : "Add a note"}
                    className="pf-mark__remove pf-mark__edit"
                  >
                    <Icon icon={faPen} title={annotation.note ? "Edit this note" : "Add a note"} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onRemoveAnnotation(annotation.id)}
                  aria-label="Remove this highlight"
                  className="pf-mark__remove"
                >
                  <Icon icon={faTrash} title="Remove this highlight" />
                </button>
              </div>
            ),
          )}
        </section>
      ))}

      {byEpisode.map(({ episode, moments }) => (
        /* The `id` is a destination, not decoration: the episode list's note
           count links to `?tab=notes#ep-N`, and on a book of twenty episodes
           landing at the top of the list is landing nowhere. See the scroll
           effect above, which does the moving — a hash alone does not, because
           this list is rendered by a tab switch rather than by a page load. */
        <section id={`ep-${episode.number}`} key={`ep-${episode.number}`} className="pf-notes__chapter">
          <h3 className="pf-notes__heading">
            <span className="pf-notes__heading-main">
              <Icon icon={faHeadphones} /> {episode.number}. {episode.title}
            </span>
            <span className="pf-notes__count">{count(moments.length, "mark")}</span>
          </h3>

          {moments.map((moment) =>
            editingId === moment.id ? (
              <div key={moment.id} className="pf-mark pf-mark--moment">
                <div className="pf-mark__body">
                  <span className="pf-mark__kind">{clock(moment.seconds)}</span>
                  {moment.quote ? <blockquote className="pf-mark__quote">{moment.quote}</blockquote> : null}
                  <RichNoteEditor
                    initialValue={editDraft}
                    onChange={setEditDraft}
                    placeholder="What are you thinking?"
                    autoFocus
                    ariaLabel="Your note at this moment"
                  />
                  <div className="pf-mark__edit-actions">
                    <button
                      type="button"
                      onClick={cancelEdit}
                      className="pf-button pf-button--sm pf-button--ghost"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => saveEpisodeNoteEdit(moment.id)}
                      className="pf-button pf-button--sm pf-button--primary"
                    >
                      Save
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              // No colour. A listening note has no highlight to be made of — the
              // Post-it look on an annotation comes from the colour the reader
              // chose, and inventing one here would say something the mark does
              // not carry.
              <div key={moment.id} className="pf-mark pf-mark--moment">
                <MomentRow moment={moment} onPlay={onPlay} className="pf-mark__body" />
                {onEditEpisodeNote === undefined ? null : (
                  <button
                    type="button"
                    onClick={() => startEdit(moment.id, moment.note)}
                    aria-label={moment.note ? "Edit this note" : "Add a note"}
                    className="pf-mark__remove pf-mark__edit"
                  >
                    <Icon icon={faPen} title={moment.note ? "Edit this note" : "Add a note"} />
                  </button>
                )}
                {onRemoveEpisodeNote === undefined ? null : (
                  <button
                    type="button"
                    onClick={() => onRemoveEpisodeNote(moment.id)}
                    aria-label="Remove this note"
                    className="pf-mark__remove"
                  >
                    <Icon icon={faTrash} title="Remove this note" />
                  </button>
                )}
              </div>
            ),
          )}
        </section>
      ))}
    </div>
  );
}

/**
 * One marked moment: the time, what was said there, and what the listener added.
 *
 * Plays from a few seconds BEFORE the stored time — see `PRE_ROLL_S`. There is
 * no link fallback and no episode page to link TO: the player is in the layout
 * and outlives navigation, so every host that can show these rows can also
 * command it. A host that passes no `onPlay` gets a row that reads and does not
 * move, which is honest rather than a control that goes nowhere.
 */
function MomentRow({
  moment,
  onPlay,
  className,
}: {
  moment: EpisodeNote;
  onPlay?: (number: number, seconds: number) => void;
  className: string;
}) {
  const from = Math.max(0, moment.seconds - PRE_ROLL_S);

  const body = (
    <>
      <span className="pf-mark__kind">{clock(moment.seconds)}</span>
      {/* The transcript line as it read when the moment was marked. Quoted like
          a highlight, because that is what it is: the words the listener was
          reacting to. */}
      {moment.quote ? <blockquote className="pf-mark__quote">{moment.quote}</blockquote> : null}
      {moment.note ? <div className="pf-mark__text">{renderNote(moment.note)}</div> : null}
      {moment.quote || moment.note ? null : (
        <p className="pf-mark__text pf-mark__text--quiet">Marked while listening.</p>
      )}
    </>
  );

  if (onPlay === undefined) return <div className={className}>{body}</div>;

  return (
    <button type="button" onClick={() => onPlay(moment.number, from)} className={className}>
      {body}
    </button>
  );
}

/** `m:ss`, the same clock the player and the transcript use. */
function clock(s: number): string {
  const total = Math.max(0, Math.floor(s));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const sec = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
    : `${m}:${String(sec).padStart(2, "0")}`;
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
