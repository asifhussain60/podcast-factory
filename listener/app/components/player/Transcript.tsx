import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { useEffect, useMemo, useRef, useState } from "react";

import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { count } from "~/lib/plural";

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
  cues,
  position,
  onSeek,
  onNote,
}: {
  /**
   * The words, already loaded by the player. Null means none — either this
   * episode has no transcript or it has not arrived, and the reader can act on
   * neither, so both say the same thing.
   *
   * Passed in rather than fetched here on purpose: the player holds the cues
   * from the moment playback starts, which is what makes opening this panel
   * mid-episode instant and lets the sync "follow silently" without this
   * component being mounted at all.
   */
  cues: Cue[] | null;
  /** Where the audio is, in seconds. */
  position: number;
  onSeek: (seconds: number) => void;
  /** Keep this moment, carrying the line as it read. */
  onNote?: (cue: Cue) => void;
}) {
  const [follow, setFollow] = useState(true);
  const list = useRef<HTMLOListElement>(null);
  /** The element that actually scrolls: the drawer body this list sits in. */
  const scroller = useRef<HTMLElement | null>(null);
  /** True while OUR scroll is in flight, so the guard below ignores it. */
  const programmatic = useRef(false);
  const settle = useRef(0);

  useEffect(() => {
    scroller.current = list.current?.closest<HTMLElement>(".pf-drawer__body") ?? null;
  }, [cues]);

  const at = useMemo(() => (cues === null ? -1 : cueAt(cues, position)), [cues, position]);

  /* Keep the spoken line in the middle of what the reader can SEE.
     Someone reading ahead to find a passage must not be dragged back every
     quarter second; the control below is how they hand following back.

     Scrolls the container EXPLICITLY rather than calling `scrollIntoView`
     (Asif, 2026-08-06 — the line was not centring on a phone). Two reasons
     scrollIntoView could not do this job here. It centres the line in its
     nearest scrolling ancestor's BOX, and this drawer is `inset-block: 0` —
     full viewport height, with its lower strip sitting behind the player bar.
     Its box centre is therefore below the centre of the visible area, so the
     spoken line lands low and, near the end of a long panel, off screen
     entirely. And it gives no way to tell its own scrolling apart from the
     reader's, which is what the guard below needs.

     Not conditioned on `playing`: opening this panel on a PAUSED episode should
     still land on the line where the audio stands, which is the whole point of
     the words being loaded before the panel is asked for. */
  useEffect(() => {
    if (!follow || at < 0) return;
    const line = list.current?.querySelector<HTMLElement>(`[data-cue="${at}"]`);
    const box = scroller.current;
    if (!line || !box) return;

    // The strip of `box` the player bar covers. Measured rather than assumed:
    // the bar's height changes with its own content and with the platform's
    // safe-area inset, and a hardcoded number would be wrong on most phones.
    const bar = document.querySelector<HTMLElement>(".pf-player");
    const hidden = bar === null ? 0 : Math.max(0, box.getBoundingClientRect().bottom - bar.getBoundingClientRect().top);
    const visible = Math.max(0, box.clientHeight - hidden);

    const target = line.offsetTop - box.offsetTop - visible / 2 + line.offsetHeight / 2;
    programmatic.current = true;
    box.scrollTo({ top: Math.max(0, target), behavior: "smooth" });
    // Released on a timer, not on a scroll event: a smooth scroll that is
    // already at its destination emits nothing at all, and the flag would
    // stick — leaving every later scroll of the reader's read as our own.
    window.clearTimeout(settle.current);
    settle.current = window.setTimeout(() => {
      programmatic.current = false;
    }, 700);
  }, [at, follow]);

  useEffect(() => {
    // The scroll container is the DRAWER's body, not this list — see the
    // stylesheet, which says so and gives the list no overflow of its own.
    // Listening on the list meant a scroll that never crossed it was invisible.
    const element = scroller.current;
    if (element === null) return;
    // Any deliberate scroll stops the following, EXCEPT the one we just made.
    // `wheel` and `touchmove` rather than `scroll`, because the smooth scroll
    // above fires `scroll` too and would switch itself off on its first move.
    const release = () => {
      if (programmatic.current) return;
      setFollow(false);
    };
    element.addEventListener("wheel", release, { passive: true });
    element.addEventListener("touchmove", release, { passive: true });
    return () => {
      element.removeEventListener("wheel", release);
      element.removeEventListener("touchmove", release);
    };
  }, [cues]);

  if (cues === null || cues.length === 0) {
    return <EmptyState>No transcript for this episode.</EmptyState>;
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
                // The line being spoken carries the FULL control — a filled
                // circle at the whole tap target — and every other line a small
                // quiet glyph. Size, not visibility, is what separates them:
                // the control used to be `opacity: 0` until `:hover`, which a
                // phone never fires, so on the surface it was designed for it
                // could not be reached at all (Asif, 2026-08-06). It also
                // answers what the opacity was guarding against — six hundred
                // identical plus signs down the page — since only one is ever
                // large, and it leaves with its line.
                className={`pf-cue__note ${i === at ? "pf-cue__note--now" : ""}`}
              >
                <Icon icon={faPlus} />
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
  return `${count(m, "minute")} ${count(sec, "second")}`;
}
