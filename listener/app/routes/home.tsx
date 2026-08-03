import type { Route } from "./+types/home";
import { BookCard } from "~/components/BookCard";
import { SiteFooter } from "~/components/SiteFooter";
import { SiteHeader } from "~/components/SiteHeader";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";
import { libraryCards } from "~/server/catalog.server";

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
  const { units, viewer, siteName } = loaderData;

  return (
    <div className="pf-shell">
      <SiteHeader here="library" isAdmin={viewer.isAdmin} />

      <main id="main" className="pf-container">
        <section className="pf-masthead">
          <p className="pf-eyebrow">{siteName}</p>
          <h1 className="pf-title">Podcast Library</h1>
          <p className="pf-lede">
            {units.length === 0
              ? "Nothing has been shared with you yet. When something is, it appears here."
              : "Every book here can be read, heard, or both — whichever of them has been published."}
          </p>
        </section>

        {units.length === 0 ? null : (
          <ul className="pf-grid pf-grid--spaced">
            {units.map((unit) => (
              <li key={unit.slug}>
                <BookCard
                  slug={unit.slug}
                  title={unit.title}
                  bucket={unit.bucket}
                  card={unit.card}
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
