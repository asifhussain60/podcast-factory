/**
 * Range requests are what make read-along possible.
 *
 * Every click on a paragraph seeks the recording to the second it was spoken,
 * and a browser can only seek when the server answers ranges. These recordings
 * are 500-600 MB, so the alternative — `api/library/file`'s whole-file buffer —
 * is both unseekable and that much memory per request.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseRange } from "./read-along-audio";

const SIZE = 1000;

test("parseRange reads an ordinary range", () => {
  assert.deepEqual(parseRange("bytes=0-499", SIZE), { start: 0, end: 499 });
});

test("parseRange reads an open-ended range as the rest of the file", () => {
  assert.deepEqual(parseRange("bytes=500-", SIZE), { start: 500, end: 999 });
});

test("parseRange reads a suffix range as the last bytes", () => {
  // Players ask for this to read an MP3's trailing metadata before scrubbing.
  assert.deepEqual(parseRange("bytes=-100", SIZE), { start: 900, end: 999 });
});

test("parseRange clamps a range that runs past the end of the file", () => {
  assert.deepEqual(parseRange("bytes=900-5000", SIZE), {
    start: 900,
    end: 999,
  });
});

test("parseRange refuses a range that starts after it ends", () => {
  assert.deepEqual(parseRange("bytes=900-100", SIZE), null);
});

test("parseRange treats no header as no range, so the whole file is sent", () => {
  assert.deepEqual(parseRange(null, SIZE), null);
});

test("parseRange refuses a header it does not understand rather than guessing", () => {
  assert.deepEqual(parseRange("bytes=abc", SIZE), null);
  assert.deepEqual(parseRange("items=0-10", SIZE), null);
  assert.deepEqual(parseRange("bytes=-", SIZE), null);
});
