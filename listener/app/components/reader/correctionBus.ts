import type { Anchor } from "~/lib/anchor";

/**
 * How the selection bar tells the correction panel "the moderator pressed Correct".
 *
 * The bar and the panel are siblings that never share a parent with room to hold state, and
 * the reader route is at its size ceiling — so neither may be wired through it. A typed event
 * on `window` is the whole connection: the bar dispatches, the panel (mounted only for
 * moderators) listens, and a reader who is not one has no listener to reach at all.
 */
export interface CorrectionRequest {
  anchor: Anchor;
}

const EVENT = "pf:correct";

export const requestCorrection = (detail: CorrectionRequest) =>
  window.dispatchEvent(new CustomEvent<CorrectionRequest>(EVENT, { detail }));

export function onCorrectionRequest(
  handler: (request: CorrectionRequest) => void,
): () => void {
  const listener = (event: Event) =>
    handler((event as CustomEvent<CorrectionRequest>).detail);
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}
