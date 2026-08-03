import { Outlet } from "react-router";

import type { Route } from "./+types/_authed";
import { PlayerProvider } from "~/components/player/Player";
import { requireInvited } from "~/middleware/authed";

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
 * The player lives HERE and nowhere else.
 *
 * React Router keeps a layout mounted across client navigations, so the single
 * <audio> element inside PlayerProvider survives moving from an episode to a
 * chapter to the library. Put it in a page instead and the sound stops the
 * moment the listener follows a link — which is most of what a listener does.
 */
export default function AuthedLayout() {
  return (
    <PlayerProvider>
      <Outlet />
    </PlayerProvider>
  );
}
