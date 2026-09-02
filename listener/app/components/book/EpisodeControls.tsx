import { faPause, faPlay } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { clock, usePlayer } from "~/components/player/Player";
import { count } from "~/lib/plural";
import type { Session } from "~/server/catalog.server";

/**
 * EpisodeControls.tsx — the two controls at the end of an episode row.
 *
 * Split out of `book.$slug.tsx` on 2026-09-02 for its size ceiling, and they
 * move together because they are one thing: what a reader can DO with a single
 * episode from the list — hear it, or read what they wrote about it. Both are
 * drawn per row, both take one episode, and neither knows anything about the
 * page around them.
 */
/**
 * How much you have kept in this episode, and a way into it.
 *
 * Where it GOES is decided by whether this episode is the one playing, and that
 * is not a flourish — the player's Notes drawer is scoped to what is playing, so
 * on any other row it would open somebody else's notes. So:
 *
 *   playing        the player's own drawer, already on screen, and the panel
 *                  these notes were made in
 *   not playing    the book's Notes tab, anchored at this episode's group
 *
 * The alternative — starting playback so the drawer becomes correct — would turn
 * a request to see your notes into a request to play half an hour of audio,
 * which is not what pressing a count means.
 *
 * Absent at zero rather than rendered as "0": an empty count reads as something
 * to clear rather than something not yet started, the same rule the reader's own
 * tab and the player's own badge follow.
 */
export function EpisodeNotes({
  slug,
  number,
  audioKey,
  kept,
}: {
  slug: string;
  number: number;
  audioKey: string | null;
  kept: number;
}) {
  const player = usePlayer();
  if (kept === 0) return null;

  // The count is in the accessible name, not only in the pill: "2" alone is not
  // a control anyone can act on by ear.
  const label = `${count(kept, "note")} in this episode`;
  const isPlaying =
    audioKey !== null && player.current?.src === `/media/${audioKey}`;

  if (isPlaying) {
    return (
      <button
        type="button"
        onClick={() => player.openPanel("notes")}
        aria-label={label}
        className="pf-row__meta pf-row__marks--button"
      >
        {kept}
      </button>
    );
  }

  return (
    <Link
      to={`/book/${slug}?tab=notes#ep-${number}`}
      aria-label={label}
      className="pf-row__meta pf-row__marks--button"
    >
      {kept}
    </Link>
  );
}

/**
 * Shows a pause glyph when this is the episode currently playing.
 *
 * Two weights, not three: the episode you are on is a solid accent button, and
 * every other episode is the soft tint of the same colour. A list of twenty
 * identical outline buttons gave the eye nothing to find; twenty SOLID ones
 * would have been twenty things all shouting at once.
 *
 * `aria-pressed` still carries the state — the colour is not the only thing
 * saying which one is playing.
 */
export function PlayButton({
  episode,
  onPlay,
}: {
  episode: Session["episodes"][number];
  onPlay: (player: ReturnType<typeof usePlayer>) => void;
}) {
  const player = usePlayer();
  const isCurrent = player.current?.src === `/media/${episode.audioKey}`;
  const isPlaying = isCurrent && player.playing;

  /* A circular transport button, not a labelled pill.
     The pill carried the word "Play" and the running time, which put the same
     word down the list as many times as there were episodes and set a clock in
     a control rather than in the row's own facts. Both moved: the duration to
     the meta line under the title, where the rest of what is true about an
     episode already sits, and the word into the accessible name.

     So the visible label is a glyph — and that is only safe because the name
     below is a full sentence naming the episode. A row of identical "Play"
     buttons is what a screen-reader user would otherwise hear. */
  const label = isPlaying
    ? `Pause ${episode.title}`
    : isCurrent
      ? `Resume ${episode.title}`
      : `Play ${episode.title}${episode.durationS ? `, ${clock(episode.durationS)}` : ""}`;

  return (
    <button
      type="button"
      onClick={() => (isCurrent ? player.toggle() : onPlay(player))}
      aria-pressed={isCurrent}
      aria-label={label}
      title={label}
      className={`pf-track__play${isPlaying ? " is-playing" : ""}`}
    >
      <Icon icon={isPlaying ? faPause : faPlay} />
    </button>
  );
}
