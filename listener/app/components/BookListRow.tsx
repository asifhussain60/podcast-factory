import {
  faAngleRight,
  faBookOpen,
  faChevronDown,
  faLayerGroup,
} from "@fortawesome/free-solid-svg-icons";
import { useState } from "react";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import type { WorkVolume } from "~/components/WorkCard";
import { percentRead } from "~/lib/book-progress";
import { count } from "~/lib/plural";
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
        <span
          className="pf-row__mark pf-row__badge"
          data-track={studyTrack ?? undefined}
          aria-hidden="true"
        >
          <Icon icon={faBookOpen} />
        </span>
        <span className="pf-row__main">{title}</span>
        {trackLabel === null ? null : (
          <span className="pf-row__meta">{trackLabel}</span>
        )}
        {percent === null ? null : (
          <span className="pf-row__meta">{percent}% read</span>
        )}
        <Icon icon={faAngleRight} className="pf-row__go" />
      </Link>
    </li>
  );
}

/**
 * A multi-volume work in the list view — one tinted, expandable header row
 * standing in for what would otherwise be one plain `BookListRow` per
 * volume. Collapsed by default; opening it reveals each volume as its own
 * ordinary `BookListRow` directly underneath, indented so the relationship
 * reads at a glance.
 *
 * Only rendered by the caller when 2+ VISIBLE volumes share a `work_slug` —
 * the same `groupIntoWorks` the grid's stacked-set card already uses, so a
 * lone volume never reaches this component and renders as a plain row,
 * unchanged. Deliberately simpler than `WorkCard`: a list row has no card's
 * worth of limited space forcing a choice of which volume to show, so there
 * is no "remembered pick" to track here — every volume is just its own row
 * the moment this one opens, every time.
 */
export function WorkListRow({
  workSlug,
  title,
  volumes,
}: {
  workSlug: string;
  title: string;
  volumes: WorkVolume[];
}) {
  const [open, setOpen] = useState(false);
  const panelId = `work-volumes-${workSlug}`;

  return (
    <li>
      <button
        type="button"
        className="pf-row pf-book-row pf-work-row"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="pf-row__mark pf-row__badge" aria-hidden="true">
          <Icon icon={faLayerGroup} />
        </span>
        <span className="pf-row__main">{title}</span>
        <span className="pf-work-row__count">
          {count(volumes.length, "volume")}
        </span>
        {/* One icon, rotated by CSS off the button's own `aria-expanded` —
            simpler than swapping between a "closed" and "open" glyph, and
            the large circle around it (not `.pf-row__go`'s small plain
            arrow) is what was asked for: an unmistakable "this opens"
            control, not a detail easy to miss beside the volume count. */}
        <span className="pf-work-row__arrow" aria-hidden="true">
          <Icon icon={faChevronDown} />
        </span>
      </button>

      {open ? (
        <ol id={panelId} className="pf-rows pf-work-row__volumes">
          {volumes.map((volume) => (
            <BookListRow
              key={volume.slug}
              slug={volume.slug}
              title={volume.title}
              card={volume.card}
              progress={volume.progress}
            />
          ))}
        </ol>
      ) : null}
    </li>
  );
}
