import {
  faArrowRight,
  faBookOpen,
  faHeadphones,
  faImages,
  faNoteSticky,
  faPause,
  faPlay,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { clock, usePlayer, type NowPlaying } from "~/components/player/Player";
import { collectionOf } from "~/lib/collection";
import type { CardPlayableEpisode, LibraryCard } from "~/server/catalog.server";

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
  listen = null,
  progress = null,
  marks = null,
}: {
  slug: string;
  title: string;
  bucket: string;
  card: LibraryCard | null;
  /** Where this reader got to, or null if they have not opened it. */
  progress?: { anchorKey: string; fraction: number; chaptersDone: number } | null;
  listen?: {
    mode: "resume" | "start";
    episode: CardPlayableEpisode;
    seconds: number | null;
  } | null;
  marks?: { notes: number; bookmarks: number } | null;
}) {
  const arabic = card?.titleArabic ?? null;
  const collection = collectionOf(bucket);
  const readKey = progress?.anchorKey ?? card?.firstChapterKey ?? null;
  const readHref = readKey === null ? null : `/book/${slug}/read/${encodeURIComponent(readKey)}`;

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
    <article
      className="pf-card pf-book"
      /* The card is the whole subtree the overlay has to cover — band, pills,
         meter and all — so the attribute goes on the link rather than on the
         band it most obviously colours. */
      data-collection={collection}
    >
      <Link to={`/book/${slug}`} className="pf-book__open">
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
      </Link>

      <div className="pf-book__body">
        {arabic === null ? null : (
          <Link to={`/book/${slug}`} className="pf-book__title-link">
            <h2 className="pf-book__title">{title}</h2>
          </Link>
        )}
        <CardActions
          slug={slug}
          title={title}
          card={card}
          collection={collection === "sessions" ? "sessions" : undefined}
          listen={listen}
          readHref={readHref}
          progress={progress}
          marks={marks}
        />

        {/* ALWAYS rendered, so every card in the grid is the same height — a book
            with no progress used to omit this block entirely and sit shorter
            than its neighbours.

            Still no 0% BAR on an unopened book: that would turn the library into
            a list of things not done, which is the opposite of what it is for.
            An unread card says so in words and reserves the same space. */}
        {percent === null ? (
          <div className="pf-book__progress">
            <p className="pf-book__resume pf-book__resume--idle">Not yet started</p>
          </div>
        ) : (
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
    </article>
  );
}

function CardActions({
  slug,
  title,
  card,
  collection,
  listen,
  readHref,
  progress,
  marks,
}: {
  slug: string;
  title: string;
  card: LibraryCard | null;
  collection: "sessions" | undefined;
  listen: {
    mode: "resume" | "start";
    episode: CardPlayableEpisode;
    seconds: number | null;
  } | null;
  readHref: string | null;
  progress: { anchorKey: string; fraction: number; chaptersDone: number } | null;
  marks: { notes: number; bookmarks: number } | null;
}) {
  const marked = (marks?.notes ?? 0) + (marks?.bookmarks ?? 0);
  const secondary =
    marked > 0
      ? { to: `/book/${slug}?tab=notes`, icon: faNoteSticky, label: `${marked} marked` }
      : card?.deckAvailable
        ? { to: `/book/${slug}?tab=slides`, icon: faImages, label: "Slides" }
        : { to: `/book/${slug}`, icon: faArrowRight, label: "Details" };

  return (
    <div className="pf-book__actions">
      {listen !== null ? (
        <ListenAction title={title} collection={collection} listen={listen} />
      ) : readHref !== null ? (
        <Link to={readHref} className="pf-book-action pf-book-action--read">
          <span className="pf-book-action__orb" aria-hidden="true">
            <Icon icon={faBookOpen} />
          </span>
          <span className="pf-book-action__copy">
            <strong>{progress === null ? "Read" : "Continue"}</strong>
            <span>{progress === null ? "First chapter" : "Saved"}</span>
          </span>
        </Link>
      ) : (
        <Link to={`/book/${slug}`} className="pf-book-action pf-book-action--read">
          <span className="pf-book-action__orb" aria-hidden="true">
            <Icon icon={faArrowRight} />
          </span>
          <span className="pf-book-action__copy">
            <strong>Open book</strong>
            <span>{card === null ? "Not published yet" : "Details"}</span>
          </span>
        </Link>
      )}

      <Link to={secondary.to} className="pf-book__quick">
        <Icon icon={secondary.icon} />
        {secondary.label}
      </Link>
    </div>
  );
}

function ListenAction({
  title,
  collection,
  listen,
}: {
  title: string;
  collection: "sessions" | undefined;
  listen: {
    mode: "resume" | "start";
    episode: CardPlayableEpisode;
    seconds: number | null;
  };
}) {
  const player = usePlayer();
  const src = `/media/${listen.episode.audioKey}`;
  const isCurrent = player.current?.src === src;
  const isPlaying = isCurrent && player.playing;
  const verb = isPlaying ? "Pause" : listen.mode === "resume" ? "Resume" : "Play";
  const position =
    listen.mode === "resume" && listen.seconds !== null
      ? `${clock(listen.seconds)} in`
      : listen.episode.durationS === null
        ? "Audio"
        : clock(listen.episode.durationS);

  const track: NowPlaying = {
    slug: listen.episode.slug,
    bookTitle: title,
    number: listen.episode.number,
    title: listen.episode.title,
    src,
    durationS: listen.episode.durationS,
    transcriptSrc:
      listen.episode.transcriptKey === null
        ? null
        : `/media/${listen.episode.transcriptKey}`,
    collection,
  };

  return (
    <button
      type="button"
      className={`pf-book-action pf-book-action--listen${
        isPlaying ? " pf-book-action--active" : ""
      }`}
      aria-label={`${verb} ${title}, episode ${listen.episode.number}: ${listen.episode.title}`}
      onClick={() => {
        if (isCurrent) player.toggle();
        else player.play(track);
        player.setExpanded(true);
      }}
    >
      <span className="pf-book-action__orb" aria-hidden="true">
        <Icon icon={isPlaying ? faPause : faPlay} />
      </span>
      <span className="pf-book-action__copy">
        <strong>{listen.mode === "resume" ? "Resume" : "Listen"}</strong>
        <span>
          EP {listen.episode.number} · {position}
        </span>
      </span>
    </button>
  );
}
