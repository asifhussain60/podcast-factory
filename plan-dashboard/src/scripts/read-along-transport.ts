/**
 * read-along-transport.ts — play the recording, and keep the chapter with it.
 *
 * The Composer's half of read-along. It owns the audio element and the tick;
 * WHICH paragraph is being spoken it does not decide — that rule lives in
 * lib/reader/read-along.ts, shared with the Podcast Factory Library so the two
 * surfaces cannot disagree about the same second of the same recording.
 *
 * It draws nothing for a chapter with no timings, which is most chapters of most
 * books: a book is timed only when its recordings and transcripts are on disk.
 * Absence is the ordinary case here, not an error.
 *
 * The audio is streamed through `api/studio/read-along-audio`, which answers
 * range requests — these recordings run to 600 MB and clicking a paragraph seeks
 * into the middle of one.
 *
 * IT DRAWS AT THE FOOT OF THE WINDOW, fixed, not in the flow above the editor.
 * Asif, 2026-08-31: "I don't want this at the top because it is inaccessible
 * after the scroll." A chapter here runs twenty minutes and several screens, so
 * a transport that scrolls away is a transport you cannot reach precisely when
 * you are using it. `readAlongTargetScrollY` — shared with the Podcast Factory
 * Library, whose player has always been at the foot — already subtracts the
 * player's height from the TOP of the usable area, which is the correct sum for
 * a bottom strip and was the wrong one for this surface all along.
 */
import {
  readAlongBlockIndex,
  readAlongTargetScrollY,
  type ReadAlongCue,
} from "../lib/reader/read-along";
import {
  readAlongElement,
  setReadAlongTarget,
} from "../components/studio/editor/read-along-decos";

interface ChapterTimings {
  cues: ReadAlongCue[];
  durationS: number;
  audio: string;
  voice: string;
  engine: string;
}

export interface ReadAlongHost {
  /** Where the transport draws itself. */
  el: HTMLElement;
  slug: string;
  /** The live editor, or null while no chapter is open. */
  editor: () => {
    view: { dom: HTMLElement; dispatch: unknown; state: unknown };
  } | null;
}

/** Seconds as a reader reads a clock. Hours only once there are hours. */
export function clock(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const whole = Math.floor(seconds);
  const h = Math.floor(whole / 3600);
  const m = Math.floor((whole % 3600) / 60);
  const s = whole % 60;
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  return `${h > 0 ? `${h}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}

/** What the engine means, in words a reader of the page would use. */
export function voiceLabel(engine: string): string {
  if (engine === "author-recording") return "the speaker's own recording";
  if (engine.startsWith("azure")) return "a synthesised voice";
  return "the recording";
}

export async function fetchTimings(
  slug: string,
  chapter: string,
): Promise<ChapterTimings | null> {
  try {
    const res = await fetch(
      `/api/studio/read-along?slug=${encodeURIComponent(slug)}&chapter=${encodeURIComponent(chapter)}`,
    );
    if (!res.ok) return null;
    const body = (await res.json()) as {
      data?: ChapterTimings;
    } & ChapterTimings;
    const data = body.data ?? body;
    if (!Array.isArray(data.cues) || data.cues.length === 0) return null;
    return data;
  } catch {
    // A chapter without timings and a network that blinked look the same to the
    // page, and both mean the same thing: draw no transport.
    return null;
  }
}

export function mountReadAlong(host: ReadAlongHost) {
  const { el, slug } = host;
  let audio: HTMLAudioElement | null = null;
  let timings: ChapterTimings | null = null;
  let follow = true;
  let painted = -1;

  function paint(position: number) {
    const editor = host.editor();
    if (!editor || !timings) return;
    const index = readAlongBlockIndex(true, timings.cues, position);
    if (index === painted) return;
    painted = index;
    const cue =
      index < 0
        ? null
        : (timings.cues.find((c) => (c.blockIndex ?? -1) === index) ?? null);
    setReadAlongTarget(editor as never, {
      blockIndex: index,
      text: cue?.text ?? "",
    });
    if (!follow || index < 0) return;
    const node = readAlongElement(editor.view);
    if (!node) return;
    const rect = node.getBoundingClientRect();
    window.scrollTo({
      top: readAlongTargetScrollY({
        rect: { top: rect.top, height: rect.height },
        scrollY: window.scrollY,
        viewportHeight: window.innerHeight,
        playerHeight: el.getBoundingClientRect().height,
      }),
      behavior: "smooth",
    });
  }

  /** The page reserves room for a fixed strip; without this the last line of a
   *  chapter sits underneath it and cannot be scrolled into view. */
  function occupy(on: boolean) {
    document.body.classList.toggle("cx-has-read-along", on);
  }

  function draw() {
    el.innerHTML = "";
    if (!timings) {
      el.hidden = true;
      occupy(false);
      return;
    }
    el.hidden = false;
    occupy(true);

    const back = document.createElement("button");
    back.type = "button";
    back.className = "cx-ra-skip";
    back.textContent = "\u21ba 15";
    back.setAttribute("aria-label", "Back 15 seconds");

    const play = document.createElement("button");
    play.type = "button";
    play.className = "cx-ra-play";
    play.textContent = "Play";
    play.setAttribute("aria-label", `Play ${voiceLabel(timings.engine)}`);

    const fwd = document.createElement("button");
    fwd.type = "button";
    fwd.className = "cx-ra-skip";
    fwd.textContent = "15 \u21bb";
    fwd.setAttribute("aria-label", "Forward 15 seconds");

    const label = document.createElement("span");
    label.className = "cx-ra-label";
    label.textContent = `Follow along with ${voiceLabel(timings.engine)}`;

    // The chapter's own span of the sitting. A chapter starts minutes into a
    // long recording, so the strip reports position WITHIN THE CHAPTER — the
    // reader is reading a chapter, not auditing a two-hour file.
    const first = timings.cues[0]?.startS ?? 0;
    const last =
      timings.cues[timings.cues.length - 1]?.endS ?? timings.durationS;
    const span = Math.max(1, last - first);

    const now = document.createElement("span");
    now.className = "cx-ra-time";
    now.textContent = clock(0);

    const total = document.createElement("span");
    total.className = "cx-ra-time";
    total.textContent = clock(span);

    // A range input rather than a styled div: it seeks with the arrow keys and
    // announces itself, both of which a div would have to reimplement badly.
    const seek = document.createElement("input");
    seek.type = "range";
    seek.className = "cx-ra-seek";
    seek.min = "0";
    seek.max = String(Math.floor(span));
    seek.value = "0";
    seek.step = "1";
    seek.setAttribute("aria-label", "Seek within this chapter");

    const followBox = document.createElement("label");
    followBox.className = "cx-ra-follow";
    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = follow;
    check.addEventListener("change", () => {
      follow = check.checked;
    });
    followBox.append(check, document.createTextNode(" Scroll with the voice"));

    audio = document.createElement("audio");
    audio.preload = "none";
    audio.src = `/api/studio/read-along-audio?slug=${encodeURIComponent(slug)}&path=${encodeURIComponent(timings.audio)}`;

    let scrubbing = false;
    function transport(position: number) {
      const into = Math.min(span, Math.max(0, position - first));
      now.textContent = clock(into);
      if (!scrubbing) seek.value = String(Math.floor(into));
    }

    audio.addEventListener("timeupdate", () => {
      const at = audio?.currentTime ?? 0;
      paint(at);
      transport(at);
    });
    audio.addEventListener("seeked", () => {
      const at = audio?.currentTime ?? 0;
      paint(at);
      transport(at);
    });
    audio.addEventListener("pause", () => {
      play.textContent = "Play";
    });
    audio.addEventListener("play", () => {
      play.textContent = "Pause";
    });

    seek.addEventListener("input", () => {
      scrubbing = true;
      now.textContent = clock(Number(seek.value));
    });
    seek.addEventListener("change", () => {
      scrubbing = false;
      if (audio) audio.currentTime = first + Number(seek.value);
    });

    function nudge(by: number) {
      if (!audio) return;
      audio.currentTime = Math.min(
        first + span,
        Math.max(first, audio.currentTime + by),
      );
    }
    back.addEventListener("click", () => nudge(-15));
    fwd.addEventListener("click", () => nudge(15));

    play.addEventListener("click", () => {
      if (!audio) return;
      if (audio.paused) {
        // Chapters start minutes into a long recording; without this the first
        // press plays the beginning of the sitting rather than this chapter.
        if (audio.currentTime < first) audio.currentTime = first;
        void audio.play().catch(() => {
          play.textContent = "Play";
        });
      } else {
        audio.pause();
      }
    });

    const controls = document.createElement("div");
    controls.className = "cx-ra-controls";
    controls.append(back, play, fwd);

    const scrubber = document.createElement("div");
    scrubber.className = "cx-ra-scrubber";
    scrubber.append(now, seek, total);

    el.append(controls, label, scrubber, followBox, audio);
  }

  return {
    /** Call on every chapter change; draws or hides the transport. */
    async open(chapterKey: string) {
      audio?.pause();
      painted = -1;
      timings = chapterKey ? await fetchTimings(slug, chapterKey) : null;
      draw();
    },
    destroy() {
      audio?.pause();
      el.innerHTML = "";
      occupy(false);
    },
  };
}
