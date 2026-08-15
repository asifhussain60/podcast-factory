/**
 * The five study-track colours are one set of values, not two.
 *
 * A track's colour belongs to the BOOK — Esoteric is the same amber on the
 * admin site's Studio shelf and on this site's library card — so the values
 * live once, in plan-dashboard/src/styles/study-track-colors.css, and
 * scripts/sync-study-tracks.mjs copies them into this app's stylesheet at
 * author time. Copied rather than imported for the reason sync-fonts.mjs and
 * sync-quote-inks.mjs both give: this app has no coupling to the admin site,
 * and a stylesheet reaching across the repo boundary would be the first.
 *
 * That leaves exactly one failure mode — someone changes a value on one side
 * and the copy goes stale — and this closes it. The repo's pre-commit hook runs
 * `npm run test` in this directory when a listener source OR the source
 * stylesheet is staged, so a stale copy cannot be committed.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { ALL_STUDY_TRACKS } from "~/lib/study-track";

const STYLESHEET = "app/styles/podcast-factory.css";

describe("study-track colours", () => {
  it("are current against the source stylesheet", () => {
    // Throws with the exact remediation command on drift, which is the message
    // worth surfacing — so the assertion is that it does not throw.
    expect(() =>
      execFileSync("node", ["scripts/sync-study-tracks.mjs", "--check"], {
        encoding: "utf8",
        stdio: "pipe",
      }),
    ).not.toThrow();
  });

  it("cover every track the app can render", () => {
    // The taxonomy and the palette are edited in different files, so a sixth
    // track added to ALL_STUDY_TRACKS without a colour would ship a ribbon with
    // no background — invisible rather than obviously broken. This fails first.
    const css = readFileSync(STYLESHEET, "utf8");
    for (const track of ALL_STUDY_TRACKS) {
      expect(css, `${track} has no ribbon background`).toContain(
        `--l-ribbon-${track}-bg:`,
      );
      expect(css, `${track} has no ribbon ink`).toContain(
        `--l-ribbon-${track}-ink:`,
      );
    }
  });

  it("keep the generated region's markers, which are the anchor", () => {
    // The sync script locates its block by these two comments and refuses to
    // guess if they are gone. Asserted here so deleting one fails as a test
    // rather than as a thrown script three commits later.
    const css = readFileSync(STYLESHEET, "utf8");
    expect(css).toContain("/* >>> study-track-colors —");
    expect(css).toContain("/* <<< study-track-colors */");
  });
});
