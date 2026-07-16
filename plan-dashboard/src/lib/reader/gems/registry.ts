/**
 * gems/registry.ts — the extensibility seam for Gem personas.
 *
 * Adding a Gem is a single entry here — no engine or route change. Mirrors
 * companion/registry.ts's shape. Unlike kindDef(), gemDef() does NOT degrade
 * gracefully for an unknown id: an unresolved Gem has no persona to fall back to,
 * so callers must treat `undefined` as an error (see engine.ts).
 */
import type { GemDef } from './types';
import { ISMAILI_SCHOLAR_GEM } from './ismaili-scholar';

/** Known Gems. Extend by appending an entry. */
export const GEM_DEFS: GemDef[] = [ISMAILI_SCHOLAR_GEM];

export const DEFAULT_GEM_ID: string = ISMAILI_SCHOLAR_GEM.id;

const GEM_MAP = new Map(GEM_DEFS.map((g) => [g.id, g]));

/** Resolve a Gem def by id. Returns undefined for an unknown id — no fallback. */
export function gemDef(id: string): GemDef | undefined {
  return GEM_MAP.get(id);
}
