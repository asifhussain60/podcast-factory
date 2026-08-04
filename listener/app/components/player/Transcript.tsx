import { useEffect, useMemo, useRef, useState } from "react";

/**
 * What is said in an episode, following the audio.
 *
 * The cue file is WebVTT, written at publish time from the same response that
 * produced the flat transcript — one cue per phrase, median two seconds, with a
 * speaker where diarization identified one. It is FETCHED rather than loaded in
 * a loader: seventeen kilobytes per episode is nothing to ask for on demand, and
 * putting it in the document would make every episode page carry a transcript
 * the reader may never open.
 *
 * Parsing lives here rather than in a shared library because there is exactly one
 * consumer and the file is one this repo wrote. A second implementation on the
 * server would be a second answer to what a cue is.
 */

export interface Cue {
  startS: number;
  endS: number;
  text: string;
  speaker: number | null;
}

const STAMP =
  /^(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})\s+-->\s+(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})/;

const seconds = (h: string | undefined, m: string, s: string, ms: string) =>
  Number(h ?? 0) * 3600 + Number(m) * 60 + Number(s) + Number(ms) / 1000;

export function parseVtt(source: string): Cue[] {
  const cues: Cue[] = [];
  let block: string[] = [];

  const close = () => {
    const timing = block.find((line) => STAMP.test(line));
    if (timing === undefined) return;
    const m = STAMP.exec(timing);
    if (m === null) return;

    let said = block
      .slice(block.indexOf(timing) + 1)
      .join(" ")
      .trim();
    let speaker: number | null = null;
    const voice = /^<v\s+Speaker\s+(\d+)>/.exec(said);
    if (voice !== null) {
      speaker = Number(voice[1]);
      said = said.slice(voice[0].length).trim();
    }
    if (said === "") return;

    cues.push({
      startS: seconds(m[1], m[2], m[3], m[4]),
      endS: seconds(m[5], m[6], m[7], m[8]),
      text: said,
      speaker,
    });
  };

  for (const raw of source.split(/\r?\n/)) {
    const line = raw.trim();
    if (line === "") {
      close();
      block = [];
      continue;
    }
    if (line === "WEBVTT" || line.startsWith("NOTE")) continue;
    block.push(line);
  }
  close();
  return cues;
}

/**
 * Which cue is being spoken at `position`.
 *
 * A binary search, not a scan: this is called on every timeupdate — four times a
 * second — against six hundred cues in a long episode, and a linear scan there is
 * a hundred thousand comparisons a minute for an answer that changes twice.
 *
 * Between cues (a pause, the music) it returns the cue that just FINISHED rather
 * than nothing. The alternative makes the highlight blink out in every gap, which
 * reads as the transcript losing its place.
 */
export function cueAt(cues: Cue[], position: number): number {
  let low = 0;
  let high = cues.length - 1;
  let found = -1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (cues[mid].startS <= position) {
      found = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return found;
}

export function Transcript({
  src,
  position,
  playing,
  onSeek,
  onNote,
}: {
  /** The media URL of the WebVTT, already gated by the route that serves it. */
  src: string;
  /** Where the audio is, in seconds. */
  position: number;
  /** Following is only worth doing while it moves. */
  playing: boolean;
  onSeek: (seconds: number) => void;
  /** Mark this moment, carrying the line as it read. Absent while loading. */
  onNote?: (cue: Cue) => void;
}) {
  const [cues, setCues] = useState<Cue[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [follow, setFollow] = useState(true);
  const list = useRef<HTMLOListElement>(null);

  useEffect(() => {
    let live = true;
    setCues(null);
    setFailed(false);

    fetch(src)
      .then((response) => (response.ok ? response.text() : Promise.reject(new Error("not ok"))))
      .then((text) => {
        if (live) setCues(parseVtt(text));
      })
      .catch(() => {
        // Said plainly below rather than rendered as an empty list. A transcript
        // that failed to load and one that does not exist look identical to a
        // reader, and only one of them is worth trying again.
        if (live) setFailed(true);
      });

    return () => {
      live = false;
    };
  }, [src]);

  const at = useMemo(() => (cues === null ? -1 : cueAt(cues, position)), [cues, position]);

  /* Keep the spoken line on screen — but only while the audio is actually
     moving, and only while the reader has not scrolled away. Someone reading
     ahead to find a passage must not be dragged back every quarter second; the
     button below is how they hand control back. */
  useEffect(() => {
    if (!follow || !playing || at < 0) return;
    const line = list.current?.querySelector<HTMLElement>(`[data-cue="${at}"]`);
    line?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [at, follow, playing]);

  useEffect(() => {
    const element = list.current;
    if (element === null) return;
    // Any deliberate scroll stops the following. `wheel` and `touchmove` rather
    // than `scroll`, because the smooth scroll above fires `scroll` too and would
    // switch itself off on its first move.
    const release = () => setFollow(false);
    element.addEventListener("wheel", release, { passive: true });
    element.addEventListener("touchmove", release, { passive: true });
    return () => {
      element.removeEventListener("wheel", release);
      element.removeEventListener("touchmove", release);
    };
  }, [cues]);

  if (failed) {
    return <p className="pf-note">The transcript could not be loaded. Reload to try again.</p>;
  }
  if (cues === null) {
    return <p className="pf-note pf-note--quiet">Loading the transcript…</p>;
  }
  if (cues.length === 0) {
    return <p className="pf-note">No speech was recognised in this recording.</p>;
  }

  return (
    <div className="pf-transcript">
      <p className="pf-note pf-note--quiet pf-transcript__caveat">
        {/* Said once, at the top, and not repeated per line. These are machine
            transcriptions: the hosts' pronunciation of this library's Arabic is
            corrected against the book's own pronunciation record where a
            mishearing has been confirmed, and everything else is printed exactly
            as it was heard — including where that is wrong. */}
        Transcribed automatically from the recording. Names and terms may be
        imperfect.
        {follow ? null : (
          <>
            {" "}
            <button type="button" onClick={() => setFollow(true)} className="pf-link pf-link--inline">
              Follow the audio again
            </button>
          </>
        )}
      </p>

      <ol ref={list} className="pf-transcript__lines">
        {cues.map((cue, i) => (
          <li
            key={i}
            data-cue={i}
            // One flat template, no nested backtick. test/styles.test.ts reads
            // class names straight out of the markup, and its template form
            // stops at the first backtick — a `${…}` holding another template
            // makes every class in this element look like dead CSS.
            className={`pf-cue ${i === at ? "pf-cue--now" : ""} ${
              cue.speaker === null ? "" : "pf-cue--speaker-" + cue.speaker
            }`}
          >
            <button
              type="button"
              onClick={() => onSeek(cue.startS)}
              className="pf-cue__body"
              // The time is the accessible name as well as the visible stamp:
              // "play from 4 minutes 12" is what the control does, and the line
              // itself is read out by the text inside it.
              aria-label={`Play from ${spoken(cue.startS)}`}
            >
              <span className="pf-cue__at" aria-hidden="true">
                {clock(cue.startS)}
              </span>
              <span className="pf-cue__text">{cue.text}</span>
            </button>

            {onNote === undefined ? null : (
              <button
                type="button"
                onClick={() => onNote(cue)}
                aria-label={`Make a note at ${spoken(cue.startS)}`}
                className="pf-cue__note"
              >
                +
              </button>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

/** `m:ss`, matching the player's own clock. */
function clock(s: number): string {
  const total = Math.max(0, Math.floor(s));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const sec = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
    : `${m}:${String(sec).padStart(2, "0")}`;
}

/** The same instant in words, for a screen reader — "4:12" is read as a date. */
function spoken(s: number): string {
  const total = Math.max(0, Math.floor(s));
  const m = Math.floor(total / 60);
  const sec = total % 60;
  return `${m} minute${m === 1 ? "" : "s"} ${sec} second${sec === 1 ? "" : "s"}`;
}
