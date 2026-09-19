// Contract for the Studio Preview cache: a page LOAD must never destroy a cache it
// cannot rebuild. Before this test, ensurePreviewPageImages() deleted
// book/_preview-cache/ first and rendered second, so a machine without the right
// browser build turned every visit into an empty cache plus a 500.
import assert from "node:assert/strict";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  rmSync,
  utimesSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { ensurePreviewPageImages } from "./preview-pages.mjs";

function makeBook() {
  const bookDir = mkdtempSync(join(tmpdir(), "preview-pages-"));
  mkdirSync(join(bookDir, "book"), { recursive: true });
  writeFileSync(join(bookDir, "book", "book.md"), "# A\n");
  return bookDir;
}

function seedStaleCache(bookDir) {
  const cache = join(bookDir, "book", "_preview-cache");
  mkdirSync(cache, { recursive: true });
  writeFileSync(join(cache, "page-001.png"), "old");
  writeFileSync(join(cache, "preview.pdf"), "old");
  // older than book.md, so the cache is stale
  const past = new Date(Date.now() - 60_000);
  utimesSync(join(cache, "preview.pdf"), past, past);
  return cache;
}

// Stands in for node/pdftoppm: the renderer writes the PDF, the rasteriser writes pages.
function workingRunner(pages) {
  return (cmd, args) => {
    if (cmd === "node") writeFileSync(args[2], "%PDF");
    else {
      const prefix = args[args.length - 1];
      for (let i = 1; i <= pages; i++)
        writeFileSync(`${prefix}-${String(i).padStart(3, "0")}.png`, "new");
    }
  };
}

const failingRunner = () => {
  throw new Error("browser build missing");
};

test("a failed render keeps the previous cache and reports the error", () => {
  const bookDir = makeBook();
  const cache = seedStaleCache(bookDir);
  const result = ensurePreviewPageImages(bookDir, { run: failingRunner });
  assert.equal(result.regenerated, false);
  assert.match(result.error, /browser build missing/);
  assert.deepEqual(readdirSync(cache).sort(), ["page-001.png", "preview.pdf"]);
  assert.equal(result.pageCount, 1);
  rmSync(bookDir, { recursive: true, force: true });
});

test("a failed render leaves no half-built scratch directory behind", () => {
  const bookDir = makeBook();
  seedStaleCache(bookDir);
  ensurePreviewPageImages(bookDir, { run: failingRunner });
  assert.deepEqual(
    readdirSync(join(bookDir, "book")).filter((n) => n.includes("_preview")),
    ["_preview-cache"],
  );
  rmSync(bookDir, { recursive: true, force: true });
});

test("a successful render replaces the stale cache", () => {
  const bookDir = makeBook();
  const cache = seedStaleCache(bookDir);
  const result = ensurePreviewPageImages(bookDir, { run: workingRunner(2) });
  assert.equal(result.regenerated, true);
  assert.equal(result.error, undefined);
  assert.equal(result.pageCount, 2);
  assert.ok(existsSync(join(cache, "preview.pdf")));
  rmSync(bookDir, { recursive: true, force: true });
});

test("a book with no book.md renders nothing and touches nothing", () => {
  const bookDir = mkdtempSync(join(tmpdir(), "preview-pages-"));
  const result = ensurePreviewPageImages(bookDir, { run: failingRunner });
  assert.equal(result.pageCount, 0);
  assert.equal(result.regenerated, false);
  rmSync(bookDir, { recursive: true, force: true });
});
