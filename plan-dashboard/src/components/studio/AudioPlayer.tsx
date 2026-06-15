/**
 * AudioPlayer.tsx — inline audio for a book's Media tab.
 *
 * Each track is a row with a play button on the left; clicking it loads the
 * track into a sticky mini-player at the bottom and plays it in place (no
 * navigation, no download redirect). Streams via the existing /api/library/file
 * endpoint. No new dependency — native HTML5 <audio>. Classes in library.css.
 */
import { useRef, useState } from 'react';

export interface Track { label: string; src: string; meta: string; }

export default function AudioPlayer({ tracks }: { tracks: Track[] }) {
  const [current, setCurrent] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  function play(i: number) {
    setCurrent(i);
    requestAnimationFrame(() => { audioRef.current?.play().catch(() => { /* user can press play */ }); });
  }

  return (
    <>
      <div className="lib-asset-list">
        {tracks.map((t, i) => (
          <div key={t.src} className={`lib-asset-row audio-row${current === i ? ' is-playing' : ''}`}>
            <button
              type="button"
              className="audio-play-btn"
              aria-label={`${current === i ? 'Now playing' : 'Play'} ${t.label}`}
              aria-pressed={current === i}
              onClick={() => play(i)}
            >
              <i className={`fa-solid ${current === i ? 'fa-volume-high' : 'fa-circle-play'}`} aria-hidden="true"></i>
            </button>
            <span className="lib-asset-name">{t.label}</span>
            <span className="lib-asset-meta">{t.meta}</span>
          </div>
        ))}
      </div>
      {current !== null && (
        <div className="audio-miniplayer" role="region" aria-label="Audio player">
          <span className="audio-miniplayer-title"><i className="fa-solid fa-headphones" aria-hidden="true"></i> {tracks[current].label}</span>
          <audio ref={audioRef} src={tracks[current].src} controls autoPlay className="audio-miniplayer-el" />
          <button type="button" className="audio-miniplayer-close" aria-label="Close player" onClick={() => setCurrent(null)}>
            <i className="fa-solid fa-xmark" aria-hidden="true"></i>
          </button>
        </div>
      )}
    </>
  );
}
