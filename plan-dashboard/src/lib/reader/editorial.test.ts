/**
 * editorial.test.ts — the `scope` argument names a file under `_system/editorial/`.
 *
 * Until 2026-09-03 it was joined into the path unchecked, so a scope of
 * `../orchestrator-state` overwrote the pipeline's state file and a deeper
 * traversal landed a JSON file at the content root. The route validated the
 * card id and the slug but never the scope. Both the route and this module now
 * refuse anything that is not `book` or a chapter key.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readEditorial, setEditorialCard } from "./editorial.ts";

const SLUG = "editorial-scope-test";

function makeRoot(): string {
  const root = mkdtempSync(join(tmpdir(), "editorial-"));
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

test("a valid chapter scope writes under _system/editorial/", () => {
  const root = makeRoot();
  const doc = setEditorialCard(SLUG, "ch-01", "key_focus", {
    preset: "general",
  });
  assert.equal(doc.scope, "ch-01");
  assert.equal(
    existsSync(
      join(
        root,
        "content",
        "Islamic",
        SLUG,
        "_system",
        "editorial",
        "ch-01.json",
      ),
    ),
    true,
  );
});

for (const scope of ["../x", "../../../../escaped", "a/b", "..", "Ch 1", ""]) {
  test(`scope ${JSON.stringify(scope)} is refused and writes nothing`, () => {
    const root = makeRoot();
    const before = walk(root);
    assert.throws(
      () =>
        setEditorialCard(SLUG, scope, "key_focus", {
          preset: "general",
        }),
      /scope/,
    );
    assert.throws(() => readEditorial(SLUG, scope), /scope/);
    assert.deepEqual(walk(root), before);
  });
}
