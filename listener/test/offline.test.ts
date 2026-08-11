import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { sourcesToPurge, type DownloadMeta } from "../app/lib/offline";

/**
 * Offline listening has exactly two rules that can lose something.
 *
 * The first is the lease: it deletes a reader's downloads, and the input it acts
 * on comes off the network, so the difference between "you hold nothing" and "I
 * could not ask" has to survive every refactor. The second is what the service
 * worker will put in a cache, which is where entitled bytes and one account's
 * Companion cards could end up in a store no access check guards.
 *
 * Both are pinned here rather than reasoned about.
 */

const episode = (slug: string, number: number): DownloadMeta => ({
  src: `/media/${slug}/m4a/ep${number}.m4a`,
  slug,
  bookTitle: slug,
  number,
  title: `Episode ${number}`,
  durationS: 600,
  transcript: null,
  bytes: 40_000_000,
  savedAt: 1,
});

const HELD = [episode("ayyuha-al-walad", 1), episode("ayyuha-al-walad", 2), episode("wisdom", 1)];

describe("the lease", () => {
  it("deletes nothing when the answer is unknown", () => {
    // THE case this function exists for. Offline is the ordinary state for a
    // device holding downloads, and a failed request must never read as an
    // empty entitlement — that is a library wiped on a plane.
    expect(sourcesToPurge(HELD, null)).toEqual([]);
  });

  it("deletes everything when the viewer genuinely holds nothing", () => {
    // The inverse, and the reason `null` and `[]` may never be collapsed into a
    // falsy check: this answer is real and must be acted on.
    expect(sourcesToPurge(HELD, [])).toEqual(HELD.map((e) => e.src));
  });

  it("keeps every episode of a book that is still granted", () => {
    expect(sourcesToPurge(HELD, ["ayyuha-al-walad", "wisdom"])).toEqual([]);
  });

  it("deletes every episode of a book that is no longer granted, and only those", () => {
    expect(sourcesToPurge(HELD, ["wisdom"])).toEqual([
      "/media/ayyuha-al-walad/m4a/ep1.m4a",
      "/media/ayyuha-al-walad/m4a/ep2.m4a",
    ]);
  });

  it("is unaffected by a slug it was told about but does not hold", () => {
    expect(sourcesToPurge(HELD, ["wisdom", "ayyuha-al-walad", "never-downloaded"])).toEqual([]);
  });
});

describe("the service worker", () => {
  const SW = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");

  /**
   * A grep, deliberately, in the same spirit as the one that watches
   * publish_to_listener.py for the two privilege bits: the failure it guards
   * against is somebody widening a cache rule for a sensible-sounding reason,
   * and that shows up as new text in this file rather than as a behaviour a unit
   * test would exercise.
   */
  it("caches only assets and the Downloads document", () => {
    // If a third cache name appears, this feature has grown a store that the
    // reasoning in the file header no longer covers.
    const opens = [...SW.matchAll(/caches\.open\((\w+)\)/g)].map((m) => m[1]);
    expect(new Set(opens)).toEqual(new Set(["ASSETS", "DOCS"]));
  });

  it("never names /media or /book as cacheable", () => {
    // /media is entitled bytes and /book can carry Scholar Companion cards that
    // one account may see. Neither may enter a cache this worker controls.
    // The worker's OWN rule, lifted out of the file and fired — not a copy of
    // it restated here, which would pass while the real one drifted.
    const literal = SW.match(/const CACHEABLE_ASSET = (\/.+\/);/);
    expect(literal, "sw.js must declare CACHEABLE_ASSET as a regex literal").not.toBeNull();
    const rule = new RegExp(literal![1].slice(1, -1));

    expect(rule.test("/assets/root-abc123.js")).toBe(true);
    expect(rule.test("/fonts/inter-latin-wght-normal.woff2")).toBe(true);

    expect(rule.test("/media/ayyuha-al-walad/m4a/ep1.m4a")).toBe(false);
    expect(rule.test("/book/ayyuha-al-walad/read/1")).toBe(false);
    expect(rule.test("/api/auth/session")).toBe(false);
  });

  it("refuses to keep a redirected response", () => {
    // A redirect is what a signed-out request looks like. Caching one serves a
    // sign-in page back to a session that is perfectly fine — and, worse, could
    // outlive the sign-out that produced it.
    const guards = SW.match(/!response\.redirected/g) ?? [];
    expect(guards.length).toBeGreaterThanOrEqual(2);
  });

  it("only ever handles GET", () => {
    expect(SW).toContain('request.method !== "GET"');
  });
});
