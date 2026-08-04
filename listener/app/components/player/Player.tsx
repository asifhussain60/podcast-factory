import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Link } from "react-router";

import { newId, refresh } from "~/lib/marks";

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
}

interface PlayerState {
  current: NowPlaying | null;
  playing: boolean;
  /** Seconds. Driven by the element, not by us. */
  position: number;
  duration: number;
  rate: number;
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
 * Mark this moment in whatever is playing, from anywhere on the site.
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
function markMoment(episode: NowPlaying, seconds: number, id: string): Promise<boolean> {
  return fetch(`/book/${encodeURIComponent(episode.slug)}/marks`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      intent: "episode-note",
      id,
      number: String(episode.number),
      // Floor, not round: the stored value is when the button was pressed, and
      // the site plays back from before it anyway.
      seconds: String(Math.floor(seconds)),
      note: "",
      quote: "",
    }),
  })
    .then((response) => response.ok)
    .catch(() => false);
}

/**
 * The server's copy, if it is further along than the cache.
 *
 * "Further along" rather than "newer": there is no clock to trust between two
 * devices, and the failure that actually matters is resuming EARLIER than you
 * got to — re-listening to ten minutes you have already heard. Taking the
 * greater of the two can only ever skip ahead by however far the other device
 * went, which is the direction a listener can correct in one gesture.
 */
async function serverPosition(slug: string, number: number): Promise<number | null> {
  try {
    const response = await fetch(`/book/${encodeURIComponent(slug)}/marks`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const marks = (await response.json()) as { listening?: Record<string, number> };
    return marks.listening?.[String(number)] ?? null;
  } catch {
    return null;
  }
}

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [current, setCurrent] = useState<NowPlaying | null>(null);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [rate, setRateState] = useState(1);

  const play = useCallback((episode: NowPlaying) => {
    const element = audio.current;
    if (element === null) return;

    if (current?.src === episode.src) {
      void element.play();
      return;
    }

    setCurrent(episode);
    element.src = episode.src;

    // Start from the cache immediately — playback must not wait on a request.
    const cached = loadPositions()[positionKey(episode.slug, episode.number)] ?? 0;
    element.currentTime = cached;
    void element.play();

    // Then ask the server, and jump forward only if another device got further.
    // Guarded on the listener not having moved in the meantime: seeking under
    // someone who has already scrubbed would be the player fighting them.
    void serverPosition(episode.slug, episode.number).then((remote) => {
      if (remote === null || remote <= cached + 5) return;
      if (audio.current === null || audio.current.src !== element.src) return;
      if (Math.abs(audio.current.currentTime - cached) > 5) return;
      audio.current.currentTime = remote;
    });
  }, [current]);

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
    element.currentTime = Math.max(0, Math.min(element.duration || 0, element.currentTime + delta));
  }, []);

  const setRate = useCallback((next: number) => {
    const element = audio.current;
    if (element !== null) element.playbackRate = next;
    setRateState(next);
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
  }, []);

  const value = useMemo<PlayerState>(
    () => ({ current, playing, position, duration, rate, play, toggle, seek, nudge, setRate, close }),
    [current, playing, position, duration, rate, play, toggle, seek, nudge, setRate, close],
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
          if (current !== null && Math.floor(e.currentTarget.currentTime) % 5 === 0) {
            savePosition(current, e.currentTarget.currentTime);
          }
        }}
      />

      {current === null ? null : <PlayerBar />}
    </PlayerContext.Provider>
  );
}

export function usePlayer(): PlayerState {
  const value = useContext(PlayerContext);
  if (value === null) throw new Error("usePlayer must be used inside PlayerProvider");
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

function PlayerBar() {
  const { current, playing, position, duration, rate, toggle, seek, nudge, setRate, close } =
    usePlayer();
  if (current === null) return null;

  const total = duration || current.durationS || 0;

  return (
    <div
      role="region"
      aria-label="Now playing"
      className="pf-player"
    >
      <div className="pf-player__inner">
        <div className="pf-player__top">
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
            onClick={() => nudge(-15)}
            aria-label="Back 15 seconds"
            className="pf-player__nudge"
          >
            &minus;15s
          </button>
          <button
            type="button"
            onClick={() => nudge(15)}
            aria-label="Forward 15 seconds"
            className="pf-player__nudge"
          >
            +15s
          </button>

          <div className="pf-player__what">
            <p className="pf-player__title">
              {current.number}. {current.title}
            </p>
            <Link
              to={`/book/${current.slug}`}
              className="pf-player__book"
            >
              {current.bookTitle}
            </Link>
          </div>

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

          <MarkButton />

          <button
            type="button"
            onClick={close}
            aria-label="Close the player"
            className="pf-player__close"
          >
            &times;
          </button>
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
          />
          <span>{clock(total || null)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * One tap to mark where you are, wherever you are on the site.
 *
 * This is the eyes-free half of listening notes. The transcript on the episode
 * page lets a moment be marked with the words attached, but most listening
 * happens with the phone face-down — and the player bar is the only thing on
 * screen for all of it, because it lives in the layout and survives navigation.
 *
 * It captures the position at the instant of the TAP and posts immediately, so
 * nothing depends on how long the listener then takes to do anything else. The
 * words come later, in the notes list.
 *
 * The confirmation is the whole feedback loop: a note made with no visible
 * response is indistinguishable from a button that does nothing, which is
 * exactly the failure the delete button had.
 */
function MarkButton() {
  const { current, position } = usePlayer();
  const [state, setState] = useState<"idle" | "saved" | "failed">("idle");

  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), 2_000);
    return () => clearTimeout(timer);
  }, [state]);

  if (current === null) return null;

  return (
    <button
      type="button"
      onClick={() => {
        // Read here, at the tap, and passed down. Reading it inside the promise
        // would record wherever the audio had reached by the time it resolved.
        const at = position;
        void markMoment(current, at, newId()).then((ok) => {
          setState(ok ? "saved" : "failed");
          // A notes drawer standing open on THIS book has to learn about it —
          // the write bypassed the store that feeds it. No-op when the open book
          // is a different one, which is the case this write exists to handle.
          if (ok) void refresh(current.slug);
        });
      }}
      aria-label={`Mark this moment, ${Math.floor(position / 60)} minutes in`}
      title="Mark this moment"
      className="pf-player__mark"
    >
      {state === "idle" ? "Mark" : state === "saved" ? "Marked" : "Not saved"}
    </button>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor">
      <path d="M8 5.5v13l11-6.5z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor">
      <path d="M7 5h3.5v14H7zm6.5 0H17v14h-3.5z" />
    </svg>
  );
}
