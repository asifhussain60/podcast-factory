import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createMemoryRouter, RouterProvider } from "react-router";

import { BookCard } from "../app/components/BookCard";
import { PlayerProvider } from "../app/components/player/Player";
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
  firstChapterKey: "intro",
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
      element: (
        <PlayerProvider>
          <BookCard slug="a-book" title="A Book" bucket="Islamic" card={card} {...props} />
        </PlayerProvider>
      ),
    },
  ]);
  return renderToStaticMarkup(<RouterProvider router={router} />);
}

describe("the library card", () => {
  it("offers useful actions instead of catalog fact pills", () => {
    const html = render({
      listen: {
        mode: "start",
        episode: {
          slug: "a-book",
          number: 1,
          title: "Episode one",
          audioKey: "a-book/audio/ep01.m4a",
          durationS: 1800,
          transcriptKey: null,
        },
        seconds: null,
      },
    });

    expect(html).toContain("pf-book-action pf-book-action--audio");
    expect(html).toContain("Episode 1");
    expect(html).toContain("Continue reading A Book");
    expect(html).toContain("Open notes for A Book");
    expect(html).not.toContain("Slides");
    expect(html).not.toContain("pf-book-action__label");
    expect(html).not.toContain("37,000");
  });

  it("resumes the newest playable listening position when provided", () => {
    const html = render({
      listen: {
        mode: "resume",
        episode: {
          slug: "a-book",
          number: 4,
          title: "Episode four",
          audioKey: "a-book/audio/ep04.m4a",
          durationS: 2700,
          transcriptKey: "a-book/transcripts/ep04.vtt",
        },
        seconds: 742,
      },
    });

    expect(html).toContain("pf-book-action pf-book-action--audio");
    expect(html).toContain("Episode 4");
    expect(html).toContain("12:22 in");
  });

  it("shows notes as the same icon-only action family, with the count as a badge", () => {
    const html = render({
      progress: { anchorKey: "intro", fraction: 0.5, chaptersDone: 3 },
      marks: { notes: 1, bookmarks: 0 },
    });
    expect(html).toContain("pf-book-action pf-book-action--notes");
    expect(html).toContain("pf-book-action__badge");
    expect(html).toContain("Open notes for A Book, 1 note");
    expect(html).toContain("39% read");
    expect(html).not.toContain("39% read · 1 marked");
    expect(html).not.toContain("Details");
  });

  it("keeps audio, reading, and notes in that order", () => {
    const html = render();
    expect(html).toContain("Open audio for A Book");
    expect(html).toContain("Continue reading A Book");
    expect(html).toContain("Open notes for A Book");
    expect(html).toContain("/book/a-book/read/intro");
    expect(html.indexOf("pf-book-action--audio")).toBeLessThan(
      html.indexOf("pf-book-action--read"),
    );
    expect(html.indexOf("pf-book-action--read")).toBeLessThan(
      html.indexOf("pf-book-action--notes"),
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
    const html = render({ progress: { anchorKey: "intro", fraction: 0.5, chaptersDone: 3 } });
    expect(html).toContain("progressbar");
    expect(html).not.toContain("Not yet started");
  });

  it("uses separate links and buttons instead of nesting a play button inside the card link", () => {
    const html = render({
      listen: {
        mode: "start",
        episode: {
          slug: "a-book",
          number: 1,
          title: "Episode one",
          audioKey: "a-book/audio/ep01.m4a",
          durationS: 1800,
          transcriptKey: null,
        },
        seconds: null,
      },
    });

    expect(html).toContain("<article");
    expect(html).toContain("<button");
    expect(html).toContain('class="pf-book__open"');
    expect(html.indexOf("<button")).toBeGreaterThan(html.indexOf("</a>"));
  });
});
