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
 * WHY POSITIONS AND NOT EPISODE NOTES. A position is idempotent and
 * last-write-wins: replaying a stale one loses nothing, and two queued entries
 * for the same episode collapse into the later. A note is none of those things —
 * it has an identity, it can be edited and withdrawn, and a queue of them has an
 * order that has to be preserved through a failed flush. Queuing notes is a
 * bigger thing that deserves its own change; today a note made with no network
 * fails and says so, which is at least honest.
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
export function queuePosition(slug: string, number: number, seconds: number): void {
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
      const response = await fetch(`/book/${encodeURIComponent(pending.slug)}/marks`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          intent: "listening",
          number: String(pending.number),
          seconds: String(pending.seconds),
        }),
      });
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
