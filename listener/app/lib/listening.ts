/**
 * Listening positions that could not be sent, held until they can be.
 *
 * WHY THIS IS NOT IN lib/marks.ts, which already has an outbox. That one holds
 * ONE book open — whichever is being READ — and posts its queue to that book's
 * endpoint. A listener can have this book's episode playing while reading a
 * different book entirely, so routing a position through it would file it under
 * the wrong work. That is exactly the objection recorded against giving the
 * player an outbox at all, and it is answered here by carrying the slug on every
 * entry rather than by having a current book.
 *
 * TWO QUEUES, because the two things are not alike. A POSITION is idempotent and
 * last-write-wins, so one entry per episode collapses and replaying a stale one
 * loses nothing. A MOMENT has an identity, can be edited and withdrawn, and its
 * queue therefore has an ORDER that must survive a failed flush: "keep this
 * moment" then "remove it" sent out of order leaves the moment there. So moments
 * are a list, appended to and drained strictly in sequence, and positions are a
 * map.
 *
 * THE LOCAL CACHE IS NOT THIS. `pf-positions` in the player already remembers
 * where you got to, and it is what makes playback resume instantly. What is lost
 * with no network is the SERVER's copy — so the other device never learns, and
 * the library card's progress bar stays where it was. This is that gap.
 */

const OUTBOX_KEY = "pf-listen-outbox";

interface Pending {
  slug: string;
  number: number;
  seconds: number;
}

/** `slug#number` -> the latest position seen for it. */
type Outbox = Record<string, Pending>;

function load(): Outbox {
  try {
    const raw = localStorage.getItem(OUTBOX_KEY);
    return raw === null ? {} : (JSON.parse(raw) as Outbox);
  } catch {
    return {};
  }
}

function store(outbox: Outbox): void {
  try {
    localStorage.setItem(OUTBOX_KEY, JSON.stringify(outbox));
  } catch {
    // Storage disabled, or full. The position is still in the player's own
    // cache, so the listener keeps their place on this device; only the other
    // device will not learn of it.
  }
}

/**
 * Remember a position that has not reached the server.
 *
 * LAST write wins, not the furthest. Where somebody stopped is where they
 * stopped: scrubbing back twenty minutes and closing the app means they want to
 * resume at twenty minutes back, and keeping the maximum would silently refuse
 * that.
 */
export function queuePosition(
  slug: string,
  number: number,
  seconds: number,
): void {
  const outbox = load();
  outbox[`${slug}#${number}`] = { slug, number, seconds };
  store(outbox);
}

/**
 * Send what is queued, oldest first, and keep whatever will not go.
 *
 * STOPS AT THE FIRST FAILURE rather than carrying on. If one request failed
 * because the network went away, the rest will fail too, and firing them anyway
 * turns one dead entry into a queue-length burst of them every time the device
 * flickers back. Anything unsent stays for the next attempt.
 *
 * A REJECTED request is different from a failed one and is dropped: a 404 means
 * the book is gone or no longer readable, and an entry that can never be
 * accepted would otherwise be retried on every launch forever.
 */
export async function flushPositions(): Promise<void> {
  const outbox = load();
  const keys = Object.keys(outbox);
  if (keys.length === 0) return;

  for (const key of keys) {
    const pending = outbox[key];
    let sent: boolean;
    try {
      const response = await fetch(
        `/book/${encodeURIComponent(pending.slug)}/marks`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            intent: "listening",
            number: String(pending.number),
            seconds: String(pending.seconds),
          }),
        },
      );
      // A redirect is the signed-out case: the gate bounced us to sign-in, which
      // is not a refusal of this position. Keep it and try again later.
      if (response.redirected) break;
      sent = response.ok || response.status === 404;
    } catch {
      break; // still no network
    }
    if (!sent) break;
    delete outbox[key];
  }

  store(outbox);
}

/** How many positions are waiting. Used by tests and nothing else today. */
export function pendingCount(): number {
  return Object.keys(load()).length;
}

/* ---- Moments kept while listening ---------------------------------------- */

/**
 * A write against an episode note that has not reached the server.
 *
 * The whole write, not a summary of it: the flush replays exactly what the
 * player would have sent, so there is no second description of an episode note
 * anywhere and nothing to keep in step with the endpoint.
 */
export interface PendingMoment {
  slug: string;
  intent: "episode-note" | "un-episode-note";
  fields: Record<string, string>;
}

const MOMENT_KEY = "pf-moment-outbox";

function loadMoments(): PendingMoment[] {
  try {
    const raw = localStorage.getItem(MOMENT_KEY);
    const parsed: unknown = raw === null ? [] : JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as PendingMoment[]) : [];
  } catch {
    return [];
  }
}

function storeMoments(queue: PendingMoment[]): void {
  try {
    localStorage.setItem(MOMENT_KEY, JSON.stringify(queue));
  } catch {
    /* storage disabled or full; the write is lost, exactly as it was before */
  }
}

/** Append a write. Order is the point — see the module note. */
export function queueMoment(pending: PendingMoment): void {
  storeMoments([...loadMoments(), pending]);
}

/** What is still waiting, for the merge below and for tests. */
export function pendingMoments(): PendingMoment[] {
  return loadMoments();
}

/**
 * Replay the queue over what the server said, so a moment kept with no network
 * is ON SCREEN.
 *
 * Without this, marking a moment offline queues it silently and the panel shows
 * nothing — which is indistinguishable from a button that does not work, and is
 * the reason `lib/marks.ts` applies every write locally before sending it. Same
 * idea, in the one place the player reads its notes.
 *
 * Replayed IN ORDER for the same reason it is sent in order: an add followed by
 * a withdrawal must end with the note gone.
 */
export function withPendingMoments(
  slug: string,
  number: number,
  notes: EpisodeNoteLike[],
): EpisodeNoteLike[] {
  const queue = loadMoments().filter((m) => m.slug === slug);
  if (queue.length === 0) return notes;

  let result = [...notes];
  for (const pending of queue) {
    const id = pending.fields.id;
    if (pending.intent === "un-episode-note") {
      result = result.filter((n) => n.id !== id);
      continue;
    }
    if (Number(pending.fields.number) !== number) continue;
    const made: EpisodeNoteLike = {
      id,
      number,
      seconds: Number(pending.fields.seconds),
      note: pending.fields.note === "" ? null : pending.fields.note,
      quote: pending.fields.quote === "" ? null : pending.fields.quote,
    };
    const at = result.findIndex((n) => n.id === id);
    if (at === -1) result = [...result, made];
    else result = result.map((n, i) => (i === at ? made : n));
  }
  return result.sort((a, b) => a.seconds - b.seconds);
}

/**
 * The shape this module needs of an episode note, and no more.
 *
 * Structural rather than an import of `EpisodeNote` from lib/marks: that module
 * is the READING store, and importing its types here would suggest the two
 * queues are related when the whole point of this file is that they are not.
 */
export interface EpisodeNoteLike {
  id: string;
  number: number;
  seconds: number;
  note: string | null;
  quote: string | null;
}

/**
 * Send the queued moments, oldest first, stopping at the first failure.
 *
 * Strictly sequential, and that is a correctness requirement rather than
 * politeness: "keep this moment" and "remove it" sent concurrently can land in
 * either order, and the wrong one leaves a withdrawn note in the book.
 *
 * A 4xx marked permanent is DROPPED — a malformed write will never succeed, and
 * keeping it would block every write behind it forever. Anything else leaves the
 * queue intact.
 */
export async function flushMoments(): Promise<void> {
  const queue = loadMoments();
  if (queue.length === 0) return;

  let remaining = [...queue];
  while (remaining.length > 0) {
    const [head, ...rest] = remaining;
    let response: Response;
    try {
      response = await fetch(`/book/${encodeURIComponent(head.slug)}/marks`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ intent: head.intent, ...head.fields }),
      });
    } catch {
      break; // still no network
    }

    if (response.redirected) break; // signed out; not a refusal of the note
    if (!response.ok) break;

    const result = (await response.json().catch(() => null)) as {
      error?: string;
      permanent?: boolean;
    } | null;
    if (result?.error && !result.permanent) break;

    remaining = rest;
  }

  storeMoments(remaining);
}
