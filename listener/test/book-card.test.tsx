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
  titleOriginal: "كتاب",
  titleLanguage: "ar",
};

function render(props: Partial<Parameters<typeof BookCard>[0]> = {}) {
  const router = createMemoryRouter([
    {
      path: "/",
      element: (
        <PlayerProvider>
          <BookCard
            slug="a-book"
            title="A Book"
            bucket="Islamic"
            card={card}
            {...props}
          />
        </PlayerProvider>
      ),
    },
  ]);
  return renderToStaticMarkup(<RouterProvider router={router} />);
}

describe("the library card", () => {
  it("marks an Urdu original title with its language for Nastaliq styling", () => {
    const html = render({
      card: {
        ...card,
        titleOriginal: "جہاں سے قافلے چلے",
        titleLanguage: "ur",
      },
    });
    expect(html).toContain('lang="ur"');
    expect(html).toContain('dir="rtl"');
    expect(html).toContain("جہاں سے قافلے چلے");
  });

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
    expect(html).toContain("Open chapters for A Book");
    expect(html).toContain("No notes yet for A Book");
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

  it("keeps reading, audio, and notes in that order", () => {
    const html = render();
    expect(html).toContain("Open chapters for A Book");
    expect(html).toContain("Open audio for A Book");
    expect(html).toContain("No notes yet for A Book");
    expect(html).toContain("/book/a-book?tab=read");
    expect(html.indexOf("pf-book-action--read")).toBeLessThan(
      html.indexOf("pf-book-action--audio"),
    );
    expect(html.indexOf("pf-book-action--audio")).toBeLessThan(
      html.indexOf("pf-book-action--notes"),
    );
  });

  it("disables the notes action, rather than hiding it, when there are none yet", () => {
    // Same reasoning as an empty track chip: the action stays visible so it
    // teaches a reader that notes exist as a thing this book can have.
    const html = render({ marks: { notes: 0, bookmarks: 0 } });
    expect(html).toContain(
      '<button type="button" class="pf-book-action pf-book-action--notes"',
    );
    expect(html).toContain("disabled");
    expect(html).not.toContain("pf-book-action__badge");
    expect(html).toContain("No notes yet for A Book");
  });

  it("gives the whole card a click target, not just the band and the title", () => {
    // Padding, the gap between action buttons, an unread book's progress
    // caption — none of that opened the book before (Asif, 2026-08-14).
    const html = render();
    expect(html).toContain('class="pf-book__stretched-link"');
    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain('tabindex="-1"');
  });

  it("sends the card-wide click target to the chapter list when the book has one, else the book page", () => {
    const withChapters = render();
    expect(withChapters).toContain(
      'class="pf-book__stretched-link" aria-hidden="true" tabindex="-1" href="/book/a-book?tab=read"',
    );

    const withoutCard = render({ card: null });
    expect(withoutCard).toContain(
      'class="pf-book__stretched-link" aria-hidden="true" tabindex="-1" href="/book/a-book"',
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
    const html = render({
      progress: { anchorKey: "intro", fraction: 0.5, chaptersDone: 3 },
    });
    expect(html).toContain("progressbar");
    expect(html).not.toContain("Not yet started");
  });

  it("sends the read action to the chapter list, never a specific chapter, even with saved progress", () => {
    // A deep link into a bookmark or the last read position used to drop a
    // reader straight into a chapter with no sense of where in the book they
    // had landed (Asif, 2026-08-14). Read always opens the chapter list now,
    // the same as it would for a reader who opens the book page directly.
    const html = render({
      progress: { anchorKey: "intro", fraction: 0.5, chaptersDone: 3 },
    });

    expect(html).toContain("/book/a-book?tab=read");
    expect(html).not.toContain("/book/a-book/read/intro");
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
