/**
 * stage-review.test.ts — the `chapter` argument names a file under `_system/review/`.
 *
 * Until 2026-09-03 it was joined into the path unchecked, and a slug the resolver
 * could not find fell back to content/Islamic/<slug> and created it — so a review
 * POST for a nonexistent book minted a phantom book directory, and a chapter of
 * `../x` wrote beside the pipeline's own state files.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  readReview,
  setChapterFinalized,
  setStageReview,
} from "./stage-review.ts";

const SLUG = "stage-review-test";

function makeRoot(): string {
  const root = mkdtempSync(join(tmpdir(), "stage-review-"));
  mkdirSync(join(root, "content", "Islamic", SLUG, "_system"), {
    recursive: true,
  });
  process.env.PODCAST_FACTORY_ROOT = root;
  return root;
}

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)],
  );
}

test("a valid chapter key writes under _system/review/", () => {
  const root = makeRoot();
  const review = setStageReview(SLUG, "ch-01", "compose", true);
  assert.equal(review.stages.compose.approved, true);
  assert.equal(
    existsSync(
      join(root, "content", "Islamic", SLUG, "_system", "review", "ch-01.json"),
    ),
    true,
  );
});

for (const chapter of ["../x", "../../../../escaped", "a/b", "..", "Ch 1"]) {
  test(`chapter ${JSON.stringify(chapter)} is refused and writes nothing`, () => {
    const root = makeRoot();
    const before = walk(root);
    assert.throws(
      () => setStageReview(SLUG, chapter, "compose", true),
      /chapter/,
    );
    assert.throws(() => setChapterFinalized(SLUG, chapter, true), /chapter/);
    assert.throws(() => readReview(SLUG, chapter), /chapter/);
    assert.deepEqual(walk(root), before);
  });
}

test("a slug the resolver cannot find throws and mints no phantom book", () => {
  const root = makeRoot();
  const before = walk(root);
  assert.throws(
    () => setStageReview("no-such-book", "ch-01", "compose", true),
    /no-such-book/,
  );
  assert.throws(
    () => setChapterFinalized("no-such-book", "ch-01", true),
    /no-such-book/,
  );
  assert.equal(
    existsSync(join(root, "content", "Islamic", "no-such-book")),
    false,
  );
  assert.deepEqual(walk(root), before);
});
