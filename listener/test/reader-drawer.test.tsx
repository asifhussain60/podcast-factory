import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";

import ReadChapter from "../app/routes/book.$slug.read.$chapter";
import type { CompanionCard } from "../app/server/companion.server";

/**
 * WHICH PANEL a reader gets, rendered rather than reasoned about.
 *
 * companion.test.ts proves the cards never leave the database for anyone but the
 * administrator, and scripts/security-smoke.mjs fires the real request to prove
 * it end to end. Neither of them looks at the PAGE. This does: it renders the
 * reading route itself and asserts what is in the markup, because "the drawer is
 * the Companion for one account and the notes list for everybody else" is a
 * claim about a ternary in a component, and a ternary is exactly the kind of
 * thing that gets inverted by a refactor while every data test stays green.
 *
 * Rendered with `renderToStaticMarkup`, which runs no effects — so this is the
 * page as the SERVER sends it, which is the only version an unauthorised reader
 * could ever be handed in one piece.
 */

const CARD: CompanionCard = {
  id: "note-1",
  idx: 1,
  title: "Milk before meat",
  quote: "he gives what can be digested",
  bodyHtml: "<p>THE-EXPLANATION-BODY</p>",
  etymology: ["ميثاق (covenant)"],
};

const CHAPTER = {
  anchorKey: "chapter-one",
  idx: 1,
  title: "1. Chapter One",
  html: "<p>He gives what can be digested, not what is asked for.</p>",
  wordCount: 9,
};

/** A book that is a reading edition and nothing else — the common case. */
const NOTHING_ELSE = { episodes: 0, deckPages: 0, pdfKey: null };

/** The reading route's markup for one viewer. */
function render(over: {
  companion: CompanionCard[];
  isCompanion: boolean;
  surfaces?: { episodes: number; deckPages: number; pdfKey: string | null };
}): string {
  const loaderData = {
    bookTitle: "The Master and the Disciple",
    slug: "the-master-and-the-disciple",
    chapter: CHAPTER,
    contents: [{ anchorKey: CHAPTER.anchorKey, idx: 1, title: CHAPTER.title, wordCount: 9 }],
    position: 0,
    previous: null,
    next: null,
    surfaces: NOTHING_ELSE,
    isAdmin: over.isCompanion,
    ...over,
  };

  // A DATA router, not `StaticRouter`. The page wears the site's shell now, and
  // the masthead's sign-out is a `<Form>` — which is a POST rather than a link
  // on purpose, and `useSubmit` inside it refuses to run without one. Still
  // `renderToStaticMarkup`, so still no effects: this is the page as the SERVER
  // hands it over, which is the only version an unauthorised reader could be
  // given in one piece.
  const router = createMemoryRouter(
    [
      {
        path: "*",
        // The route component takes more props than this in its generated type;
        // it reads only `loaderData`, and inventing the rest would be inventing
        // a router internal this test has no business asserting about.
        Component: () => createElement(ReadChapter as never, { loaderData } as never),
      },
    ],
    { initialEntries: [`/book/${loaderData.slug}/read/${CHAPTER.anchorKey}`] },
  );

  return renderToStaticMarkup(createElement(RouterProvider as never, { router } as never));
}

/**
 * Just the chip row.
 *
 * Every assertion about the chips has to be made against THIS rather than
 * against the whole page: the masthead's wordmark and the footer both read
 * "Podcast Factory", so `not.toContain("Podcast")` over the document became a
 * claim about the shell the moment the reading page acquired one.
 */
function elsewhere(html: string): string {
  const start = html.indexOf('class="pf-elsewhere"');
  if (start === -1) return "";
  return html.slice(start, html.indexOf("</nav>", start));
}

/**
 * The way back, and the rest of the book.
 *
 * Asif could not find the book page's tabs from inside a chapter, twice — and he
 * was right that something was missing: the title was a plain heading and the
 * only link to `/book/:slug` sat after the LAST chapter. These pin the door and
 * the chips that sit beside it, including the case that matters most, which is a
 * book that has nothing else and must therefore show nothing.
 */
describe("finding the rest of the book from inside a chapter", () => {
  it("makes the book's title the way back to it", () => {
    const html = render({ companion: [], isCompanion: false });
    expect(html).toContain('href="/book/the-master-and-the-disciple"');
  });

  it("shows a chip for each thing the book actually has", () => {
    const html = render({
      companion: [],
      isCompanion: false,
      surfaces: { episodes: 20, deckPages: 15, pdfKey: "the-master-and-the-disciple/book.pdf" },
    });

    expect(elsewhere(html)).toContain("Podcast");
    expect(elsewhere(html)).toContain("Slides");
    expect(elsewhere(html)).toContain("PDF");
    // Each lands on the tab it names, which is only possible because those tabs
    // now have URLs.
    expect(html).toContain("?tab=listen");
    expect(html).toContain("?tab=slides");
    expect(html).toContain('href="/media/the-master-and-the-disciple/book.pdf"');
  });

  it("shows nothing at all for a book that is only a reading edition", () => {
    // Degrees of Excellence, in the database as it stands: ten chapters, no
    // episodes, no deck, no print edition. Four dead chips would be worse than
    // none, and would be the thing that made it look broken in the first place.
    const html = render({ companion: [], isCompanion: false });

    expect(html).not.toContain("pf-elsewhere");
    expect(elsewhere(html)).toBe("");
  });

  it("offers each surface independently", () => {
    const audioOnly = elsewhere(
      render({
        companion: [],
        isCompanion: false,
        surfaces: { episodes: 4, deckPages: 0, pdfKey: null },
      }),
    );

    expect(audioOnly).toContain("Podcast");
    expect(audioOnly).not.toContain("Slides");
    expect(audioOnly).not.toContain(">PDF<");
  });
});

describe("the right-hand drawer", () => {
  // Every assertion below is a `not.toContain`, and an empty string satisfies
  // all of them. This is the one that fails if the route stops rendering.
  it("renders the reading page at all", () => {
    const html = render({ companion: [], isCompanion: false });
    expect(html).toContain("pf-reader-page");
    expect(html).toContain("pf-edge-tab--end");
    expect(html).toContain(CHAPTER.title);
  });

  it("is the Companion for the one account it belongs to", () => {
    const html = render({ companion: [CARD], isCompanion: true });

    expect(html).toContain("Companion");
    expect(html).toContain("Open companion");
    // And the notes list is not also there. Two panels on one edge would mean
    // the branch had become an addition.
    expect(html).not.toContain("Your notes");
    expect(html).not.toContain("Nothing marked yet");
  });

  it("is the notes list for every other reader, and carries no card", () => {
    // The shape a non-admin loader produces: `companionFor` returned nothing,
    // so there is nothing for the component to show even if it tried.
    const html = render({ companion: [], isCompanion: false });

    expect(html).toContain("Your notes");
    expect(html).toContain("Open your notes");
    expect(html).not.toContain("Companion");
    expect(html).not.toContain("Milk before meat");
    expect(html).not.toContain("THE-EXPLANATION-BODY");
  });

  it("shows no card to another reader even if cards somehow reach the page", () => {
    // The belt to companion.test.ts's braces. If a future loader change let the
    // cards through — a widened SELECT, a copied Promise.all — this reader must
    // still not be shown them, and must still get their own notes drawer.
    const html = render({ companion: [CARD], isCompanion: false });

    expect(html).toContain("Your notes");
    expect(html).not.toContain("Milk before meat");
    expect(html).not.toContain("THE-EXPLANATION-BODY");
    expect(html).not.toContain("ميثاق");
  });

  it("does not tint the chapter for another reader", () => {
    // The passages are painted into the live DOM by an effect, so no server
    // render carries a tint. What this pins is the prose itself: the chapter a
    // non-admin is sent is byte-identical to the one the administrator is sent,
    // which is what makes the Companion invisible rather than merely hidden.
    const mine = render({ companion: [CARD], isCompanion: true });
    const theirs = render({ companion: [], isCompanion: false });

    expect(theirs).toContain(CHAPTER.html);
    expect(mine).toContain(CHAPTER.html);
    expect(theirs).not.toContain("pf-cp");
  });
});
