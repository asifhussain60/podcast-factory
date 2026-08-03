import { useEffect, useState } from "react";
import { Link } from "react-router";

import type { Route } from "./+types/book.$slug.slides";
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
    <div className="min-h-dvh bg-pf-bg">
      <SiteHeader here="book" isAdmin={isAdmin} />

      <main id="main" className="mx-auto max-w-5xl px-6 pb-32">
        <div className="flex flex-wrap items-baseline justify-between gap-3 border-t border-pf-rule pt-10">
          <h1 className="font-prose text-3xl text-pf-ink">{title}</h1>
          <Link to={`/book/${slug}`} className="font-ui text-sm text-pf-muted hover:text-pf-ink">
            Back to the book
          </Link>
        </div>

        <figure className="mt-8">
          <img
            src={`/media/${pages[index]}`}
            alt={`Slide ${index + 1} of ${pages.length}`}
            className="w-full rounded-lg border border-pf-rule bg-pf-surface"
          />
          <figcaption className="mt-4 flex items-center justify-between font-ui text-sm text-pf-muted">
            <button
              type="button"
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              disabled={index === 0}
              className="rounded-lg border border-pf-rule px-3 py-1.5 transition-colors hover:border-pf-accent disabled:opacity-40"
            >
              Previous
            </button>
            <span className="tabular-nums">
              {index + 1} / {pages.length}
            </span>
            <button
              type="button"
              onClick={() => setIndex((i) => Math.min(pages.length - 1, i + 1))}
              disabled={index === pages.length - 1}
              className="rounded-lg border border-pf-rule px-3 py-1.5 transition-colors hover:border-pf-accent disabled:opacity-40"
            >
              Next
            </button>
          </figcaption>
        </figure>

        <ol className="mt-8 flex gap-2 overflow-x-auto pb-2">
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
                className={[
                  "block aspect-[4/3] w-24 shrink-0 overflow-hidden rounded border bg-pf-sunken transition-colors",
                  i === index ? "border-pf-accent" : "border-pf-rule hover:border-pf-accent",
                ].join(" ")}
              >
                <img
                  src={`/media/${key}`}
                  alt={`Go to slide ${i + 1}`}
                  loading="lazy"
                  className="size-full object-cover"
                />
              </button>
            </li>
          ))}
        </ol>
      </main>
    </div>
  );
}
