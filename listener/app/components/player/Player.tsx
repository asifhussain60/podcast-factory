import {
  faChevronDown,
  faPlus,
  faRotateLeft,
  faRotateRight,
} from "@fortawesome/free-solid-svg-icons";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { NotesList } from "~/components/reader/NotesList";
import { RichNoteEditor } from "~/components/notes/RichNoteEditor";
import { Transcript, parseVtt, type Cue } from "~/components/player/Transcript";
import { newId, refresh, type EpisodeNote } from "~/lib/marks";

/**
 * One <audio> element for the whole site.
 *
 * It lives in the authenticated LAYOUT, not in any page, which is the only way
 * playback survives navigation: React Router keeps a layout mounted across
 * client transitions, so moving from an episode to a chapter re-renders the
 * outlet and leaves this element — and the sound — untouched. An <audio> per
 * page would stop the moment the reader followed a link.
 *
 * No volume control anywhere in here. iOS silently ignores `volume` on
 * HTMLMediaElement, so a slider would be a control that visibly does nothing on
 * the platform most of this listening happens on. The device's own buttons are
 * the volume control.
 */

export interface NowPlaying {
  slug: string;
  bookTitle: string;
  number: number;
  title: string;
  src: string;
  durationS: number | null;
  /** The media URL of this episode's WebVTT, or null when none was made. */
  transcriptSrc: string | null;
  /**
   * Which collection the book being played belongs to — see `lib/collection.ts`.
   *
   * Carried on the EPISODE rather than read from the page, and that is the whole
   * point of it being here. The player is mounted in `_authed`, above every book
   * route, so that sound survives navigation: a listener can start a session and
   * walk into a book's page while it plays. An attribute taken from the page
   * would then paint the bar for whatever is on screen instead of for what is
   * coming out of the speakers.
   */
  collection?: "sessions";
}

/** Which side panel the player is showing, or none. */
export type PlayerPanel = "transcript" | "notes" | null;

interface PlayerState {
  current: NowPlaying | null;
  playing: boolean;
  /** Seconds. Driven by the element, not by us. */
  position: number;
  duration: number;
  rate: number;
  /**
   * What is said in the episode being played, loaded with the audio.
   *
   * Held HERE rather than fetched by the panel that shows it, which is what
   * makes the transcript follow the audio silently: the words are in memory from
   * the moment playback starts, so opening the panel mid-episode lands on the
   * line being spoken instead of showing a spinner. Nothing runs in between —
   * which line is current is derived from `position` at render time, and while
   * the panel is closed nobody asks.
   *
   * Null means either "no transcript for this episode" or "still loading"; the
   * panel says the same thing for both, because a listener can do nothing with
   * either distinction.
   */
  cues: Cue[] | null;
  /**
   * The PLAYING book's episode notes, held here rather than in the panel.
   *
   * The panel used to own them, fetched when it opened, which meant nothing on
   * screen could say how many there were until you had already looked. They cost
   * no request: `/book/<slug>/marks` returns them in the SAME response the
   * resume position is read from, and that response was being fetched and
   * three-quarters discarded on every play. Scoped to the playing book, never
   * the book being read — see `markMoment` for why those differ.
   */
  notes: EpisodeNote[];
  /** Re-read the playing book's notes after one is kept, edited or removed. */
  reloadNotes: () => void;
  panel: PlayerPanel;
  openPanel: (panel: PlayerPanel) => void;
  /**
   * Whether the player has taken over the screen.
   *
   * ONE flag, read by CSS rather than by JS, and that is the whole design: the
   * expanded player is the SAME markup as the bar with a different layout, so
   * there is no second player to keep in step, no second transport, and nothing
   * that can be playing in one and stopped in the other. `data-expanded` on the
   * root is what the stylesheet switches on.
   *
   * It only takes over on a phone. On a desktop the bar is already out of the
   * way at the foot of a wide page, and a full-screen player there would hide
   * the book somebody is reading along with.
   */
  expanded: boolean;
  setExpanded: (expanded: boolean) => void;
  play: (episode: NowPlaying) => void;
  toggle: () => void;
  seek: (seconds: number) => void;
  nudge: (delta: number) => void;
  setRate: (rate: number) => void;
  close: () => void;
}

const PlayerContext = createContext<PlayerState | null>(null);

export const RATES = [0.9, 1, 1.2, 1.5, 1.8] as const;

/**
 * Where the listener had got to, keyed by the EPISODE rather than by its file.
 *
 * This used to key on `episode.src` — the media URL, which contains
 * `media_asset.key`. That key changes whenever an episode's audio is re-uploaded
 * under a new name, and when it does the old entry simply never matches again:
 * everyone silently lost their place, and nothing anywhere reported it, because
 * "no stored position" and "position stored under a name nothing asks for" look
 * identical. `slug` and `number` are the episode's own identity and survive a
 * re-publish exactly as `chapter.anchor_key` does.
 *
 * Local storage is now a CACHE, not the record. The record is
 * `listening_progress` in D1, so closing the iPad and opening the phone resumes
 * where the iPad stopped; the cache is what lets playback resume instantly
 * without waiting for a round trip, and what holds the position when the network
 * is gone.
 */
const POSITION_KEY = "pf-positions";

/**
 * How fast the listener plays things — remembered like every other setting.
 *
 * It was React state alone, so a listener who plays at 1.5× was returned to 1×
 * by every reload and every new visit, on every episode. That is not a position
 * (which belongs to one episode) but a PREFERENCE about listening, so it is one
 * value rather than a map, and it sits beside the positions rather than in
 * `pf-reading` — that key is the reading column's typography, and a listening
 * speed inside it would be a second meaning for one store.
 */
const RATE_KEY = "pf-rate";

function loadRate(): number {
  try {
    const stored = Number(localStorage.getItem(RATE_KEY));
    // Validated against the SCALE THE UI OFFERS, never merely against "is a
    // number". `playbackRate = 0` is a silent, unrecoverable pause, and a rate
    // between the buttons would light none of them — the control would read as
    // broken. Same rule as `storedReading`, and it must keep using the exported
    // RATES rather than a second list: a copy that drifted would reject every
    // real stored value and reset to 1, which is the bug this exists to fix.
    return (RATES as readonly number[]).includes(stored) ? stored : 1;
  } catch {
    return 1;
  }
}

const positionKey = (slug: string, number: number) => `${slug}#${number}`;

function loadPositions(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(POSITION_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePosition(episode: NowPlaying, seconds: number) {
  const whole = Math.floor(seconds);

  try {
    const all = loadPositions();
    all[positionKey(episode.slug, episode.number)] = whole;
    localStorage.setItem(POSITION_KEY, JSON.stringify(all));
  } catch {
    // Storage disabled. Playback still works; only the local memory is lost —
    // the server copy below is unaffected, which is the point of having both.
  }

  // Throttled to one write a minute, and deliberately not more. A position is
  // only useful to within a few seconds, this fires every five, and a listener
  // going through a two-hour episode would otherwise post 1,400 times.
  const now = Date.now();
  if (now - lastServerWrite < 60_000) return;
  lastServerWrite = now;

  void fetch(`/book/${encodeURIComponent(episode.slug)}/marks`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      intent: "listening",
      number: String(episode.number),
      seconds: String(whole),
    }),
    // The listener is mid-episode; a failed bookkeeping write must not surface
    // as an unhandled rejection in their console.
  }).catch(() => {});
}

let lastServerWrite = 0;

/**
 * Keep a moment of what is playing, with the line that was said at it.
 *
 * A DIRECT post, not a write through the marks store, and that is a correctness
 * requirement rather than a shortcut. `lib/marks.ts` holds one book open at a
 * time — whichever one is being READ — and posts its outbox to that book's
 * endpoint. A listener can have this book's episode playing while reading a
 * different book entirely, and routing this through the store would file the
 * note under the wrong work. `savePosition` above already writes this way, for
 * the same reason.
 *
 * The cost is that this one write has no offline outbox. That is the right trade:
 * a note is made in a moment the listener can see happen, and the alternative is
 * a queue that can attribute it to the wrong book.
 */
function markMoment(
  episode: NowPlaying,
  seconds: number,
  id: string,
  quote: string,
  // Optional and defaulted to "", so the transcript's one-tap "mark this
  // line" action — which has always sent no text — is unaffected by this
  // parameter existing. The same call now also serves the Notes panel's
  // "+ Add note" composer and its edit-in-place save, both of which pass
  // real content.
  note: string = "",
): Promise<boolean> {
  return fetch(`/book/${encodeURIComponent(episode.slug)}/marks`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      intent: "episode-note",
      id,
      number: String(episode.number),
      // Floor, not round: the stored value is where the line STARTS, and the
      // site plays back from a little before it anyway.
      seconds: String(Math.floor(seconds)),
      note,
      quote,
    }),
  })
    .then((response) => response.ok)
    .catch(() => false);
}

/** What the marks endpoint gives back, as much of it as the player uses. */
interface PlayingMarks {
  listening?: Record<string, number>;
  episodeNotes?: EpisodeNote[];
}

/**
 * The playing book's marks: where other devices got to, and what is kept in it.
 *
 * ONE request for both, because the endpoint answers with both and the player
 * needs both. It used to read only `listening` and drop the rest, and the notes
 * panel then fetched the identical URL again when it opened — two requests for
 * one response, which is also why nothing could show a count before the panel
 * was asked for.
 */
async function fetchMarks(slug: string): Promise<PlayingMarks | null> {
  try {
    const response = await fetch(`/book/${encodeURIComponent(slug)}/marks`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    return (await response.json()) as PlayingMarks;
  } catch {
    return null;
  }
}

/**
 * The server's copy of the position, if it is further along than the cache.
 *
 * "Further along" rather than "newer": there is no clock to trust between two
 * devices, and the failure that actually matters is resuming EARLIER than you
 * got to — re-listening to ten minutes you have already heard. Taking the
 * greater of the two can only ever skip ahead by however far the other device
 * went, which is the direction a listener can correct in one gesture.
 */
const positionIn = (
  marks: PlayingMarks | null,
  number: number,
): number | null => marks?.listening?.[String(number)] ?? null;

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [current, setCurrent] = useState<NowPlaying | null>(null);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  // Starts at 1 and is corrected from storage on mount, never read during
  // render: the server has no localStorage, so seeding state from it directly
  // would make the first client render differ from the server's. Same reasoning
  // as `hydrateReading`.
  const [rate, setRateState] = useState(1);
  const [cues, setCues] = useState<Cue[] | null>(null);
  const [notes, setNotes] = useState<EpisodeNote[]>([]);
  const [panel, setPanel] = useState<PlayerPanel>(null);
  const [expanded, setExpanded] = useState(false);

  /**
   * Which episode the cues in state belong to.
   *
   * A ref, not state: it exists to make a late-arriving fetch discard itself
   * when the listener has already moved to another episode, and re-rendering
   * because it changed would be pointless. Without it, opening episode 3 while
   * episode 2's transcript is still in flight shows episode 2's words against
   * episode 3's audio — which is worse than showing none.
   */
  const cuesFor = useRef<string | null>(null);

  /**
   * Which book the notes in state belong to — the same guard, same reason.
   *
   * Two books can be in play in one session: one being read, one being heard.
   * A response that arrives after the listener has moved to another work would
   * otherwise put that work's count on this work's button.
   */
  const notesFor = useRef<string | null>(null);

  /** Re-read the playing book's notes. Used after a note is kept or removed. */
  const reloadNotes = useCallback(() => {
    const slug = current?.slug ?? null;
    if (slug === null) return;
    notesFor.current = slug;
    void fetchMarks(slug).then((marks) => {
      if (notesFor.current !== slug) return;
      setNotes(marks?.episodeNotes ?? []);
    });
  }, [current]);

  /**
   * The stored listening speed, applied once the client is running.
   *
   * In an effect rather than in `useState(loadRate())` because the server has no
   * localStorage: seeding the initial state from it would make the first client
   * render differ from the server's, which is the hydration mismatch every other
   * stored setting on this site avoids the same way.
   *
   * It sets the element too, not only the state. `play` re-applies it on each
   * new source below — a fresh `<audio>` src resets `playbackRate` to 1 — but
   * that runs on the NEXT episode, and something already playing when this
   * mounts would otherwise keep the default while the buttons showed 1.5x.
   */
  useEffect(() => {
    const stored = loadRate();
    if (stored === 1) return;
    setRateState(stored);
    const element = audio.current;
    if (element !== null) element.playbackRate = stored;
  }, []);

  const play = useCallback(
    (episode: NowPlaying) => {
      const element = audio.current;
      if (element === null) return;

      if (current?.src === episode.src) {
        void element.play();
        return;
      }

      setCurrent(episode);
      element.src = episode.src;
      // Setting a new source resets `playbackRate` to 1. Without this, choosing
      // 1.5x and then playing the next episode silently dropped back to normal
      // speed while the control still showed 1.5x.
      element.playbackRate = rate;

      // The words, loaded alongside the audio rather than when the panel opens.
      // Cleared FIRST so the panel never shows the previous episode's transcript
      // while this one arrives.
      setCues(null);
      cuesFor.current = episode.src;
      if (episode.transcriptSrc !== null) {
        const wanted = episode.src;
        void fetch(episode.transcriptSrc)
          .then((response) =>
            response.ok ? response.text() : Promise.reject(new Error("not ok")),
          )
          .then((text) => {
            if (cuesFor.current !== wanted) return; // they moved on; this is stale
            setCues(parseVtt(text));
          })
          .catch(() => {
            // No transcript to show. The panel says so; playback is unaffected,
            // and a failed side-fetch must not surface as an unhandled rejection
            // in the listener's console mid-episode.
          });
      }

      // Start from the cache immediately — playback must not wait on a request.
      const cached =
        loadPositions()[positionKey(episode.slug, episode.number)] ?? 0;
      element.currentTime = cached;
      void element.play();

      // Then ask the server ONCE, for both halves of what it knows: how far other
      // devices got, and what this listener has kept in this book. The notes are
      // what the Notes button counts, which is why they are read now rather than
      // when the panel opens — a count that only appears after you look is not a
      // count.
      setNotes([]);
      notesFor.current = episode.slug;
      void fetchMarks(episode.slug).then((marks) => {
        if (notesFor.current === episode.slug)
          setNotes(marks?.episodeNotes ?? []);

        // Jump forward only if another device got further, and only if the
        // listener has not moved in the meantime: seeking under someone who has
        // already scrubbed would be the player fighting them.
        const remote = positionIn(marks, episode.number);
        if (remote === null || remote <= cached + 5) return;
        if (audio.current === null || audio.current.src !== element.src) return;
        if (Math.abs(audio.current.currentTime - cached) > 5) return;
        audio.current.currentTime = remote;
      });
      // `rate` is a dependency because the new source is started at it. Without it
      // this closure keeps whichever rate was current when it was last built, and
      // a speed chosen mid-episode would not survive to the next one.
    },
    [current, rate],
  );

  const toggle = useCallback(() => {
    const element = audio.current;
    if (element === null || current === null) return;
    if (element.paused) void element.play();
    else element.pause();
  }, [current]);

  const seek = useCallback((seconds: number) => {
    const element = audio.current;
    if (element !== null) element.currentTime = seconds;
  }, []);

  const nudge = useCallback((delta: number) => {
    const element = audio.current;
    if (element === null) return;
    element.currentTime = Math.max(
      0,
      Math.min(element.duration || 0, element.currentTime + delta),
    );
  }, []);

  const setRate = useCallback((next: number) => {
    const element = audio.current;
    if (element !== null) element.playbackRate = next;
    setRateState(next);
    try {
      localStorage.setItem(RATE_KEY, String(next));
    } catch {
      // Storage disabled. The rate still applies to this session.
    }
  }, []);

  const close = useCallback(() => {
    const element = audio.current;
    if (element !== null) {
      element.pause();
      element.removeAttribute("src");
      element.load();
    }
    setCurrent(null);
    setPlaying(false);
    // The panel belongs to what is playing. Left open over a closed player it
    // would be a transcript of nothing, with no control on screen to shut it.
    setPanel(null);
    setCues(null);
    cuesFor.current = null;
    setNotes([]);
    notesFor.current = null;
  }, []);

  /** Pressing the open panel's own button closes it, which is what a toggle is. */
  const openPanel = useCallback(
    (next: PlayerPanel) => setPanel((now) => (now === next ? null : next)),
    [],
  );

  /**
   * Hand the episode to the phone itself.
   *
   * Everything below the lock screen — the Control Centre card, the AirPods
   * stem, the car head unit, the watch — reads one browser API, and this site
   * never called it, so with the screen off a listener had a nameless audio
   * stream and no way to skip within it. The hardware's own back/forward map to
   * the SAME fifteen seconds the bar's buttons use rather than to next/previous
   * track: there is no queue here, so a track control would be a control that
   * does nothing, and fifteen seconds is what those buttons mean in every
   * podcast app anyway.
   *
   * Artwork is the site's mark. Books have no cover images in this repo — a
   * per-book image would have to be invented, and inventing one is worse than
   * showing whose library this is.
   *
   * Feature-detected, not assumed: Firefox and older Safari have parts of this,
   * and `setPositionState` throws outright if the numbers it is handed are not
   * self-consistent (a position past the duration, a rate of zero), which is
   * reachable in the moment between a new src and its first `durationchange`.
   */
  useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator))
      return;
    const session = navigator.mediaSession;

    if (current === null) {
      session.metadata = null;
      session.playbackState = "none";
      return;
    }

    session.metadata = new MediaMetadata({
      title: `${current.number}. ${current.title}`,
      artist: current.bookTitle,
      album: "The Podcast Factory Library",
      artwork: [
        { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png" },
      ],
    });
    session.playbackState = playing ? "playing" : "paused";

    const handlers: [MediaSessionAction, MediaSessionActionHandler][] = [
      ["play", () => toggle()],
      ["pause", () => toggle()],
      ["seekbackward", () => nudge(-15)],
      ["seekforward", () => nudge(15)],
      [
        "seekto",
        (details) => {
          if (typeof details.seekTime === "number") seek(details.seekTime);
        },
      ],
    ];

    for (const [action, handler] of handlers) {
      // Not every platform implements every action, and setting an unsupported
      // one throws rather than being ignored.
      try {
        session.setActionHandler(action, handler);
      } catch {
        /* unsupported here; the rest still work */
      }
    }

    return () => {
      for (const [action] of handlers) {
        try {
          session.setActionHandler(action, null);
        } catch {
          /* as above */
        }
      }
    };
  }, [current, playing, toggle, nudge, seek]);

  /* Where the scrubber on the lock screen sits. Separate from the effect above
     so a moving position does not tear down and rebuild every action handler
     four times a second. */
  useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator))
      return;
    if (typeof navigator.mediaSession.setPositionState !== "function") return;
    if (current === null || !Number.isFinite(duration) || duration <= 0) return;
    try {
      navigator.mediaSession.setPositionState({
        duration,
        playbackRate: rate,
        position: Math.min(Math.max(0, position), duration),
      });
    } catch {
      /* The numbers were momentarily inconsistent; the next tick corrects it. */
    }
  }, [current, position, duration, rate]);

  const value = useMemo<PlayerState>(
    () => ({
      current,
      playing,
      position,
      duration,
      rate,
      cues,
      notes,
      reloadNotes,
      panel,
      openPanel,
      expanded,
      setExpanded,
      play,
      toggle,
      seek,
      nudge,
      setRate,
      close,
    }),
    [
      current,
      playing,
      position,
      duration,
      rate,
      cues,
      notes,
      reloadNotes,
      panel,
      openPanel,
      expanded,
      setExpanded,
      play,
      toggle,
      seek,
      nudge,
      setRate,
      close,
    ],
  );

  return (
    <PlayerContext.Provider value={value}>
      {children}

      <audio
        ref={audio}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onDurationChange={(e) => setDuration(e.currentTarget.duration || 0)}
        onTimeUpdate={(e) => {
          setPosition(e.currentTarget.currentTime);
          if (
            current !== null &&
            Math.floor(e.currentTarget.currentTime) % 5 === 0
          ) {
            savePosition(current, e.currentTarget.currentTime);
          }
        }}
      />

      {current === null ? null : (
        <>
          <PlayerPanelDrawer />
          <PlayerBar />
        </>
      )}
    </PlayerContext.Provider>
  );
}

export function usePlayer(): PlayerState {
  const value = useContext(PlayerContext);
  if (value === null)
    throw new Error("usePlayer must be used inside PlayerProvider");
  return value;
}

/** mm:ss, or —:— when the duration is not known yet. */
export function clock(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "--:--";
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * The transport bar, in three groups rather than one row of eight controls.
 *
 * It was one flex row, and at a phone's width that row could not hold what was
 * in it — so the fix taken at the time was to HIDE the two skip buttons below
 * 640px. The result was that the two controls a listener reaches for most were
 * absent on the device almost all the listening happens on (Asif, 2026-08-06).
 * Un-hiding them alone would only restore the overflow that caused it.
 *
 * So the markup is now three named groups — what is playing, the transport, the
 * panels — and the breakpoint re-flows the groups instead of deleting controls
 * from them. On a phone the title takes its own line and the transport sits
 * below it as three round 44px targets; from 640px up the groups sit in one row
 * as before. Nothing is hidden at any width any more except the speed menu,
 * which is a preference rather than a transport control and which the browser's
 * own long-press menu can still reach.
 */
function PlayerBar() {
  const {
    current,
    playing,
    position,
    duration,
    rate,
    notes,
    panel,
    openPanel,
    expanded,
    setExpanded,
    toggle,
    seek,
    nudge,
    setRate,
    close,
  } = usePlayer();
  const bar = useRef<HTMLDivElement>(null);

  /**
   * Publish this bar's real height, for the panel that stops on top of it.
   *
   * The side panel used to end at `calc(var(--pf-space-3) * 2 + 4.5rem)` — the
   * bar's height, worked out by hand from the space scale. That number was
   * already a liability and this change would have falsified it outright: a
   * two-row bar on a phone would have had a third of the drawer hidden behind
   * it, and the transcript's own centring (which measures the bar live) would
   * have been centring lines into a strip nobody can see. Measured, so the
   * question cannot be got wrong again — including the safe-area inset, which
   * differs per device and could never have been in a constant.
   */
  useEffect(() => {
    const element = bar.current;
    if (element === null || typeof ResizeObserver === "undefined") return;
    const publish = () =>
      document.documentElement.style.setProperty(
        "--pf-player-h",
        `${element.offsetHeight}px`,
      );
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(element);
    return () => {
      observer.disconnect();
      document.documentElement.style.removeProperty("--pf-player-h");
    };
  }, []);

  if (current === null) return null;

  const total = duration || current.durationS || 0;
  /* THIS episode's, matching what the panel shows when it opens. A count of the
     whole book's notes on a button that opens one episode's would be a number
     the panel then contradicts. */
  const here = notes.filter((n) => n.number === current.number).length;

  return (
    <div
      ref={bar}
      role="region"
      aria-label="Now playing"
      className="pf-player"
      data-collection={current.collection}
      /* ONE attribute, and everything about the full-screen player follows from
         it in CSS. There is no second component: the expanded view is this bar
         re-laid-out, so the transport, the scrubber and the panels are the same
         elements and cannot disagree with a compact copy of themselves. */
      data-expanded={expanded ? "true" : undefined}
    >
      <div className="pf-player__inner">
        {/* The artwork, which only the expanded player draws. Generated from the
            accent exactly as the deck's track tiles are — these recordings have
            no cover art to show and never will. */}
        <div className="pf-player__art" aria-hidden="true">
          {String(current.number).padStart(2, "0")}
        </div>

        <div className="pf-player__top">
          <div className="pf-player__what">
            {/* Tapping what is playing is how every phone player opens its full
                screen. It is a BUTTON on a phone and inert above that width —
                `pointer-events` in the stylesheet — because on a desktop there
                is nothing to expand into. */}
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="pf-player__grow"
              aria-label={`Open the player for ${current.title}`}
            >
              <p className="pf-player__title">
                {current.number}. {current.title}
              </p>
            </button>
            <Link to={`/book/${current.slug}`} className="pf-player__book">
              {current.bookTitle}
            </Link>
          </div>

          {/* Play, and the fifteen seconds either side of it. One group, always
              together, present at every width — a listener who has missed a
              sentence reaches for the same place whatever they are holding. */}
          <div className="pf-player__transport">
            <button
              type="button"
              onClick={() => nudge(-15)}
              aria-label="Back 15 seconds"
              className="pf-player__nudge"
            >
              {/* The glyph carries the direction and the numeral the amount,
                  which is the idiom every podcast app uses — and it fits a
                  round tap target where "−15s" as text did not. */}
              <Icon icon={faRotateLeft} />
              <span className="pf-player__nudge-n" aria-hidden="true">
                15
              </span>
            </button>

            <button
              type="button"
              onClick={toggle}
              aria-label={playing ? "Pause" : "Play"}
              className="pf-player__play"
            >
              {playing ? <PauseIcon /> : <PlayIcon />}
            </button>

            <button
              type="button"
              onClick={() => nudge(15)}
              aria-label="Forward 15 seconds"
              className="pf-player__nudge"
            >
              <Icon icon={faRotateRight} />
              <span className="pf-player__nudge-n" aria-hidden="true">
                15
              </span>
            </button>
          </div>

          <div className="pf-player__panels">
            <label className="pf-player__rate">
              <span className="sr-only">Playback speed</span>
              <select
                value={rate}
                onChange={(e) => setRate(Number(e.target.value))}
                className="pf-select pf-select--sm"
              >
                {RATES.map((r) => (
                  <option key={r} value={r}>
                    {r}&times;
                  </option>
                ))}
              </select>
            </label>

            {current.transcriptSrc === null ? null : (
              <button
                type="button"
                onClick={() => openPanel("transcript")}
                aria-expanded={panel === "transcript"}
                className="pf-player__panel-tab"
              >
                Transcript
              </button>
            )}

            <button
              type="button"
              onClick={() => openPanel("notes")}
              aria-expanded={panel === "notes"}
              /* The count is in the accessible name, not only in the badge —
                 a screen reader gets "Notes, 2 in this episode" rather than a
                 button called "Notes 2", which is read as a label ending in a
                 stray number. */
              aria-label={
                here === 0 ? "Notes" : `Notes, ${here} in this episode`
              }
              className="pf-player__panel-tab"
            >
              <span aria-hidden="true">Notes</span>
              {/* Never rendered as zero. An empty count reads as something to
                  clear rather than something not yet started — the same rule
                  the reader's own tab follows. */}
              {here === 0 ? null : (
                <span aria-hidden="true" className="pf-player__badge">
                  {here}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={close}
              aria-label="Close the player"
              className="pf-player__close"
            >
              &times;
            </button>

            {/* Collapse. Drawn only while expanded — see the stylesheet — so it
                is never a control on a bar that has nothing to collapse. */}
            <button
              type="button"
              onClick={() => setExpanded(false)}
              aria-label="Shrink the player"
              className="pf-player__shrink"
            >
              <Icon icon={faChevronDown} />
            </button>
          </div>
        </div>

        <div className="pf-player__scrub">
          <span>{clock(position)}</span>
          <input
            type="range"
            min={0}
            max={Math.max(1, total)}
            step={1}
            value={Math.min(position, total || 1)}
            onChange={(e) => seek(Number(e.target.value))}
            aria-label="Seek"
            className="pf-player__seek"
            /* How much has been played, as a scalar the stylesheet paints the
               track from — the same arrangement `.pf-meter` uses. The browser's
               own `accent-color` fill was not usable here: it leaves the
               UNPLAYED remainder to whatever the platform derives, which on a
               navy deck came out near-black. */
            style={
              {
                "--pf-seek": total > 0 ? Math.min(position, total) / total : 0,
              } as CSSProperties
            }
          />
          <span>{clock(total || null)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * The player's own side panel: what is being said, or what you have marked.
 *
 * It belongs to the PLAYER rather than to any page, for the same reason the
 * <audio> element does — playback outlives navigation, so the transcript of what
 * is playing has to be reachable from wherever the listener happens to be. A
 * transcript that lives on one page is a transcript you have to go and find,
 * which is exactly the failure this replaces.
 *
 * It has no edge tab. The two buttons in the bar are its openers, so no page
 * grows a second tab beside its own, and it is closed until asked for.
 *
 * It is scoped to the PLAYING book, which is not always the book on screen — a
 * chapter of one work can be open while another work's episode plays. So the
 * notes here are fetched for `current.slug` rather than read from the marks
 * store, which holds whichever book is being READ. Same reason the position
 * write posts directly.
 */
function PlayerPanelDrawer() {
  const {
    current,
    panel,
    openPanel,
    cues,
    position,
    seek,
    notes,
    reloadNotes,
  } = usePlayer();
  // The "+ Add note" composer. `composeSeconds` is frozen at the moment the
  // button is pressed, not read again at save time — typing takes a while and
  // playback keeps advancing, so a live read would land the note on whatever
  // second the listener finished typing at, not the one they meant to mark.
  const [composing, setComposing] = useState(false);
  const [composeSeconds, setComposeSeconds] = useState(0);
  const [composeQuote, setComposeQuote] = useState("");
  /* Which panel sent us to the composer. Closing a note started from a
     transcript line returns you to the transcript, because that is where you
     were listening and where the next line you want to mark is (Asif,
     2026-08-06). A note started from the Notes panel's own button has nowhere
     to go back to, so it stays — which is why this records the origin rather
     than always returning. */
  const [composeFrom, setComposeFrom] = useState<PlayerPanel>(null);

  /** Leave the composer, and go back where it was opened from. */
  const closeCompose = useCallback(() => {
    setComposing(false);
    setComposeQuote("");
    if (composeFrom === "transcript") openPanel("transcript");
    setComposeFrom(null);
  }, [composeFrom, openPanel]);
  const [composeDraft, setComposeDraft] = useState("");

  /* The notes come from the PLAYER now, not from a fetch of this panel's own —
     they arrive with the episode so the bar's badge can count them before
     anyone opens this. Still re-read on open, because another device may have
     added one since playback started; the difference is that this is a refresh
     of something already on screen rather than the only way to see it. */
  const reload = reloadNotes;

  useEffect(() => {
    if (panel === "notes") reload();
    else setComposing(false);
  }, [panel, reload]);

  if (current === null || panel === null) return null;

  /* THIS EPISODE's notes, not the whole book's.
     The panel belongs to what is playing, exactly as the transcript does — and
     it is also the only honest scope available here: the marks endpoint returns
     notes with an episode NUMBER, and rendering the ones from other episodes
     would need their titles, which nothing on this side has. Showing them as
     bare numbers, or silently dropping them, are both worse than a panel that
     says plainly what it covers. The whole book's notes are one press away on
     the book page, which has the titles. */
  const here = notes.filter((n) => n.number === current.number);
  const label = panel === "transcript" ? "Transcript" : "Notes in this episode";

  return (
    <>
      {/* Below the player bar in the stack, so the transport stays usable with
          the panel open — pausing while reading along must not mean closing it
          first. */}
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        onClick={() => openPanel(null)}
        className="pf-player-panel__scrim"
      />

      <aside
        aria-label={`${label} for ${current.title}`}
        className="pf-player-panel"
      >
        <div className="pf-drawer__head">
          <h2 className="pf-drawer__title">{label}</h2>
          <button
            type="button"
            onClick={() => openPanel(null)}
            aria-label={`Close ${label.toLowerCase()}`}
            className="pf-tool"
          >
            &times;
          </button>
        </div>

        <div className="pf-drawer__body">
          {panel === "transcript" ? (
            <Transcript
              cues={cues}
              position={position}
              onSeek={seek}
              onNote={(cue) => {
                // Opens the same composer the "+ Add note" button does, on
                // the Notes panel — rather than saving a bare, textless mark
                // on tap. A transcript line's "+" is the one place this
                // composer arrives pre-filled with WHICH line, so the quote
                // travels with it; the timestamp and blank draft otherwise
                // work exactly as the generic composer's do.
                setComposeSeconds(Math.floor(cue.startS));
                setComposeQuote(cue.text);
                setComposeDraft("");
                setComposeFrom("transcript");
                setComposing(true);
                openPanel("notes");
              }}
            />
          ) : (
            <>
              {/* Not inside the Transcript panel, and not gated on one
                  existing — the Transcript tab button itself is hidden for an
                  episode with no transcript, so this is the only marking
                  control those episodes have at all. */}
              {composing ? (
                <div className="pf-mark pf-mark--moment">
                  <div className="pf-mark__body">
                    <span className="pf-mark__kind">
                      {clock(composeSeconds)}
                    </span>
                    {/* Only present when opened from a transcript line's "+" —
                        the generic "+ Add note" button has no line to quote. */}
                    {composeQuote ? (
                      <blockquote className="pf-mark__quote">
                        {composeQuote}
                      </blockquote>
                    ) : null}
                    <RichNoteEditor
                      initialValue={composeDraft}
                      onChange={setComposeDraft}
                      placeholder="What are you thinking?"
                      autoFocus
                      ariaLabel="Your note at this moment"
                    />
                    <div className="pf-mark__edit-actions">
                      <button
                        type="button"
                        onClick={closeCompose}
                        className="pf-button pf-button--sm pf-button--ghost"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          void markMoment(
                            current,
                            composeSeconds,
                            newId(),
                            composeQuote,
                            composeDraft,
                          ).then((ok) => {
                            // Same return as Cancel: saved or abandoned, you
                            // came from the transcript and that is where the
                            // next line you want to mark is.
                            closeCompose();
                            if (!ok) return;
                            void refresh(current.slug);
                            reload();
                          });
                        }}
                        className="pf-button pf-button--sm pf-button--primary"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setComposeSeconds(Math.floor(position));
                    setComposeQuote("");
                    setComposeDraft("");
                    setComposeFrom(null);
                    setComposing(true);
                  }}
                  className="pf-button pf-button--primary pf-notes__add"
                >
                  <Icon icon={faPlus} /> Add note at {clock(position)}
                </button>
              )}

              <NotesList
                annotations={[]}
                bookmarks={[]}
                chapters={[]}
                episodes={[{ number: current.number, title: current.title }]}
                episodeNotes={here}
                orphaned={NOTHING_ORPHANED}
                slug={current.slug}
                onPlay={(_number, seconds) => seek(seconds)}
                onRemoveAnnotation={NOTHING}
                onRemoveBookmark={NOTHING}
                onRemoveEpisodeNote={(id) => {
                  void fetch(
                    `/book/${encodeURIComponent(current.slug)}/marks`,
                    {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                      },
                      body: new URLSearchParams({
                        intent: "un-episode-note",
                        id,
                      }),
                    },
                  )
                    .then(() => {
                      void refresh(current.slug);
                      reload();
                    })
                    .catch(() => {});
                }}
                onEditEpisodeNote={(id, note) => {
                  const existing = here.find((n) => n.id === id);
                  if (existing === undefined) return;
                  void markMoment(
                    current,
                    existing.seconds,
                    id,
                    existing.quote ?? "",
                    note,
                  ).then((ok) => {
                    if (!ok) return;
                    void refresh(current.slug);
                    reload();
                  });
                }}
              />
            </>
          )}
        </div>
      </aside>
    </>
  );
}

const NOTHING_ORPHANED: ReadonlySet<string> = new Set<string>();
const NOTHING = () => {};

function PlayIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      fill="currentColor"
    >
      <path d="M8 5.5v13l11-6.5z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      fill="currentColor"
    >
      <path d="M7 5h3.5v14H7zm6.5 0H17v14h-3.5z" />
    </svg>
  );
}
