import { useEffect, useRef, useState } from "react";
import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import type { Route } from "./+types/book.$slug.read.$chapter";
import { ReaderSettings } from "~/components/ReaderSettings";
import { ReadingControls } from "~/components/ReadingControls";
import { Icon } from "~/components/Icon";
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
  const bar = useRef<HTMLSpanElement>(null);

  // Progress is measured from the ARTICLE, not the window: the masthead and the
  // footer navigation are not part of the chapter, and counting them makes the
  // bar reach 100% while there is still a page of text left.
  //
  // The bar is driven by a custom property rather than an inline `transform`,
  // the same way `lib/reading.ts` drives the reading controls: JS supplies one
  // scalar, and what that scalar MEANS is a rule in reader.css. No declaration
  // lives in this file.
  useEffect(() => {
    function measure() {
      const element = body.current;
      if (element === null) return;
      const start = element.offsetTop;
      const height = element.offsetHeight - window.innerHeight;
      const scrolled = window.scrollY - start;
      const fraction = height <= 0 ? 1 : Math.min(1, Math.max(0, scrolled / height));
      setProgress(fraction);
      bar.current?.style.setProperty("--l-progress", String(fraction));
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
    <div className="pf-shell">
      <div className="reading-progress" aria-hidden="true">
        <span ref={bar} />
      </div>

      <header className="pf-header--sticky">
        <div className="pf-reader-bar">
          <Link to="/" aria-label="Back to your library" className="pf-logo-link">
            <Logo size={28} wordmark={false} />
          </Link>

          <button
            type="button"
            onClick={() => setContentsOpen((v) => !v)}
            aria-expanded={contentsOpen}
            className="pf-reader-bar__where"
          >
            <span className="pf-reader-bar__book">{bookTitle}</span>
            <span className="pf-reader-bar__sep"> · </span>
            {chapter.title}
          </button>

          <span className="pf-reader-bar__left">
            {left === 0 ? "finished" : `about ${left} min left`}
          </span>

          <ReaderSettings />
        </div>

        {contentsOpen ? (
          <nav aria-label="Table of contents" className="pf-toc">
            <ol className="pf-toc__list">
              {contents.map((entry) => (
                <li key={entry.anchorKey}>
                  <Link
                    to={`/book/${slug}/read/${encodeURIComponent(entry.anchorKey)}`}
                    onClick={() => setContentsOpen(false)}
                    aria-current={entry.anchorKey === chapter.anchorKey ? "page" : undefined}
                    className="pf-row pf-toc__row"
                  >
                    <span className="pf-row__main">{entry.title}</span>
                    <span className="pf-row__meta">{readingMinutes(entry.wordCount)} min</span>
                  </Link>
                </li>
              ))}
            </ol>
          </nav>
        ) : null}
      </header>

      <main id="main" className="pf-reader-page">
        {/* ---- Above the page ----
            The work this chapter belongs to, and the two controls that change
            how it is set. Both sit OUTSIDE the sheet deliberately: the sheet is
            the book, and a control printed on it would be a control printed in
            the book.

            This is the page's <h1> and the chapter heading below is an <h2>,
            which is also the true nesting — a chapter is part of a work, and
            until now every chapter page claimed to be a top-level document
            called "2. A Stranger in the City". */}
        <div className="pf-reader-head">
          <h1 className="pf-reader-head__book">{bookTitle}</h1>
          <ReadingControls />
        </div>

        <article ref={body} className="pf-page">
          <h2 className="pf-chapter-title">{chapter.title}</h2>

          {/* Position in the edition, NOT a chapter number: the introduction is
              the first entry, so this and the book's own "3." in the heading
              differ by one. Saying "chapter" here would contradict the page. */}
          <p className="pf-chapter-meta">
            {chapter.idx} of {contents.length} in this edition · about {total} minutes
          </p>

          {/* The HTML was rendered at publish time by the same function that
              produces the printed book, so this is not "trusting user input" —
              it is the book. See app/server/catalog.server.ts. */}
          <div
            className="reader pf-chapter-body"
            dangerouslySetInnerHTML={{ __html: chapter.html }}
          />
        </article>

        <nav className="pf-turn">
          {previous ? (
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(previous.anchorKey)}`}
              className="pf-card pf-card--link pf-card--padded pf-turn__link"
            >
              <span className="pf-eyebrow">
                <Icon icon={faChevronLeft} />
                Previous
              </span>
              <span className="pf-turn__title">{previous.title}</span>
            </Link>
          ) : (
            <span className="pf-turn__gap" />
          )}

          {next ? (
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(next.anchorKey)}`}
              className="pf-card pf-card--link pf-card--padded pf-turn__link pf-turn__link--end"
            >
              <span className="pf-eyebrow">
                Next
                <Icon icon={faChevronRight} />
              </span>
              <span className="pf-turn__title">{next.title}</span>
            </Link>
          ) : (
            <Link
              to={`/book/${slug}`}
              className="pf-card pf-card--link pf-card--padded pf-turn__link pf-turn__link--end"
            >
              <span className="pf-eyebrow">
                The end
                <Icon icon={faChevronRight} />
              </span>
              <span className="pf-turn__title">Back to {bookTitle}</span>
            </Link>
          )}
        </nav>
      </main>
    </div>
  );
}
