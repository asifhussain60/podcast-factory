import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import type { Route } from "./+types/book.$slug.read.$chapter";
import { ReaderSettings } from "~/components/ReaderSettings";
import { Logo } from "~/components/brand/Logo";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { unitBySlug } from "~/server/access.server";
import { readingMinutes } from "~/lib/reading";
import { chapterOf, chaptersOf } from "~/server/catalog.server";

/**
 * One chapter of the reading edition.
 *
 * Same gate as the book page, on the same `params.slug`, so there is no second
 * access rule to keep in step. Continuous scroll rather than pagination: this is
 * argued prose that runs for pages at a time, and page breaks in a translation
 * put a seam where the author did not.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const slug = params.slug;
  const key = decodeURIComponent(params.chapter);

  const [unit, chapter, all] = await Promise.all([
    unitBySlug(env.DB, slug),
    chapterOf(env.DB, slug, key),
    chaptersOf(env.DB, slug),
  ]);

  // A chapter key that is not in this book is a 404 exactly like a slug that is
  // not in the library — same shape, so neither reveals what exists.
  if (unit === null || chapter === null) notFound();

  const here = all.findIndex((c) => c.anchorKey === chapter.anchorKey);

  return {
    bookTitle: unit.title,
    slug,
    chapter,
    contents: all,
    previous: here > 0 ? all[here - 1] : null,
    next: here >= 0 && here < all.length - 1 ? all[here + 1] : null,
  };
}

export default function ReadChapter({ loaderData }: Route.ComponentProps) {
  const { bookTitle, slug, chapter, contents, previous, next } = loaderData;
  const [progress, setProgress] = useState(0);
  const [contentsOpen, setContentsOpen] = useState(false);
  const body = useRef<HTMLDivElement>(null);

  // Progress is measured from the ARTICLE, not the window: the masthead and the
  // footer navigation are not part of the chapter, and counting them makes the
  // bar reach 100% while there is still a page of text left.
  useEffect(() => {
    function measure() {
      const element = body.current;
      if (element === null) return;
      const start = element.offsetTop;
      const height = element.offsetHeight - window.innerHeight;
      const scrolled = window.scrollY - start;
      setProgress(height <= 0 ? 1 : Math.min(1, Math.max(0, scrolled / height)));
    }

    measure();
    window.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    return () => {
      window.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
    };
  }, [chapter.anchorKey]);

  const total = readingMinutes(chapter.wordCount);
  const left = Math.max(0, Math.round(total * (1 - progress)));

  return (
    <div className="min-h-dvh bg-pf-bg">
      <div className="reading-progress" aria-hidden="true">
        <span style={{ transform: `scaleX(${progress})` }} />
      </div>

      <header className="sticky top-0 z-30 border-b border-pf-rule-soft bg-pf-bg/92 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center gap-4 px-6 py-3">
          <Link to="/" aria-label="Back to your library" className="shrink-0">
            <Logo size={28} />
          </Link>

          <button
            type="button"
            onClick={() => setContentsOpen((v) => !v)}
            aria-expanded={contentsOpen}
            className="min-w-0 flex-1 truncate text-left font-ui text-sm text-pf-muted transition-colors hover:text-pf-ink"
          >
            <span className="text-pf-faint">{bookTitle}</span>
            <span className="text-pf-faint"> · </span>
            {chapter.title}
          </button>

          <span className="hidden shrink-0 font-ui text-xs text-pf-faint sm:block">
            {left === 0 ? "finished" : `about ${left} min left`}
          </span>

          <ReaderSettings />
        </div>

        {contentsOpen ? (
          <nav
            aria-label="Table of contents"
            className="max-h-[60dvh] overflow-y-auto border-t border-pf-rule-soft bg-pf-surface"
          >
            <ol className="mx-auto max-w-3xl px-6 py-2">
              {contents.map((entry) => {
                const current = entry.anchorKey === chapter.anchorKey;
                return (
                  <li key={entry.anchorKey}>
                    <Link
                      to={`/book/${slug}/read/${encodeURIComponent(entry.anchorKey)}`}
                      onClick={() => setContentsOpen(false)}
                      aria-current={current ? "page" : undefined}
                      className={[
                        "flex items-baseline gap-3 py-2 no-underline",
                        current ? "text-pf-accent" : "text-pf-muted hover:text-pf-ink",
                      ].join(" ")}
                    >
                      <span className="flex-1 font-prose">{entry.title}</span>
                      <span className="shrink-0 font-ui text-xs text-pf-faint">
                        {readingMinutes(entry.wordCount)} min
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ol>
          </nav>
        ) : null}
      </header>

      <main id="main" className="mx-auto max-w-3xl px-6 pb-32">
        <article ref={body}>
          <h1 className="mt-14 max-w-[var(--l-reading-measure)] text-balance font-prose text-3xl leading-[1.15] text-pf-ink sm:text-4xl">
            {chapter.title}
          </h1>

          {/* Position in the edition, NOT a chapter number: the introduction is
              the first entry, so this and the book's own "3." in the heading
              differ by one. Saying "chapter" here would contradict the page. */}
          <p className="mt-3 font-ui text-sm text-pf-faint">
            {chapter.idx} of {contents.length} in this edition · about {total} minutes
          </p>

          {/* The HTML was rendered at publish time by the same function that
              produces the printed book, so this is not "trusting user input" —
              it is the book. See app/server/catalog.server.ts. */}
          <div
            className="reader mt-10"
            dangerouslySetInnerHTML={{ __html: chapter.html }}
          />
        </article>

        <nav className="mt-20 flex gap-4 border-t border-pf-rule pt-8">
          {previous ? (
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(previous.anchorKey)}`}
              className="flex-1 rounded-lg border border-pf-rule bg-pf-surface p-4 no-underline transition-colors hover:border-pf-accent"
            >
              <span className="font-ui text-xs uppercase tracking-widest text-pf-faint">
                Previous
              </span>
              <span className="mt-1 block font-prose text-pf-ink">{previous.title}</span>
            </Link>
          ) : (
            <span className="flex-1" />
          )}

          {next ? (
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(next.anchorKey)}`}
              className="flex-1 rounded-lg border border-pf-rule bg-pf-surface p-4 text-right no-underline transition-colors hover:border-pf-accent"
            >
              <span className="font-ui text-xs uppercase tracking-widest text-pf-faint">Next</span>
              <span className="mt-1 block font-prose text-pf-ink">{next.title}</span>
            </Link>
          ) : (
            <Link
              to={`/book/${slug}`}
              className="flex-1 rounded-lg border border-pf-rule bg-pf-surface p-4 text-right no-underline transition-colors hover:border-pf-accent"
            >
              <span className="font-ui text-xs uppercase tracking-widest text-pf-faint">
                The end
              </span>
              <span className="mt-1 block font-prose text-pf-ink">Back to {bookTitle}</span>
            </Link>
          )}
        </nav>
      </main>
    </div>
  );
}
