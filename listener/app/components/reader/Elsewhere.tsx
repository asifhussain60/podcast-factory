import {
  faDownload,
  faHeadphones,
  faImages,
  faNoteSticky,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";

/**
 * The other ways this book can be taken, from inside one of them.
 *
 * Availability decides it, book by book, exactly as the book page's tabs do: a
 * chip appears only when the thing is IN R2 — episodes with a recording, deck
 * pages, a print edition — and Notes only once this reader has made one. A book
 * that is a reading edition and nothing else therefore shows no chips at all,
 * which is the honest answer rather than four dead controls.
 *
 * They are LINKS, not tabs. The panels live on the book page and this is a
 * different page; each chip lands on the tab it names, which is possible because
 * that tab now has a URL. The PDF is the exception and goes straight to the
 * file, because a download is not a view to switch to.
 *
 * Access is not consulted here, and does not need to be: every one of these
 * lands on a route that runs `requireUnitAccess` on the same slug this chapter
 * already passed. When per-surface permission arrives, this list is where it
 * will show — a chip for something a reader may not take should not be drawn.
 */
export function Elsewhere({
  slug,
  surfaces,
  marks,
  episodesFolded,
}: {
  slug: string;
  surfaces: { episodes: number; deckPages: number; pdfKey: string | null };
  /** This reader's own marks in this book — highlights and bookmarks together. */
  marks: number;
  /** True when every episode plays a chapter's own recording — see
   *  `episodesAreChapterNarration`. The "Podcast" chip below is the same
   *  offer this page's own Listen control already is, so it is withdrawn
   *  rather than pointing at a tab that no longer exists for this book. */
  episodesFolded: boolean;
}) {
  const chips = [
    surfaces.episodes > 0 && !episodesFolded
      ? {
          key: "listen",
          to: `/book/${slug}?tab=listen`,
          icon: faHeadphones,
          label: "Podcast",
          count: surfaces.episodes,
        }
      : null,
    surfaces.deckPages > 0
      ? {
          key: "slides",
          to: `/book/${slug}?tab=slides`,
          icon: faImages,
          label: "Slides",
          count: surfaces.deckPages,
        }
      : null,
    surfaces.pdfKey === null
      ? null
      : {
          key: "pdf",
          to: `/media/${surfaces.pdfKey}`,
          icon: faDownload,
          label: "PDF",
          count: 0,
        },
    marks > 0
      ? {
          key: "notes",
          to: `/book/${slug}?tab=notes`,
          icon: faNoteSticky,
          label: "Notes",
          count: marks,
        }
      : null,
  ].filter((c): c is NonNullable<typeof c> => c !== null);

  if (chips.length === 0) return null;

  return (
    <nav aria-label="The rest of this book" className="pf-elsewhere">
      {chips.map((chip) => (
        <Link key={chip.key} to={chip.to} className="pf-elsewhere__chip">
          <Icon icon={chip.icon} />
          {chip.label}
          {chip.count > 0 ? (
            <span className="pf-elsewhere__count">{chip.count}</span>
          ) : null}
        </Link>
      ))}
    </nav>
  );
}
