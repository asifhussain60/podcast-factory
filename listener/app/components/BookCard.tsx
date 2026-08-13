import {
  faBookOpen,
  faHeadphones,
  faNoteSticky,
  faPause,
  faPlay,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useNavigate } from "react-router";

import { Icon } from "~/components/Icon";
import { clock, usePlayer, type NowPlaying } from "~/components/player/Player";
import { collectionOf } from "~/lib/collection";
import { PRE_ROLL_S } from "~/lib/marks";
import type { CardPlayableEpisode, LibraryCard } from "~/server/catalog.server";

/**
 * One book in the library grid.
 *
 * The card is in two halves and the split is the design: the BAND carries who
 * the book is, the BODY carries what it contains. Identity above, contents
 * below, and nothing crosses over.
 *
 * The band prefers the original-script title, because for most of this library that is
 * the book's real name and it is the thing worth setting large. Where a book has
 * no Arabic title the band takes the English one in the display serif instead —
 * the band never sits empty, and it keeps its height either way so a mixed grid
 * still lines up. The English title is never printed twice: it is in the band or
 * in the body, whichever place is carrying it.
 *
 * Everything else about a book is an action. The card used to spend this space
 * naming static facts — chapters, minutes, formats — but a reader standing in
 * the library needs the next move more than a contents receipt.
 */
export function BookCard({
  slug,
  title,
  bucket,
  card,
  listen = null,
  progress = null,
  bookmarks = [],
  marks = null,
}: {
  slug: string;
  title: string;
  bucket: string;
  card: LibraryCard | null;
  /** Where this reader got to, or null if they have not opened it. */
  progress?: { anchorKey: string; fraction: number; chaptersDone: number } | null;
  bookmarks?: { id: string; anchorKey: string; createdAt: string }[];
  listen?: {
    mode: "resume" | "start";
    episode: CardPlayableEpisode;
    seconds: number | null;
  } | null;
  marks?: { notes: number; bookmarks: number } | null;
}) {
  const originalTitle = card?.titleOriginal ?? null;
  const originalLanguage = card?.titleLanguage ?? "ar";
  const collection = collectionOf(bucket);
  const bookmark =
    bookmarks.find((b) => b.anchorKey === progress?.anchorKey) ?? bookmarks[0] ?? null;
  const readKey = bookmark?.anchorKey ?? progress?.anchorKey ?? card?.firstChapterKey ?? null;
  const readHref =
    readKey === null
      ? null
      : `/book/${slug}/read/${encodeURIComponent(readKey)}${
          bookmark === null ? "" : `#mark-${bookmark.id}`
        }`;

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

          {originalTitle === null ? (
            <h2 className="pf-book__band-title pf-book__band-title--latin">{title}</h2>
          ) : (
            /* dir="rtl" is required for shaping and ordering. Centred here, unlike
               the old card, because the band is the title's own space rather than
               a line in a left-aligned stack. */
            <p
              lang={originalLanguage}
              dir={originalLanguage === "ar" || originalLanguage === "ur" ? "rtl" : undefined}
              className="pf-book__band-title"
            >
              {originalTitle}
            </p>
          )}

          <span className="pf-book__ornament pf-book__ornament--end" aria-hidden="true" />
        </div>
      </Link>

      <div className="pf-book__body">
        {originalTitle === null ? null : (
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
  const notes = marks?.notes ?? 0;
  const hasAudioSurface = listen !== null || (card?.episodes ?? 0) > 0;

  return (
    <div className="pf-book__actions" aria-label={`Actions for ${title}`}>
      {listen !== null ? (
        <ListenAction title={title} collection={collection} listen={listen} />
      ) : hasAudioSurface ? (
        <BookActionLink
          to={`/book/${slug}?tab=listen`}
          tone="audio"
          icon={faHeadphones}
          ariaLabel={`Open audio for ${title}`}
        />
      ) : null}

      {readHref !== null ? (
        <BookActionLink
          to={readHref}
          tone="read"
          icon={faBookOpen}
          ariaLabel={`Continue reading ${title}`}
        />
      ) : null}

      {card === null ? null : (
        <BookActionLink
          to={`/book/${slug}?tab=notes`}
          tone="notes"
          icon={faNoteSticky}
          badge={notes > 0 ? notes : null}
          ariaLabel={
            notes > 0
              ? `Open notes for ${title}, ${notes} note${notes === 1 ? "" : "s"}`
              : `Open notes for ${title}`
          }
        />
      )}
    </div>
  );
}

function BookActionLink({
  to,
  tone,
  icon,
  ariaLabel,
  badge = null,
}: {
  to: string;
  tone: "audio" | "read" | "notes";
  icon: IconDefinition;
  ariaLabel: string;
  badge?: number | null;
}) {
  return (
    <Link
      to={to}
      className={`pf-book-action ${
        tone === "audio"
          ? "pf-book-action--audio"
          : tone === "read"
            ? "pf-book-action--read"
            : "pf-book-action--notes"
      }`}
      aria-label={ariaLabel}
    >
      <span className="pf-book-action__circle" aria-hidden="true">
        <Icon icon={icon} />
        {badge === null ? null : <span className="pf-book-action__badge">{badge}</span>}
      </span>
    </Link>
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
  const navigate = useNavigate();
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
      className={`pf-book-action pf-book-action--audio${
        isPlaying ? " pf-book-action--active" : ""
      }`}
      aria-label={`${verb} ${title}, episode ${listen.episode.number}: ${listen.episode.title}`}
      onClick={() => {
        if (isCurrent) player.toggle();
        else
          player.play(track, {
            startAt: listen.seconds === null ? undefined : listen.seconds - PRE_ROLL_S,
          });
        player.setExpanded(true);
        navigate(`/book/${listen.episode.slug}?tab=listen`, {
          preventScrollReset: true,
        });
      }}
    >
      <span className="pf-book-action__circle" aria-hidden="true">
        <Icon icon={isPlaying ? faPause : faPlay} />
      </span>
      <span className="sr-only">
        Episode {listen.episode.number}, {position}
      </span>
    </button>
  );
}
