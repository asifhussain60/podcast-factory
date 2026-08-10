/**
 * The quotation cards' inks are one set of values, not two.
 *
 * A card's colour belongs to the EDITION — scripture is the same gold in the
 * printed PDF, in the Book Composer and on this site — so the values live once,
 * in plan-dashboard/src/styles/quote-typography.css, and scripts/sync-quote-inks.mjs
 * copies them into this app's stylesheet at author time. Copied rather than
 * imported for the reason sync-fonts.mjs gives: this app has no coupling to the
 * admin site, and a stylesheet reaching across the repo boundary would be the
 * first one.
 *
 * That leaves exactly one failure mode — someone changes a value on one side and
 * the copy goes stale — and this closes it. The repo's pre-commit hook runs
 * `npm run test` in this directory on every commit, so a stale copy cannot be
 * committed; there is no separate hook to remember to install.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const STYLESHEET = "app/styles/podcast-factory.css";

describe("quotation-card inks", () => {
  it("are current against the printed edition's stylesheet", () => {
    // Throws with the exact remediation command on drift, which is the message
    // worth surfacing — so the assertion is that it does not throw.
    expect(() =>
      execFileSync("node", ["scripts/sync-quote-inks.mjs", "--check"], {
        encoding: "utf8",
        stdio: "pipe",
      }),
    ).not.toThrow();
  });

  it("carry the sepia palette by hand, and say so", () => {
    // The one carve-out, asserted so it cannot be quietly generated later: the
    // print stylesheet measures against a cream page and a near-black one, and
    // the sepia sheet is neither. If someone adds a sepia ink region, this fails
    // and they have to argue for the colour rather than derive it.
    const css = readFileSync(STYLESHEET, "utf8");
    expect(css).not.toContain(">>> quote-inks-sepia");
    expect(css).toContain("HAND-AUTHORED");
  });

  it("keep every generated region paired and closed", () => {
    const css = readFileSync(STYLESHEET, "utf8");
    const opened = [...css.matchAll(/>>> (quote-[\w-]+) —/g)].map((m) => m[1]);
    const closed = [...css.matchAll(/<<< (quote-[\w-]+) \*\//g)].map((m) => m[1]);
    expect(opened).toEqual(closed);
    expect(opened.length).toBe(5);
  });
});
