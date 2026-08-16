import {
  faChevronLeft,
  faChevronRight,
  faList,
  faNoteSticky,
} from "@fortawesome/free-solid-svg-icons";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";

import type { Route } from "./+types/read-offline";
import { AppShell } from "~/components/AppShell";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { NotesList } from "~/components/reader/NotesList";
import { useHighlights, type Painted } from "~/components/reader/Highlights";
import { useMarks } from "~/components/reader/useMarks";
import { annotationsInChapter, bookmarksInChapter, submit } from "~/lib/marks";
import { readBook, type StoredChapter } from "~/lib/offline";
import { session } from "~/middleware/session";

/**
 * A downloaded chapter, read with no network.
 *
 * WHY THIS EXISTS RATHER THAN THE REAL READER WORKING OFFLINE. The reader lives
 * at /book/:slug/read/:chapter, and serving that page with no network would mean
 * the service worker keeping a copy of its document — which for one account
 * carries Scholar Companion cards, in a store no `viewer.isAdmin` check guards.
 * public/sw.js refuses to cache any /book document for exactly that reason, and
 * a test holds it to that. So the offline path is a DIFFERENT page whose
 * document contains nothing about anybody: everything on screen is read from
 * IndexedDB after it loads.
 *
 * WHY ONE ROUTE WITH THE BOOK IN THE QUERY, rather than /read-offline/:slug/:ch.
 * The worker caches documents by PATH. A parameterised path is a different key
 * per chapter, so only the chapters already visited online would open — which is
 * precisely backwards. As a query, every chapter of every downloaded book is
 * served from the one cached shell.
 *
 * YOUR MARKS ARE HERE, and they cost nothing to bring: `lib/marks.ts` already
 * paints from a local cache before the network answers and already queues writes
 * until they can be sent — it has survived a tunnel since long before any of this
 * existed. So the same `useMarks` and the same `paintHighlights` run here, over
 * the same chapter HTML, and a highlight resolves against it exactly as it does
 * online. Removing or editing one queues like any other write.
 *
 * WHAT IS STILL NOT HERE, and is said on the page rather than left to be
 * discovered: MAKING a new highlight. That needs the selection machinery and an
 * anchor computed from a live range, which is the reader's own surface and a
 * larger thing than reading on a plane.
 *
 * AND NO COMPANION, ever. Its cards are readable by one account through one
 * function with the gate inside it; nothing on this page has been near them, and
 * `paintHighlights` is called with no passages at all rather than with an empty
 * list that a later edit might fill.
 */

export function meta(): Route.MetaDescriptors {
  return [
    { title: "Reading offline — Podcast Factory" },
    {
      name: "description",
      content: "A downloaded chapter, read with no network.",
    },
  ];
}

export function loader({ context }: Route.LoaderArgs) {
  // The masthead's Dashboard link and NOTHING else. This document is the one the
  // worker keeps, so anything the loader returned would be served back to
  // whoever opens the page next — see the module note.
  return { isAdmin: context.get(session).viewer?.isAdmin === true };
}

export default function ReadOffline({ loaderData }: Route.ComponentProps) {
  const [params, setParams] = useSearchParams();
  const slug = params.get("book") ?? "";
  const wanted = params.get("chapter");

  const [chapters, setChapters] = useState<StoredChapter[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [showContents, setShowContents] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [orphaned, setOrphaned] = useState<ReadonlySet<string>>(EMPTY);

  /* The element the highlights are painted INTO.
     They are added to the live DOM rather than to the HTML string, because the
     prose is injected with `dangerouslySetInnerHTML` and React will not
     reconcile inside it — re-injecting the chapter to add a mark would throw
     away the scroll position. Same reason, same mechanism, as the reader. */
  const body = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void readBook(slug).then((found) => {
      if (cancelled) return;
      setChapters(found);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const here =
    chapters === null
      ? -1
      : wanted === null
        ? 0
        : Math.max(
            0,
            chapters.findIndex((c) => c.anchorKey === wanted),
          );
  const chapter =
    chapters === null || here < 0 ? null : (chapters[here] ?? null);

  // Scrolled to the top on every chapter change. Without it, moving to the next
  // chapter leaves the reader wherever they were down the previous one.
  useEffect(() => {
    if (chapter !== null) window.scrollTo(0, 0);
  }, [chapter?.anchorKey]);

  const goTo = (key: string) => {
    setParams({ book: slug, chapter: key }, { preventScrollReset: false });
    setShowContents(false);
    setShowNotes(false);
  };

  /* ONE object per chapter, not one per render.
     Load-bearing, and the reader's own note at its element says why: React
     compares props by identity, and `dangerouslySetInnerHTML` written inline is
     a new object every render — so React re-sets `innerHTML` on each one and
     wipes every painted highlight, while the paint effect's own dependencies
     have not changed so nothing puts them back. Written inline here first, and
     the highlight duly vanished the moment the notes panel was opened. */
  const html = useMemo(
    () => ({ __html: chapter?.html ?? "" }),
    [chapter?.html],
  );

  /* ---- The reader's own marks, unchanged ---------------------------------
     `useMarks` paints the local cache before it asks the server and treats a
     failed request as nothing to report, so with no network it simply shows
     what the last visit knew. `submit` applies a change on screen at once,
     queues it, and replays it until it lands. Neither needed anything added
     for this page; they have worked this way since long before it existed. */
  const marks = useMarks(slug);
  const key = chapter?.anchorKey ?? "";
  const annotations = useMemo(
    () => annotationsInChapter(marks, key),
    [marks, key],
  );
  const bookmarks = useMemo(() => bookmarksInChapter(marks, key), [marks, key]);

  const onResolved = useCallback((painted: Painted) => {
    // Replaced only when the SET differs, not on every paint. The painter runs
    // whenever the annotations change, and handing back a fresh Set each time
    // would re-render this page on every one of them.
    setOrphaned((current) =>
      sameSet(current, painted.orphaned) ? current : painted.orphaned,
    );
  }, []);

  // No passages argument at all — see the module note. The Companion is not
  // absent here by being empty; it is absent by never being asked for.
  useHighlights(body, annotations, activeId, onResolved);

  const contents = useMemo(
    () =>
      (chapters ?? []).map((c) => ({
        anchorKey: c.anchorKey,
        title: c.title,
        idx: c.idx,
      })),
    [chapters],
  );

  /* Scroll to a mark, or move to the chapter holding it first.
     `requestAnimationFrame` because setting the active id repaints the chapter,
     and the element to scroll to is the one that repaint produces. */
  const jump = useCallback(
    (anchorKey: string, id: string) => {
      if (anchorKey !== key) {
        goTo(anchorKey);
        return;
      }
      setShowNotes(false);
      setActiveId(id);
      requestAnimationFrame(() => {
        body.current
          ?.querySelector(`mark[data-mark-id="${id}"]`)
          ?.scrollIntoView({ block: "center", behavior: "smooth" });
      });
    },
    // `goTo` is recreated every render and depending on it would rebuild this
    // on each one; what it closes over — `slug` — cannot change without the
    // whole page changing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key],
  );

  return (
    <AppShell here="downloads" isAdmin={loaderData.isAdmin}>
      {loading ? (
        // Deliberately blank rather than a spinner: reading the chapters out of
        // IndexedDB takes a frame or two, and a spinner that flashes for 40ms is
        // noise on the page a listener opened to read.
        <p className="sr-only">Loading</p>
      ) : chapter === null ? (
        <EmptyState>
          {slug === ""
            ? "No book was named."
            : "This book is not on your device. When you next have a signal, open it and press Read Offline."}{" "}
          <Link to="/downloads" className="pf-link">
            See what is downloaded
          </Link>
          .
        </EmptyState>
      ) : (
        <>
          <div className="pf-offline-read__bar">
            <button
              type="button"
              className="pf-button pf-button--soft pf-button--sm"
              onClick={() => setShowContents((open) => !open)}
              aria-expanded={showContents}
            >
              <Icon icon={faList} />
              Chapters
            </button>
            {/* Drawn only when there is something in it. A Notes control that
                opens an empty panel teaches that the control does nothing —
                the same rule the book page's own Notes tab follows. */}
            {annotations.length + bookmarks.length === 0 ? null : (
              <button
                type="button"
                className="pf-button pf-button--soft pf-button--sm"
                onClick={() => setShowNotes((open) => !open)}
                aria-expanded={showNotes}
              >
                <Icon icon={faNoteSticky} />
                Notes {annotations.length + bookmarks.length}
              </button>
            )}

            <p className="pf-offline-read__where">
              {here + 1} of {chapters!.length} · reading from this device
            </p>
          </div>

          {showNotes ? (
            <div className="pf-offline-read__notes">
              <NotesList
                annotations={annotations}
                bookmarks={bookmarks}
                chapters={contents}
                orphaned={orphaned}
                slug={slug}
                onJump={jump}
                onRemoveAnnotation={(id) => submit("unannotate", { id })}
                onRemoveBookmark={(id) => submit("unbookmark", { id })}
                onEditAnnotation={(id, note) => {
                  const existing = annotations.find((a) => a.id === id);
                  if (existing === undefined) return;
                  submit("annotate", {
                    id: existing.id,
                    anchorKey: existing.anchorKey,
                    blockIndex: String(existing.blockIndex),
                    startOffset: String(existing.startOffset),
                    endOffset: String(existing.endOffset),
                    quote: existing.quote,
                    colour: existing.colour,
                    note,
                  });
                }}
              />
              <p className="pf-offline-read__caveat">
                Marks made elsewhere appear here, and changes you make are sent
                when you next have a signal. Making a NEW highlight needs the
                full reader.
              </p>
            </div>
          ) : null}

          {showContents ? (
            <nav aria-label="Chapters" className="pf-offline-read__contents">
              <ol>
                {chapters!.map((c, i) => (
                  <li key={c.anchorKey}>
                    <button
                      type="button"
                      onClick={() => goTo(c.anchorKey)}
                      aria-current={i === here ? "true" : undefined}
                      className="pf-offline-read__link"
                    >
                      {c.title}
                    </button>
                  </li>
                ))}
              </ol>
            </nav>
          ) : null}

          <article className="pf-page">
            <h1 className="pf-chapter-title">{chapter.title}</h1>
            {/* The SAME classes the reader's own prose carries, so a chapter
                read offline is set in the same measure, the same face and the
                same Arabic handling. The HTML was rendered at publish time;
                nothing here re-renders it. */}
            <div
              ref={body}
              className="reader pf-chapter-body"
              dangerouslySetInnerHTML={html}
            />
          </article>

          <nav
            className="pf-offline-read__move"
            aria-label="Move between chapters"
          >
            {here > 0 ? (
              <button
                type="button"
                className="pf-button pf-button--soft"
                onClick={() => goTo(chapters![here - 1].anchorKey)}
              >
                <Icon icon={faChevronLeft} />
                {chapters![here - 1].title}
              </button>
            ) : (
              <span />
            )}
            {here < chapters!.length - 1 ? (
              <button
                type="button"
                className="pf-button pf-button--soft"
                onClick={() => goTo(chapters![here + 1].anchorKey)}
              >
                {chapters![here + 1].title}
                <Icon icon={faChevronRight} />
              </button>
            ) : (
              <span />
            )}
          </nav>
        </>
      )}
    </AppShell>
  );
}

/** A stable "nothing orphaned", so the initial value cannot drive a re-render. */
const EMPTY: ReadonlySet<string> = new Set();

/** Whether two sets hold the same ids — see `onResolved`. */
function sameSet(a: ReadonlySet<string>, b: ReadonlySet<string>): boolean {
  if (a.size !== b.size) return false;
  for (const id of a) if (!b.has(id)) return false;
  return true;
}
