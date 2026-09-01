/**
 * AudioPlayer.tsx — inline audio for a book's Media tab.
 *
 * Each track is a row with a play button on the left; clicking it loads the
 * track into a sticky mini-player at the bottom and plays it in place (no
 * navigation, no download redirect). Streams via the existing /api/library/file
 * endpoint. No new dependency — native HTML5 <audio>. Classes in library.css.
 */
import { useEffect, useRef, useState } from "react";

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

function loadRate(): number {
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

export interface Track {
  label: string;
  src: string;
  meta: string;
}

export default function AudioPlayer({ tracks }: { tracks: Track[] }) {
  const [current, setCurrent] = useState<number | null>(null);
  const [rate, setRate] = useState(1);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Read after mount, never in `useState(loadRate())`: the server has no
  // localStorage, so seeding initial state from it makes the first client render
  // differ from the server's.
  useEffect(() => setRate(loadRate()), []);

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
    setRate(next);
    try {
      localStorage.setItem(RATE_KEY, String(next));
    } catch {
      // Storage disabled. The speed still applies to this session.
    }
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
