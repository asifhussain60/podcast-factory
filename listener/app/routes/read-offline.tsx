import { faChevronLeft, faChevronRight, faList } from "@fortawesome/free-solid-svg-icons";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";

import type { Route } from "./+types/read-offline";
import { AppShell } from "~/components/AppShell";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { readBook, type StoredChapter } from "~/lib/offline";
import { session } from "~/middleware/session";

/**
 * A downloaded chapter, read with no network.
 *
 * WHY THIS EXISTS RATHER THAN THE REAL READER WORKING OFFLINE. The reader lives
 * at /book/:slug/read/:chapter, and serving that page with no network would mean
 * the service worker keeping a copy of its document — which for one account
 * carries Scholar Companion cards, in a store no `viewer.isAdmin` check guards.
 * public/sw.js refuses to cache any /book document for exactly that reason, and
 * a test holds it to that. So the offline path is a DIFFERENT page whose
 * document contains nothing about anybody: everything on screen is read from
 * IndexedDB after it loads.
 *
 * WHY ONE ROUTE WITH THE BOOK IN THE QUERY, rather than /read-offline/:slug/:ch.
 * The worker caches documents by PATH. A parameterised path is a different key
 * per chapter, so only the chapters already visited online would open — which is
 * precisely backwards. As a query, every chapter of every downloaded book is
 * served from the one cached shell.
 *
 * WHAT IT IS NOT: the reader. There are no highlights, no notes and no Companion
 * here, and it does not pretend otherwise — it is the prose, the chapter list
 * and the way between them. Reproducing the reader's marks against a copy of the
 * text that cannot reach the server is a bigger thing than reading on a plane,
 * and half of it would be worse than none.
 */

export function meta(): Route.MetaDescriptors {
  return [
    { title: "Reading offline — Podcast Factory" },
    { name: "description", content: "A downloaded chapter, read with no network." },
  ];
}

export function loader({ context }: Route.LoaderArgs) {
  // The masthead's Access link and NOTHING else. This document is the one the
  // worker keeps, so anything the loader returned would be served back to
  // whoever opens the page next — see the module note.
  return { isAdmin: context.get(session).viewer?.isAdmin === true };
}

export default function ReadOffline({ loaderData }: Route.ComponentProps) {
  const [params, setParams] = useSearchParams();
  const slug = params.get("book") ?? "";
  const wanted = params.get("chapter");

  const [chapters, setChapters] = useState<StoredChapter[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [showContents, setShowContents] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void readBook(slug).then((found) => {
      if (cancelled) return;
      setChapters(found);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const here =
    chapters === null
      ? -1
      : wanted === null
        ? 0
        : Math.max(
            0,
            chapters.findIndex((c) => c.anchorKey === wanted),
          );
  const chapter = chapters === null || here < 0 ? null : (chapters[here] ?? null);

  // Scrolled to the top on every chapter change. Without it, moving to the next
  // chapter leaves the reader wherever they were down the previous one.
  useEffect(() => {
    if (chapter !== null) window.scrollTo(0, 0);
  }, [chapter?.anchorKey]);

  const goTo = (key: string) => {
    setParams({ book: slug, chapter: key }, { preventScrollReset: false });
    setShowContents(false);
  };

  return (
    <AppShell here="downloads" isAdmin={loaderData.isAdmin}>
      {loading ? (
        // Deliberately blank rather than a spinner: reading the chapters out of
        // IndexedDB takes a frame or two, and a spinner that flashes for 40ms is
        // noise on the page a listener opened to read.
        <p className="sr-only">Loading</p>
      ) : chapter === null ? (
        <EmptyState>
          {slug === ""
            ? "No book was named."
            : "This book is not on your device. When you next have a signal, open it and press Keep the text."}{" "}
          <Link to="/downloads" className="pf-link">
            See what is downloaded
          </Link>
          .
        </EmptyState>
      ) : (
        <>
          <div className="pf-offline-read__bar">
            <button
              type="button"
              className="pf-button pf-button--soft pf-button--sm"
              onClick={() => setShowContents((open) => !open)}
              aria-expanded={showContents}
            >
              <Icon icon={faList} />
              Chapters
            </button>
            <p className="pf-offline-read__where">
              {here + 1} of {chapters!.length} · reading from this device
            </p>
          </div>

          {showContents ? (
            <nav aria-label="Chapters" className="pf-offline-read__contents">
              <ol>
                {chapters!.map((c, i) => (
                  <li key={c.anchorKey}>
                    <button
                      type="button"
                      onClick={() => goTo(c.anchorKey)}
                      aria-current={i === here ? "true" : undefined}
                      className="pf-offline-read__link"
                    >
                      {c.title}
                    </button>
                  </li>
                ))}
              </ol>
            </nav>
          ) : null}

          <article className="pf-page">
            <h1 className="pf-chapter-title">{chapter.title}</h1>
            {/* The SAME classes the reader's own prose carries, so a chapter
                read offline is set in the same measure, the same face and the
                same Arabic handling. The HTML was rendered at publish time;
                nothing here re-renders it. */}
            <div
              className="reader pf-chapter-body"
              dangerouslySetInnerHTML={{ __html: chapter.html }}
            />
          </article>

          <nav className="pf-offline-read__move" aria-label="Move between chapters">
            {here > 0 ? (
              <button
                type="button"
                className="pf-button pf-button--soft"
                onClick={() => goTo(chapters![here - 1].anchorKey)}
              >
                <Icon icon={faChevronLeft} />
                {chapters![here - 1].title}
              </button>
            ) : (
              <span />
            )}
            {here < chapters!.length - 1 ? (
              <button
                type="button"
                className="pf-button pf-button--soft"
                onClick={() => goTo(chapters![here + 1].anchorKey)}
              >
                {chapters![here + 1].title}
                <Icon icon={faChevronRight} />
              </button>
            ) : (
              <span />
            )}
          </nav>
        </>
      )}
    </AppShell>
  );
}
