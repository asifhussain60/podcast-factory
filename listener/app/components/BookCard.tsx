import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { describeContents } from "~/lib/facts";
import type { LibraryCard } from "~/server/catalog.server";

/**
 * One book in the library grid.
 *
 * The card is in two halves and the split is the design: the BAND carries who
 * the book is, the BODY carries what it contains. Identity above, contents
 * below, and nothing crosses over.
 *
 * The band prefers the Arabic title, because for most of this library that is
 * the book's real name and it is the thing worth setting large. Where a book has
 * no Arabic title the band takes the English one in the display serif instead —
 * the band never sits empty, and it keeps its height either way so a mixed grid
 * still lines up. The English title is never printed twice: it is in the band or
 * in the body, whichever place is carrying it.
 *
 * Everything else about a book is a pill, per Asif's instruction. The rule the
 * old `Badges` helper established is kept exactly: name only what EXISTS. Most
 * books in this library are missing most things, and a row of icons with the
 * absent ones greyed out reads as a fault report, where naming only what is
 * there reads as a fact — a book with one pill does not look broken.
 */
export function BookCard({
  slug,
  title,
  bucket,
  card,
  progress = null,
  marks = null,
}: {
  slug: string;
  title: string;
  bucket: string;
  card: LibraryCard | null;
  /** Where this reader got to, or null if they have not opened it. */
  progress?: { fraction: number; chaptersDone: number } | null;
  marks?: { notes: number; bookmarks: number } | null;
}) {
  const arabic = card?.titleArabic ?? null;

  // Whole chapters finished, plus how far into the current one — so a reader on
  // chapter 4 of 9 reads about 40%, not 11% because one chapter is "done".
  // Absent when the book has no chapters: a percentage of nothing is a lie.
  const percent =
    progress === null || card === null || card.chapters === 0
      ? null
      : Math.min(
          99,
          Math.max(
            1,
            Math.round(((progress.chaptersDone + progress.fraction) / card.chapters) * 100),
          ),
        );

  return (
    <Link to={`/book/${slug}`} className="pf-card pf-card--link pf-book">
      <div className="pf-book__band">
        <span className="pf-pill pf-pill--pinned">{bucket}</span>

        <span className="pf-book__ornament pf-book__ornament--start" aria-hidden="true" />

        {arabic === null ? (
          <h2 className="pf-book__band-title pf-book__band-title--latin">{title}</h2>
        ) : (
          /* dir="rtl" is required for shaping and ordering. Centred here, unlike
             the old card, because the band is the title's own space rather than
             a line in a left-aligned stack. */
          <p lang="ar" dir="rtl" className="pf-book__band-title">
            {arabic}
          </p>
        )}

        <span className="pf-book__ornament pf-book__ornament--end" aria-hidden="true" />
      </div>

      <div className="pf-book__body">
        {arabic === null ? null : <h2 className="pf-book__title">{title}</h2>}
        <Contents card={card} />

        {/* Only for a book actually begun. A 0% bar on every unopened card would
            turn the library into a list of things not done, which is the
            opposite of what it is for. */}
        {percent === null ? null : (
          <div className="pf-book__progress">
            <div
              role="progressbar"
              aria-valuenow={percent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${percent}% read`}
              className="pf-meter"
            >
              {/* The width is a custom property the stylesheet turns into a
                  scale, the same contract the reading progress bar uses: JS
                  supplies one scalar and never a declaration. */}
              <span
                className="pf-meter__fill"
                style={{ "--pf-meter": String(percent / 100) } as React.CSSProperties}
              />
            </div>
            <span className="pf-book__resume">
              {percent}% read
              {marks && marks.notes + marks.bookmarks > 0
                ? ` · ${marks.notes + marks.bookmarks} marked`
                : ""}
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}

function Contents({ card }: { card: LibraryCard | null }) {
  if (card === null) {
    return (
      <p className="pf-book__pills">
        <span className="pf-pill pf-pill--quiet">Not published yet</span>
      </p>
    );
  }

  // The icon rides ALONGSIDE the word, never instead of it. The rule this list
  // has always followed is that a pill names something the book HAS; an icon
  // row where the absent things are greyed out is the fault report that rule
  // exists to avoid, and swapping words for glyphs would rebuild it.
  //
  // The list itself is no longer built here. It is the SAME list the book page
  // shows, and while it was written out twice the two drifted — different words
  // for the print edition, and only one of them knowing whether the file could
  // actually be opened. See `app/lib/facts.ts`.
  const pills = describeContents({
    chapters: card.chapters,
    words: card.words,
    episodes: card.episodes,
    withAudio: card.recorded,
    pdf: card.hasPdf,
    pdfAvailable: card.pdfAvailable,
    deckPages: card.deckPages,
    deckAvailable: card.deckAvailable,
  });

  if (pills.length === 0) {
    return (
      <p className="pf-book__pills">
        <span className="pf-pill pf-pill--quiet">Nothing published yet</span>
      </p>
    );
  }

  return (
    <ul className="pf-book__pills">
      {pills.map((pill) => (
        <li key={pill.label} className="pf-pill pf-pill--outline">
          <Icon icon={pill.icon} />
          {pill.label}
        </li>
      ))}
    </ul>
  );
}
