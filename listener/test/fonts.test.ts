/**
 * The self-hosted faces in public/fonts/ are current against their sources.
 *
 * The third of this app's three generated artifacts, and the one that had no pin
 * until 2026-08-16. Its two siblings — the study-track colours and the quote inks
 * — are each held current by a test that runs the generator's own `--check`, and
 * the reason applies identically here: sync-fonts.mjs copies from node_modules and
 * from the admin site, the copies are COMMITTED, and a copy that goes stale is
 * invisible until somebody notices a page setting the wrong face.
 *
 * The gap was found by the repo-surgeon probe's GEN-UNPINNED check, which asks of
 * every declared generator whether anything tracked ever invokes the `--check` it
 * offers. This file is the answer for this one.
 *
 * A missing FILE and a stale one are deliberately the same failure here. The
 * generator reports both with the exact remediation command, so the assertion is
 * that it does not throw rather than a re-derivation of what it already knows —
 * a second opinion about which faces should exist would be a second manifest.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const STYLESHEET = "app/styles/podcast-factory.css";

describe("self-hosted fonts", () => {
  it("are all present and current against their sources", () => {
    expect(() =>
      execFileSync("node", ["scripts/sync-fonts.mjs", "--check"], {
        encoding: "utf8",
        stdio: "pipe",
      }),
    ).not.toThrow();
  });

  it("are reached by a same-origin @font-face, never a third-party link", () => {
    // The reason these are copied at all: a fonts.googleapis.com <link> is a
    // third-party request on every page load of a PRIVATE library — it tells
    // another origin who is reading and when. Copying the faces is only half of
    // that guarantee; the other half is that nothing quietly adds the link back.
    const css = readFileSync(STYLESHEET, "utf8");
    expect(css).not.toMatch(/fonts\.googleapis\.com|fonts\.gstatic\.com/);
    expect(css).toContain("@font-face");
  });
});
