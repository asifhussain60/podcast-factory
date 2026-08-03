import { Outlet } from "react-router";

import type { Route } from "./+types/_authed";
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

export default function AuthedLayout() {
  return <Outlet />;
}
