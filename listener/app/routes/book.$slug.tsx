import {
  faAngleRight,
  faBookOpen,
  faCircleInfo,
  faCircleMinus,
  faClock,
  faDownload,
  faFileLines,
  faHeadphones,
  faImages,
  faLayerGroup,
  faNoteSticky,
  faPause,
  faPlay,
  faTag,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import {
  Link,
  useFetcher,
  useSearchParams,
  type ShouldRevalidateFunctionArgs,
} from "react-router";

import type { Route } from "./+types/book.$slug";
import { AppShell } from "~/components/AppShell";
import { collectionOf } from "~/lib/collection";
import { DeckShelf } from "~/components/DeckViewer";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { clock, usePlayer } from "~/components/player/Player";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { session } from "~/middleware/session";
import { NotesList } from "~/components/reader/NotesList";
import { unitBySlug } from "~/server/access.server";
import { marksFor } from "~/server/marks.server";
import { describeContents } from "~/lib/facts";
import { count, plural } from "~/lib/plural";
import { readingMinutes } from "~/lib/reading";
import {
  chaptersOf,
  deckPagesOf,
  detailOf,
  sessionsOf,
  type Session,
} from "~/server/catalog.server";

/**
 * Layer 4. The gate is here rather than on a shared parent so it can read
 * `params.slug` directly instead of re-deriving it from the URL.
 *
 * Because it is MIDDLEWARE, the `_routes` single-fetch filter cannot skip it:
 * `filterMatchesToLoad` (single-fetch.js:79-84) selects which LOADERS run, and
 * middleware wraps the whole call. A gate written as a parent loader would fall
 * to `GET /book/x.data?_routes=routes/book.$slug`.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const slug = params.slug;

  const unit = await unitBySlug(env.DB, slug);

  // Unreachable in practice — the middleware already proved it is readable —
  // but the loader must not assume that, or a future change to the gate turns
  // into a null dereference here.
  if (unit === null) notFound();

  const viewer = context.get(session).viewer!;

  const [detail, chapters, sessions, deck, marks] = await Promise.all([
    detailOf(env.DB, slug),
    chaptersOf(env.DB, slug),
    sessionsOf(env.DB, slug),
    deckPagesOf(env.DB, slug),
    // Loaded here, unlike the reader, which fetches its own client-side: this
    // page has no cached copy to paint from and the Notes tab needs the whole
    // book's marks before it can render anything at all.
    marksFor(env.DB, viewer.email, slug),
  ]);

  return {
    unit,
    detail,
    chapters,
    sessions,
    marks,
    // Every page across every deck, so the "exists but not uploaded" panel can
    // say how big the deck is even when none of it can be shown.
    deckPages: deck.reduce((n, d) => n + d.pages.length, 0),
    // The decks whose pages are actually in R2, so the Slides tab can show them
    // rather than link out. A page on disk but not uploaded is deliberately
    // absent: it would render as a broken image.
    decks: deck
      .map((d) => ({
        id: d.id,
        title: d.title,
        pages: d.pages.filter((p) => p.available).map((p) => p.key),
      }))
      .filter((d) => d.pages.length > 0),
    isAdmin: viewer.isAdmin,
  };
}

/**
 * Switching a tab must not re-fetch the book.
 *
 * The open tab lives in `?tab=` so it can be linked to, and a search-param
 * change is a navigation, which by default re-runs every loader on the match —
 * six queries to answer a question none of them were asked. Nothing this loader
 * returns depends on `tab`, so that navigation alone is declared uninteresting.
 *
 * Deliberately NARROW: only when the pathname is identical and the two searches
 * agree on everything else. Any other change revalidates as it always did, and
 * this is a display concern in any case — the gate is middleware and runs on
 * every request regardless of what this returns.
 */
export function shouldRevalidate({
  currentUrl,
  nextUrl,
  formMethod,
  defaultShouldRevalidate,
}: ShouldRevalidateFunctionArgs) {
  /* A SUBMISSION always revalidates.
     This is checked first and it is the whole reason the function has a bug
     history: deleting a bookmark from the Notes tab posts to the marks endpoint
     with a fetcher, and a fetcher does not change the URL — so the comparison
     below found "nothing changed" and cancelled the refresh. The row really was
     deleted; the page simply never asked again, which reads exactly like a
     delete button that does not work. Only a plain GET navigation is ever
     eligible to be skipped here. */
  if (formMethod !== undefined && formMethod !== "GET") return defaultShouldRevalidate;

  if (currentUrl.pathname !== nextUrl.pathname) return defaultShouldRevalidate;

  const before = new URLSearchParams(currentUrl.search);
  const after = new URLSearchParams(nextUrl.search);
  before.delete("tab");
  after.delete("tab");

  return before.toString() === after.toString() ? false : defaultShouldRevalidate;
}

export default function BookDetail({ loaderData }: Route.ComponentProps) {
  const { unit, detail, chapters, sessions, marks, deckPages, decks, isAdmin } = loaderData;
  const fetcher = useFetcher();

  const totalWords = chapters.reduce((n, c) => n + c.wordCount, 0);
  const episodes = sessions.flatMap((s) => s.episodes);
  const withAudio = episodes.filter((e) => e.hasAudio).length;

  // What this book HAS decides the shape of the page. A book with no podcast
  // gets no Listen tab at all rather than an empty one — a tab reading "no
  // episodes" is a fault report where its absence is simply a fact. "Real" for
  // the podcast means at least one episode you can actually play, and for the
  // deck at least one page actually in R2.
  const canRead = chapters.length > 0;
  const canListen = withAudio > 0;
  const canWatch = decks.length > 0;

  // How many marks sit in each chapter, so a row can say so. A Map rather than a
  // filter per row: nine chapters against a few hundred marks is a few hundred
  // scans, and this list grows on both axes.
  const markedChapters = new Map<string, number>();
  for (const m of [...marks.annotations, ...marks.bookmarks]) {
    markedChapters.set(m.anchorKey, (markedChapters.get(m.anchorKey) ?? 0) + 1);
  }

  // The same, for the podcast. The episode list said nothing about what was kept
  // in each episode, so the only way to find out whether you had marked anything
  // in episode four was to play it and open the panel (Asif, 2026-08-06).
  const markedEpisodes = new Map<number, number>();
  for (const n of marks.episodeNotes) {
    markedEpisodes.set(n.number, (markedEpisodes.get(n.number) ?? 0) + 1);
  }

  /* ---- Where you left off ----
     Computed HERE rather than inside the reading edition, because it is shown
     ABOVE the panel now (Asif, 2026-08-04). Inside, sandwiched between the
     chapter count and the first chapter row, it read as another row of the list
     — the thing it exists not to be. Out on the page it is the first thing
     under the title, which is what "continue" should be for a book you are
     part-way through.

     Offered only when there IS somewhere to go back to, and not when that place
     is simply the first chapter — "continue from the beginning" is a second
     Start button wearing a different word. Null too when the chapter no longer
     exists, which a re-compose can do by renaming one. */
  const startedIn =
    marks.progress === null
      ? undefined
      : chapters.find((c) => c.anchorKey === marks.progress!.anchorKey);
  const resume =
    startedIn === undefined || marks.progress === null
      ? null
      : chapters[0]?.anchorKey === startedIn.anchorKey && marks.progress.fraction < 0.05
        ? null
        : {
            anchorKey: startedIn.anchorKey,
            title: startedIn.title,
            fraction: marks.progress.fraction,
          };

  // Offered ONLY when the file is actually in R2. The row exists as soon as the
  // PDF is on the author's disk, and linking to that would promise a download
  // that 404s.
  //
  // `--soft`, not `--primary`. A solid accent slab at the head of the chapter
  // list was the loudest thing on a page whose subject is the chapter list —
  // it read as the page's main action when it is an alternative format of what
  // is already right underneath it. The subtle fill keeps it findable in the
  // accent colour without competing with the nine rows it sits above.
  const printEdition =
    detail?.pdfKey && detail.pdfAvailable ? (
      <a href={`/media/${detail.pdfKey}`} className="pf-button pf-button--soft">
        <Icon icon={faDownload} />
        Download PDF
        <span className="pf-button__meta">{megabytes(detail.pdfBytes)}</span>
      </a>
    ) : null;

  return (
    <AppShell here="book" isAdmin={isAdmin} collection={collectionOf(unit.bucket)}>
      {/* ---- Identity ----
          The same two-part identity the library card carries, opened out: the
          English name, the work's own Arabic beneath it, both held in one
          rectangular plate (Asif, 2026-08-05, replacing the circular seal that
          preceded it). One wrapper, so every book's page gets it from this
          template rather than one book at a time. */}
      <header className="pf-masthead pf-masthead--tight pf-masthead--centred">
        <p className="pf-eyebrow">
          <Icon icon={faTag} />
          {unit.bucket}
          {detail?.editionNote ? ` · ${detail.editionNote.replace(/_/g, " ")}` : null}
        </p>

        {/* No per-book type size (Asif, 2026-08-05): a length-based step-down
            made a short title larger than a long one, so the same library read
            at three different sizes as you moved between books. One size for
            every book; the plate takes the width each title needs instead. */}
        <div className="pf-title-plate">
          {/* English first, Arabic under it (Asif, 2026-08-05): the name the
              reader came looking for leads, and the original sits beneath it
              as the work's own name. The order is the DOM's, not a flex
              `order` — a heading that reads second in the source and first on
              screen is a different page to a screen reader than to the eye. */}
          <h1 className="pf-title pf-title--sm">{unit.title}</h1>

          {detail?.titleArabic ? (
            <p lang="ar" dir="rtl" className="pf-book-title-ar">
              {detail.titleArabic}
            </p>
          ) : null}
        </div>

        {/* ---- The description ----
            In a panel of its own, running the page's full width. It used to
            sit as loose prose directly under the title, in the muted ink and
            at the reading column's 68ch — which on a wide page put a short,
            important paragraph in a narrow strip with nothing beside it, so it
            read as a caption rather than as the thing that tells you what this
            book IS. On white, with a header naming it, it is the first block
            the eye lands on after the title.

            The HTML is rendered at publish time, not here — italics, inline
            Arabic and the folded transliteration all come from the same
            renderer as the chapters, so the blurb reads exactly as the book
            does. */}
        {detail?.blurbHtml ? (
          <section className="pf-panel" aria-labelledby="about-this-book">
            <div className="pf-panel__head">
              <Icon icon={faCircleInfo} />
              <h2 id="about-this-book" className="pf-panel__title">
                About this book
              </h2>
            </div>
            <div className="pf-panel__body">
              <div
                className="reader pf-blurb"
                dangerouslySetInnerHTML={{ __html: detail.blurbHtml }}
              />
            </div>
          </section>
        ) : null}

        {/* ---- What this book actually has ----
            One pill per fact, and only for facts that are true. Most books in
            this library are missing most things, and a greyed-out icon reads
            as a fault where a named pill reads as a fact. */}
        <ul className="pf-pills">
          {describeContents({
            chapters: chapters.length,
            words: totalWords,
            episodes: episodes.length,
            withAudio,
            pdf: Boolean(detail?.pdfKey),
            pdfAvailable: Boolean(detail?.pdfAvailable),
            deckPages,
            deckAvailable: canWatch,
          }).map((fact) => (
            <li key={fact.label} className="pf-pill pf-pill--outline">
              <Icon icon={fact.icon} />
              {fact.label}
            </li>
          ))}
        </ul>

        {/* The print edition normally rides at the head of the Read panel,
            beside the chapters it is another format of. A book with a PDF and
            no chapters has no such panel, and the button falls back to here
            rather than disappearing. */}
        {!canRead && printEdition ? (
          <p className="pf-masthead__action">{printEdition}</p>
        ) : null}
      </header>

      {/* ---- What there is of this book ----
          One tab per way of taking it, and Read is the one you land on.

          Read and Listen used to sit side by side in two columns, with the
          deck as a third block below them. That put nine chapters next to
          twenty episodes, and the two lists — different lengths, different row
          shapes, drawn along different lines from the same book — competed the
          whole way down the page: whichever one you were reading, the other
          was moving in the corner of your eye. Tabs say the true thing about
          them, which is that they are three ways to take one book and you are
          taking one of them right now.

          Only the ways this book actually offers get a tab, and a book with
          just one of them gets no tab strip at all — a tablist with a single
          tab is a control that cannot be used. */}
      {resume === null ? null : (
        <Link
          to={`/book/${unit.slug}/read/${encodeURIComponent(resume.anchorKey)}`}
          className="pf-resume"
        >
          <span className="pf-resume__label">
            <Icon icon={faBookOpen} />
            Continue reading
          </span>
          <span className="pf-resume__title">{resume.title}</span>
          <span className="pf-resume__meta">{Math.round(resume.fraction * 100)}% through</span>
        </Link>
      )}

      <Tabs
        panels={[
          canRead
            ? {
                key: "read",
                icon: faBookOpen,
                label: "Read",
                count: chapters.length,
                render: () => (
                  <ReadingEdition
                    slug={unit.slug}
                    chapters={chapters}
                    progress={marks.progress}
                    markedChapters={markedChapters}
                    download={printEdition}
                  />
                ),
              }
            : null,
          canListen
            ? {
                key: "listen",
                icon: faHeadphones,
                label: "Listen",
                count: withAudio,
                render: () => (
                  <Podcast
                    slug={unit.slug}
                    bookTitle={unit.title}
                    collection={collectionOf(unit.bucket)}
                    sessions={sessions}
                    chapters={chapters}
                    markedEpisodes={markedEpisodes}
                    alongsideAnEdition={canRead}
                  />
                ),
              }
            : null,
          canWatch
            ? {
                key: "slides",
                icon: faImages,
                label: "Slides",
                count: decks.reduce((n, d) => n + d.pages.length, 0),
                // The deck ITSELF, not a link to it. It used to be a button
                // reading "Open the deck", which asked the reader to leave the
                // page to find out whether the deck was worth looking at.
                render: () => (
                  <section className="pf-section">
                    <p className="pf-note pf-note--quiet pf-section__intro">
                      {decks.length > 1
                        ? "One deck per chapter — choose below."
                        : "A deck for the whole book."}{" "}
                      <Link to={`/book/${unit.slug}/slides`} className="pf-link pf-link--inline">
                        Open it on its own page
                      </Link>{" "}
                      for the full width.
                    </p>
                    <DeckShelf decks={decks} />
                  </section>
                ),
              }
            : null,
          // A book with a deck on disk that has never been uploaded says so
          // here rather than offering a tab that opens onto broken images.
          !canWatch && deckPages > 0
            ? {
                key: "slides",
                icon: faImages,
                label: "Slides",
                count: deckPages,
                render: () => (
                  <section className="pf-section">
                    <EmptyState>
                      A {deckPages}-page deck exists for this book but has not been
                      uploaded yet.
                    </EmptyState>
                  </section>
                ),
              }
            : null,

          // Only once there is something in it. An empty "Notes" tab on every
          // book would advertise a feature by showing it not working, and the
          // same list is one tap away inside the reader where marks are made.
          marks.annotations.length + marks.bookmarks.length + marks.episodeNotes.length > 0
            ? {
                key: "notes",
                icon: faNoteSticky,
                label: "Notes",
                count:
                  marks.annotations.length + marks.bookmarks.length + marks.episodeNotes.length,
                render: () => (
                  <section className="pf-section">
                    <NotesList
                      annotations={marks.annotations}
                      bookmarks={marks.bookmarks}
                      chapters={chapters}
                      // Both lists, because this page is the one place that
                      // holds everything marked in this book — the reader's
                      // drawer shows chapters and an episode page shows
                      // episodes, each showing what it can act on.
                      episodes={episodes.map((e) => ({ number: e.number, title: e.title }))}
                      episodeNotes={marks.episodeNotes}
                      // Nothing is resolved here: this page never renders the
                      // chapter text, so it cannot know whether a passage
                      // still exists. The reader is where that is discovered,
                      // and claiming it here would be a guess.
                      orphaned={EMPTY_SET}
                      slug={unit.slug}
                      onRemoveAnnotation={(id) =>
                        void fetcher.submit(
                          { intent: "unannotate", id },
                          { method: "post", action: `/book/${unit.slug}/marks` },
                        )
                      }
                      onRemoveBookmark={(id) =>
                        void fetcher.submit(
                          { intent: "unbookmark", id },
                          { method: "post", action: `/book/${unit.slug}/marks` },
                        )
                      }
                      onRemoveEpisodeNote={(id) =>
                        void fetcher.submit(
                          { intent: "un-episode-note", id },
                          { method: "post", action: `/book/${unit.slug}/marks` },
                        )
                      }
                      onEditAnnotation={(id, text) => {
                        const existing = marks.annotations.find((a) => a.id === id);
                        if (existing === undefined) return;
                        void fetcher.submit(
                          {
                            intent: "annotate",
                            id: existing.id,
                            anchorKey: existing.anchorKey,
                            blockIndex: String(existing.blockIndex),
                            startOffset: String(existing.startOffset),
                            endOffset: String(existing.endOffset),
                            quote: existing.quote,
                            prefix: existing.prefix,
                            colour: existing.colour,
                            note: text,
                          },
                          { method: "post", action: `/book/${unit.slug}/marks` },
                        );
                      }}
                      onEditEpisodeNote={(id, text) => {
                        const existing = marks.episodeNotes.find((n) => n.id === id);
                        if (existing === undefined) return;
                        void fetcher.submit(
                          {
                            intent: "episode-note",
                            id: existing.id,
                            number: String(existing.number),
                            seconds: String(existing.seconds),
                            quote: existing.quote ?? "",
                            note: text,
                          },
                          { method: "post", action: `/book/${unit.slug}/marks` },
                        );
                      }}
                    />
                  </section>
                ),
              }
            : null,
        ]}
        empty={<EmptyState>Nothing of this book is readable or listenable yet.</EmptyState>}
      />
    </AppShell>
  );
}

/**
 * Nothing is orphaned here, and this constant says so once.
 *
 * `NotesList` takes the set of marks whose passage could not be found. Only the
 * READER can know that — it is discovered by resolving each anchor against the
 * rendered chapter, and this page never renders one. A frozen empty set is the
 * honest answer, and hoisting it out of the render keeps `NotesList` from
 * repainting on every unrelated state change.
 */
const EMPTY_SET: ReadonlySet<string> = new Set<string>();

/** One way of taking this book: what the tab says, and what it reveals. */
interface Panel {
  key: string;
  icon: IconDefinition;
  label: string;
  count: number;
  render: () => ReactNode;
}

/**
 * Read, Listen and Slides, as one control and one visible panel.
 *
 * Written out rather than pulled from a library because the whole thing is
 * sixty lines and the ARIA tab pattern is a short, fixed contract: exactly one
 * tab is `aria-selected`, only that tab is in the tab order, the arrow keys move
 * between tabs, and each panel names itself from the tab that reveals it.
 *
 * Takes a LIST rather than one prop per panel. Adding the deck as a third tab
 * under the old shape would have meant a third prop, a third count, and a third
 * branch in the render — the point at which "two named things" should have
 * become "a list" three panels ago. Nulls are filtered here so the caller can
 * write one conditional per panel and not think about ordering.
 *
 * The hidden panels stay MOUNTED (`hidden`, not unmounted). Switching to Listen
 * and back must not lose your place in the chapter list or your page in the
 * deck, and — the reason it is load-bearing — the play buttons subscribe to the
 * player, so unmounting the Listen panel while an episode is playing would tear
 * down the button that knows how to pause it.
 */
function Tabs({ panels, empty }: { panels: (Panel | null)[]; empty: ReactNode }) {
  const tabs = panels.filter((p): p is Panel => p !== null);

  /* ---- The open tab is in the URL ---------------------------------------
     It was `useState(0)`, which made every tab unaddressable: a link could only
     ever land on Read and leave the reader to press again. That is what the
     reading page needs — its chips point at the podcast and the deck of the book
     it is inside — and it also makes any tab something you can bookmark or send.

     Keyed by NAME, not index. A book can lose a panel between renders, a deck
     withdrawn or an episode un-uploaded, and an index would then open whatever
     had slid into that position; an unknown name simply falls back to the first
     tab, which is the honest answer to "that view is not here any more".

     `shouldRevalidate` below is what keeps this instant: nothing this loader
     returns depends on `?tab`, so switching must not re-fetch the book.        */
  const [params, setParams] = useSearchParams();
  const strip = useRef<HTMLDivElement>(null);
  const id = useId();

  const named = tabs.findIndex((t) => t.key === params.get("tab"));
  const at = named === -1 ? 0 : named;

  const setOpen = (next: number) =>
    setParams(
      (current) => {
        current.set("tab", tabs[next].key);
        return current;
      },
      // `replace`, so a reader who tried three tabs does not have to press Back
      // three times to leave the page.
      { replace: true, preventScrollReset: true },
    );

  if (tabs.length === 0) return <div className="pf-single">{empty}</div>;

  /**
   * Arrow keys move between tabs and take focus with them, which is what makes
   * the strip ONE stop in the tab order rather than three — the roving
   * `tabIndex` below is the other half of that.
   */
  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const next =
      event.key === "ArrowRight"
        ? (at + 1) % tabs.length
        : event.key === "ArrowLeft"
          ? (at - 1 + tabs.length) % tabs.length
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? tabs.length - 1
              : null;

    if (next === null) return;
    event.preventDefault();
    setOpen(next);
    strip.current
      ?.querySelector<HTMLButtonElement>(`#${CSS.escape(`${id}-${tabs[next].key}`)}`)
      ?.focus();
  }

  return (
    <>
      {/* A book with one way in gets the panel and no strip — a tablist holding
          a single tab is a control that cannot be used. What it does NOT get is
          a different layout: a book that is only readable used to render its
          chapters bare, with a heading of their own, so the two books in this
          library with a podcast looked like a different product from the ones
          without. One template, and the strip is the only thing conditional. */}
      {tabs.length === 1 ? null : (
      <div
        ref={strip}
        role="tablist"
        aria-label="How to take this book"
        className="pf-tabset"
        onKeyDown={onKeyDown}
      >
        {tabs.map((tab, i) => (
          <button
            key={tab.key}
            id={`${id}-${tab.key}`}
            type="button"
            role="tab"
            aria-selected={at === i}
            aria-controls={`${id}-${tab.key}-panel`}
            tabIndex={at === i ? 0 : -1}
            onClick={() => setOpen(i)}
            className="pf-tabset__tab"
          >
            <Icon icon={tab.icon} />
            {tab.label}
            <span className="pf-tabset__count">{tab.count}</span>
          </button>
        ))}
      </div>
      )}

      {tabs.map((tab, i) => (
        <div
          key={tab.key}
          id={`${id}-${tab.key}-panel`}
          role="tabpanel"
          aria-labelledby={`${id}-${tab.key}`}
          hidden={at !== i}
          tabIndex={0}
          className="pf-tabpanel pf-panel"
        >
          <div className="pf-panel__body">{tab.render()}</div>
        </div>
      ))}
    </>
  );
}

/**
 * The chapters-and-episodes problem, stated rather than hidden.
 *
 * The reading edition and the podcast are drawn along DIFFERENT lines from the
 * same source — this book is nine chapters and twenty episodes — and a reader
 * who is not told that concludes the site is broken or that there are two
 * different products. Each list is labelled with its own count, and where both
 * exist the Listen panel says outright that they do not line up.
 *
 * `showHeading` is false when a tab is already carrying the word "Read" three
 * inches above; printing it again as an <h2> is the page saying the same thing
 * twice, and the panel takes its accessible name from the tab regardless. The
 * count is too useful to lose with it, so it stays on its own.
 */
function ReadingEdition({
  slug,
  chapters,
  progress,
  markedChapters,
  download,
}: {
  slug: string;
  chapters: Route.ComponentProps["loaderData"]["chapters"];
  progress: Route.ComponentProps["loaderData"]["marks"]["progress"];
  markedChapters: Map<string, number>;
  /** The print-edition button, when there is one. See `PrintEdition`. */
  download: ReactNode;
}) {
  if (chapters.length === 0) {
    return (
      <section className="pf-section">
        <SectionHeading icon={faBookOpen} title="Read" count="no reading edition yet" />
        <EmptyState>
          The translated edition of this book has not been published here yet.
        </EmptyState>
      </section>
    );
  }

  return (
    <section className="pf-section">
      {/* The print edition sits HERE, at the head of the reading edition, rather
          than under the masthead where it used to. It is the same nine chapters
          in another format, so its place is beside them — under the title it was
          a third call to action competing with the tab strip for the first thing
          you do on the page. */}
      <div className="pf-section__head pf-section__head--wrap">
        <div className="pf-section__naming">
          <span className="pf-section__count">{count(chapters.length, "chapter")}</span>
        </div>
        {download}
      </div>

      <ol className="pf-rows pf-rows--striped pf-section__intro">
        {chapters.map((chapter) => (
          <li key={chapter.anchorKey}>
            {/* No ordinal column. The heading already carries the book's OWN
                number where it has one ("3. The Hours Before Dawn"), and our
                position counts the introduction as the first entry — so the two
                disagreed by one on every line. The book's numbering wins. */}
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(chapter.anchorKey)}`}
              aria-current={progress?.anchorKey === chapter.anchorKey ? "true" : undefined}
              className="pf-row"
            >
              {/* A mark of what the row IS, which every other list on this
                  page now has and this one did not: the deck has its artwork
                  tile, the slides tab its thumbnails. An open book, in the
                  accent, at the head of every chapter. */}
              <Icon icon={faBookOpen} className="pf-row__mark" />
              <span className="pf-row__main">{chapter.title}</span>
              {markedChapters.get(chapter.anchorKey) ? (
                <span className="pf-row__meta pf-row__marks">
                  <Icon icon={faNoteSticky} />
                  {markedChapters.get(chapter.anchorKey)}
                </span>
              ) : null}
              <span className="pf-row__meta">{readingMinutes(chapter.wordCount)} min</span>
              <Icon icon={faAngleRight} className="pf-row__go" />
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * The podcast, grouped into the sessions the author declared.
 *
 * A session heading is rendered only when the session HAS a title — the
 * catalog puts ungrouped episodes in a titleless session numbered 0, so a book
 * that was never grouped renders as one plain list without any special case
 * here. That is why there is no `if (grouped)` branch in this component.
 */
function Podcast({
  slug,
  bookTitle,
  collection,
  sessions,
  chapters,
  markedEpisodes,
  alongsideAnEdition,
}: {
  slug: string;
  bookTitle: string;
  /** Which collection this book belongs to, for the bar it hands the audio to. */
  collection: "sessions" | undefined;
  sessions: Session[];
  chapters: Route.ComponentProps["loaderData"]["chapters"];
  markedEpisodes: Map<number, number>;
  alongsideAnEdition: boolean;
}) {
  const titleOf = new Map(chapters.map((c) => [c.anchorKey, c.title]));
  const episodes = sessions.flatMap((s) => s.episodes);
  const withAudio = episodes.filter((e) => e.hasAudio).length;
  const grouped = sessions.some((s) => s.title !== "");

  // Named `summary`, not `count` — `count` is the shared plural helper now, and a
  // local of that name would shadow it in exactly the place it is needed.
  const summary = [
    grouped ? count(sessions.length, "session") : null,
    withAudio === episodes.length
      ? count(episodes.length, "episode")
      : `${withAudio} of ${count(episodes.length, "episode")}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="pf-section pf-deck">
      <p className="pf-section__count">{summary}</p>

      {/* Only worth saying when both lists are on screen. On a page with no
          reading edition there is nothing for the reader to be confused with.

          WHICH sentence depends on what the recordings ARE, because the two
          collections stand in opposite relations to their text. A podcast book's
          episodes were generated from the chapters and re-segmented along their
          own lines, so a reader who expects chapter 3 to be episode 3 needs
          warning. A lecture is the other way round entirely: the recording came
          first and the chapter is its transcript, so they are one thing filed
          twice. Printing the podcast sentence over a lecture would assert
          something plainly untrue about where the audio came from — which is
          the one thing this page must never do. */}
      {alongsideAnEdition ? (
        <p className="pf-note pf-note--quiet pf-section__intro">
          {collection === "sessions"
            ? "These are the recordings of the sessions themselves. Each chapter is what was said in the recording beside it."
            : "The episodes are drawn along different lines from the chapters — they are two readings of the same book, not two halves of one."}
        </p>
      ) : null}

      {sessions.map((session) => (
        <div key={session.number} className="pf-session">
          {/* The TITLE leads, and the session number follows it as a badge
              (Asif, 2026-08-06). What a sitting is ABOUT is what a reader scans
              for; its ordinal is how they refer to it afterwards. The badge went
              first for most of this component's life, which made every heading
              in the list open with the same word and put the one thing that
              differed second.

              Still two flex items rather than one wrapping line of inline
              spans: as inline text a long title wrapped back to the left margin
              and set its later lines under the badge, so the two read as
              unrelated fragments. */}
          {session.title ? (
            <h3 className="pf-session__head">
              <span className="pf-session__title">{session.title}</span>
              <span className="pf-session__label">
                <Icon icon={faLayerGroup} />
                Session {session.number}
              </span>
            </h3>
          ) : null}

          <ol className="pf-rows pf-deck__list pf-session__list">
            {session.episodes.map((episode) => (
              <li key={episode.number}>
                <div className="pf-row pf-track">
                  {/* ARTWORK, which is what a track list has and a chapter list
                      does not. These recordings have no cover art and never
                      will — there is nothing to photograph — so the tile is
                      generated: a wash of THIS book's accent whose depth steps
                      with the track's position, which gives the column the
                      rhythm a row of identical rectangles was missing.

                      A scalar, not a colour. `--pf-art` is a number the
                      stylesheet mixes with `--l-accent`, so a session's deck
                      comes out violet and a book's blue with no second rule and
                      no palette repeated outside §3.

                      Two digits, tabular: a ragged 1/2/…/10 breaks the column
                      the tiles just made. */}
                  <span
                    className="pf-track__art"
                    aria-hidden="true"
                    style={
                      {
                        "--pf-art": String(
                          0.55 + (0.45 * (episode.number - 1)) / Math.max(1, episodes.length - 1),
                        ),
                      } as React.CSSProperties
                    }
                  >
                    {String(episode.number).padStart(2, "0")}
                  </span>

                  <div className="pf-row__main">
                    {/* Not a link. An episode has no page of its own: what is
                        said in it is the player's Transcript panel, reachable
                        from wherever the listening is happening rather than from
                        a page you would have to know to visit. */}
                    <p>{episode.title}</p>

                    <p className="pf-note pf-note--quiet pf-track__meta">
                      {episode.durationS ? (
                        <span className="pf-track__time">
                          <Icon icon={faClock} />
                          {clock(episode.durationS)}
                        </span>
                      ) : null}

                      {episode.chapters.length > 0 ? (
                        <span>
                          <Icon icon={faBookOpen} />
                          Read along:{" "}
                          {episode.chapters.map((key) => titleOf.get(key) ?? key).join(", ")}
                        </span>
                      ) : null}
                    </p>
                  </div>

                  {/* The row's controls, as ONE group rather than as siblings
                      of the title. With the note count beside it three things
                      competed for a phone's width and the title lost — text ran
                      under the count's pill. Grouped, they drop to a line of
                      their own at that width, which is the same answer the
                      player bar's crowding got: re-flow, never remove. */}
                  <div className="pf-row__actions">
                    <EpisodeNotes
                      slug={slug}
                      number={episode.number}
                      audioKey={episode.audioKey}
                      kept={markedEpisodes.get(episode.number) ?? 0}
                    />

                    {episode.hasAudio && episode.audioKey !== null ? (
                      <PlayButton
                        episode={episode}
                        onPlay={(p) => p.play({
                          slug,
                          bookTitle,
                          number: episode.number,
                          title: episode.title,
                          src: `/media/${episode.audioKey}`,
                          // Handed over WITH the audio, so the player can load
                          // the words alongside it rather than when somebody
                          // asks to see them. Null for an episode with no
                          // transcript, which is what hides the panel's button.
                          transcriptSrc:
                            episode.transcriptKey === null
                              ? null
                              : `/media/${episode.transcriptKey}`,
                          durationS: episode.durationS,
                          // Handed over with the audio for the same reason the
                          // transcript is: the bar outlives this page.
                          collection,
                        })}
                      />
                    ) : (
                      <span className="pf-row__meta pf-row__action">
                        <Icon icon={faCircleMinus} />
                        not recorded
                      </span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </section>
  );
}

/**
 * How much you have kept in this episode, and a way into it.
 *
 * Where it GOES is decided by whether this episode is the one playing, and that
 * is not a flourish — the player's Notes drawer is scoped to what is playing, so
 * on any other row it would open somebody else's notes. So:
 *
 *   playing        the player's own drawer, already on screen, and the panel
 *                  these notes were made in
 *   not playing    the book's Notes tab, anchored at this episode's group
 *
 * The alternative — starting playback so the drawer becomes correct — would turn
 * a request to see your notes into a request to play half an hour of audio,
 * which is not what pressing a count means.
 *
 * Absent at zero rather than rendered as "0": an empty count reads as something
 * to clear rather than something not yet started, the same rule the reader's own
 * tab and the player's own badge follow.
 */
function EpisodeNotes({
  slug,
  number,
  audioKey,
  kept,
}: {
  slug: string;
  number: number;
  audioKey: string | null;
  kept: number;
}) {
  const player = usePlayer();
  if (kept === 0) return null;

  // The count is in the accessible name, not only in the pill: "2" alone is not
  // a control anyone can act on by ear.
  const label = `${count(kept, "note")} in this episode`;
  const isPlaying = audioKey !== null && player.current?.src === `/media/${audioKey}`;

  if (isPlaying) {
    return (
      <button
        type="button"
        onClick={() => player.openPanel("notes")}
        aria-label={label}
        className="pf-row__meta pf-row__marks--button"
      >
        {kept}
      </button>
    );
  }

  return (
    <Link
      to={`/book/${slug}?tab=notes#ep-${number}`}
      aria-label={label}
      className="pf-row__meta pf-row__marks--button"
    >
      {kept}
    </Link>
  );
}

/**
 * Shows a pause glyph when this is the episode currently playing.
 *
 * Two weights, not three: the episode you are on is a solid accent button, and
 * every other episode is the soft tint of the same colour. A list of twenty
 * identical outline buttons gave the eye nothing to find; twenty SOLID ones
 * would have been twenty things all shouting at once.
 *
 * `aria-pressed` still carries the state — the colour is not the only thing
 * saying which one is playing.
 */
function PlayButton({
  episode,
  onPlay,
}: {
  episode: Session["episodes"][number];
  onPlay: (player: ReturnType<typeof usePlayer>) => void;
}) {
  const player = usePlayer();
  const isCurrent = player.current?.src === `/media/${episode.audioKey}`;
  const isPlaying = isCurrent && player.playing;

  /* A circular transport button, not a labelled pill.
     The pill carried the word "Play" and the running time, which put the same
     word down the list as many times as there were episodes and set a clock in
     a control rather than in the row's own facts. Both moved: the duration to
     the meta line under the title, where the rest of what is true about an
     episode already sits, and the word into the accessible name.

     So the visible label is a glyph — and that is only safe because the name
     below is a full sentence naming the episode. A row of identical "Play"
     buttons is what a screen-reader user would otherwise hear. */
  const label = isPlaying
    ? `Pause ${episode.title}`
    : isCurrent
      ? `Resume ${episode.title}`
      : `Play ${episode.title}${episode.durationS ? `, ${clock(episode.durationS)}` : ""}`;

  return (
    <button
      type="button"
      onClick={() => (isCurrent ? player.toggle() : onPlay(player))}
      aria-pressed={isCurrent}
      aria-label={label}
      title={label}
      className={`pf-track__play${isPlaying ? " is-playing" : ""}`}
    >
      <Icon icon={isPlaying ? faPause : faPlay} />
    </button>
  );
}

function SectionHeading({
  icon,
  title,
  count,
}: {
  icon: IconDefinition;
  title: string;
  count: string;
}) {
  return (
    <div className="pf-section__head">
      <h2 className="pf-section__title">
        <Icon icon={icon} />
        {title}
      </h2>
      <span className="pf-section__count">{count}</span>
    </div>
  );
}

function megabytes(bytes: number | null | undefined): string {
  if (!bytes) return "";
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}
