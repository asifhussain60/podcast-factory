/**
 * The candidate palette may only offer assets that exist.
 *
 * `book/visuals/index.json` is written by the producers and merged additively by
 * id, so an asset deleted from the folder leaves its entry behind. The Composer
 * used to turn every entry into a candidate regardless — a broken image in the
 * palette and a 404 on every chapter load.
 *
 * Measured on the-master-and-the-disciple, 2026-08-06: all 29 entries pointed at
 * SVGs that commit ef97c27 had removed in July, and none of the 15 slides
 * actually in the folder appeared, because they had never been indexed. The
 * palette was not merely noisy, it was empty of everything real.
 *
 * Nothing cheap enough to run in a test ever asked whether a candidate's file
 * existed — `loadComposer` needs a whole content directory to run — which is why
 * the rule is a pure function and why this file exists.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { partitionByAsset } from "./composer";

test("an entry whose file is on disk is offered", () => {
  const { available, missing } = partitionByAsset(
    [{ file: "slide-1001.jpg" }],
    ["slide-1001.jpg", "index.json"],
  );
  assert.equal(available.length, 1);
  assert.deepEqual(missing, []);
});

test("an entry whose file was deleted is not offered, and is named", () => {
  const { available, missing } = partitionByAsset(
    [{ file: "2-a-stranger-in-the-city-1.svg" }],
    ["index.json"],
  );
  assert.deepEqual(available, []);
  assert.deepEqual(missing, ["2-a-stranger-in-the-city-1.svg"]);
});

test("the real regression: every entry stale, every real asset unindexed", () => {
  // The exact shape of the-master-and-the-disciple. The palette must come back
  // empty rather than full of broken images — an empty palette is legible, 29
  // broken thumbnails are not.
  const stale = Array.from({ length: 29 }, (_, i) => ({
    file: `diagram-${i}.svg`,
  }));
  const onDisk = Array.from({ length: 15 }, (_, i) => `slide-10${i + 1}.jpg`);
  const { available, missing } = partitionByAsset(stale, onDisk);
  assert.equal(available.length, 0);
  assert.equal(missing.length, 29);
});

test("an entry with no file at all is missing, not available", () => {
  // It could only ever produce a request for the empty string.
  const { available, missing } = partitionByAsset(
    [{ file: "" }, {} as { file?: string }],
    ["slide-1001.jpg"],
  );
  assert.deepEqual(available, []);
  assert.deepEqual(missing, ["(no file)", "(no file)"]);
});

test("order is preserved, so the palette does not reshuffle when one asset goes", () => {
  const entries = [{ file: "a.svg" }, { file: "gone.svg" }, { file: "b.svg" }];
  const { available } = partitionByAsset(entries, ["a.svg", "b.svg"]);
  assert.deepEqual(
    available.map((v) => v.file),
    ["a.svg", "b.svg"],
  );
});

test("a directory that cannot be read offers nothing rather than everything", () => {
  // The loader passes [] when readdir fails. Failing OPEN here would restore the
  // exact bug on any book whose visuals folder is absent.
  const { available } = partitionByAsset([{ file: "a.svg" }], []);
  assert.deepEqual(available, []);
});
