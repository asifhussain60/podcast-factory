import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  faBookOpen,
  faChevronLeft,
  faChevronRight,
  faDownload,
  faHeadphones,
  faImages,
  faNoteSticky,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useNavigate } from "react-router";

import type { Route } from "./+types/book.$slug.read.$chapter";
import { AppShell } from "~/components/AppShell";
import { Icon } from "~/components/Icon";
import { CompanionList } from "~/components/reader/CompanionList";
import { NotesList } from "~/components/reader/NotesList";
import { ContentsPanel } from "~/components/reader/ContentsPanel";
import { SidePanel } from "~/components/reader/SidePanel";
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
import { session } from "~/middleware/session";
import { unitBySlug } from "~/server/access.server";
import { readingMinutes } from "~/lib/reading";
import { chapterOf, chaptersOf, surfacesOf } from "~/server/catalog.server";
import { companionFor } from "~/server/companion.server";

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

  const viewer = context.get(session).viewer;

  const [unit, chapter, all, surfaces, companion] = await Promise.all([
    unitBySlug(env.DB, slug),
    chapterOf(env.DB, slug, key),
    chaptersOf(env.DB, slug),
    // What ELSE this book offers, so a chapter can say so and point at it. One
    // query rather than the three the book page runs, because this needs only
    // whether each thing exists.
    surfacesOf(env.DB, slug),
    // Empty, and un-queried, for everyone but the administrator. The gate is
    // inside that function rather than a condition here — see the module.
    companionFor(env.DB, viewer, slug, key),
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
    companion,
    surfaces,
    // Which DRAWER this reader gets, decided once for the whole book rather than
    // per chapter. Derived from `companion.length` it would have been free, but
    // then the right-hand panel would be the Companion on the two chapters that
    // have cards and the notes list on the other seven — a drawer that changes
    // what it is depending on where you are standing.
    isCompanion: viewer?.isAdmin === true,
    // The same value, and deliberately a second field: this one decides whether
    // the MASTHEAD offers the Access link, which is a question about who is
    // signed in. Folding the two together would make a change to who gets the
    // Companion silently change who is offered the admin section.
    isAdmin: viewer?.isAdmin === true,
  };
}

export default function ReadChapter({ loaderData }: Route.ComponentProps) {
  const {
    bookTitle,
    slug,
    chapter,
    contents,
    position,
    previous,
    next,
    companion,
    isCompanion,
    isAdmin,
    surfaces,
  } = loaderData;
  const navigate = useNavigate();

  const [progress, setProgress] = useState(0);
  const [contentsOpen, setContentsOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [orphaned, setOrphaned] = useState<Set<string>>(() => new Set());
  const [unplaced, setUnplaced] = useState<Set<string>>(() => new Set());
  /** Companion cards whose sentence is on screen, in reading order. */
  const [inView, setInView] = useState<string[]>([]);
  /** A tinted sentence was tapped; the nonce makes a repeat tap re-fire. */
  const [focusCard, setFocusCard] = useState<{ id: string; nonce: number } | null>(null);
  /** Bumped once per paint, so the sweep below re-observes the marks just made. */
  const [paints, setPaints] = useState(0);

  const body = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLSpanElement>(null);

  // One object per chapter, not one per render. See the note at the element
  // itself: a fresh literal here makes React re-set `innerHTML` on every
  // re-render, which throws away every highlight painted into it.
  const html = useMemo(() => ({ __html: chapter.html }), [chapter.html]);

  const marks = useMarks(slug);
  const markCount = marks.annotations.length + marks.bookmarks.length;
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
      setUnplaced((current) =>
        sameSet(current, painted.unplaced) ? current : painted.unplaced,
      );
      // Unconditional, and that is the point: it says a paint HAPPENED, which is
      // what the observer below needs to know. Comparing sets like the two above
      // would miss the repaint that produced the same marks in a new DOM.
      setPaints((n) => n + 1);

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

  /* ---- The Companion ----------------------------------------------------
     The cards' sentences are tinted by the SAME paint pass as the highlights —
     one function owns this DOM — and the panel then follows the page from the
     marks that pass produced. `companion` comes from the loader and is stable
     for the life of the chapter, so the memo is what keeps it from counting as
     a change and repainting the chapter on every scroll tick.                */
  const passages = useMemo(
    () => companion.filter((c) => c.quote !== null).map((c) => ({ id: c.id, quote: c.quote! })),
    [companion],
  );

  useHighlights(body, annotations, activeId, onResolved, passages);

  // Which explained sentences are on screen. An observer rather than a scroll
  // handler: the answer changes only when a passage crosses the viewport edge,
  // and a scroll listener would recompute it a hundred times on the way there.
  // Re-created after every paint, because the previous marks no longer exist.
  useEffect(() => {
    const root = body.current;
    if (root === null || passages.length === 0) return;

    const marks = Array.from(root.querySelectorAll<HTMLElement>("mark.pf-cp"));
    if (marks.length === 0) return;

    const visible = new Set<string>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = (entry.target as HTMLElement).dataset.companionId;
          if (id === undefined) continue;
          if (entry.isIntersecting) visible.add(id);
          else visible.delete(id);
        }
        // In READING order, not in the order the observer reported them, so the
        // card that opens is the passage furthest up the page — the one being
        // read rather than the one just appearing at the bottom.
        const ordered = marks
          .map((m) => m.dataset.companionId)
          .filter((id): id is string => id !== undefined && visible.has(id));
        setInView((current) => (sameList(current, ordered) ? current : ordered));
      },
      // A band around the middle of the screen. The whole viewport would call a
      // passage "here" while it is still a screen away at the bottom.
      { rootMargin: "-25% 0px -35% 0px" },
    );

    for (const mark of marks) observer.observe(mark);
    return () => observer.disconnect();
  }, [passages, paints]);

  /* ---- Open on arrival, for the account the Companion belongs to ---------
     The panel is not something to go and get: it is part of how this reader
     reads, so it is already there when the chapter opens, and again on the next
     chapter. Closing it closes it for that chapter, which is what a close button
     has to mean.

     Only where it can stand BESIDE the text. Below that width the drawer covers
     the page and dims it, so opening it automatically would land the reader on a
     chapter they cannot read until they dismiss something — and the tab is right
     there. `matchMedia` rather than a width comparison so the same number lives
     in one place, the stylesheet, with the rule it drives.

     It runs after hydration rather than in the initial state because the server
     does not know the viewport. The panel arrives a frame after the text, which
     on a wide screen reads as it sliding in, and on a phone never happens.     */
  useEffect(() => {
    if (!isCompanion) return;
    if (!window.matchMedia(DOCKED_AT).matches) return;
    setNotesOpen(true);
    setContentsOpen(false);
  }, [isCompanion, chapter.anchorKey]);

  // Tapping an explained sentence opens its card. A tap that lands inside the
  // reader's OWN highlight is theirs — the selection bar answers it — because a
  // mark they made is the one they meant to press.
  useEffect(() => {
    const root = body.current;
    if (root === null || passages.length === 0) return;

    const open = (target: HTMLElement | null) => {
      if (target?.closest("mark.pf-hl")) return;
      const mark = target?.closest("mark.pf-cp") as HTMLElement | null;
      const id = mark?.dataset.companionId;
      if (id === undefined) return;
      setNotesOpen(true);
      setContentsOpen(false);
      setFocusCard({ id, nonce: Date.now() });
    };

    const onClick = (event: MouseEvent) => open(event.target as HTMLElement | null);
    // The marks are focusable and carry a button role, so they have to answer the
    // keyboard too — a click listener alone makes them a control only a pointer
    // can reach. Same shape as SelectionBar's own key handler.
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("mark.pf-cp") === null) return;
      event.preventDefault();
      open(target);
    };

    root.addEventListener("click", onClick);
    root.addEventListener("keydown", onKey);
    return () => {
      root.removeEventListener("click", onClick);
      root.removeEventListener("keydown", onKey);
    };
  }, [passages]);

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

  return (
    // The reading page wears the same shell as every other signed-in page, which
    // it did not until now: there was no footer, no theme control and no way to
    // sign out from inside a chapter, and the way back to the book was a single
    // link under the last one. What the shell does NOT touch is the reading
    // column — its own head, its toolbar, its two panels and the sheet are
    // unchanged and are still the only things between the masthead and the floor.
    //
    // `docked` says the page lays out in the width the Companion leaves it rather
    // than underneath it. It belongs to the shell rather than to `main` because
    // the masthead and the footer have to clear the panel too, and because the
    // drawer is the shell's sibling, not `main`'s child.
    <AppShell
      here="book"
      isAdmin={isAdmin}
      reader
      docked={isCompanion && notesOpen}
      overlays={
        <>
          <div className="reading-progress" aria-hidden="true">
            <span ref={bar} />
          </div>

          {/* Contents on the LEFT, your own marks on the RIGHT — the same drawer
              mirrored, so a reader learns one behaviour and the book's structure
              and their notes on it stay on opposite sides. */}
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

          {/* ONE drawer on this edge, and what it holds depends on who is
              reading. For the account the Scholar Companion belongs to it is the
              Companion — the cards written against this chapter, following the
              passage. For everyone else it is unchanged: their own marks, as it
              has always been. Not two tabs and not two tabs' worth of chrome; the
              Companion account reaches its own marks from the book page's Notes
              tab, and the drawer stays one thing per reader rather than a thing
              with a mode. */}
          <SidePanel
            side="end"
            as="aside"
            open={notesOpen}
            onOpen={() => {
              setNotesOpen(true);
              setContentsOpen(false);
            }}
            onClose={() => setNotesOpen(false)}
            label={isCompanion ? "Companion" : "Your notes"}
            icon={isCompanion ? faBookOpen : faNoteSticky}
            docked={isCompanion}
            count={
              isCompanion ? companion.length : marks.annotations.length + marks.bookmarks.length
            }
          >
            {isCompanion ? (
              <CompanionList
                cards={companion}
                unplaced={unplaced}
                inViewIds={inView}
                focus={focusCard}
              />
            ) : (
              <NotesList
                annotations={marks.annotations}
                bookmarks={marks.bookmarks}
                chapters={contents}
                orphaned={orphaned}
                slug={slug}
                onJump={jump}
                onRemoveAnnotation={removeAnnotation}
                onRemoveBookmark={removeBookmark}
                // `note` already has a full "look up by id, resubmit with the
                // new note" path — the same one a re-highlight or recolour uses.
                onEditAnnotation={(id, text) => note(id, null, text)}
              />
            )}
          </SidePanel>
        </>
      }
    >
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
        {/* The title is the way back to the book.
            It was a plain heading, and the only link to `/book/:slug` in the
            whole reader sat after the LAST chapter — so from chapter six there
            was no door to the page holding this book's podcast, deck and PDF,
            and the home control goes to the library rather than to the book
            (Asif, 2026-08-04: "I am not seeing the tabs, where are they?"). */}
        <h1 className="pf-reader-head__book">
          <Link to={`/book/${slug}`}>{bookTitle}</Link>
        </h1>

        <Elsewhere slug={slug} surfaces={surfaces} marks={markCount} />

        <div className="pf-toolbar-rail">
          <ReaderToolbar
            bookmarked={bookmarked}
            onToggleBookmark={toggleBookmark}
          />
        </div>
      </div>

      <div className="pf-reader-page">
        <article ref={body} className="pf-page">
          {/* An <h2>, and the book above is the <h1> — which is also the true
              nesting: a chapter is part of a work. */}
          <h2 className="pf-chapter-title">{chapter.title}</h2>

          {/* No standfirst under the title. "5 of 10 in this edition · about
              13 minutes" stood here until 2026-08-04: a position the contents
              panel already shows and an estimate the reader is about to find
              out for themselves, printed on the sheet, between the chapter's
              name and its first line. A book does not put that there. */}

          {/* The HTML was rendered at publish time by the same function that
              produces the printed book, so this is not "trusting user input" —
              it is the book. See app/server/catalog.server.ts. Highlights are
              added to the live DOM after this renders; React never reconciles
              inside it.

              `html` is MEMOISED, and that is load-bearing rather than an
              optimisation. React compares props by identity, and
              `dangerouslySetInnerHTML` written inline is a new object every
              render — so React re-set `innerHTML` on each one, wiping every
              painted highlight. Scrolling ticks the progress state, which
              re-renders, which is why a highlight vanished on the first
              scroll and did not come back until a reload: the paint effect's
              own dependencies had not changed, so nothing repainted it. */}
          <div className="reader pf-chapter-body" dangerouslySetInnerHTML={html} />
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
    </AppShell>
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

/**
 * The other ways this book can be taken, from inside one of them.
 *
 * Availability decides it, book by book, exactly as the book page's tabs do: a
 * chip appears only when the thing is IN R2 — episodes with a recording, deck
 * pages, a print edition — and Notes only once this reader has made one. A book
 * that is a reading edition and nothing else therefore shows no chips at all,
 * which is the honest answer rather than four dead controls.
 *
 * They are LINKS, not tabs. The panels live on the book page and this is a
 * different page; each chip lands on the tab it names, which is possible because
 * that tab now has a URL. The PDF is the exception and goes straight to the
 * file, because a download is not a view to switch to.
 *
 * Access is not consulted here, and does not need to be: every one of these
 * lands on a route that runs `requireUnitAccess` on the same slug this chapter
 * already passed. When per-surface permission arrives, this list is where it
 * will show — a chip for something a reader may not take should not be drawn.
 */
function Elsewhere({
  slug,
  surfaces,
  marks,
}: {
  slug: string;
  surfaces: { episodes: number; deckPages: number; pdfKey: string | null };
  /** This reader's own marks in this book — highlights and bookmarks together. */
  marks: number;
}) {
  const chips = [
    surfaces.episodes > 0
      ? { key: "listen", to: `/book/${slug}?tab=listen`, icon: faHeadphones, label: "Podcast", count: surfaces.episodes }
      : null,
    surfaces.deckPages > 0
      ? { key: "slides", to: `/book/${slug}?tab=slides`, icon: faImages, label: "Slides", count: surfaces.deckPages }
      : null,
    surfaces.pdfKey === null
      ? null
      : { key: "pdf", to: `/media/${surfaces.pdfKey}`, icon: faDownload, label: "PDF", count: 0 },
    marks > 0
      ? { key: "notes", to: `/book/${slug}?tab=notes`, icon: faNoteSticky, label: "Notes", count: marks }
      : null,
  ].filter((c): c is NonNullable<typeof c> => c !== null);

  if (chips.length === 0) return null;

  return (
    <nav aria-label="The rest of this book" className="pf-elsewhere">
      {chips.map((chip) => (
        <Link key={chip.key} to={chip.to} className="pf-elsewhere__chip">
          <Icon icon={chip.icon} />
          {chip.label}
          {chip.count > 0 ? <span className="pf-elsewhere__count">{chip.count}</span> : null}
        </Link>
      ))}
    </nav>
  );
}

/**
 * The width at which the Companion stands beside the text instead of over it.
 *
 * The same 64rem the stylesheet uses, and it has to be: above it the panel is
 * docked and the page lays out around it, below it it is a drawer that covers
 * what it opens over. Written as the media query rather than as a number so the
 * two are one sentence in two files.
 */
const DOCKED_AT = "(min-width: 64rem)";

/** Whether two id lists are the same, in the same order. Same purpose as below. */
function sameList(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

/** Whether two id sets hold the same members — used to avoid a needless render. */
function sameSet(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const v of a) if (!b.has(v)) return false;
  return true;
}
