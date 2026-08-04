import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router";
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

/** The reading route's markup for one viewer. */
function render(over: { companion: CompanionCard[]; isCompanion: boolean }): string {
  const loaderData = {
    bookTitle: "The Master and the Disciple",
    slug: "the-master-and-the-disciple",
    chapter: CHAPTER,
    contents: [{ anchorKey: CHAPTER.anchorKey, idx: 1, title: CHAPTER.title, wordCount: 9 }],
    position: 0,
    previous: null,
    next: null,
    ...over,
  };

  return renderToStaticMarkup(
    createElement(
      StaticRouter,
      { location: `/book/${loaderData.slug}/read/${CHAPTER.anchorKey}` },
      // The route component takes more props than this in its generated type;
      // it reads only `loaderData`, and inventing the rest would be inventing a
      // router internal this test has no business asserting about.
      createElement(ReadChapter as never, { loaderData } as never),
    ),
  );
}

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
