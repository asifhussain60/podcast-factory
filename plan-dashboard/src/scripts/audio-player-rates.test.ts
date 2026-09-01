/**
 * "The same speeds as on the Podcast Factory Library" — enforced, not remembered.
 *
 * The two apps are deliberately separate: the Library is a Cloudflare Worker and
 * imports nothing from this Astro site at runtime, so its speed scale is COPIED
 * into `AudioPlayer.tsx` rather than imported. A copy nobody checks is a copy that
 * drifts, and the drift would be silent — both players keep working, at different
 * speeds, which is exactly the thing Asif asked for the opposite of.
 *
 * So this reads both files off disk and compares the lists. Same pattern the
 * repo already uses for its other cross-surface copies: the rule lives in one
 * place, and a test fails when the other one stops agreeing with it.
 */
import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

const RATES_RE = /RATES = \[([^\]]+)\] as const;/;

function rates(url: URL): number[] {
  const match = RATES_RE.exec(readFileSync(url, "utf8"));
  if (match === null)
    throw new Error(`no RATES array found in ${url.pathname}`);
  return match[1].split(",").map((n) => Number(n.trim()));
}

test("the Studio player offers exactly the Library's speeds", () => {
  const studio = rates(
    new URL("../components/studio/AudioPlayer.tsx", import.meta.url),
  );
  const library = rates(
    new URL("../../../listener/app/lib/playback-rate.ts", import.meta.url),
  );
  assert.deepEqual(studio, library);
});

test("and that scale is the one Asif chose", () => {
  // Pinned literally as well as relatively: two files agreeing on the WRONG list
  // would pass the test above and fail the person using them.
  assert.deepEqual(
    rates(new URL("../components/studio/AudioPlayer.tsx", import.meta.url)),
    [1, 1.5, 2, 2.5, 3],
  );
});
