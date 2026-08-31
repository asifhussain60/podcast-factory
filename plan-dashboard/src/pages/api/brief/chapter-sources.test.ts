/**
 * The reader for what Claude Code writes back.
 *
 * `readChapters` is the seam between a file edited by hand and a form that acts
 * on it, so every shape it has to survive is pinned: the full object, a bare
 * array, coverage marks present and absent, and a file that will not parse at
 * all. A typo in that JSON must leave the page working — it is written by hand
 * every time, which is exactly why it cannot be trusted to be well-formed.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readChapters } from "./chapter-sources";

function withFile(contents: string): string {
  const dir = mkdtempSync(join(tmpdir(), "chapsrc-"));
  writeFileSync(join(dir, "chapters.json"), contents, "utf8");
  return dir;
}

test("the full shape reads back with its coverage marks and note", () => {
  const dir = withFile(
    JSON.stringify({
      chapters: [
        { title: "Miserliness", covered: false },
        { title: "Love of the World", covered: true },
      ],
      note: "the recordings start late",
    }),
  );
  const got = readChapters(dir);
  assert.equal(got?.chapters.length, 2);
  assert.equal(got?.chapters[0].covered, false);
  assert.equal(got?.chapters[1].covered, true);
  assert.equal(got?.note, "the recordings start late");
});

test("a plain list of titles is every chapter covered", () => {
  // A contents page with no transcript to compare against is exactly this: a
  // list of chapters, all of them in play. Absent marks must not read as false,
  // or the Load button would offer nothing.
  const got = readChapters(withFile(JSON.stringify(["Envy", "Anger"])));
  assert.deepEqual(got?.chapters, [
    { title: "Envy", covered: true },
    { title: "Anger", covered: true },
  ]);
});

test("an entry with no coverage mark counts as covered", () => {
  const got = readChapters(
    withFile(JSON.stringify({ chapters: [{ title: "Envy" }] })),
  );
  assert.equal(got?.chapters[0].covered, true);
});

test("blank and untitled entries are dropped, not rendered empty", () => {
  const got = readChapters(
    withFile(
      JSON.stringify({
        chapters: [{ title: "  Envy  " }, { title: "   " }, {}],
      }),
    ),
  );
  assert.deepEqual(
    got?.chapters.map((c) => c.title),
    ["Envy"],
  );
});

test("a file that will not parse reads as absent rather than throwing", () => {
  assert.equal(readChapters(withFile("{ not json at all")), null);
});

test("a parseable file with no chapters in it reads as absent", () => {
  assert.equal(readChapters(withFile(JSON.stringify({ note: "hi" }))), null);
  assert.equal(readChapters(withFile(JSON.stringify({ chapters: [] }))), null);
});

test("a folder with no result yet reads as absent", () => {
  assert.equal(readChapters(mkdtempSync(join(tmpdir(), "chapsrc-"))), null);
});
