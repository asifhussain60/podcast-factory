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

const POSITION_KEY = "pf-positions";

/** Where the reader had got to in each episode, by media key. */
function loadPositions(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(POSITION_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePosition(src: string, seconds: number) {
  try {
    const all = loadPositions();
    all[src] = Math.floor(seconds);
    localStorage.setItem(POSITION_KEY, JSON.stringify(all));
  } catch {
    // Storage disabled. Playback still works; only the memory of it is lost.
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
    element.currentTime = loadPositions()[episode.src] ?? 0;
    void element.play();
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
            savePosition(current.src, e.currentTarget.currentTime);
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
