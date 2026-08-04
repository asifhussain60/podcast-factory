import { useMemo, useState } from "react";

import type { Route } from "./+types/home";
import { AppShell } from "~/components/AppShell";
import { BookCard } from "~/components/BookCard";
import { EmptyState } from "~/components/EmptyState";
import { SearchBox } from "~/components/SearchBox";
import { count, plural } from "~/lib/plural";
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
    // The site name is NOT returned here any more. It is one fact about the
    // site, and every page's footer wants it — so it is read once by the
    // `_authed` layout and taken from there by `AppShell`.
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
  const { units, viewer } = loaderData;
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
    <AppShell here="library" isAdmin={viewer.isAdmin}>
      <section className="pf-masthead">
        <h1 className="pf-title">Podcast Library</h1>
        <p className="pf-lede">
          {units.length === 0
            ? "Nothing has been shared with you yet. When something is, it appears here."
            : "Every book here can be read, heard, or both — whichever of them has been published."}
        </p>

        {units.length === 0 ? null : (
          <SearchBox
            id="library-search"
            label="Search the library"
            placeholder="Search by title"
            action={{ kind: "filter", value: query, onChange: setQuery }}
          />
        )}
      </section>

      {/* Announced rather than only drawn: filtering happens with no page
          change, so a screen reader is otherwise never told the grid moved. */}
      <p aria-live="polite" className="sr-only">
        {needle === ""
          ? count(units.length, "book")
          : `${shown.length} of ${count(units.length, "book")} ${plural(shown.length, "matches", "match")}`}
      </p>

      {units.length === 0 ? null : shown.length === 0 ? (
        <EmptyState>
          Nothing matches <strong className="pf-strong">{query.trim()}</strong>.
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
