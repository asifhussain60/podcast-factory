/**
 * AudioPlayer.tsx — inline audio for a book's Media tab.
 *
 * Each track is a row with a play button on the left; clicking it loads the
 * track into a sticky mini-player at the bottom and plays it in place (no
 * navigation, no download redirect). Streams via the existing /api/library/file
 * endpoint. No new dependency — native HTML5 <audio>. Classes in library.css.
 */
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

/**
 * The listening speeds, matching the Podcast Factory Library exactly (Asif,
 * 2026-09-01: "I want the same speeds as on the Podcast-factory Library").
 *
 * Copied rather than imported: this is the Astro Site and that is the Worker
 * app, and the Library imports nothing from here at runtime by design. The
 * copy is pinned instead — `AudioPlayer.test.ts` reads
 * `listener/app/lib/playback-rate.ts` off disk and fails when the two lists
 * disagree, so "the same speeds" is a thing a test enforces rather than a thing
 * somebody remembers.
 */
const RATES = [1, 1.5, 2, 2.5, 3] as const;
const RATE_KEY = "cx-audio-rate";

function readStoredRate(): number {
  try {
    const stored = Number(localStorage.getItem(RATE_KEY));
    // Validated against the list the control OFFERS, not merely against "is a
    // number": `playbackRate = 0` is a silent, unrecoverable pause, and a speed
    // between the options would select none of them and read as broken.
    return (RATES as readonly number[]).includes(stored) ? stored : 1;
  } catch {
    return 1;
  }
}

/**
 * The chosen speed, kept OUTSIDE React as a tiny external store.
 *
 * The speed has to come from localStorage, which the server does not have — so
 * seeding it with `useState(readStoredRate())` would make the first client
 * render disagree with the server's. Reading it in an effect and calling
 * setState fixed that by rendering once at 1x and immediately again at the
 * stored speed, which is the cascading re-render `react-hooks/set-state-in-effect`
 * exists to flag.
 *
 * `useSyncExternalStore` is the shape React provides for exactly this: it hands
 * the server (and the hydrating client) `serverRate`, then re-reads the real
 * value once hydration is done — no effect, no second state write, and no
 * mismatch. The value is CACHED in `rate` because a snapshot must be referentially
 * stable between changes, and caching is also what keeps the speed applying for
 * the session when storage is disabled and the write below throws.
 */
let rate: number | null = null;
const rateListeners = new Set<() => void>();

function subscribeRate(onChange: () => void): () => void {
  rateListeners.add(onChange);
  return () => rateListeners.delete(onChange);
}

function currentRate(): number {
  if (rate === null) rate = readStoredRate();
  return rate;
}

/** What the server renders, and what the client hydrates against: the default. */
function serverRate(): number {
  return 1;
}

function storeRate(next: number): void {
  rate = next;
  try {
    localStorage.setItem(RATE_KEY, String(next));
  } catch {
    // Storage disabled. The speed still applies to this session.
  }
  for (const listener of rateListeners) listener();
}

export interface Track {
  label: string;
  src: string;
  meta: string;
}

export default function AudioPlayer({ tracks }: { tracks: Track[] }) {
  const [current, setCurrent] = useState<number | null>(null);
  const rate = useSyncExternalStore(subscribeRate, currentRate, serverRate);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Re-applied whenever the element or the track changes, because setting a new
  // `src` resets `playbackRate` to 1 — without this the control would read 2x
  // while the next track played at normal speed. `preservesPitch` is what makes
  // the top of the scale usable at all; every current browser defaults it to
  // true, which has not always been so.
  useEffect(() => {
    const element = audioRef.current;
    if (element === null) return;
    element.preservesPitch = true;
    element.playbackRate = rate;
  }, [rate, current]);

  function chooseRate(next: number) {
    storeRate(next);
  }

  function play(i: number) {
    setCurrent(i);
    requestAnimationFrame(() => {
      audioRef.current?.play().catch(() => {
        /* user can press play */
      });
    });
  }

  return (
    <>
      <div className="lib-asset-list">
        {tracks.map((t, i) => (
          <div
            key={t.src}
            className={`lib-asset-row audio-row${current === i ? " is-playing" : ""}`}
          >
            <button
              type="button"
              className="audio-play-btn"
              aria-label={`${current === i ? "Now playing" : "Play"} ${t.label}`}
              aria-pressed={current === i}
              onClick={() => play(i)}
            >
              <i
                className={`fa-solid ${current === i ? "fa-volume-high" : "fa-circle-play"}`}
                aria-hidden="true"
              ></i>
            </button>
            <span className="lib-asset-name">{t.label}</span>
            <span className="lib-asset-meta">{t.meta}</span>
          </div>
        ))}
      </div>
      {current !== null && (
        <div
          className="audio-miniplayer"
          role="region"
          aria-label="Audio player"
        >
          <span className="audio-miniplayer-title">
            <i className="fa-solid fa-headphones" aria-hidden="true"></i>{" "}
            {tracks[current].label}
          </span>
          <audio
            ref={audioRef}
            src={tracks[current].src}
            controls
            autoPlay
            className="audio-miniplayer-el"
          />
          <label className="audio-miniplayer-rate">
            <span className="sr-only">Playback speed</span>
            <select
              value={rate}
              onChange={(e) => chooseRate(Number(e.target.value))}
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
            className="audio-miniplayer-close"
            aria-label="Close player"
            onClick={() => setCurrent(null)}
          >
            <i className="fa-solid fa-xmark" aria-hidden="true"></i>
          </button>
        </div>
      )}
    </>
  );
}
