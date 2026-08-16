import {
  faChevronLeft,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import { useEffect, useState } from "react";

import { Icon } from "~/components/Icon";

/**
 * The slide deck: one page large, the rest as a rail beneath it.
 *
 * A page-image viewer rather than a PDF embed. The deck is already rasterised by
 * the pipeline, and a browser's PDF viewer brings its own chrome, its own zoom
 * and its own theme, none of which follow the reader's.
 *
 * It lives here rather than inside the slides route because the book page's
 * Slides tab shows the deck ITSELF — not a link to it — and two viewers would be
 * two answers to what a deck looks like. The standalone `/book/:slug/slides`
 * page is now this component plus a masthead.
 *
 * `arrowKeys` is off by default. On the standalone page the deck is the only
 * thing on screen and the arrows obviously belong to it; inside a tab panel they
 * do not, because Left and Right are already how you move between the tabs
 * themselves — see the tablist in routes/book.$slug.tsx. Binding both would mean
 * one key press doing two things and the reader unable to predict which.
 */
/** One deck as the shelf needs it: what to call it, and the pages that can be shown. */
export interface ShelfDeck {
  id: string;
  title: string | null;
  pages: string[];
}

/**
 * A book's decks, with a way to choose between them.
 *
 * The chooser is drawn ONLY when there is more than one. A single deck with a
 * control offering to switch to it is a question with one answer, and every book
 * on this site had exactly one until Ayyuha al-Walad arrived with four.
 *
 * The viewer below is one instance, not one per deck: mounting four and hiding
 * three would load four decks' images to show one. Swapping `pages` on the single
 * instance is why `DeckViewer` resets its page index — see the effect there.
 */
export function DeckShelf({
  decks,
  arrowKeys = false,
}: {
  decks: ShelfDeck[];
  arrowKeys?: boolean;
}) {
  const [chosen, setChosen] = useState(0);
  const deck = decks[chosen] ?? decks[0];

  if (deck === undefined) return null;

  return (
    <>
      {decks.length > 1 ? (
        <nav className="pf-deck__choose" aria-label="Slide decks">
          {decks.map((d, i) => (
            <button
              key={d.id}
              type="button"
              onClick={() => setChosen(i)}
              aria-pressed={i === chosen}
              className={`pf-button pf-button--sm${i === chosen ? " pf-button--primary" : " pf-button--soft"}`}
            >
              {d.title ?? d.id}
            </button>
          ))}
        </nav>
      ) : null}

      <DeckViewer pages={deck.pages} arrowKeys={arrowKeys} />
    </>
  );
}

export function DeckViewer({
  pages,
  arrowKeys = false,
}: {
  pages: string[];
  arrowKeys?: boolean;
}) {
  const [index, setIndex] = useState(0);

  /* Back to page one whenever the DECK changes.
     Required now that a book can have several and the chooser swaps `pages` on a
     mounted viewer: standing on page 11 of a twelve-page deck and switching to a
     ten-page one left the index untouched, so it rendered `pages[10]` —
     undefined — as `src="/media/undefined"`, a broken image where a slide should
     be. Keyed on the first page rather than on identity, because the array is
     rebuilt on every render and would fire this on every one. */
  useEffect(() => {
    setIndex(0);
  }, [pages[0]]);

  useEffect(() => {
    if (!arrowKeys) return;

    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight")
        setIndex((i) => Math.min(pages.length - 1, i + 1));
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [arrowKeys, pages.length]);

  // Nothing to show. Callers currently guarantee a non-empty deck, but this
  // component is one render away from deciding whether the reader sees a broken
  // image, and it should not rest on that promise. AFTER every hook, so the hook
  // order is the same on every render whatever the deck holds.
  if (pages.length === 0) return null;

  return (
    <>
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
              <img
                src={`/media/${key}`}
                alt={`Go to slide ${i + 1}`}
                loading="lazy"
              />
            </button>
          </li>
        ))}
      </ol>
    </>
  );
}
