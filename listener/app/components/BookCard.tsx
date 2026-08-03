import { Link } from "react-router";

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
}: {
  slug: string;
  title: string;
  bucket: string;
  card: LibraryCard | null;
}) {
  const arabic = card?.titleArabic ?? null;

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

  const pills: string[] = [];

  if (card.chapters > 0) pills.push(`${card.chapters} chapters`);
  if (card.minutes > 0) pills.push(`${card.minutes} min read`);

  if (card.recorded > 0) {
    pills.push(
      card.recorded === card.episodes
        ? `${card.episodes} episodes`
        : `${card.recorded} of ${card.episodes} episodes`,
    );
  } else if (card.episodes > 0) {
    pills.push(`${card.episodes} episodes planned`);
  }

  if (card.hasPdf) pills.push("PDF");
  if (card.deckPages > 0) pills.push("slides");

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
        <li key={pill} className="pf-pill pf-pill--outline">
          {pill}
        </li>
      ))}
    </ul>
  );
}
