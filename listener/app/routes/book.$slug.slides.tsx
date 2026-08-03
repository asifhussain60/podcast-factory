import { useEffect, useState } from "react";
import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import type { Route } from "./+types/book.$slug.slides";
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
 * The slide deck, for the one book in the library that has one.
 *
 * A page-image viewer rather than a PDF embed: the deck is already rasterised by
 * the pipeline, and a browser PDF viewer brings its own chrome, its own zoom and
 * its own theme, none of which follow the reader's.
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
  const [index, setIndex] = useState(0);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight") setIndex((i) => Math.min(pages.length - 1, i + 1));
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pages.length]);

  return (
    <div className="pf-shell">
      <SiteHeader here="book" isAdmin={isAdmin} />

      <main id="main" className="pf-container">
        <div className="pf-masthead pf-masthead--tight pf-deck__head">
          <h1 className="pf-title pf-title--sm">{title}</h1>
          <Link to={`/book/${slug}`} className="pf-navlink">
            Back to the book
          </Link>
        </div>

        <figure className="pf-deck">
          <img
            src={`/media/${pages[index]}`}
            alt={`Slide ${index + 1} of ${pages.length}`}
            className="pf-deck__page"
          />
          <figcaption className="pf-deck__controls">
            <button
              type="button"
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              disabled={index === 0}
              className="pf-button pf-button--sm"
            >
              <Icon icon={faChevronLeft} />
              Previous
            </button>
            <span className="pf-deck__count">
              {index + 1} / {pages.length}
            </span>
            <button
              type="button"
              onClick={() => setIndex((i) => Math.min(pages.length - 1, i + 1))}
              disabled={index === pages.length - 1}
              className="pf-button pf-button--sm"
            >
              Next
              <Icon icon={faChevronRight} />
            </button>
          </figcaption>
        </figure>

        <ol className="pf-rail">
          {pages.map((key, i) => (
            <li key={key}>
              {/* The aspect ratio is on the BUTTON, not the image. Lazy-loaded
                  images have no intrinsic size until they arrive, so a rail of
                  fifteen of them rendered as fifteen hairlines that then jumped
                  to full height one by one. Reserving the box keeps the rail
                  still. */}
              <button
                type="button"
                onClick={() => setIndex(i)}
                aria-current={i === index ? "true" : undefined}
                className="pf-rail__thumb"
              >
                <img src={`/media/${key}`} alt={`Go to slide ${i + 1}`} loading="lazy" />
              </button>
            </li>
          ))}
        </ol>
      </main>

      <SiteFooter />
    </div>
  );
}
