import type { MiddlewareFunction } from "react-router";

import { notFound } from "./deny";
import { session } from "./session";

/**
 * Layer 3b — moderator (which includes every admin).
 *
 * A sibling of `requireAdmin`, and the same shape for the same reason: a 404 rather than a
 * 403, because a 403 confirms that the surface exists. `isModerator` was resolved once in
 * layer 1 and is FALSE while the administrator is simulating somebody, so nothing here needs
 * to remember to ask a second question about simulation.
 */
export const requireModerator: MiddlewareFunction<Response> = async (
  { context },
  next,
) => {
  const viewer = context.get(session).viewer;
  if (viewer === null || !viewer.isModerator) notFound();
  return next();
};
