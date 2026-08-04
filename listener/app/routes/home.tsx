import { faMagnifyingGlass, faXmark } from "@fortawesome/free-solid-svg-icons";
import { useMemo, useState } from "react";

import type { Route } from "./+types/home";
import { BookCard } from "~/components/BookCard";
import { Icon } from "~/components/Icon";
import { SiteFooter } from "~/components/SiteFooter";
import { SiteHeader } from "~/components/SiteHeader";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";
import { libraryCards } from "~/server/catalog.server";
import { markCounts, progressForAll } from "~/server/marks.server";

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
  const [cards, progress, counts] = await Promise.all([
    libraryCards(env.DB, units.map((u) => u.slug)),
    progressForAll(env.DB, viewer.email),
    markCounts(env.DB, viewer.email),
  ]);

  return {
    siteName: env.PUBLIC_SITE_NAME ?? "Podcast Factory",
    viewer: { name: viewer.name, isAdmin: viewer.isAdmin },
    units: units
      .map((u) => ({
        ...u,
        card: cards.get(u.slug) ?? null,
        progress: progress[u.slug] ?? null,
        marks: counts[u.slug] ?? null,
      }))
      // By English title. `localeCompare` rather than `<`, so "Ayyuha" sorts
      // next to "Áyyuha" and case never decides the order.
      .sort((a, b) => a.title.localeCompare(b.title, "en", { sensitivity: "base" })),
  };
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

export default function Home({ loaderData }: Route.ComponentProps) {
  const { units, viewer, siteName } = loaderData;
  const [query, setQuery] = useState("");

  const needle = fold(query);
  const shown = useMemo(
    () =>
      needle === ""
        ? units
        : units.filter((unit) =>
            // Title, Arabic title and bucket: the three things actually printed
            // on a card, so nothing matches for a reason the reader cannot see.
            [unit.title, unit.card?.titleArabic ?? "", unit.bucket].some((field) =>
              fold(field).includes(needle),
            ),
          ),
    [units, needle],
  );

  return (
    <div className="pf-shell">
      <SiteHeader here="library" isAdmin={viewer.isAdmin} />

      <main id="main" className="pf-container">
        <section className="pf-masthead">
          <h1 className="pf-title">Podcast Library</h1>
          <p className="pf-lede">
            {units.length === 0
              ? "Nothing has been shared with you yet. When something is, it appears here."
              : "Every book here can be read, heard, or both — whichever of them has been published."}
          </p>

          {units.length === 0 ? null : (
            <search className="pf-search">
              <Icon icon={faMagnifyingGlass} className="pf-search__icon" />
              <label htmlFor="library-search" className="sr-only">
                Search the library
              </label>
              <input
                id="library-search"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search by title"
                autoComplete="off"
                className="pf-search__input"
              />
              {query === "" ? null : (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  aria-label="Clear the search"
                  className="pf-search__clear"
                >
                  <Icon icon={faXmark} />
                </button>
              )}
            </search>
          )}
        </section>

        {/* Announced rather than only drawn: filtering happens with no page
            change, so a screen reader is otherwise never told the grid moved. */}
        <p aria-live="polite" className="sr-only">
          {needle === ""
            ? `${units.length} books`
            : `${shown.length} of ${units.length} books match`}
        </p>

        {units.length === 0 ? null : shown.length === 0 ? (
          <p className="pf-note pf-empty">
            Nothing matches <strong className="pf-strong">{query.trim()}</strong>.
          </p>
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
      </main>

      <SiteFooter siteName={siteName} />
    </div>
  );
}
