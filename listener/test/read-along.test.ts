/**
 * Which paragraph is being spoken is one rule, not two.
 *
 * Two surfaces ask it — this reader, where somebody follows a recording through
 * a published chapter, and the Book Composer, where Asif follows it through the
 * chapter he is editing. Two implementations would be free to disagree about the
 * same second of the same audio, and the disagreement would show as the wrong
 * sentence lit up in one of them: the precise failure the timing gate exists to
 * prevent.
 *
 * So the rule lives once, in plan-dashboard/src/lib/reader/read-along.ts, and
 * scripts/sync-read-along.mjs copies it into app/lib at author time. Copied
 * rather than imported for the reason sync-quote-inks.mjs gives: this app has no
 * coupling to the admin site, and a module reaching across the repo boundary
 * would be the first one.
 *
 * That leaves exactly one failure mode — someone changes the rule on one side and
 * the copy goes stale — and this closes it. The repo's pre-commit hook runs
 * `npm run test` in this directory, so a stale copy cannot be committed.
 */
import { execFileSync } from "node:child_process";
import { describe, expect, it } from "vitest";

import { cueAt, readAlongBlockIndex } from "../app/lib/read-along";

describe("the read-along rule", () => {
  it("is current against the copy the Book Composer uses", () => {
    // Throws with the exact remediation command on drift, which is the message
    // worth showing rather than a boolean.
    execFileSync("node", ["scripts/sync-read-along.mjs", "--check"], {
      stdio: "pipe",
    });
  });

  it("holds the last cue through a pause instead of blinking out", () => {
    const cues = [
      { startS: 0, endS: 5 },
      { startS: 10, endS: 15 },
    ];
    // 7s is a gap: nothing is being said, but the page must not lose its place.
    expect(cueAt(cues, 7)).toBe(0);
  });

  it("highlights nothing before the first cue", () => {
    expect(readAlongBlockIndex(true, [{ startS: 4, endS: 8 }], 1)).toBe(-1);
  });

  it("highlights nothing for a chapter published without timings", () => {
    expect(readAlongBlockIndex(true, [], 12)).toBe(-1);
    expect(readAlongBlockIndex(true, null, 12)).toBe(-1);
  });

  it("follows the cue's own block rather than its position in the list", () => {
    const cues = [
      { startS: 0, endS: 5, blockIndex: 2 },
      { startS: 5, endS: 9, blockIndex: 4 },
    ];
    expect(readAlongBlockIndex(true, cues, 6)).toBe(4);
  });

  it("refuses a position no clock could produce", () => {
    expect(readAlongBlockIndex(true, [{ startS: 0, endS: 5 }], NaN)).toBe(-1);
  });
});
