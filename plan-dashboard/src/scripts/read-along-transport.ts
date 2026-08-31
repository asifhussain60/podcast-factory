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

  function draw() {
    el.innerHTML = "";
    if (!timings) {
      el.hidden = true;
      return;
    }
    el.hidden = false;

    const play = document.createElement("button");
    play.type = "button";
    play.className = "cx-ra-play";
    play.textContent = "Play";
    play.setAttribute("aria-label", `Play ${voiceLabel(timings.engine)}`);

    const label = document.createElement("span");
    label.className = "cx-ra-label";
    label.textContent = `Follow along with ${voiceLabel(timings.engine)}`;

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
    audio.addEventListener("timeupdate", () => paint(audio?.currentTime ?? 0));
    audio.addEventListener("seeked", () => paint(audio?.currentTime ?? 0));
    audio.addEventListener("pause", () => {
      play.textContent = "Play";
    });
    audio.addEventListener("play", () => {
      play.textContent = "Pause";
    });

    play.addEventListener("click", () => {
      if (!audio) return;
      if (audio.paused) {
        // Chapters start minutes into a long recording; without this the first
        // press plays the beginning of the sitting rather than this chapter.
        if (audio.currentTime < (timings?.cues[0]?.startS ?? 0)) {
          audio.currentTime = timings?.cues[0]?.startS ?? 0;
        }
        void audio.play().catch(() => {
          play.textContent = "Play";
        });
      } else {
        audio.pause();
      }
    });

    el.append(play, label, followBox, audio);
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
    },
  };
}
