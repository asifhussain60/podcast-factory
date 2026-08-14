import { faAngleRight, faBookOpen } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { percentRead } from "~/lib/book-progress";
import { studyTrackLabel } from "~/lib/study-track";
import type { LibraryCard } from "~/server/catalog.server";
import type { Progress } from "~/server/marks.server";

/**
 * One book in the library's list view — the same chapter/episode row shape
 * used everywhere else in the app (`.pf-row`/`.pf-row__badge`), so a scanned
 * list of books reads as the same kind of list a reader already knows rather
 * than a fourth layout the site draws directories in.
 *
 * Deliberately narrower than `BookCard`: title, track, and progress are the
 * three facts worth a glance in a dense list. Everything else the card offers
 * — read/listen/notes, the original-script title — is one click away on the
 * book page this row links to.
 */
export function BookListRow({
  slug,
  title,
  card,
  progress = null,
}: {
  slug: string;
  title: string;
  card: LibraryCard | null;
  progress?: Progress | null;
}) {
  const studyTrack = card?.studyTrack ?? null;
  const trackLabel = studyTrackLabel(studyTrack);
  const percent = card === null ? null : percentRead(card.chapters, progress);

  return (
    <li>
      <Link to={`/book/${slug}`} className="pf-row pf-book-row">
        <span className="pf-row__mark pf-row__badge" data-track={studyTrack ?? undefined} aria-hidden="true">
          <Icon icon={faBookOpen} />
        </span>
        <span className="pf-row__main">{title}</span>
        {trackLabel === null ? null : <span className="pf-row__meta">{trackLabel}</span>}
        {percent === null ? null : <span className="pf-row__meta">{percent}% read</span>}
        <Icon icon={faAngleRight} className="pf-row__go" />
      </Link>
    </li>
  );
}
