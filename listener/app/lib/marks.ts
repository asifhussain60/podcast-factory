/**
 * The reader's own marks, on the client: cached, painted immediately, synced.
 *
 * The server is the authority — that is what makes a highlight made on the iPad
 * appear on the phone. But the server is also a round trip, and a reader who
 * opens a chapter should not watch their highlights fade in a moment after the
 * text. So `localStorage` holds two things:
 *
 *   cache   the last known server state, painted on first render
 *   outbox  writes not yet acknowledged, replayed until they are
 *
 * The outbox is what makes this survive a tunnel. Every write is applied locally
 * first, queued, and POSTed; a failure leaves it queued and it goes again on the
 * next load, on `online`, and when the tab becomes visible. Every server write is
 * an UPSERT keyed on a client-generated id (see marks.server.ts), so replaying an
 * outbox the server has already seen changes nothing.
 *
 * Shape follows `lib/reading.ts` exactly — a module-level snapshot, an explicit
 * listener set, `useSyncExternalStore` in the component. Deliberately NOT seeded
 * from storage at module load: several of these components render on the server,
 * and reading storage in a `useState` initializer is a hydration mismatch.
 */

import type { Anchor } from "./anchor";

export const COLOURS = ["gold", "sage", "sky", "rose"] as const;
export type Colour = (typeof COLOURS)[number];

export const COLOUR_LABELS: Record<Colour, string> = {
  gold: "Gold",
  sage: "Sage",
  sky: "Sky",
  rose: "Rose",
};

export interface Bookmark {
  id: string;
  anchorKey: string;
  blockIndex: number;
  label: string;
  createdAt: string;
}

export interface Annotation extends Anchor {
  id: string;
  anchorKey: string;
  colour: Colour;
  note: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Progress {
  anchorKey: string;
  fraction: number;
  chaptersDone: number;
  updatedAt: string;
}

/**
 * A moment in an episode, and what the listener said about it.
 *
 * `seconds` is when the button was PRESSED. Playback starts earlier than this on
 * purpose — see `PRE_ROLL_S` — because the thought lands before the hand does.
 */
export interface EpisodeNote {
  id: string;
  number: number;
  seconds: number;
  note: string | null;
  quote: string | null;
  createdAt: string;
  updatedAt: string;
}

/**
 * How far before the mark playback resumes.
 *
 * A listener taps AFTER the sentence that struck them, so replaying from the
 * stored second reliably starts one thought too late. Ten seconds is about the
 * length of the run-up you need to hear it land again, and it is applied here at
 * the edge rather than baked into the stored value — the record is when the
 * button was pressed, which stays true if this number ever changes.
 */
export const PRE_ROLL_S = 10;

export interface Marks {
  progress: Progress | null;
  bookmarks: Bookmark[];
  annotations: Annotation[];
  /**
   * Seconds into each episode, by number.
   *
   * Carried here because it comes back in the same response — the reader never
   * uses it, and the player reads it straight from its own fetch rather than
   * through this store. Declaring it keeps the client's `Marks` the same shape
   * as the server's, so the cast in `useMarks` is honest.
   */
  listening: Record<number, number>;
  /** Moments marked in the podcast, in episode then time order. */
  episodeNotes: EpisodeNote[];
}

export const EMPTY: Marks = {
  progress: null,
  bookmarks: [],
  annotations: [],
  listening: {},
  episodeNotes: [],
};

/** One queued write: the form fields the marks route expects, verbatim. */
interface Pending {
  intent: string;
  fields: Record<string, string>;
}

interface Cache {
  v: 1;
  marks: Marks;
  outbox: Pending[];
}

const key = (slug: string) => `pf-marks:${slug}`;

/**
 * Version 1, and a bump discards rather than migrates.
 *
 * The cache is a copy of state the server holds; losing it costs one fetch. A
 * migration path for it would be code that can only ever introduce bugs into
 * data that is, by construction, disposable. The OUTBOX is the exception — but
 * an outbox old enough to survive a deployment that changed this shape has
 * failed to flush for a very long time, and re-sending it blind is worse than
 * dropping it.
 */
function read(slug: string): Cache {
  try {
    const raw = JSON.parse(localStorage.getItem(key(slug)) || "null");
    if (raw?.v !== 1) return { v: 1, marks: EMPTY, outbox: [] };
    return {
      v: 1,
      marks: {
        progress: raw.marks?.progress ?? null,
        bookmarks: Array.isArray(raw.marks?.bookmarks) ? raw.marks.bookmarks : [],
        annotations: Array.isArray(raw.marks?.annotations) ? raw.marks.annotations : [],
        listening: raw.marks?.listening ?? {},
        episodeNotes: Array.isArray(raw.marks?.episodeNotes) ? raw.marks.episodeNotes : [],
      },
      outbox: Array.isArray(raw.outbox) ? raw.outbox : [],
    };
  } catch {
    // Storage disabled, or a value another tab wrote badly. Neither is a reason
    // to fail: the reader simply waits for the fetch, as they would on a new
    // device.
    return { v: 1, marks: EMPTY, outbox: [] };
  }
}

function write(slug: string, cache: Cache) {
  try {
    localStorage.setItem(key(slug), JSON.stringify(cache));
  } catch {
    // Private browsing, or quota. The marks still apply to this page view and
    // the outbox still flushes from memory; only the memory of it is lost.
  }
}

/* -------------------------------------------------------------------------- */
/* The store                                                                   */
/* -------------------------------------------------------------------------- */

let slug: string | null = null;
let snapshot: Marks = EMPTY;
let outbox: Pending[] = [];
const listeners = new Set<() => void>();

export const marksSnapshot = (): Marks => snapshot;

export function subscribeMarks(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function publish() {
  for (const listener of listeners) listener();
}

function persist() {
  if (slug !== null) write(slug, { v: 1, marks: snapshot, outbox });
}

/**
 * Point the store at a book and paint whatever is already known.
 *
 * Called from an effect, never during render. Switching books replaces the
 * snapshot outright rather than merging — two books' marks in one array would
 * mean a stray `anchorKey` collision paints a highlight from a different work.
 */
export function openBook(next: string) {
  if (slug === next) return;
  slug = next;
  const cache = read(next);
  snapshot = cache.marks;
  outbox = cache.outbox;
  publish();
}

/**
 * Replace the cache with what the server just said, keeping unsent work.
 *
 * The server response does not yet include anything still in the outbox, so
 * adopting it wholesale would make a highlight the reader just made blink out and
 * come back. Pending writes are re-applied on top, which is also what happens on
 * the server when the outbox lands — same order, same result.
 */
export function reconcile(server: Marks) {
  snapshot = server;
  for (const pending of outbox) snapshot = applyLocally(snapshot, pending);
  persist();
  publish();
}

/** The local effect of a queued write. The server's UPSERTs mirror these exactly. */
function applyLocally(marks: Marks, pending: Pending): Marks {
  const f = pending.fields;

  switch (pending.intent) {
    case "progress":
      return {
        ...marks,
        progress: {
          anchorKey: f.anchorKey,
          fraction: Number(f.fraction),
          chaptersDone: Number(f.chaptersDone),
          updatedAt: new Date().toISOString(),
        },
      };

    case "bookmark":
      return {
        ...marks,
        bookmarks: [
          ...marks.bookmarks.filter((b) => b.id !== f.id),
          {
            id: f.id,
            anchorKey: f.anchorKey,
            blockIndex: Number(f.blockIndex),
            label: f.label,
            createdAt: new Date().toISOString(),
          },
        ],
      };

    case "unbookmark":
      return { ...marks, bookmarks: marks.bookmarks.filter((b) => b.id !== f.id) };

    case "annotate": {
      const existing = marks.annotations.find((a) => a.id === f.id);
      const next: Annotation = {
        id: f.id,
        anchorKey: f.anchorKey,
        blockIndex: Number(f.blockIndex),
        startOffset: Number(f.startOffset),
        endOffset: Number(f.endOffset),
        quote: f.quote,
        prefix: f.prefix ?? "",
        colour: f.colour as Colour,
        note: f.note ? f.note : null,
        createdAt: existing?.createdAt ?? new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      return {
        ...marks,
        annotations: [...marks.annotations.filter((a) => a.id !== f.id), next].sort(
          byPosition,
        ),
      };
    }

    case "unannotate":
      return { ...marks, annotations: marks.annotations.filter((a) => a.id !== f.id) };

    case "episode-note": {
      const existing = marks.episodeNotes.find((n) => n.id === f.id);
      const next: EpisodeNote = {
        id: f.id,
        number: Number(f.number),
        seconds: Number(f.seconds),
        note: f.note ? f.note : null,
        quote: f.quote ? f.quote : null,
        createdAt: existing?.createdAt ?? new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      return {
        ...marks,
        episodeNotes: [...marks.episodeNotes.filter((n) => n.id !== f.id), next].sort(byMoment),
      };
    }

    case "un-episode-note":
      return { ...marks, episodeNotes: marks.episodeNotes.filter((n) => n.id !== f.id) };

    default:
      return marks;
  }
}

/** Reading order: down the chapter, then across the paragraph. */
const byPosition = (a: Annotation, b: Annotation) =>
  a.blockIndex - b.blockIndex || a.startOffset - b.startOffset;

/** Listening order: through the podcast, then through the episode. */
const byMoment = (a: EpisodeNote, b: EpisodeNote) =>
  a.number - b.number || a.seconds - b.seconds;

/**
 * Ask the server again for the book this store has open, if it is this one.
 *
 * For the ONE write that does not go through this store: the player's Mark
 * button, which posts straight to the episode's own book because the audio and
 * the open book can be different works (see `markMoment` in Player.tsx). That
 * write is correct and this store knows nothing about it — so a drawer standing
 * open when the button is pressed would show everything except the mark just
 * made, which is indistinguishable from a button that does nothing.
 *
 * Scoped to a matching slug on purpose. Marking a moment in one book while
 * reading another must not refetch the book being read: nothing about it has
 * changed, and the two are genuinely unrelated.
 */
export async function refresh(book: string): Promise<void> {
  if (slug !== book) return;
  try {
    const response = await fetch(`/book/${encodeURIComponent(book)}/marks`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return;
    if (slug !== book) return; // navigated away mid-flight
    reconcile((await response.json()) as Marks);
  } catch {
    // Offline. The mark is on the server or it is not; either way the next load
    // settles it, and there is nothing useful to say here.
  }
}

/**
 * Apply a write here and now, queue it, and try to send it.
 *
 * Optimistic without exception. A highlight that appears only once the network
 * agrees is a highlight that feels broken on a train, and the write is an UPSERT
 * on an id this client chose, so there is no server-assigned value to wait for.
 */
export function submit(intent: string, fields: Record<string, string>) {
  const pending: Pending = { intent, fields };
  snapshot = applyLocally(snapshot, pending);
  outbox = [...outbox, pending];
  persist();
  publish();
  void flush();
}

let flushing = false;

/**
 * Send the outbox, oldest first, stopping at the first failure.
 *
 * Order matters and the queue is strictly sequential: "add this highlight" then
 * "delete it" must not be sent concurrently, or the delete can land against a row
 * that does not exist yet and the highlight survives its own deletion.
 *
 * A 4xx carrying `permanent` drops the item — a malformed mark will never
 * succeed, and retrying it forever would block every write behind it. Anything
 * else leaves the queue intact for the next attempt.
 */
export async function flush(): Promise<void> {
  if (flushing || slug === null || outbox.length === 0) return;
  if (typeof navigator !== "undefined" && navigator.onLine === false) return;

  flushing = true;
  const book = slug;

  try {
    while (outbox.length > 0 && slug === book) {
      const [head, ...rest] = outbox;
      const body = new URLSearchParams({ intent: head.intent, ...head.fields });

      let response: Response;
      try {
        response = await fetch(`/book/${encodeURIComponent(book)}/marks`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body,
        });
      } catch {
        return; // offline mid-flight. Everything stays queued.
      }

      if (!response.ok) return;

      const result = (await response.json().catch(() => null)) as
        | { error?: string; permanent?: boolean }
        | null;

      if (result?.error && !result.permanent) return;

      outbox = rest;
      persist();
    }
  } finally {
    flushing = false;
  }
}

/**
 * Progress, throttled, plus a guaranteed final write.
 *
 * Scroll fires far too often to POST from, and the last position is the one that
 * matters — so it is coalesced to one write every few seconds, and `pagehide`
 * sends whatever is outstanding with `sendBeacon`. A beacon rather than a fetch
 * because the page is being torn down and an in-flight fetch is cancelled with
 * it; a beacon is handed to the browser to deliver afterwards. It can only carry
 * a body, which is exactly why the marks route takes form data.
 */
const PROGRESS_INTERVAL_MS = 4_000;
let lastProgressAt = 0;
let unsentProgress: Record<string, string> | null = null;

export function recordProgress(fields: Record<string, string>) {
  unsentProgress = fields;
  const now = Date.now();
  if (now - lastProgressAt < PROGRESS_INTERVAL_MS) return;
  lastProgressAt = now;
  submit("progress", fields);
  unsentProgress = null;
}

/** Called on pagehide and on visibility change. Safe to call with nothing due. */
export function flushProgressNow() {
  if (unsentProgress === null || slug === null) return;
  const body = new URLSearchParams({ intent: "progress", ...unsentProgress });
  unsentProgress = null;

  if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
    const ok = navigator.sendBeacon(
      `/book/${encodeURIComponent(slug)}/marks`,
      new Blob([body.toString()], { type: "application/x-www-form-urlencoded" }),
    );
    if (ok) return;
  }

  // No beacon, or it refused (it can, when the queue is full). Fall back to the
  // outbox so the write is not simply dropped — it will go on the next load.
  submit("progress", Object.fromEntries(body.entries()) as Record<string, string>);
}

/**
 * An id for a mark this client is creating.
 *
 * `crypto.randomUUID` needs a secure context, which localhost and the deployed
 * site both are — but a stale browser without it must not crash the reader, so
 * there is a fallback. Its shape matches the format marks.server.ts validates.
 */
export function newId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const hex = (n: number) =>
    Array.from({ length: n }, () => Math.floor(Math.random() * 16).toString(16)).join("");
  return `${hex(8)}-${hex(4)}-4${hex(3)}-a${hex(3)}-${hex(12)}`;
}

/* -------------------------------------------------------------------------- */
/* Selectors — asked for by name so components do not filter inline            */
/* -------------------------------------------------------------------------- */

export const annotationsInChapter = (marks: Marks, anchorKey: string): Annotation[] =>
  marks.annotations.filter((a) => a.anchorKey === anchorKey).sort(byPosition);

export const bookmarksInChapter = (marks: Marks, anchorKey: string): Bookmark[] =>
  marks.bookmarks.filter((b) => b.anchorKey === anchorKey);

export const notesInEpisode = (marks: Marks, number: number): EpisodeNote[] =>
  marks.episodeNotes.filter((n) => n.number === number).sort(byMoment);
