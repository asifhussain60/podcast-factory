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
import { collectionOf, type CollectionAccent } from "~/lib/collection";
import { percentRead } from "~/lib/book-progress";
import { PRE_ROLL_S } from "~/lib/marks";
import { studyTrackLabel } from "~/lib/study-track";
import type { CardPlayableEpisode, LibraryCard } from "~/server/catalog.server";
import type { Progress } from "~/server/marks.server";

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
  marks = null,
  compact = false,
  volumeLabel = null,
}: {
  slug: string;
  title: string;
  bucket: string;
  card: LibraryCard | null;
  /** Where this reader got to, or null if they have not opened it. */
  progress?: Progress | null;
  listen?: {
    mode: "resume" | "start";
    episode: CardPlayableEpisode;
    seconds: number | null;
  } | null;
  marks?: { notes: number; bookmarks: number } | null;
  /**
   * The library's tile view: the same identity — ribbon, band, progress —
   * at a footprint built for scanning many at once. The actions row drops
   * rather than shrinking, because a thumbnail with three legible buttons on
   * it is not actually smaller, it is the same card with worse hit targets.
   * The whole tile already opens the book, same as a list row does.
   */
  compact?: boolean;
  /**
   * Set only by `WorkCard`'s selected state: `title` there is the WORK's own
   * name (e.g. "Mukhtasar-ul-Asaar"), never a per-volume string, and this is
   * the "Volume 1 of 2" line that says which one this particular card is —
   * real structured data (the volume's own position, the work's own count),
   * never parsed back out of a title string. A standalone book has no
   * concept of "which volume," so this stays `null` everywhere else and the
   * title renders exactly as it always has.
   */
  volumeLabel?: string | null;
}) {
  const originalTitle = card?.titleOriginal ?? null;
  const collection = collectionOf(bucket);
  /* The Read action opens the chapter list on the book page, never a specific
     chapter (Asif, 2026-08-14) — the deep link into a bookmark or the last
     read position used to drop a reader straight into a chapter with no
     sense of where in the book they'd landed. Resuming from where you left
     off still works; it now happens from the chapter list itself, the same
     as it always has for a reader who opens the book page directly. */
  const readHref =
    card !== null && card.chapters > 0 ? `/book/${slug}?tab=read` : null;

  const percent = card === null ? null : percentRead(card.chapters, progress);

  return (
    <article
      className={
        compact ? "pf-card pf-book pf-book--compact" : "pf-card pf-book"
      }
      /* The card is the whole subtree the overlay has to cover — band, pills,
         meter and all — so the attribute goes on the link rather than on the
         band it most obviously colours. */
      data-collection={collection}
    >
      {/* A "stretched link": fills the card so blank space (padding, the gap
          between action buttons, an unread book's progress caption) opens the
          book too, not just the band and the title. Positioned (`inset: 0`
          needs that) but placed FIRST in the markup, so it paints below every
          other link/button on the card by DOM-order tiebreaking — CSS stacks
          sibling elements that share `z-index: auto` in tree order, and
          `.pf-book__open`, `.pf-book__title-link`, and `.pf-book-action` all
          come after it and are all themselves positioned. Those keep their
          own more specific destination; only empty space falls through to
          this one. `aria-hidden` + untabbable because the band and title
          links already reach the same page for keyboard and screen-reader
          use — this is a mouse/touch hit-area expansion, not a new
          destination. A real `<Link>`, not an onClick handler, so
          cmd/middle-click-to-new-tab still works on the blank space the same
          as it does on the visible links. */}
      <Link
        to={readHref ?? `/book/${slug}`}
        className="pf-book__stretched-link"
        aria-hidden="true"
        tabIndex={-1}
      />

      <Link to={`/book/${slug}`} className="pf-book__open">
        <BookBand title={title} bucket={bucket} card={card} />
      </Link>

      <div className="pf-book__body">
        {originalTitle === null ? null : (
          <Link to={`/book/${slug}`} className="pf-book__title-link">
            <h2
              className={
                volumeLabel === null
                  ? "pf-book__title"
                  : "pf-book__title pf-book__title--work"
              }
            >
              {title}
            </h2>
            {volumeLabel === null ? null : (
              <p className="pf-book__volume-label">{volumeLabel}</p>
            )}
          </Link>
        )}
        {compact ? null : (
          <CardActions
            slug={slug}
            title={title}
            card={card}
            collection={collection === "sessions" ? "sessions" : undefined}
            listen={listen}
            readHref={readHref}
            marks={marks}
          />
        )}

        {/* ALWAYS rendered, so every card in the grid is the same height — a book
            with no progress used to omit this block entirely and sit shorter
            than its neighbours.

            Still no 0% BAR on an unopened book: that would turn the library into
            a list of things not done, which is the opposite of what it is for.
            An unread card says so in words and reserves the same space. */}
        {percent === null ? (
          <div className="pf-book__progress">
            <p className="pf-book__resume pf-book__resume--idle">
              Not yet started
            </p>
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
                style={
                  { "--pf-meter": String(percent / 100) } as React.CSSProperties
                }
              />
            </div>
            <span className="pf-book__resume">{percent}% read</span>
          </div>
        )}
      </div>
    </article>
  );
}

/**
 * The coloured identity band alone — the original-script title over the
 * accented strip, or the English title in the display serif when a book has
 * none.
 *
 * Split out of `BookCard` so a second surface can show the same "cover" a
 * volume already has without re-deriving the original-title/fallback logic a
 * second time. `WorkCard`'s closed stack is that second surface: its front
 * leaf is this band, undecorated by a `<Link>`, standing in for the whole
 * card the way a book's spine stands in for the book.
 */
export function BookBand({
  title,
  bucket,
  card,
}: {
  title: string;
  bucket: string;
  card: LibraryCard | null;
}) {
  const originalTitle = card?.titleOriginal ?? null;
  // The alias, because it fits on one line. The full attribution goes to the
  // accessible name and the tooltip — a religious text's author is not a thing
  // to lose, only a thing that does not fit on a card.
  const author = card?.authorShort ?? card?.author ?? "Anonymous";
  const authorFull = card?.author ?? author;
  const originalLanguage = card?.titleLanguage ?? "ar";
  const studyTrack = card?.studyTrack ?? null;
  const trackLabel = studyTrackLabel(studyTrack);

  return (
    <div className="pf-book__band">
      <span className="pf-pill pf-pill--pinned">{bucket}</span>

      {trackLabel === null ? null : (
        <span className="pf-book__ribbon" data-track={studyTrack}>
          {trackLabel}
        </span>
      )}

      <span
        className="pf-book__ornament pf-book__ornament--start"
        aria-hidden="true"
      />

      {originalTitle === null ? (
        <h2 className="pf-book__band-title pf-book__band-title--latin">
          {title}
        </h2>
      ) : (
        /* dir="rtl" is required for shaping and ordering. Centred here, unlike
           the old card, because the band is the title's own space rather than
           a line in a left-aligned stack. */
        <p
          lang={originalLanguage}
          dir={
            originalLanguage === "ar" || originalLanguage === "ur"
              ? "rtl"
              : undefined
          }
          className="pf-book__band-title"
        >
          {originalTitle}
        </p>
      )}

      {/* The jacket credit. A cover prints the author under the title, smaller
          and quieter, and that is the whole reason this sits in the BAND rather
          than down in the white body with the buttons: the band is the cover.

          Never conditional. The column is NOT NULL with an 'Anonymous' default
          and the loader coalesces the LEFT JOIN, so there is always a name to
          set — which is what lets every card in the grid keep the same shape
          instead of some of them starting their white a line higher.

          No "by". A jacket rarely prints it and position carries the meaning;
          the accessible name below supplies it for a reader who cannot see the
          layout. */}
      <p className="pf-book__author" title={authorFull}>
        <span className="sr-only">Written by {authorFull}</span>
        <span aria-hidden="true">{author}</span>
      </p>

      <span
        className="pf-book__ornament pf-book__ornament--end"
        aria-hidden="true"
      />
    </div>
  );
}

function CardActions({
  slug,
  title,
  card,
  collection,
  listen,
  readHref,
  marks,
}: {
  slug: string;
  title: string;
  card: LibraryCard | null;
  collection: CollectionAccent;
  listen: {
    mode: "resume" | "start";
    episode: CardPlayableEpisode;
    seconds: number | null;
  } | null;
  readHref: string | null;
  marks: { notes: number; bookmarks: number } | null;
}) {
  const notes = marks?.notes ?? 0;
  const hasAudioSurface = listen !== null || (card?.episodes ?? 0) > 0;

  return (
    <div className="pf-book__actions" aria-label={`Actions for ${title}`}>
      {readHref !== null ? (
        <BookActionLink
          to={readHref}
          tone="read"
          icon={faBookOpen}
          ariaLabel={`Open chapters for ${title}`}
        />
      ) : null}

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

      {card === null ? null : (
        <BookActionLink
          to={`/book/${slug}?tab=notes`}
          tone="notes"
          icon={faNoteSticky}
          badge={notes > 0 ? notes : null}
          disabled={notes === 0}
          ariaLabel={
            notes > 0
              ? `Open notes for ${title}, ${notes} note${notes === 1 ? "" : "s"}`
              : `No notes yet for ${title}`
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
  disabled = false,
}: {
  to: string;
  tone: "audio" | "read" | "notes";
  icon: IconDefinition;
  ariaLabel: string;
  badge?: number | null;
  /** Visible rather than hidden — same reasoning as a track chip with
   * nothing filed under it yet: the action still teaches a reader that
   * notes exist as a thing this book can have, before it has any. A real
   * `disabled` button, not a styled link, so it drops out of tab order and
   * the browser's own affordances (no hover, no cursor change) do the rest. */
  disabled?: boolean;
}) {
  if (disabled) {
    return (
      <button
        type="button"
        className={`pf-book-action ${
          tone === "audio"
            ? "pf-book-action--audio"
            : tone === "read"
              ? "pf-book-action--read"
              : "pf-book-action--notes"
        }`}
        aria-label={ariaLabel}
        disabled
      >
        <span className="pf-book-action__circle" aria-hidden="true">
          <Icon icon={icon} />
        </span>
      </button>
    );
  }

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
        {badge === null ? null : (
          <span className="pf-book-action__badge">{badge}</span>
        )}
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
  collection: CollectionAccent;
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
  const verb = isPlaying
    ? "Pause"
    : listen.mode === "resume"
      ? "Resume"
      : "Play";
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
            startAt:
              listen.seconds === null ? undefined : listen.seconds - PRE_ROLL_S,
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
