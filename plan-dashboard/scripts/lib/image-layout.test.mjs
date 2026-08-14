/**
 * image-layout.test.mjs — read/write round-trip for the per-image resize sidecar.
 * Run: node --test plan-dashboard/scripts/lib/image-layout.test.mjs
 */
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import {
  readImageLayout,
  writeImageLayout,
  flattenImageLayout,
} from "./image-layout.mjs";

test("a book with no image-layout.json reads as empty", () => {
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    assert.deepEqual(readImageLayout(tmp), {});
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test("a malformed store yields nothing rather than raising", () => {
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    const sys = path.join(tmp, "_system");
    mkdirSync(sys, { recursive: true });
    writeFileSync(path.join(sys, "image-layout.json"), "{ not json", "utf-8");
    assert.deepEqual(readImageLayout(tmp), {});
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test("writeImageLayout round-trips a real resize through a temp book dir", () => {
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    writeImageLayout(tmp, "chapter one", "images/103/abc.jpg", {
      height_px: 500,
      align: "left",
    });
    const read = readImageLayout(tmp);
    assert.deepEqual(read, {
      "chapter one": {
        "images/103/abc.jpg": { height_px: 500, align: "left" },
      },
    });
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test("writing back the defaults clears the entry rather than recording it", () => {
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    writeImageLayout(tmp, "chapter one", "images/103/abc.jpg", {
      height_px: 500,
      align: "left",
    });
    writeImageLayout(tmp, "chapter one", "images/103/abc.jpg", {
      height_px: 350,
      align: "center",
    });
    assert.deepEqual(readImageLayout(tmp), {});
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test("saving align alone does not erase a previously saved height (the drag-then-click case)", () => {
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    writeImageLayout(tmp, "chapter one", "images/103/abc.jpg", {
      height_px: 500,
    });
    writeImageLayout(tmp, "chapter one", "images/103/abc.jpg", {
      align: "left",
    });
    const read = readImageLayout(tmp);
    assert.deepEqual(read, {
      "chapter one": {
        "images/103/abc.jpg": { height_px: 500, align: "left" },
      },
    });
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test("a partial declaration (height only) keeps the other at its default", () => {
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    writeImageLayout(tmp, "chapter one", "images/103/abc.jpg", {
      height_px: 420,
    });
    const read = readImageLayout(tmp);
    assert.deepEqual(read, {
      "chapter one": { "images/103/abc.jpg": { height_px: 420 } },
    });
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test("flattenImageLayout merges chapters into one src-keyed map", () => {
  const flat = flattenImageLayout({
    "chapter one": { "images/a.jpg": { height_px: 500 } },
    "chapter two": { "images/b.jpg": { align: "right" } },
  });
  assert.deepEqual(flat, {
    "images/a.jpg": { height_px: 500 },
    "images/b.jpg": { align: "right" },
  });
});

test("out-of-range or invalid values are dropped, not trusted into a class", () => {
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    writeImageLayout(tmp, "chapter one", "images/103/abc.jpg", {
      height_px: 5000,
      align: "diagonal",
    });
    assert.deepEqual(readImageLayout(tmp), {});
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test("a v1 file (width_pct) reads as empty, never misread as a pixel count", () => {
  // The one thing worse than losing a saved size is applying last version's
  // number under this version's unit — a leftover `width_pct: 49` must never
  // be read back as `height_px: 49` (a 49px-tall picture).
  const tmp = mkdtempSync(path.join(tmpdir(), "image-layout-test-"));
  try {
    const sys = path.join(tmp, "_system");
    mkdirSync(sys, { recursive: true });
    writeFileSync(
      path.join(sys, "image-layout.json"),
      JSON.stringify({
        schema: "book.image-layout/v1",
        chapters: {
          "chapter one": { "images/103/abc.jpg": { width_pct: 49 } },
        },
      }),
      "utf-8",
    );
    assert.deepEqual(readImageLayout(tmp), {});
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});
