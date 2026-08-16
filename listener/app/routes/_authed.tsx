import { Outlet } from "react-router";

import type { Route } from "./+types/_authed";
import { OfflineAgent } from "~/components/offline/OfflineAgent";
import { PlayerProvider } from "~/components/player/Player";
import { SimulationBanner } from "~/components/SimulationBanner";
import { cloudflare } from "~/context";
import { requireInvited } from "~/middleware/authed";
import { simulatingOf } from "~/middleware/session";

/**
 * Layer 2 — the gate every non-public route sits behind.
 *
 * Pathless: it adds protection without adding a URL segment. It exports no
 * ErrorBoundary on purpose (see root.tsx) and no loader, so there is nothing
 * here for a `_routes` filter to skip past — the gate is the middleware, which
 * that filter cannot reach.
 */
export const middleware: Route.MiddlewareFunction[] = [requireInvited];

/**
 * Whether a simulation is running, for the banner — and what this site is called.
 *
 * A loader here and not in `root.tsx`, which would otherwise be the obvious home
 * for something every page needs: root's own note forbids reading session
 * context there, because the hard-404 path has none and touching it would make a
 * denied 404 render differently from a real one. This layout is never matched on
 * that path at all.
 *
 * It gates nothing, so it does not matter that a `_routes` filter could skip it
 * — the gate above is middleware, which that filter cannot reach.
 */
export function loader({ context }: Route.LoaderArgs) {
  return {
    simulating: simulatingOf(context),
    // Read ONCE for every signed-in page, and used by `AppShell` for the footer.
    // It used to be read by the library's own loader and by no other, which is
    // why a configured name appeared there and on none of the other four.
    siteName: context.get(cloudflare).env.PUBLIC_SITE_NAME,
  };
}

/**
 * The player lives HERE and nowhere else.
 *
 * React Router keeps a layout mounted across client navigations, so the single
 * <audio> element inside PlayerProvider survives moving from an episode to a
 * chapter to the library. Put it in a page instead and the sound stops the
 * moment the listener follows a link — which is most of what a listener does.
 */
export default function AuthedLayout({ loaderData }: Route.ComponentProps) {
  return (
    <PlayerProvider>
      {/* Beside the player and for the same reason: it has to outlive every
          navigation, and it must not run for somebody who is not signed in.
          It is told whether a simulation is running because the lease it
          enforces would otherwise delete the administrator's own downloads
          while he is looking at the site as somebody else. */}
      <OfflineAgent simulating={loaderData.simulating !== null} />
      {loaderData.simulating ? (
        <SimulationBanner as={loaderData.simulating.as} />
      ) : null}
      <Outlet />
    </PlayerProvider>
  );
}
