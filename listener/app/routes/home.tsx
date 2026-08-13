import { faSliders } from "@fortawesome/free-solid-svg-icons";
import { useMemo, useState } from "react";
import { Link } from "react-router";

import type { Route } from "./+types/home";
import { AppShell } from "~/components/AppShell";
import { BookCard } from "~/components/BookCard";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { collectionOf } from "~/lib/collection";
import { count, plural } from "~/lib/plural";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";
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

export default function Home({ loaderData }: Route.ComponentProps) {
  const { units, viewer } = loaderData;
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState<Collection>("all");

  // The control is drawn only when there is something to choose BETWEEN. A
  // reader with books and no sessions is offered nothing to press, which is
  // right: a filter whose every option shows the same grid teaches the reader
  // that the control does not work.
  const mixed = useMemo(() => {
    const kinds = new Set(units.map((unit) => collectionOf(unit.bucket) ?? "books"));
    return kinds.size > 1;
  }, [units]);

  const needle = fold(query);
  const shown = useMemo(
    () =>
      units
        .filter((unit) => inCollection(unit.bucket, collection))
        .filter(
          (unit) =>
            needle === "" ||
            // Title, Arabic title and bucket: the three things actually printed
            // on a card, so nothing matches for a reason the reader cannot see.
            [unit.title, unit.card?.titleArabic ?? "", unit.bucket].some((field) =>
              fold(field).includes(needle),
            ),
        ),
    [units, needle, collection],
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
      </section>

      {/* Announced rather than only drawn: filtering happens with no page
          change, so a screen reader is otherwise never told the grid moved. */}
      <p aria-live="polite" className="sr-only">
        {needle === "" && collection === "all"
          ? count(units.length, "book")
          : `${shown.length} of ${count(units.length, "book")} ${plural(shown.length, "matches", "match")}`}
      </p>

      {units.length === 0 ? null : shown.length === 0 ? (
        <EmptyState>
          {query.trim() === "" ? (
            <>
              Nothing in{" "}
              <strong className="pf-strong">{COLLECTION_LABELS[collection]}</strong> yet.
            </>
          ) : (
            <>
              Nothing matches <strong className="pf-strong">{query.trim()}</strong>.
            </>
          )}
        </EmptyState>
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
                marks={unit.marks}
              />
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  );
}
