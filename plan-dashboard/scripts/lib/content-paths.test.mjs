/**
 * content-paths.test.mjs — the JS half of the content-paths <-> _paths mirror pair.
 *
 * The Python half is `tests/test_paths_mirror.py`. Both read the SAME fixture file,
 * `content-paths.fixtures.json`, so an implementation change on either side that is
 * not matched on the other fails a test.
 *
 * Until 2026-07-26 nothing checked these two agreed, and they had drifted: the
 * legacy resolution ladders broke ties differently, so a repo carrying both a flat
 * `content/drafts/<slug>` and a categorised `content/published/books/<slug>`
 * resolved to two DIFFERENT directories depending on whether the pipeline or this
 * site asked. See the fixture's `_comment` block for the full rationale.
 *
 * `getRepoRoot()` re-reads PODCAST_FACTORY_ROOT on every call, so each layout case
 * simply points the env var at its own temp tree — no module reload needed (the
 * Python side does need one; it snapshots at import).
 *
 * Run: cd plan-dashboard && npm test
 */

import assert from "node:assert/strict";
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  writeFileSync,
  existsSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  BUCKETS,
  ALLOWED_CATEGORIES,
  WORK_MANIFEST_NAME,
  findContent,
  findContentDirSync,
  slugOf,
  statusOf,
} from "../../src/lib/content-paths.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIX = JSON.parse(
  readFileSync(join(HERE, "content-paths.fixtures.json"), "utf8"),
);

/** Run `fn` with PODCAST_FACTORY_ROOT bound to a throwaway tree, then clean up. */
function withTempRoot(fn) {
  const previous = process.env.PODCAST_FACTORY_ROOT;
  const root = mkdtempSync(join(tmpdir(), "content-paths-mirror-"));
  process.env.PODCAST_FACTORY_ROOT = root;
  try {
    return fn(root);
  } finally {
    if (previous === undefined) delete process.env.PODCAST_FACTORY_ROOT;
    else process.env.PODCAST_FACTORY_ROOT = previous;
    rmSync(root, { recursive: true, force: true });
  }
}

function fsIsCaseSensitive(root) {
  mkdirSync(join(root, "CaseProbe"));
  return !existsSync(join(root, "caseprobe"));
}

function materialise(root, testCase) {
  for (const d of testCase.tree ?? [])
    mkdirSync(join(root, d), { recursive: true });
  for (const [rel, body] of Object.entries(testCase.files ?? {})) {
    const target = join(root, rel);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, body, "utf8");
  }
}

// ── vocabulary — catches an enum extended on one side only ────────────────────
test("vocabulary matches the shared fixtures", () => {
  const v = FIX.vocabulary;
  assert.deepEqual([...BUCKETS], v.buckets);
  assert.deepEqual([...ALLOWED_CATEGORIES], v.allowed_categories);
  assert.equal(WORK_MANIFEST_NAME, v.work_manifest_name);
});

// ── regex dialect — the anchorKey bug class, in a second place ────────────────
test("the volume-dir pattern matches the shared fixtures", () => {
  // JS \d is ASCII-only and Python's is Unicode-aware. Both sides now spell the
  // digit class out explicitly so `vol-٠١` is rejected identically.
  const VOL_DIR_RE = /^vol-[0-9]+$/;
  for (const c of FIX.vol_dir_cases) {
    assert.equal(VOL_DIR_RE.test(c.in), c.is_vol, JSON.stringify(c.in));
  }
});

test("the composite-slug pattern matches the shared fixtures", () => {
  const COMPOSITE_SLUG_RE = /^(.+)-(vol-[0-9]+)$/;
  for (const c of FIX.composite_slug_cases) {
    const m = COMPOSITE_SLUG_RE.exec(c.in);
    if (c.work === null) {
      assert.equal(m, null, JSON.stringify(c.in));
    } else {
      assert.ok(m, JSON.stringify(c.in));
      assert.equal(m[1], c.work, JSON.stringify(c.in));
      assert.equal(m[2], c.dir, JSON.stringify(c.in));
    }
  }
});

// ── on-disk resolution — the precedence assertions ────────────────────────────
for (const testCase of FIX.layout_cases) {
  test(`layout: ${testCase.name}`, (t) => {
    withTempRoot((root) => {
      if (testCase.requires_case_sensitive_fs && !fsIsCaseSensitive(root)) {
        t.skip(
          "case-insensitive filesystem — outcome would vary by platform, not by implementation",
        );
        return;
      }
      materialise(root, testCase);
      const found = findContentDirSync(testCase.slug);

      if (testCase.expect_dir === null) {
        assert.equal(
          found,
          null,
          `expected no match for ${testCase.slug}, got ${found}`,
        );
        return;
      }
      assert.ok(
        found,
        `expected ${testCase.expect_dir} for ${testCase.slug}, got no match`,
      );
      assert.equal(found.slice(root.length + 1), testCase.expect_dir);
    });
  });
}

// The ASYNC twin. findContent is what most of the site actually calls, and it is a
// SECOND hand-written copy of the same ladder — which is how it ended up with a
// LECTURES guard the sync version lacked and without the nested-BOOKS fallback the
// sync version had. Both ladders are pinned against the same fixture so neither can
// drift from Python or from each other.
for (const testCase of FIX.layout_cases) {
  test(`layout (async): ${testCase.name}`, async (t) => {
    const previous = process.env.PODCAST_FACTORY_ROOT;
    const root = mkdtempSync(join(tmpdir(), "content-paths-mirror-"));
    process.env.PODCAST_FACTORY_ROOT = root;
    try {
      if (testCase.requires_case_sensitive_fs && !fsIsCaseSensitive(root)) {
        t.skip(
          "case-insensitive filesystem — outcome would vary by platform, not by implementation",
        );
        return;
      }
      materialise(root, testCase);
      const ref = await findContent(testCase.slug);

      if (testCase.expect_dir === null) {
        assert.equal(
          ref,
          null,
          `expected no match for ${testCase.slug}, got ${ref?.dir}`,
        );
        return;
      }
      assert.ok(
        ref,
        `expected ${testCase.expect_dir} for ${testCase.slug}, got no match`,
      );
      assert.equal(ref.dir.slice(root.length + 1), testCase.expect_dir);
    } finally {
      if (previous === undefined) delete process.env.PODCAST_FACTORY_ROOT;
      else process.env.PODCAST_FACTORY_ROOT = previous;
      rmSync(root, { recursive: true, force: true });
    }
  });
}

test("status cases match the shared fixtures", async () => {
  // statusOf is async here and synchronous in Python; the CONTRACT being pinned is
  // the value, not the calling convention.
  for (const c of FIX.status_cases) {
    const previous = process.env.PODCAST_FACTORY_ROOT;
    const root = mkdtempSync(join(tmpdir(), "content-paths-mirror-"));
    process.env.PODCAST_FACTORY_ROOT = root;
    try {
      const book = join(root, "content", "Islamic", "book");
      mkdirSync(join(book, "_system"), { recursive: true });
      writeFileSync(
        join(book, "_system", "orchestrator-state.json"),
        c.state,
        "utf8",
      );
      assert.equal(await statusOf(book), c.expect, c.name);
    } finally {
      if (previous === undefined) delete process.env.PODCAST_FACTORY_ROOT;
      else process.env.PODCAST_FACTORY_ROOT = previous;
      rmSync(root, { recursive: true, force: true });
    }
  }
});

test("slugOf returns the composite slug for a volume dir", () => {
  // Two works can each contain a `vol-01`; the plain dir name is not a stable
  // identity. Mirrors _paths.slug_of.
  withTempRoot((root) => {
    const work = join(root, "content", "Islamic", "work-a");
    mkdirSync(join(work, "vol-01"), { recursive: true });
    writeFileSync(join(work, WORK_MANIFEST_NAME), "title: Work A\n", "utf8");
    assert.equal(slugOf(join(work, "vol-01")), "work-a-vol-01");
    assert.equal(slugOf(work), "work-a");

    const loose = join(root, "content", "Islamic", "notwork");
    mkdirSync(join(loose, "vol-01"), { recursive: true });
    assert.equal(
      slugOf(join(loose, "vol-01")),
      "vol-01",
      "no work.yml marker means no composite slug",
    );
  });
});
