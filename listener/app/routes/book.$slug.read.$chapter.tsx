import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  faChevronLeft,
  faChevronRight,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useNavigate } from "react-router";

import type { Route } from "./+types/book.$slug.read.$chapter";
import { Icon } from "~/components/Icon";
import { NotesList } from "~/components/reader/NotesList";
import { ContentsPanel } from "~/components/reader/ContentsPanel";
import { ReaderToolbar } from "~/components/reader/ReaderToolbar";
import { SelectionBar } from "~/components/reader/SelectionBar";
import { useHighlights, type Painted } from "~/components/reader/Highlights";
import { useMarks } from "~/components/reader/useMarks";
import { cloudflare } from "~/context";
import { blocksOf } from "~/lib/anchor";
import type { Anchor } from "~/lib/anchor";
import {
  annotationsInChapter,
  bookmarksInChapter,
  newId,
  recordProgress,
  submit,
  type Colour,
} from "~/lib/marks";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { unitBySlug } from "~/server/access.server";
import { readingMinutes } from "~/lib/reading";
import { chapterOf, chaptersOf } from "~/server/catalog.server";

/**
 * One chapter of the reading edition.
 *
 * Same gate as the book page, on the same `params.slug`, so there is no second
 * access rule to keep in step. Continuous scroll rather than pagination: this is
 * argued prose that runs for pages at a time, and page breaks in a translation
 * put a seam where the author did not.
 *
 * The reader's own marks are NOT loaded here. They are fetched client-side by
 * `useMarks`, on purpose: the cached copy paints before the network answers, and
 * putting them in the loader would make every chapter navigation wait on a query
 * whose result is usually already known. It would also put per-person data into
 * the SSR HTML, which is a thing to keep out of a cache by accident.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const slug = params.slug;
  const key = decodeURIComponent(params.chapter);

  const [unit, chapter, all] = await Promise.all([
    unitBySlug(env.DB, slug),
    chapterOf(env.DB, slug, key),
    chaptersOf(env.DB, slug),
  ]);

  // A chapter key that is not in this book is a 404 exactly like a slug that is
  // not in the library — same shape, so neither reveals what exists.
  if (unit === null || chapter === null) notFound();

  const here = all.findIndex((c) => c.anchorKey === chapter.anchorKey);

  return {
    bookTitle: unit.title,
    slug,
    chapter,
    contents: all,
    position: here,
    previous: here > 0 ? all[here - 1] : null,
    next: here >= 0 && here < all.length - 1 ? all[here + 1] : null,
  };
}

export default function ReadChapter({ loaderData }: Route.ComponentProps) {
  const { bookTitle, slug, chapter, contents, position, previous, next } =
    loaderData;
  const navigate = useNavigate();

  const [progress, setProgress] = useState(0);
  const [contentsOpen, setContentsOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [orphaned, setOrphaned] = useState<Set<string>>(() => new Set());

  const body = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLSpanElement>(null);

  const marks = useMarks(slug);
  const annotations = useMemo(
    () => annotationsInChapter(marks, chapter.anchorKey),
    [marks, chapter.anchorKey],
  );
  const bookmarks = useMemo(
    () => bookmarksInChapter(marks, chapter.anchorKey),
    [marks, chapter.anchorKey],
  );

  /* ---- Progress ---------------------------------------------------------
     Measured from the ARTICLE, not the window: the masthead and the footer
     navigation are not part of the chapter, and counting them makes the bar
     reach 100% while there is still a page of text left.

     The bar is driven by a custom property rather than an inline `transform`,
     the same way `lib/reading.ts` drives the reading controls: JS supplies one
     scalar, and what that scalar MEANS is a rule in the stylesheet.

     It now also RECORDS. `recordProgress` coalesces to one write every few
     seconds and the store forces a final one out on page-hide, so scrolling a
     chapter is a handful of requests rather than hundreds.                  */
  useEffect(() => {
    function measure() {
      const element = body.current;
      if (element === null) return;
      const start = element.offsetTop;
      const height = element.offsetHeight - window.innerHeight;
      const scrolled = window.scrollY - start;
      const fraction =
        height <= 0 ? 1 : Math.min(1, Math.max(0, scrolled / height));
      setProgress(fraction);
      bar.current?.style.setProperty("--l-progress", String(fraction));

      recordProgress({
        anchorKey: chapter.anchorKey,
        fraction: fraction.toFixed(4),
        chaptersDone: String(Math.max(0, position)),
      });
    }

    measure();
    window.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    return () => {
      window.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
    };
  }, [chapter.anchorKey, position]);

  /* ---- Restore where you were ------------------------------------------
     Runs once per chapter, and only when the reader arrived at the chapter
     they left off in — jumping to chapter 6 from the contents must not throw
     them back to where they were in chapter 6 last week, because they chose to
     open it fresh. Deliberately guarded on `restored` so a later reconcile
     from the server cannot scroll the page out from under a reader who has
     already started moving.                                                */
  const restored = useRef<string | null>(null);
  useEffect(() => {
    const saved = marks.progress;
    if (saved === null) return;
    if (restored.current === chapter.anchorKey) return;
    restored.current = chapter.anchorKey;

    if (saved.anchorKey !== chapter.anchorKey) return;
    if (saved.fraction <= 0.02 || saved.fraction >= 0.98) return;
    if (window.scrollY > 0) return; // they have already moved; leave them alone

    const element = body.current;
    if (element === null) return;
    const height = element.offsetHeight - window.innerHeight;
    if (height <= 0) return;

    window.scrollTo({
      top: element.offsetTop + height * saved.fraction,
      behavior: "instant",
    });
  }, [marks.progress, chapter.anchorKey]);

  /* ---- Highlights -------------------------------------------------------- */

  const onResolved = useCallback(
    (painted: Painted) => {
      setOrphaned((current) =>
        sameSet(current, painted.orphaned) ? current : painted.orphaned,
      );

      // A passage that moved gets its corrected offsets written back, so the
      // next device to open this chapter finds it first time instead of
      // repeating the search. Same intent as creating it — the server's UPSERT
      // makes create and correct one statement.
      for (const [id, at] of painted.corrected) {
        const annotation = annotations.find((a) => a.id === id);
        if (annotation === undefined) continue;
        if (
          annotation.blockIndex === at.blockIndex &&
          annotation.startOffset === at.startOffset &&
          annotation.endOffset === at.endOffset
        ) {
          continue; // already agrees; writing would be a pointless round trip
        }
        submit("annotate", {
          id,
          anchorKey: annotation.anchorKey,
          blockIndex: String(at.blockIndex),
          startOffset: String(at.startOffset),
          endOffset: String(at.endOffset),
          quote: annotation.quote,
          prefix: annotation.prefix,
          colour: annotation.colour,
          note: annotation.note ?? "",
        });
      }
    },
    [annotations],
  );

  useHighlights(body, annotations, activeId, onResolved);

  const highlight = useCallback(
    (anchor: Anchor, colour: Colour) => {
      submit("annotate", {
        id: newId(),
        anchorKey: chapter.anchorKey,
        blockIndex: String(anchor.blockIndex),
        startOffset: String(anchor.startOffset),
        endOffset: String(anchor.endOffset),
        quote: anchor.quote,
        prefix: anchor.prefix,
        colour,
        note: "",
      });
    },
    [chapter.anchorKey],
  );

  const recolour = useCallback(
    (id: string, colour: Colour) => {
      const existing = annotations.find((a) => a.id === id);
      if (existing === undefined) return;
      submit("annotate", { ...toFields(existing), colour });
    },
    [annotations],
  );

  const note = useCallback(
    (id: string | null, anchor: Anchor | null, text: string) => {
      // Writing a note on an unhighlighted selection creates the highlight too.
      // A note with no passage would have nothing to point at, and gold is the
      // default because it is the least emphatic of the four.
      if (id === null) {
        if (anchor === null) return;
        submit("annotate", {
          id: newId(),
          anchorKey: chapter.anchorKey,
          blockIndex: String(anchor.blockIndex),
          startOffset: String(anchor.startOffset),
          endOffset: String(anchor.endOffset),
          quote: anchor.quote,
          prefix: anchor.prefix,
          colour: "gold",
          note: text,
        });
        return;
      }

      const existing = annotations.find((a) => a.id === id);
      if (existing === undefined) return;
      submit("annotate", { ...toFields(existing), note: text });
    },
    [annotations, chapter.anchorKey],
  );

  const removeAnnotation = useCallback(
    (id: string) => submit("unannotate", { id }),
    [],
  );
  const removeBookmark = useCallback(
    (id: string) => submit("unbookmark", { id }),
    [],
  );

  /* ---- Bookmarks --------------------------------------------------------
     A bookmark marks the topmost block currently on screen, which is what
     "here" means to someone looking at the page. Toggling removes whichever
     bookmark is in this chapter — there is at most one per chapter by design,
     because "where I left off in this chapter" has one answer and a list of
     near-identical bookmarks in one chapter would be noise, not a feature.  */
  const bookmarked = bookmarks.length > 0;

  const toggleBookmark = useCallback(() => {
    if (bookmarked) {
      for (const b of bookmarks) submit("unbookmark", { id: b.id });
      return;
    }

    const root = body.current;
    if (root === null) return;
    const blocks = blocksOf(root);
    const index = blocks.findIndex(
      (b) => b.getBoundingClientRect().bottom > 120,
    );
    const block = blocks[index === -1 ? 0 : index];

    submit("bookmark", {
      id: newId(),
      anchorKey: chapter.anchorKey,
      blockIndex: String(index === -1 ? 0 : index),
      label: (block?.textContent ?? chapter.title)
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 160),
    });
  }, [bookmarked, bookmarks, chapter.anchorKey, chapter.title]);

  /* ---- Jumping to a mark from the notes drawer -------------------------- */
  const jump = useCallback(
    (anchorKey: string, id: string) => {
      if (anchorKey !== chapter.anchorKey) {
        void navigate(
          `/book/${slug}/read/${encodeURIComponent(anchorKey)}#mark-${id}`,
        );
        return;
      }
      setNotesOpen(false);
      setActiveId(id);
      // After the repaint that the activeId change triggers, so the element the
      // ring was added to is the one scrolled to.
      requestAnimationFrame(() => {
        const target = body.current?.querySelector(
          `mark[data-mark-id="${id}"]`,
        );
        target?.scrollIntoView({ block: "center", behavior: "smooth" });
      });
    },
    [chapter.anchorKey, navigate, slug],
  );

  // Arriving from the book page's Notes tab with `#mark-<id>` in the URL.
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash.startsWith("#mark-")) return;
    const id = hash.slice("#mark-".length);
    if (
      !annotations.some((a) => a.id === id) &&
      !bookmarks.some((b) => b.id === id)
    )
      return;
    setActiveId(id);
    requestAnimationFrame(() => {
      body.current
        ?.querySelector(`mark[data-mark-id="${id}"]`)
        ?.scrollIntoView({ block: "center", behavior: "smooth" });
    });
  }, [annotations, bookmarks]);

  const total = readingMinutes(chapter.wordCount);
  const left = Math.max(0, Math.round(total * (1 - progress)));

  return (
    <div className="pf-shell">
      <div className="reading-progress" aria-hidden="true">
        <span ref={bar} />
      </div>

      {/* Contents on the LEFT, your own marks on the RIGHT — the same drawer
          mirrored, so a reader learns one behaviour and the book's structure and
          their notes on it stay on opposite sides. */}
      <ContentsPanel
        open={contentsOpen}
        onOpen={() => {
          setContentsOpen(true);
          setNotesOpen(false);
        }}
        onClose={() => setContentsOpen(false)}
        chapters={contents}
        currentKey={chapter.anchorKey}
        slug={slug}
      />

      {notesOpen ? (
        <>
          {/* Click-away. Not focusable and hidden from assistive tech — Escape
              and the close button are the keyboard routes out, and a scrim in
              the tab order is a stop that announces nothing. */}
          <button
            type="button"
            aria-hidden="true"
            tabIndex={-1}
            onClick={() => setNotesOpen(false)}
            className="pf-drawer__scrim"
          />
          <aside aria-label="Your notes and highlights" className="pf-drawer">
            <div className="pf-drawer__head">
              <h2 className="pf-drawer__title">Your notes</h2>
              <button
                type="button"
                onClick={() => setNotesOpen(false)}
                aria-label="Close your notes"
                className="pf-tool"
              >
                <Icon icon={faXmark} title="Close your notes" />
              </button>
            </div>
            <div className="pf-drawer__body">
              <NotesList
                annotations={marks.annotations}
                bookmarks={marks.bookmarks}
                chapters={contents}
                orphaned={orphaned}
                slug={slug}
                onJump={jump}
                onRemoveAnnotation={removeAnnotation}
                onRemoveBookmark={removeBookmark}
              />
            </div>
          </aside>
        </>
      ) : null}

      <main id="main" className="pf-reader">
        {/* ---- Above the page ----
            The work's name, then the controls, then the sheet. Both sit OUTSIDE
            the article deliberately: the sheet is the book, and a control
            printed on it would be a control printed in the book.

            The toolbar was in a sticky header until now. Out of it, nothing at
            all covers the prose while reading — and the title, which a sticky
            bar could only ever show as a truncated fragment, gets its full size
            back. The cost is honest: changing a setting mid-chapter means
            scrolling up. */}
        <div className="pf-reader-head">
          <h1 className="pf-reader-head__book">{bookTitle}</h1>

          <div className="pf-toolbar-rail">
            <ReaderToolbar
              minutesLeft={left}
              bookmarked={bookmarked}
              onToggleBookmark={toggleBookmark}
              notesCount={marks.annotations.length + marks.bookmarks.length}
              notesOpen={notesOpen}
              onToggleNotes={() => {
                setNotesOpen((v) => !v);
                setContentsOpen(false);
              }}
            />
          </div>
        </div>

        <div className="pf-reader-page">
          <article ref={body} className="pf-page">
            {/* An <h2>, and the book above is the <h1> — which is also the true
                nesting: a chapter is part of a work. */}
            <h2 className="pf-chapter-title">{chapter.title}</h2>

            {/* Position in the edition, NOT a chapter number: the introduction
                is the first entry, so this and the book's own "3." in the
                heading differ by one. Saying "chapter" would contradict it. */}
            <p className="pf-chapter-meta">
              {chapter.idx} of {contents.length} in this edition · about {total}{" "}
              {total === 1 ? "minute" : "minutes"}
            </p>

            {/* The HTML was rendered at publish time by the same function that
                produces the printed book, so this is not "trusting user input" —
                it is the book. See app/server/catalog.server.ts. Highlights are
                added to the live DOM after this renders; React never reconciles
                inside it. */}
            <div
              className="reader pf-chapter-body"
              dangerouslySetInnerHTML={{ __html: chapter.html }}
            />
          </article>

          {/* Inside the page container, so the two cards line up with the edges
              of the sheet above them. As a sibling it inherited the reader's
              full width and ran to both edges of the window. */}
          <nav className="pf-turn">
            {previous ? (
              <Link
                to={`/book/${slug}/read/${encodeURIComponent(previous.anchorKey)}`}
                className="pf-card pf-card--link pf-card--padded pf-turn__link"
              >
                <span className="pf-eyebrow">
                  <Icon icon={faChevronLeft} />
                  Previous
                </span>
                <span className="pf-turn__title">{previous.title}</span>
              </Link>
            ) : (
              <span className="pf-turn__gap" />
            )}

            {next ? (
              <Link
                to={`/book/${slug}/read/${encodeURIComponent(next.anchorKey)}`}
                className="pf-card pf-card--link pf-card--padded pf-turn__link pf-turn__link--end"
              >
                <span className="pf-eyebrow">
                  Next
                  <Icon icon={faChevronRight} />
                </span>
                <span className="pf-turn__title">{next.title}</span>
              </Link>
            ) : (
              <Link
                to={`/book/${slug}`}
                className="pf-card pf-card--link pf-card--padded pf-turn__link pf-turn__link--end"
              >
                <span className="pf-eyebrow">
                  The end
                  <Icon icon={faChevronRight} />
                </span>
                <span className="pf-turn__title">Back to {bookTitle}</span>
              </Link>
            )}
          </nav>
        </div>

        <SelectionBar
          bodyRef={body}
          onHighlight={highlight}
          onRecolour={recolour}
          onNote={note}
          onRemove={removeAnnotation}
        />
      </main>
    </div>
  );
}

/** An annotation as the form fields the marks route expects. */
const toFields = (a: {
  id: string;
  anchorKey: string;
  blockIndex: number;
  startOffset: number;
  endOffset: number;
  quote: string;
  prefix: string;
  colour: string;
  note: string | null;
}) => ({
  id: a.id,
  anchorKey: a.anchorKey,
  blockIndex: String(a.blockIndex),
  startOffset: String(a.startOffset),
  endOffset: String(a.endOffset),
  quote: a.quote,
  prefix: a.prefix,
  colour: a.colour,
  note: a.note ?? "",
});

/** Whether two id sets hold the same members — used to avoid a needless render. */
function sameSet(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const v of a) if (!b.has(v)) return false;
  return true;
}
