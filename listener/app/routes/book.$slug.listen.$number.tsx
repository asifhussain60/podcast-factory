import { useCallback, useEffect, useMemo, useState } from "react";
import {
  faBookOpen,
  faChevronLeft,
  faChevronRight,
  faHeadphones,
  faNoteSticky,
  faPause,
  faPlay,
} from "@fortawesome/free-solid-svg-icons";
import { Link, useSearchParams } from "react-router";

import type { Route } from "./+types/book.$slug.listen.$number";
import { Icon } from "~/components/Icon";
import { NotesList } from "~/components/reader/NotesList";
import { SidePanel } from "~/components/reader/SidePanel";
import { Transcript, type Cue } from "~/components/player/Transcript";
import { clock, usePlayer } from "~/components/player/Player";
import { useMarks } from "~/components/reader/useMarks";
import { cloudflare } from "~/context";
import { newId, notesInEpisode, submit, PRE_ROLL_S } from "~/lib/marks";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { session } from "~/middleware/session";
import { unitBySlug } from "~/server/access.server";
import { chaptersOf, episodesOf } from "~/server/catalog.server";

/**
 * One episode of the podcast: what is said, and where you marked it.
 *
 * The audio counterpart of the chapter reader, deliberately built to the same
 * plan — same gate on the same `params.slug`, transcript where the prose goes,
 * the reader's own marks in the drawer on the right. Somebody who has read a
 * chapter here already knows how this page works.
 *
 * Marks are NOT loaded here, for the same reason the reader does not load them:
 * `useMarks` paints the cached copy before the network answers, and putting
 * per-person data in the loader would put it in the SSR document.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const slug = params.slug;
  const number = Number(params.number);

  // A non-numeric segment is a 404 in the same shape a missing episode is, so
  // neither says anything about what exists.
  if (!Number.isInteger(number) || number < 0) notFound();

  const [unit, episodes, chapters] = await Promise.all([
    unitBySlug(env.DB, slug),
    episodesOf(env.DB, slug),
    chaptersOf(env.DB, slug),
  ]);

  const here = episodes.findIndex((e) => e.number === number);
  if (unit === null || here === -1) notFound();

  const episode = episodes[here];

  return {
    bookTitle: unit.title,
    slug,
    episode,
    // Every episode, for the drawer — a listener's marks in this book are one
    // list, and the ones in other episodes have to be shown somewhere they can
    // be reached from.
    episodes: episodes.map((e) => ({ number: e.number, title: e.title })),
    // Titles for the "read along" line. Names only, so this stays one small
    // query rather than the chapter bodies.
    chapterTitles: Object.fromEntries(chapters.map((c) => [c.anchorKey, c.title])),
    previous: here > 0 ? episodes[here - 1] : null,
    next: here < episodes.length - 1 ? episodes[here + 1] : null,
    isAdmin: context.get(session).viewer?.isAdmin === true,
  };
}

export default function ListenEpisode({ loaderData }: Route.ComponentProps) {
  const { bookTitle, slug, episode, episodes, chapterTitles, previous, next } = loaderData;
  const player = usePlayer();
  const marks = useMarks(slug);
  const [notesOpen, setNotesOpen] = useState(false);
  const [params] = useSearchParams();

  const moments = useMemo(() => notesInEpisode(marks, episode.number), [marks, episode.number]);

  const src = episode.audioKey === null ? null : `/media/${episode.audioKey}`;
  const isCurrent = src !== null && player.current?.src === src;
  // Only the episode being PLAYED has a position. Reading the player's clock on
  // any other episode would follow the transcript of this page against audio
  // from a different one.
  const position = isCurrent ? player.position : 0;

  const start = useCallback(
    (at?: number) => {
      if (src === null) return;
      if (!isCurrent) {
        player.play({
          slug,
          bookTitle,
          number: episode.number,
          title: episode.title,
          src,
          durationS: episode.durationS,
        });
      }
      if (at !== undefined) player.seek(at);
      else if (isCurrent) player.toggle();
    },
    [src, isCurrent, player, slug, bookTitle, episode],
  );

  /* ---- Arriving from a marked moment ------------------------------------
     `?at=` is written by the notes list when there is no player to command —
     from the book page, or a link opened cold. It starts the episode there and
     is deliberately not cleared from the URL: the address stays a link to that
     moment, which is what makes it shareable with yourself.

     Once per arrival. Re-running on every render would fight a listener who has
     since scrubbed somewhere else.                                          */
  const [seeded, setSeeded] = useState(false);
  useEffect(() => {
    if (seeded || src === null) return;
    const at = Number(params.get("at"));
    if (!Number.isFinite(at) || at <= 0) return;
    setSeeded(true);
    start(at);
  }, [seeded, src, params, start]);

  /** Mark this moment. The transcript line rides along when there is one. */
  const mark = useCallback(
    (seconds: number, quote: string | null) => {
      submit("episode-note", {
        id: newId(),
        number: String(episode.number),
        seconds: String(Math.floor(seconds)),
        note: "",
        quote: quote ?? "",
      });
      setNotesOpen(true);
    },
    [episode.number],
  );

  const removeMoment = useCallback((id: string) => submit("un-episode-note", { id }), []);

  const jump = useCallback(
    (number: number, seconds: number) => {
      if (number !== episode.number) return; // another episode: the row links instead
      start(seconds);
    },
    [episode.number, start],
  );

  return (
    <div className="pf-shell">
      <SidePanel
        side="end"
        as="aside"
        open={notesOpen}
        onOpen={() => setNotesOpen(true)}
        onClose={() => setNotesOpen(false)}
        label="Your notes"
        icon={faNoteSticky}
        count={marks.episodeNotes.length}
      >
        {/* Episodes only. The chapters are deliberately absent — this page has
            no chapter rendered, so a highlight row here could neither scroll to
            its passage nor be corrected against it. The reader's drawer makes
            the mirror-image choice for the same reason. */}
        <NotesList
          annotations={[]}
          bookmarks={[]}
          chapters={[]}
          episodes={episodes}
          episodeNotes={marks.episodeNotes}
          orphaned={EMPTY_SET}
          slug={slug}
          onPlay={jump}
          onRemoveAnnotation={NOTHING}
          onRemoveBookmark={NOTHING}
          onRemoveEpisodeNote={removeMoment}
        />
      </SidePanel>

      <main id="main" className="pf-reader">
        <div className="pf-reader-head">
          <h1 className="pf-reader-head__book">
            <Link to={`/book/${slug}?tab=listen`}>{bookTitle}</Link>
          </h1>

          <p className="pf-eyebrow">
            <Icon icon={faHeadphones} />
            Episode {episode.number}
            {episode.durationS ? ` · ${clock(episode.durationS)}` : null}
          </p>
        </div>

        <div className="pf-reader-page">
          <article className="pf-page">
            <h2 className="pf-chapter-title">{episode.title}</h2>

            {episode.chapters.length > 0 ? (
              <p className="pf-note pf-note--quiet">
                <Icon icon={faBookOpen} />
                Read along:{" "}
                {episode.chapters.map((key, i) => (
                  <span key={key}>
                    {i > 0 ? ", " : null}
                    <Link
                      to={`/book/${slug}/read/${encodeURIComponent(key)}`}
                      className="pf-link pf-link--inline"
                    >
                      {chapterTitles[key] ?? key}
                    </Link>
                  </span>
                ))}
              </p>
            ) : null}

            {src === null ? (
              <p className="pf-note">This episode has not been recorded yet.</p>
            ) : (
              <div className="pf-episode-controls">
                <button
                  type="button"
                  onClick={() => start()}
                  aria-pressed={isCurrent}
                  className={`pf-button ${isCurrent ? "pf-button--primary" : "pf-button--soft"}`}
                >
                  <Icon icon={isCurrent && player.playing ? faPause : faPlay} />
                  {isCurrent && player.playing ? "Pause" : "Play"}
                </button>

                {/* Marking from HERE, not only from a transcript line. The
                    moment a listener wants is often between two lines, and on an
                    episode with no transcript this is the only way to mark one
                    at all. */}
                <button
                  type="button"
                  onClick={() => mark(position, null)}
                  disabled={!isCurrent}
                  className="pf-button pf-button--soft"
                  title={
                    isCurrent
                      ? "Mark where the audio is now"
                      : "Play this episode to mark a moment in it"
                  }
                >
                  <Icon icon={faNoteSticky} />
                  Mark {isCurrent ? clock(position) : "this moment"}
                </button>
              </div>
            )}

            {episode.transcriptKey === null ? (
              <p className="pf-note pf-note--quiet">
                No transcript for this episode yet.
              </p>
            ) : (
              <Transcript
                src={`/media/${episode.transcriptKey}`}
                position={position}
                playing={isCurrent && player.playing}
                onSeek={(at) => start(at)}
                onNote={(cue: Cue) => mark(cue.startS, cue.text)}
              />
            )}
          </article>

          <nav className="pf-turn">
            {previous ? (
              <Link
                to={`/book/${slug}/listen/${previous.number}`}
                className="pf-card pf-card--link pf-card--padded pf-turn__link"
              >
                <span className="pf-eyebrow">
                  <Icon icon={faChevronLeft} />
                  Previous
                </span>
                <span className="pf-turn__title">{previous.title}</span>
              </Link>
            ) : (
              <span className="pf-turn__gap" />
            )}

            {next ? (
              <Link
                to={`/book/${slug}/listen/${next.number}`}
                className="pf-card pf-card--link pf-card--padded pf-turn__link pf-turn__link--end"
              >
                <span className="pf-eyebrow">
                  Next
                  <Icon icon={faChevronRight} />
                </span>
                <span className="pf-turn__title">{next.title}</span>
              </Link>
            ) : (
              <Link
                to={`/book/${slug}?tab=listen`}
                className="pf-card pf-card--link pf-card--padded pf-turn__link pf-turn__link--end"
              >
                <span className="pf-eyebrow">
                  The end
                  <Icon icon={faChevronRight} />
                </span>
                <span className="pf-turn__title">Back to {bookTitle}</span>
              </Link>
            )}
          </nav>
        </div>
      </main>
    </div>
  );
}

/** Nothing is orphaned here, and nothing on this page can remove a highlight. */
const EMPTY_SET: ReadonlySet<string> = new Set<string>();
const NOTHING = () => {};

/** Re-exported so the notes list and this page cannot disagree about the pre-roll. */
export { PRE_ROLL_S };
