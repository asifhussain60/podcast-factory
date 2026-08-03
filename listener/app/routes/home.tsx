import { Link } from "react-router";

import type { Route } from "./+types/home";
import { SiteHeader } from "~/components/SiteHeader";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";
import { libraryCards, type LibraryCard } from "~/server/catalog.server";

/**
 * The library.
 *
 * Behind the invited gate, so `viewer` is always present. The list comes from
 * `visibleUnits`, the ONLY place the entitlement rule is written — this loader
 * does no filtering of its own, and adding any would be the start of the rule
 * existing in two places that can disagree. The counts are fetched for exactly
 * the slugs that survived it, never for the whole catalog.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;

  const units = await visibleUnits(env.DB, viewer.email);
  const cards = await libraryCards(env.DB, units.map((u) => u.slug));

  return {
    siteName: env.PUBLIC_SITE_NAME ?? "Podcast Factory",
    viewer: { name: viewer.name, isAdmin: viewer.isAdmin },
    units: units.map((u) => ({ ...u, card: cards.get(u.slug) ?? null })),
  };
}

export default function Home({ loaderData }: Route.ComponentProps) {
  const { units, viewer } = loaderData;

  return (
    <div className="min-h-dvh bg-pf-bg">
      <SiteHeader here="library" isAdmin={viewer.isAdmin} />

      <main id="main" className="mx-auto max-w-5xl px-6 pb-32">
        <section className="border-t border-pf-rule pt-14">
          <p className="font-ui text-xs uppercase tracking-[0.18em] text-pf-muted">
            {loaderData.siteName}
          </p>
          <h1 className="mt-4 max-w-3xl text-balance font-prose text-5xl leading-[1.08] text-pf-ink sm:text-6xl">
            Your library
          </h1>
        </section>

        {units.length === 0 ? (
          <p className="mt-12 max-w-xl font-prose text-lg leading-relaxed text-pf-muted">
            Nothing has been shared with you yet. When something is, it appears
            here.
          </p>
        ) : (
          <ul className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {units.map((unit) => (
              <li key={unit.slug}>
                <Link
                  to={`/book/${unit.slug}`}
                  className="flex h-full flex-col rounded-xl border border-pf-rule bg-pf-surface p-6 no-underline transition-colors hover:border-pf-accent"
                  style={{ boxShadow: "var(--l-shadow)" }}
                >
                  <p className="font-ui text-xs uppercase tracking-widest text-pf-faint">
                    {unit.bucket}
                  </p>

                  <h2 className="mt-2 font-prose text-xl leading-snug text-pf-ink">
                    {unit.title}
                  </h2>

                  {/* dir="rtl" is required for shaping and ordering; the
                      alignment is deliberately LEFT so the Arabic sits under the
                      English title rather than drifting to the far edge of a
                      card whose every other line starts at the left. */}
                  {unit.card?.titleArabic ? (
                    <p
                      lang="ar"
                      dir="rtl"
                      className="mt-1 text-left font-arabic text-lg text-pf-muted"
                    >
                      {unit.card.titleArabic}
                    </p>
                  ) : null}

                  <div className="mt-auto pt-5">
                    <Badges card={unit.card} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}

/**
 * What a book actually contains, stated rather than iconified.
 *
 * Most books in this library are missing most things — one has a deck, two have
 * a PDF, one has audio for part of its run. A row of icons with the absent ones
 * greyed out reads as a fault report; naming only what IS there reads as a fact,
 * and a book with a single badge does not look broken.
 */
function Badges({ card }: { card: LibraryCard | null }) {
  if (card === null) {
    return <span className="font-ui text-xs text-pf-faint">Not published yet</span>;
  }

  const badges: string[] = [];
  if (card.chapters > 0) badges.push(`${card.chapters} chapters`);
  if (card.recorded > 0) {
    badges.push(
      card.recorded === card.episodes
        ? `${card.episodes} episodes`
        : `${card.recorded} of ${card.episodes} episodes`,
    );
  } else if (card.episodes > 0) {
    badges.push(`${card.episodes} episodes planned`);
  }
  if (card.hasPdf) badges.push("PDF");
  if (card.deckPages > 0) badges.push("slides");

  if (badges.length === 0) {
    return <span className="font-ui text-xs text-pf-faint">Nothing published yet</span>;
  }

  return (
    <ul className="flex flex-wrap gap-1.5">
      {badges.map((badge) => (
        <li
          key={badge}
          className="rounded-full border border-pf-rule-soft px-2.5 py-1 font-ui text-xs text-pf-muted"
        >
          {badge}
        </li>
      ))}
    </ul>
  );
}
