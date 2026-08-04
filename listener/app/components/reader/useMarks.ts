import { useEffect, useSyncExternalStore } from "react";

import {
  flush,
  flushProgressNow,
  marksSnapshot,
  openBook,
  reconcile,
  subscribeMarks,
  type Marks,
} from "~/lib/marks";

/**
 * This reader's marks in this book — cached, then reconciled with the server.
 *
 * Same store shape as `useReading`: `marksSnapshot` is both `getSnapshot` and
 * `getServerSnapshot`, so the first client render matches the server's empty one
 * and nothing is read from storage during render.
 *
 * The effect does four things in a deliberate order:
 *
 *   1. `openBook` — paint whatever the last visit cached, immediately. Without
 *      this the highlights appear a network round trip after the text, which
 *      reads as them being applied rather than as them already being there.
 *   2. Fetch the server's copy and `reconcile` — pending local writes are
 *      re-applied on top, so a highlight made a second ago does not blink out.
 *   3. `flush` — send anything the last session could not.
 *   4. Re-flush on `online` and on the tab becoming visible, and force out any
 *      throttled progress on `pagehide`.
 *
 * `pagehide` rather than `beforeunload`: `beforeunload` does not fire reliably on
 * iOS Safari, which is a large share of where this is read, and it also blocks
 * the bfcache. `visibilitychange` covers the case iOS actually takes — the app
 * being backgrounded rather than closed.
 */
export function useMarks(slug: string): Marks {
  const marks = useSyncExternalStore(subscribeMarks, marksSnapshot, marksSnapshot);

  useEffect(() => {
    openBook(slug);

    const controller = new AbortController();

    void (async () => {
      try {
        const response = await fetch(`/book/${encodeURIComponent(slug)}/marks`, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) return;
        const server = (await response.json()) as Marks;
        reconcile(server);
      } catch {
        // Offline, or navigated away mid-flight. The cache is already painted
        // and the outbox is already queued; there is nothing to report.
      }
      void flush();
    })();

    const retry = () => void flush();
    const onHide = () => flushProgressNow();
    const onVisibility = () => {
      if (document.visibilityState === "hidden") flushProgressNow();
      else void flush();
    };

    window.addEventListener("online", retry);
    window.addEventListener("pagehide", onHide);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      controller.abort();
      window.removeEventListener("online", retry);
      window.removeEventListener("pagehide", onHide);
      document.removeEventListener("visibilitychange", onVisibility);
      // Leaving the chapter is the last chance to record where it got to. A
      // client-side navigation to the next chapter does not fire pagehide.
      flushProgressNow();
    };
  }, [slug]);

  return marks;
}
