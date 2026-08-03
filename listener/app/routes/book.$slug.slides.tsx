import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import type { Route } from "./+types/book.$slug.slides";
import { DeckViewer } from "~/components/DeckViewer";
import { Icon } from "~/components/Icon";
import { SiteFooter } from "~/components/SiteFooter";
import { SiteHeader } from "~/components/SiteHeader";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { session } from "~/middleware/session";
import { unitBySlug } from "~/server/access.server";
import { deckPagesOf } from "~/server/catalog.server";

/**
 * The slide deck on a page of its own.
 *
 * The book page's Slides tab shows the same deck inline, through the same
 * `DeckViewer`; this route is what a link to a deck resolves to, and what gives
 * the deck the whole window when the tabs above it are in the way.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);

  const [unit, pages] = await Promise.all([
    unitBySlug(env.DB, params.slug),
    deckPagesOf(env.DB, params.slug),
  ]);

  const available = pages.filter((p) => p.available);

  // No deck, or one that exists on disk but has not been uploaded — both are a
  // 404 rather than an empty viewer, because the book page never links here in
  // either case and a reachable empty page reads as a fault.
  if (unit === null || available.length === 0) notFound();

  return {
    slug: params.slug,
    title: unit.title,
    pages: available.map((p) => p.key),
    isAdmin: context.get(session).viewer!.isAdmin,
  };
}

export default function Slides({ loaderData }: Route.ComponentProps) {
  const { slug, title, pages, isAdmin } = loaderData;

  return (
    <div className="pf-shell">
      <SiteHeader here="book" isAdmin={isAdmin} />

      <main id="main" className="pf-container">
        <div className="pf-masthead pf-masthead--tight pf-deck__head">
          <h1 className="pf-title pf-title--sm">{title}</h1>
          <Link to={`/book/${slug}`} className="pf-navlink">
            <Icon icon={faArrowLeft} />
            Back to the book
          </Link>
        </div>

        <DeckViewer pages={pages} arrowKeys />
      </main>

      <SiteFooter />
    </div>
  );
}
