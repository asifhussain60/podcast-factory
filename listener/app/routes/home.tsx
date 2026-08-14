import {
  faList,
  faSliders,
  faTableCells,
  faTableCellsLarge,
} from "@fortawesome/free-solid-svg-icons";
import { useMemo, useState } from "react";
import { Link } from "react-router";

import type { Route } from "./+types/home";
import { AppShell } from "~/components/AppShell";
import { BookCard } from "~/components/BookCard";
import { BookListRow } from "~/components/BookListRow";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { collectionOf } from "~/lib/collection";
import { count, plural } from "~/lib/plural";
import { ALL_STUDY_TRACKS, isStudyTrack, studyTrackLabel, type StudyTrack } from "~/lib/study-track";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";
import {
  libraryCards,
  playableEpisodesForCards,
  type CardPlayableEpisode,
} from "~/server/catalog.server";
import {
  bookmarkTargetsForAll,
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
  const [cards, playable, progress, listening, counts, bookmarks] = await Promise.all([
    libraryCards(env.DB, slugs),
    playableEpisodesForCards(env.DB, slugs),
    progressForAll(env.DB, viewer.email),
    listeningForAll(env.DB, viewer.email),
    markCounts(env.DB, viewer.email),
    bookmarkTargetsForAll(env.DB, viewer.email),
  ]);

  return {
    // The site name is NOT returned here any more. It is one fact about the
    // site, and every page's footer wants it — so it is read once by the
    // `_authed` layout and taken from there by `AppShell`.
    viewer: { name: viewer.name, isAdmin: viewer.isAdmin },
    units: units
      .map((u) => ({
        ...u,
        card: cards.get(u.slug) ?? null,
        progress: progress[u.slug] ?? null,
        listen: listenAction(playable.get(u.slug) ?? [], listening[u.slug] ?? []),
        marks: counts[u.slug] ?? null,
        bookmarks: bookmarks[u.slug] ?? [],
      }))
      // By English title. `localeCompare` rather than `<`, so "Ayyuha" sorts
      // next to "Áyyuha" and case never decides the order.
      .sort((a, b) => a.title.localeCompare(b.title, "en", { sensitivity: "base" })),
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

  const byNumber = new Map(episodes.map((episode) => [episode.number, episode]));
  const saved = progress.find((row) => byNumber.has(row.number) && row.seconds > 10);

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
 * "Books" is defined as NOT sessions rather than as a list of buckets, so a
 * bucket added later lands with the books instead of vanishing from a library
 * that offers no way to reach it. The failure mode of getting this backwards is
 * silent — the card simply is not there under any filter.
 */
const COLLECTIONS = ["all", "books", "sessions"] as const;
type Collection = (typeof COLLECTIONS)[number];

const COLLECTION_LABELS: Record<Collection, string> = {
  all: "Everything",
  books: "Books",
  sessions: "Sessions",
};

const inCollection = (bucket: string, choice: Collection): boolean =>
  choice === "all" || (collectionOf(bucket) === "sessions") === (choice === "sessions");

/**
 * The study-track filter.
 *
 * "all" plus the five real tracks, kept apart from `StudyTrack` itself so a
 * sixth track never has to teach this file about a sentinel value it does not
 * own. Unlike the collection toggle, this is drawn even when every book on
 * the page carries no track yet — the taxonomy is the point of showing it,
 * not how much of the current library happens to be classified under it.
 */
type TrackChoice = "all" | StudyTrack;

const inTrack = (studyTrack: string | null | undefined, choice: TrackChoice): boolean =>
  choice === "all" || studyTrack === choice;

/**
 * Cards, compact tiles, or list — remembered client-side only, since this is
 * a display preference, not data, so it has no business in the loader or the
 * URL. Read the same way `Player.tsx`'s `loadRate()` reads the playback rate:
 * a plain function inside a `try/catch`, used as a lazy `useState`
 * initializer. `localStorage` does not exist during the server render, so
 * the catch is what makes that safe rather than a special case.
 */
const VIEW_MODE_KEY = "pf-library-view";
const VIEW_MODES = ["cards", "compact", "list"] as const;
type ViewMode = (typeof VIEW_MODES)[number];

function loadViewMode(): ViewMode {
  try {
    const stored = localStorage.getItem(VIEW_MODE_KEY);
    return (VIEW_MODES as readonly string[]).includes(stored ?? "") ? (stored as ViewMode) : "cards";
  } catch {
    return "cards";
  }
}

export default function Home({ loaderData }: Route.ComponentProps) {
  const { units, viewer } = loaderData;
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState<Collection>("all");
  const [track, setTrack] = useState<TrackChoice>("all");
  const [viewMode, setViewMode] = useState<ViewMode>(loadViewMode);

  function setMode(mode: ViewMode) {
    setViewMode(mode);
    try {
      localStorage.setItem(VIEW_MODE_KEY, mode);
    } catch {
      // Best-effort. A reader whose storage is full or blocked still gets the
      // toggle for this visit — it just doesn't survive to the next one.
    }
  }

  // The control is drawn only when there is something to choose BETWEEN. A
  // reader with books and no sessions is offered nothing to press, which is
  // right: a filter whose every option shows the same grid teaches the reader
  // that the control does not work.
  const mixed = useMemo(() => {
    const kinds = new Set(units.map((unit) => collectionOf(unit.bucket) ?? "books"));
    return kinds.size > 1;
  }, [units]);

  // Counts against the FULL library, never `shown` — a track's chip reports
  // whether the taxonomy has anything in it at all, not whether today's
  // collection/search narrowing happens to have hidden its only book. Basing
  // it on the filtered list would make a chip flicker disabled while a
  // reader is mid-search, which teaches the wrong lesson about what "0" means.
  const trackCounts = useMemo(() => {
    const counts = new Map<StudyTrack, number>(ALL_STUDY_TRACKS.map((t) => [t, 0]));
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
            [unit.title, unit.card?.titleOriginal ?? "", unit.bucket].some((field) =>
              fold(field).includes(needle),
            ),
        ),
    [units, needle, collection, track],
  );

  return (
    <AppShell here="library" isAdmin={viewer.isAdmin}>
      <section className="pf-masthead">
        <h1 className="pf-title">Podcast Library</h1>
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
            <Link to="/search" className="pf-button pf-button--soft pf-library-find__more">
              <Icon icon={faSliders} />
              Advanced search
            </Link>
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
            <div className="pf-tracks" role="group" aria-labelledby="library-tracks-label">
              <button
                type="button"
                className="pf-track-chip"
                aria-pressed={track === "all"}
                onClick={() => setTrack("all")}
              >
                All tracks
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
                    {studyTrackLabel(choice)}
                    <span className="pf-track-chip__count">{n}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* Gated on the FULL library, same as the search/track controls above —
          a temporary zero-result search should not make the toggle itself
          flicker away. */}
      {units.length === 0 ? null : (
        <div className="pf-library-view-toggle">
          <div role="group" aria-label="Book display" className="pf-stepper pf-stepper--sm">
            <button
              type="button"
              onClick={() => setMode("cards")}
              aria-pressed={viewMode === "cards"}
              aria-label="Card view"
              title="Card view"
              className="pf-stepper__step pf-stepper__step--toggle"
            >
              <Icon icon={faTableCellsLarge} title="Card view" />
            </button>
            <button
              type="button"
              onClick={() => setMode("compact")}
              aria-pressed={viewMode === "compact"}
              aria-label="Compact tile view"
              title="Compact tile view"
              className="pf-stepper__step pf-stepper__step--toggle"
            >
              <Icon icon={faTableCells} title="Compact tile view" />
            </button>
            <button
              type="button"
              onClick={() => setMode("list")}
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
              Nothing matches <strong className="pf-strong">{query.trim()}</strong>.
            </>
          )}
        </EmptyState>
      ) : viewMode === "list" ? (
        /* Same elevated container the chapter/episode rows already sit in
           (`.pf-panel` + `.pf-panel__body`) rather than a bare striped list
           floating on the page background — one surface, reused. */
        <div className="pf-panel pf-library-list">
          <div className="pf-panel__body">
            <ol className="pf-rows pf-rows--striped">
              {shown.map((unit) => (
                <BookListRow
                  key={unit.slug}
                  slug={unit.slug}
                  title={unit.title}
                  card={unit.card}
                  progress={unit.progress}
                />
              ))}
            </ol>
          </div>
        </div>
      ) : viewMode === "compact" ? (
        <ul className="pf-grid pf-grid--spaced pf-grid--compact">
          {shown.map((unit) => (
            <li key={unit.slug}>
              <BookCard
                slug={unit.slug}
                title={unit.title}
                bucket={unit.bucket}
                card={unit.card}
                progress={unit.progress}
                bookmarks={unit.bookmarks}
                listen={unit.listen}
                marks={unit.marks}
                compact
              />
            </li>
          ))}
        </ul>
      ) : (
        <ul className="pf-grid pf-grid--spaced">
          {shown.map((unit) => (
            <li key={unit.slug}>
              <BookCard
                slug={unit.slug}
                title={unit.title}
                bucket={unit.bucket}
                card={unit.card}
                progress={unit.progress}
                bookmarks={unit.bookmarks}
                listen={unit.listen}
                marks={unit.marks}
              />
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  );
}
