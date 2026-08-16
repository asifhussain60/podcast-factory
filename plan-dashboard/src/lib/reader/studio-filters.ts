/**
 * studio-filters.ts — the Studio picker's filtering RULES, with no DOM in them.
 *
 * Why this is a module and not a closure inside the page's script: the rules
 * here have been wrong twice, in ways no static check could see and only a real
 * browser could catch. Both were arithmetic, not markup:
 *
 *   1. Counts were measured over raw books while the shelf drew folded series
 *      decks — "Esoteric 7" for a shelf showing two esoteric things.
 *   2. Counts were then measured PER FACET in isolation, which is true only
 *      while the other two sit on "All". With Published chosen, "Shariah 2"
 *      promised two books and delivered none.
 *
 * Both are properties of a pure function over a list of units, so they belong
 * somewhere a test can state them directly rather than by driving a page. The
 * browser gate (INV-8 in scripts/site-health-smoke.mjs) still presses every
 * chip end to end — these tests do not replace it, they make its failures
 * diagnosable, because a red test here names the rule that broke.
 */

/** The three independent facets. Any one narrows on its own, in any order. */
export type Facet = "bucket" | "status" | "track";

export const FACETS: readonly Facet[] = ["bucket", "status", "track"];

/** The value that means "not narrowed" — every facet's default and reset. */
export const ALL = "all";

/**
 * One thing the shelf DRAWS: a standalone book, or a series deck counted once
 * rather than once per volume. Every count is measured over these, because a
 * chip's number is a promise about what pressing it will put on screen.
 */
export interface FilterUnit {
  bucket: string;
  /**
   * The lifecycle bucket, or `"always"` for a series deck.
   *
   * A deck has no single status of its own — its volumes each carry theirs —
   * so it is never hidden by the status facet. Spelled as a value rather than
   * handled as a special case at the call site, so the filter and the counter
   * cannot disagree about what a deck does.
   */
  status: string;
  /** The study track, or `""`/undefined when the book names none. */
  track?: string;
}

/** The current choice per facet. */
export type Chosen = Record<Facet, string>;

export const wideOpen = (): Chosen => ({
  bucket: ALL,
  status: ALL,
  track: ALL,
});

export const isWideOpen = (chosen: Chosen): boolean =>
  FACETS.every((f) => chosen[f] === ALL);

/** Does this unit satisfy ONE facet's value? `all` matches everything. */
export function satisfies(
  unit: FilterUnit,
  facet: Facet,
  want: string,
): boolean {
  if (want === ALL) return true;
  const value = facet === "track" ? (unit.track ?? "") : unit[facet];
  // The deck rule, in the one place both the filter and the counter read it.
  if (facet === "status" && value === "always") return true;
  return value === want;
}

/** Does it satisfy ALL THREE? This is what decides whether a card is shown. */
export const matches = (unit: FilterUnit, chosen: Chosen): boolean =>
  FACETS.every((facet) => satisfies(unit, facet, chosen[facet]));

/**
 * What choosing `value` in `facet` WOULD show, given everything else already
 * chosen.
 *
 * The chip's own facet is excluded from the test — including it would make
 * every unchosen chip in a narrowed group report zero. This is the whole reason
 * the counts are contextual: measured without the exclusion they are a
 * different question's answer, and measured without the other facets they are
 * the answer to a question nobody asked once a second facet is active.
 */
export function contextualCount(
  units: readonly FilterUnit[],
  chosen: Chosen,
  facet: Facet,
  value: string,
): number {
  const others = FACETS.filter((f) => f !== facet);
  return units.filter(
    (unit) =>
      others.every((f) => satisfies(unit, f, chosen[f])) &&
      satisfies(unit, facet, value),
  ).length;
}

/** How many units are on screen under the current choice. */
export const shownCount = (
  units: readonly FilterUnit[],
  chosen: Chosen,
): number => units.filter((u) => matches(u, chosen)).length;
