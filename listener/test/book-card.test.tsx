import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createMemoryRouter, RouterProvider } from "react-router";

import { BookCard } from "../app/components/BookCard";
import type { LibraryCard } from "../app/server/catalog.server";

/**
 * Every card in the grid is the same shape.
 *
 * Two things made them differ, and both were visible on the live library: a book
 * with five facts wrapped its pills to three rows while its neighbours took two,
 * and a book nobody had opened omitted the progress block entirely and sat
 * shorter than the cards beside it.
 */

const card: LibraryCard = {
  chapters: 9,
  words: 37_000,
  episodes: 20,
  recorded: 20,
  hasPdf: true,
  pdfAvailable: true,
  deckPages: 15,
  deckAvailable: true,
  titleArabic: "كتاب",
};

function render(props: Partial<Parameters<typeof BookCard>[0]> = {}) {
  const router = createMemoryRouter([
    {
      path: "/",
      element: <BookCard slug="a-book" title="A Book" bucket="Islamic" card={card} {...props} />,
    },
  ]);
  return renderToStaticMarkup(<RouterProvider router={router} />);
}

describe("the library card", () => {
  it("never shows more than four facts, so they never exceed two rows", () => {
    // The fullest possible book: chapters, reading time, episodes, print AND a
    // deck. The last two share one pill rather than taking a third row.
    const pills = render().match(/pf-pill pf-pill--outline/g) ?? [];
    expect(pills).toHaveLength(4);
  });

  it("combines print and deck into one fact, still named in words", () => {
    const html = render();
    expect(html).toContain("print + 15 slides");
    // Not glyphs. A row of bare icons is what the component was written to avoid.
    expect(html).not.toMatch(/aria-hidden="true"><\/svg>\s*<\/li>/);
  });

  it("names a single format in full rather than abbreviating it", () => {
    expect(render({ card: { ...card, deckPages: 0, deckAvailable: false } })).toContain(
      "print edition",
    );
    expect(render({ card: { ...card, hasPdf: false, pdfAvailable: false } })).toContain(
      "15 slides",
    );
  });

  it("reserves the progress row on a book nobody has opened", () => {
    // THE regression: this block used to be omitted entirely, so an unread card
    // was shorter than the cards beside it and the grid did not line up.
    const html = render({ progress: null });
    expect(html).toContain("pf-book__progress");
    expect(html).toContain("Not yet started");
  });

  it("still refuses to draw a 0% bar on an unopened book", () => {
    // A library of empty progress bars is a list of things not done, which is
    // the opposite of what it is for.
    expect(render({ progress: null })).not.toContain("progressbar");
  });

  it("draws the bar once there is progress", () => {
    const html = render({ progress: { fraction: 0.5, chaptersDone: 3 } });
    expect(html).toContain("progressbar");
    expect(html).not.toContain("Not yet started");
  });
});
