// font-floor.mjs — count font-size declarations under the reading floor, over ALL selectors.
//
// The reading-floor lint (REQ-010, lint-html-views.mjs) deliberately inspects prose selectors only, because chips,
// badges and toolbar labels are legitimately small. That leaves class selectors unwatched, and the count drifts
// (~180 in 2026-09 against 22 reported warnings). This is the raw count, for a shrink-only ratchet — it does not judge
// any single declaration, it only refuses to let the total grow.

/** REQ-010's prose floor, in rem. */
export const FLOOR_REM = 1.2;
const ROOT_PX = 16;

/** Number of `font-size` declarations whose plain rem/em/px value is below the floor. Dynamic values are skipped. */
export function countSubFloorFontSizes(css) {
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
  let count = 0;
  for (const m of stripped.matchAll(/(?:^|[;{\s])font-size\s*:\s*([^;}]+)/gi)) {
    const value = m[1].trim().replace(/\s*!important\s*$/i, "");
    const parts = value.match(/^(\d*\.?\d+)(rem|em|px)$/i);
    if (!parts) continue; // var(), clamp(), calc(), %, keywords — never guessed at
    const n = parseFloat(parts[1]);
    const rem = parts[2].toLowerCase() === "px" ? n / ROOT_PX : n;
    if (rem < FLOOR_REM) count += 1;
  }
  return count;
}
