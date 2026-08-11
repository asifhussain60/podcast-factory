import { useEffect } from "react";

import { flushPositions } from "~/lib/listening";
import { hydrate, purgeExcept } from "~/lib/offline";

/**
 * The three things offline listening needs done once, when the app opens.
 *
 * Mounted in the authenticated layout beside the player, for the same reason the
 * player is there: it must survive navigation, and it must not run on the
 * sign-in page.
 *
 * Renders nothing. It is a lifecycle, not a control.
 */
export function OfflineAgent({ simulating }: { simulating: boolean }) {
  useEffect(() => {
    // 1. Make what is already downloaded playable. Until this resolves, the
    //    player falls back to the network, which is the correct behaviour
    //    rather than a degraded one.
    void hydrate();

    // 2. Register the worker that lets the site open with no signal. Failure is
    //    silent and survivable: without it, downloads still play — the listener
    //    just has to have the app open already.
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);

  useEffect(() => {
    /*
     * 3. The lease.
     *
     * NOT WHILE SIMULATING, and this is the sharp edge in the whole feature.
     * `withSession` swaps the viewer for the simulated one, so /offline/allowed
     * would answer with THAT person's books — and purging against it would
     * delete the administrator's own downloads from his own phone, silently,
     * because he looked at the site as somebody else. Simulation is supposed to
     * change what he sees, never what he has.
     */
    if (simulating) return;

    let cancelled = false;

    async function lease() {
      // `slugs: null` means "could not find out", which `purgeExcept` treats as
      // change nothing. Offline is the ordinary case here and must never look
      // like an empty entitlement.
      let slugs: string[] | null = null;
      try {
        const response = await fetch("/offline/allowed", { credentials: "same-origin" });
        // `redirected` is the signed-out case: the gate bounced us to sign-in,
        // and that page is HTML, not an answer about anybody's books.
        if (response.ok && !response.redirected) {
          const body = (await response.json()) as { slugs?: unknown };
          if (Array.isArray(body.slugs) && body.slugs.every((s) => typeof s === "string")) {
            slugs = body.slugs as string[];
          }
        }
      } catch {
        // No network. Nothing is withdrawn on the strength of a failed request.
      }
      if (!cancelled) await purgeExcept(slugs);
    }

    /*
     * 4. Positions listened to with no network.
     *
     * AFTER the lease, not before, and not in parallel. A position for a book
     * whose access was withdrawn is a request the server will refuse; sending it
     * first would mean every launch fires a burst of rejections before the queue
     * that produced them is cleared.
     */
    async function catchUp() {
      await lease();
      if (!cancelled) await flushPositions();
    }

    void catchUp();
    // Also when the device comes back: the app is open for hours at a time on a
    // phone, and the launch that matters may be the one that had no signal.
    const onOnline = () => void catchUp();
    window.addEventListener("online", onOnline);

    return () => {
      cancelled = true;
      window.removeEventListener("online", onOnline);
    };
  }, [simulating]);

  return null;
}
