import {
  faList,
  faSliders,
  faTableCells,
  faTableCellsLarge,
} from "@fortawesome/free-solid-svg-icons";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { Link, useSearchParams } from "react-router";

import type { Route } from "./+types/home";
import { AppShell } from "~/components/AppShell";
import { BookCard } from "~/components/BookCard";
import { BookListRow, WorkListRow } from "~/components/BookListRow";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { groupIntoWorks, WorkCard } from "~/components/WorkCard";
import {
  collectionOf,
  COLLECTIONS,
  inCollection,
  type Collection,
} from "~/lib/collection";
import { count, plural } from "~/lib/plural";
import {
  collectionSnapshot,
  defaultCollection,
  defaultTrack,
  defaultViewMode,
  setCollection,
  setTrack,
  setViewMode,
  subscribeShelf,
  trackSnapshot,
  viewModeSnapshot,
} from "~/lib/shelf";
import {
  ALL_STUDY_TRACKS,
  inTrack,
  isStudyTrack,
  studyTrackLabel,
  type StudyTrack,
} from "~/lib/study-track";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits, workTitles } from "~/server/access.server";
import {
  libraryCards,
  playableEpisodesForCards,
  type CardPlayableEpisode,
} from "~/server/catalog.server";
import {
  listeningForAll,
  markCounts,
  progressForAll,
  type ListeningProgress,
} from "~/server/marks.server";

/**
 * The library.
 *
 * Behind the invited gate, so `viewer` is always present. The list comes from
 * `visibleUnits`, the ONLY place the entitlement rule is written — this loader
 * does no filtering of its own, and adding any would be the start of the rule
 * existing in two places that can disagree. The counts are fetched for exactly
 * the slugs that survived it, never for the whole catalog.
 *
 * The SORT is a different thing from a filter and is safe here: it reorders what
 * `visibleUnits` returned without adding to or removing from it.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;

  const units = await visibleUnits(env.DB, viewer.email);

  // Progress and mark counts are for THIS viewer and are keyed by slug, so they
  // are joined to what `visibleUnits` returned rather than being queried per
  // book. A slug present in progress but absent from `units` simply never gets
  // read — access is decided in one place and this is not it.
  const slugs = units.map((u) => u.slug);
  const [cards, playable, progress, listening, counts] = await Promise.all([
    libraryCards(env.DB, slugs),
    playableEpisodesForCards(env.DB, slugs),
    progressForAll(env.DB, viewer.email),
    listeningForAll(env.DB, viewer.email),
    markCounts(env.DB, viewer.email),
  ]);

  // Only a work_slug shared by 2+ VISIBLE volumes is a set worth a title
  // lookup — a lone volume never renders as a `WorkCard`, so its parent's
  // title (if any) is never read. Counted straight from `units`, before any
  // per-unit fields are attached, since that count is exactly what
  // `groupIntoWorks` on the client will re-derive from the same field.
  const volumeCounts = new Map<string, number>();
  for (const u of units) {
    if (u.workSlug === null) continue;
    volumeCounts.set(u.workSlug, (volumeCounts.get(u.workSlug) ?? 0) + 1);
  }
  const setWorkSlugs = [...volumeCounts.entries()]
    .filter(([, n]) => n >= 2)
    .map(([workSlug]) => workSlug);
  const workTitleMap = await workTitles(env.DB, setWorkSlugs);

  return {
    // The site name is NOT returned here any more. It is one fact about the
    // site, and every page's footer wants it — so it is read once by the
    // `_authed` layout and taken from there by `AppShell`.
    viewer: { name: viewer.name, isAdmin: viewer.isAdmin },
    // A plain object, not a Map — Maps do not survive the loader/component
    // serialization boundary.
    workTitles: Object.fromEntries(workTitleMap),
    units: units
      .map((u) => ({
        ...u,
        card: cards.get(u.slug) ?? null,
        progress: progress[u.slug] ?? null,
        listen: listenAction(
          playable.get(u.slug) ?? [],
          listening[u.slug] ?? [],
        ),
        marks: counts[u.slug] ?? null,
      }))
      // By English title. `localeCompare` rather than `<`, so "Ayyuha" sorts
      // next to "Áyyuha" and case never decides the order.
      .sort((a, b) =>
        a.title.localeCompare(b.title, "en", { sensitivity: "base" }),
      ),
  };
}

function listenAction(
  episodes: CardPlayableEpisode[],
  progress: ListeningProgress[],
): {
  mode: "resume" | "start";
  episode: CardPlayableEpisode;
  seconds: number | null;
} | null {
  if (episodes.length === 0) return null;

  const byNumber = new Map(
    episodes.map((episode) => [episode.number, episode]),
  );
  const saved = progress.find(
    (row) => byNumber.has(row.number) && row.seconds > 10,
  );

  if (saved !== undefined) {
    return {
      mode: "resume",
      episode: byNumber.get(saved.number)!,
      seconds: saved.seconds,
    };
  }

  return { mode: "start", episode: episodes[0], seconds: null };
}

/**
 * Fold a string down to what a search should actually compare.
 *
 * NFKD then dropping every combining mark does two jobs at once. In Latin it
 * makes "Kitab" find "Kitāb". In Arabic it strips the harakat, so typing the
 * bare consonants finds a vowelled title — and because أ decomposes to ا plus a
 * hamza mark, typing the plain alif finds it too. Without this, searching a
 * fully-vowelled corpus means reproducing the vowels exactly.
 */
function fold(value: string): string {
  return value.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().trim();
}

/**
 * The two collections, and the control that picks between them.
 *
 * `inCollection`, `COLLECTIONS` and `Collection` live in `~/lib/collection`
 * now, alongside `collectionOf` — the same file, because both are the same
 * question ("which collection"), and pulling `inCollection` out to its own
 * module while leaving `collectionOf` behind would split one concept across
 * two files for no reason. Kept importable so the filter matrix is unit-
 * tested directly rather than only through a rendered `Home`.
 */
const COLLECTION_LABELS: Record<Collection, string> = {
  all: "Everything",
  books: "Books",
  sessions: "Sessions",
};

/**
 * The study-track filter.
 *
 * `inTrack` and `TrackChoice` live in `~/lib/study-track`, next to `StudyTrack`
 * itself. Unlike the collection toggle, the panel below is drawn even when every
 * book on the page carries no track yet — the taxonomy is the point of showing
 * it, not how much of the current library happens to be classified under it.
 *
 * What a reader last chose — here, in the collection toggle, and in the view
 * switch — is remembered by `~/lib/shelf`, which is also where the reason those
 * three may not be read during render is written down.
 */
export default function Home({ loaderData }: Route.ComponentProps) {
  const { units, viewer, workTitles } = loaderData;
  // Search stays plain `useState` and is the one deliberate exception: a
  // stale query silently re-applied on a later, unrelated visit would look
  // like the library had shrunk, not like a remembered convenience.
  const [query, setQuery] = useState("");

  /**
   * The three remembered settings, read through `useSyncExternalStore`.
   *
   * The third argument is what the server renders and what the client hydrates
   * against — the defaults, always. React re-reads the real value in the commit
   * straight after hydration, so a reader who chose List sees Cards for one
   * frame and keeps their colour theme, instead of the reverse. `~/lib/shelf`
   * carries the full reason; the short version is that a mismatch here makes
   * React rebuild the document and take `data-theme` with it.
   */
  const viewMode = useSyncExternalStore(
    subscribeShelf,
    viewModeSnapshot,
    defaultViewMode,
  );
  const collection = useSyncExternalStore(
    subscribeShelf,
    collectionSnapshot,
    defaultCollection,
  );
  const track = useSyncExternalStore(
    subscribeShelf,
    trackSnapshot,
    defaultTrack,
  );

  /**
   * `/library?collection=sessions` — the welcome chooser telling this page which
   * collection it was opened for.
   *
   * It goes through `setCollection` like a press of the control itself, so an
   * arrival remembers exactly as a click does: a reader who chose Sessions at
   * the door and then closes the tab finds Sessions on the next visit. That is
   * deliberate, and it means the tile wins over whatever was remembered before.
   *
   * The parameter is then STRIPPED, replacing rather than pushing. Left in
   * place it would re-apply on every reload and on Back — so a reader who
   * arrived on Sessions, switched to Everything, then reloaded would be
   * silently put back on Sessions by a URL they never typed, which reads as the
   * control having failed. Replacing keeps Back pointing at the chooser.
   */
  const [params, setParams] = useSearchParams();
  const requested = params.get("collection");

  useEffect(() => {
    if (requested === null) return;
    if ((COLLECTIONS as readonly string[]).includes(requested)) {
      setCollection(requested as Collection);
    }
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("collection");
        return next;
      },
      { replace: true, preventScrollReset: true },
    );
    // `setParams` is re-made every render; including it would re-run this on
    // every render instead of on the arrival it is for.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requested]);

  // The control is drawn only when there is something to choose BETWEEN. A
  // reader with books and no sessions is offered nothing to press, which is
  // right: a filter whose every option shows the same grid teaches the reader
  // that the control does not work.
  const mixed = useMemo(() => {
    const kinds = new Set(
      units.map((unit) => collectionOf(unit.bucket) ?? "books"),
    );
    return kinds.size > 1;
  }, [units]);

  // Counts against the FULL library, never `shown` — a track's chip reports
  // whether the taxonomy has anything in it at all, not whether today's
  // collection/search narrowing happens to have hidden its only book. Basing
  // it on the filtered list would make a chip flicker disabled while a
  // reader is mid-search, which teaches the wrong lesson about what "0" means.
  const trackCounts = useMemo(() => {
    const counts = new Map<StudyTrack, number>(
      ALL_STUDY_TRACKS.map((t) => [t, 0]),
    );
    for (const unit of units) {
      const track = unit.card?.studyTrack ?? null;
      if (isStudyTrack(track)) counts.set(track, (counts.get(track) ?? 0) + 1);
    }
    return counts;
  }, [units]);

  const needle = fold(query);
  const shown = useMemo(
    () =>
      units
        .filter((unit) => inCollection(unit.bucket, collection))
        .filter((unit) => inTrack(unit.card?.studyTrack, track))
        .filter(
          (unit) =>
            needle === "" ||
            // Title, Arabic title and bucket: the three things actually printed
            // on a card, so nothing matches for a reason the reader cannot see.
            [unit.title, unit.card?.titleOriginal ?? "", unit.bucket].some(
              (field) => fold(field).includes(needle),
            ),
        ),
    [units, needle, collection, track],
  );

  /**
   * The two groups the shelf draws when it is showing everything, or `null`
   * when it should stay one grid.
   *
   * `null` in the two cases where a heading would be wrong rather than merely
   * unnecessary: narrowed to one collection, where the grid IS that collection
   * and a title over it only repeats the button just pressed; and where the
   * search or track filter has left one kind with nothing, where the second
   * heading would title an empty grid.
   *
   * Split from `shown`, so it inherits every filter already applied rather than
   * re-deriving them — and by the same `collectionOf` the cards paint from, so
   * a card can never land under the other group's heading.
   */
  const split = useMemo(() => {
    if (collection !== "all") return null;
    const sessions = shown.filter(
      (unit) => collectionOf(unit.bucket) === "sessions",
    );
    const books = shown.filter(
      (unit) => collectionOf(unit.bucket) !== "sessions",
    );
    if (books.length === 0 || sessions.length === 0) return null;
    return [
      {
        key: "books" as const,
        label: COLLECTION_LABELS.books,
        noun: "title",
        nounPlural: "titles",
        units: books,
      },
      {
        key: "sessions" as const,
        label: COLLECTION_LABELS.sessions,
        noun: "series",
        nounPlural: "series",
        units: sessions,
      },
    ];
  }, [shown, collection]);

  /**
   * One group's worth of cards, in whichever view the reader has chosen.
   *
   * Lifted out of the JSX unchanged so the shelf can draw the same three views
   * twice — once for the books and once for the sessions — without a second
   * copy of any of them going out of step with the first.
   */
  function renderUnits(list: typeof shown) {
    if (viewMode === "list") {
      /* Same elevated container the chapter/episode rows already sit in
         (`.pf-panel` + `.pf-panel__body`) rather than a bare striped list
         floating on the page background — one surface, reused. */
      return (
        <div className="pf-panel pf-library-list">
          <div className="pf-panel__body">
            <ol className="pf-rows pf-rows--striped">
              {groupIntoWorks(list).map((entry) =>
                entry.kind === "work" ? (
                  <WorkListRow
                    key={entry.workSlug}
                    workSlug={entry.workSlug}
                    title={
                      workTitles[entry.workSlug] ?? entry.volumes[0]!.title
                    }
                    volumes={entry.volumes}
                  />
                ) : (
                  <BookListRow
                    key={entry.unit.slug}
                    slug={entry.unit.slug}
                    title={entry.unit.title}
                    card={entry.unit.card}
                    progress={entry.unit.progress}
                  />
                ),
              )}
            </ol>
          </div>
        </div>
      );
    }

    if (viewMode === "compact") {
      return (
        <ul className="pf-grid pf-grid--spaced pf-grid--compact">
          {list.map((unit) => (
            <li key={unit.slug}>
              <BookCard
                slug={unit.slug}
                title={unit.title}
                bucket={unit.bucket}
                card={unit.card}
                progress={unit.progress}
                listen={unit.listen}
                marks={unit.marks}
                compact
              />
            </li>
          ))}
        </ul>
      );
    }

    // The only view that groups multi-volume works into a stacked set
    // card — compact tiles and the list row above stay one row per
    // volume, exactly as they always have. `groupIntoWorks` only forms a
    // set from 2+ units sharing a `work_slug`; a lone volume (including
    // one made lone by a search/collection/track filter narrowing the list
    // down to it) falls through to the plain `BookCard` branch below,
    // unchanged.
    return (
      <ul className="pf-grid pf-grid--spaced">
        {groupIntoWorks(list).map((entry) =>
          entry.kind === "work" ? (
            <li key={entry.workSlug}>
              <WorkCard
                workSlug={entry.workSlug}
                title={workTitles[entry.workSlug] ?? entry.volumes[0]!.title}
                volumes={entry.volumes}
              />
            </li>
          ) : (
            <li key={entry.unit.slug}>
              <BookCard
                slug={entry.unit.slug}
                title={entry.unit.title}
                bucket={entry.unit.bucket}
                card={entry.unit.card}
                progress={entry.unit.progress}
                listen={entry.unit.listen}
                marks={entry.unit.marks}
              />
            </li>
          ),
        )}
      </ul>
    );
  }

  return (
    <AppShell here="library" isAdmin={viewer.isAdmin}>
      <section className="pf-masthead">
        <h1 className="pf-title">The Shelf</h1>
        <p className="pf-lede">
          {units.length === 0
            ? "Nothing has been shared with you yet. When something is, it appears here."
            : "Every book here can be read, heard, or both — whichever of them has been published."}
        </p>

        {units.length === 0 ? null : (
          /* One row: type, narrow, or go and ask a harder question.
             They were stacked — the box on its own line, the chips on the next
             — which read as three unrelated controls and pushed the first card
             below the fold on a laptop. They are three ways of narrowing ONE
             grid, so they sit on one line and wrap together on a phone. */
          <div className="pf-library-find">
            <SearchBox
              id="library-search"
              label="Search the library"
              placeholder="Search by title"
              action={{ kind: "filter", value: query, onChange: setQuery }}
            />

            {/* The same segmented control the theme picker uses, for the same
                reason it does: three choices, mutually exclusive, and pressing
                one is the whole interaction. `aria-pressed` rather than a
                tablist — nothing here is a tab panel; it is one grid being
                narrowed. */}
            {mixed ? (
              <div
                className="pf-swatches pf-collections"
                role="group"
                aria-label="Show which part of the library"
              >
                {COLLECTIONS.map((choice) => (
                  <button
                    key={choice}
                    type="button"
                    className="pf-swatch"
                    aria-pressed={collection === choice}
                    onClick={() => setCollection(choice)}
                  >
                    {COLLECTION_LABELS[choice]}
                  </button>
                ))}
              </div>
            ) : null}

            {/* A LINK, not a button: it goes to a page, so it must open in a new
                tab on a middle-click and be copyable like any other address. */}
            <Link
              to="/search"
              className="pf-button pf-button--soft pf-library-find__more"
            >
              <Icon icon={faSliders} />
              Advanced search
            </Link>

            {/* Pinned to the row's end rather than given a row of its own below
                the panel — a dedicated row for three buttons left the rest of
                that row's width empty. This one changes how the same result is
                DRAWN, which is a different kind of choice than the search box
                and the collection/track filters beside it (which change WHAT
                shows), so it keeps its own group rather than joining theirs. */}
            <div
              role="group"
              aria-label="Book display"
              className="pf-stepper pf-stepper--sm pf-library-view-toggle"
            >
              <button
                type="button"
                onClick={() => setViewMode("cards")}
                aria-pressed={viewMode === "cards"}
                aria-label="Card view"
                title="Card view"
                className="pf-stepper__step pf-stepper__step--toggle"
              >
                <Icon icon={faTableCellsLarge} title="Card view" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode("compact")}
                aria-pressed={viewMode === "compact"}
                aria-label="Compact tile view"
                title="Compact tile view"
                className="pf-stepper__step pf-stepper__step--toggle"
              >
                <Icon icon={faTableCells} title="Compact tile view" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode("list")}
                aria-pressed={viewMode === "list"}
                aria-label="List view"
                title="List view"
                className="pf-stepper__step pf-stepper__step--toggle"
              >
                <Icon icon={faList} title="List view" />
              </button>
            </div>
          </div>
        )}

        {units.length === 0 ? null : (
          /* Its own bordered panel, not a second loose row under the search
             box — the two are different tools (search by name, browse by
             taxonomy) and read that way now instead of blurring into one
             wall of controls. Independent chips inside it, not a segmented
             control: a sixth track should wrap onto a second line rather
             than force the row to squeeze or overflow. Each chip's colour
             comes from the SAME `--l-ribbon-*` pair its cards paint their
             corner ribbon from, in `.pf-track-chip` — so choosing "Esoteric"
             here and seeing it on a card are the same colour, not two
             decisions that happen to agree today. */
          <div className="pf-tracks-panel">
            <p className="pf-tracks-panel__label" id="library-tracks-label">
              Browse by track
            </p>
            <div
              className="pf-tracks"
              role="group"
              aria-labelledby="library-tracks-label"
            >
              <button
                type="button"
                className="pf-track-chip"
                aria-pressed={track === "all"}
                onClick={() => setTrack("all")}
              >
                <span className="pf-track-chip__label">All tracks</span>
                <span className="pf-track-chip__count">{units.length}</span>
              </button>
              {ALL_STUDY_TRACKS.map((choice) => {
                const n = trackCounts.get(choice) ?? 0;
                return (
                  <button
                    key={choice}
                    type="button"
                    className="pf-track-chip"
                    data-track={choice}
                    aria-pressed={track === choice}
                    // Disabled rather than hidden: the empty track still
                    // teaches the reader the taxonomy has five members, even
                    // before anything is filed under it.
                    disabled={n === 0}
                    onClick={() => setTrack(choice)}
                  >
                    <span className="pf-track-chip__label">
                      {studyTrackLabel(choice)}
                    </span>
                    <span className="pf-track-chip__count">{n}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* Announced rather than only drawn: filtering happens with no page
          change, so a screen reader is otherwise never told the grid moved. */}
      <p aria-live="polite" className="sr-only">
        {needle === "" && collection === "all" && track === "all"
          ? count(units.length, "book")
          : `${shown.length} of ${count(units.length, "book")} ${plural(shown.length, "matches", "match")}`}
      </p>

      {units.length === 0 ? null : shown.length === 0 ? (
        <EmptyState>
          {query.trim() === "" ? (
            <>
              Nothing in{" "}
              <strong className="pf-strong">
                {track === "all"
                  ? COLLECTION_LABELS[collection]
                  : collection === "all"
                    ? studyTrackLabel(track)
                    : `${studyTrackLabel(track)} · ${COLLECTION_LABELS[collection]}`}
              </strong>{" "}
              yet.
            </>
          ) : (
            <>
              Nothing matches{" "}
              <strong className="pf-strong">{query.trim()}</strong>.
            </>
          )}
        </EmptyState>
      ) : split === null ? (
        /* No heading — narrowed to one collection, or a filter left one kind
           with nothing, so there is nothing to tell apart. The panel is drawn
           anyway: the cards should sit on the same ground however the shelf is
           filtered, or switching the filter would change the page's furniture
           as well as its contents. */
        <section className="pf-shelf-group">{renderUnits(shown)}</section>
      ) : (
        /* Books and sessions in their own titled groups rather than
           interleaved through one grid (Asif, 2026-08-29). They are read
           differently — one is a book you can also hear, the other is a talk
           with no printed edition — and mixed into a single alphabetical run
           the only thing telling them apart was a card's colour.
 
           Drawn ONLY when "Everything" is showing and both kinds actually
           survive the current search and track filters. Narrowed to one
           collection the grid is already that collection, and a heading over
           the whole page repeating the button just pressed is noise; with one
           kind filtered away entirely, the second heading would title nothing.
 
           `pf-section__head` is the book page's own heading row, reused rather
           than reinvented, and `data-collection` on the sessions group is the
           same attribute §3b paints from — so that heading and its count come
           out violet beside the cards they belong to, from the rule that
           already exists. */
        <>
          {split.map((group) => (
            <section
              key={group.key}
              className="pf-shelf-group"
              data-collection={
                group.key === "sessions" ? "sessions" : undefined
              }
              aria-labelledby={`shelf-${group.key}`}
            >
              <div className="pf-section__head pf-shelf-group__head">
                <div className="pf-section__naming">
                  <h2 className="pf-section__title" id={`shelf-${group.key}`}>
                    {group.label}
                  </h2>
                  <span className="pf-section__count">
                    {count(group.units.length, group.noun, group.nounPlural)}
                  </span>
                </div>
              </div>
              {renderUnits(group.units)}
            </section>
          ))}
        </>
      )}
    </AppShell>
  );
}
