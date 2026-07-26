/**
 * keys.test.ts — the Companion-note chapter key is ONE rule.
 *
 * A note is written by the Composer and read by the LIVE Session. If those two
 * sides derive the chapter key differently the note is stored successfully, the
 * reader looks in another file, and nothing is shown — a silent loss with no
 * error anywhere. These tests pin the rule to the keys already on disk and to the
 * renderer that produces the reader's TOC ids.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { sectionKeyFromHeading, safeChapterKey } from "./keys";
import { anchorKey } from "../../../../scripts/lib/anchor-key.mjs";
import { renderMarkdown } from "../markdown";

test("a numbered heading keeps its ordinal — the reader's TOC id", () => {
  assert.equal(
    sectionKeyFromHeading("## 2. A Stranger in the City"),
    "2-a-stranger-in-the-city",
  );
  // Same result whether the raw heading or its text is passed.
  assert.equal(
    sectionKeyFromHeading("2. A Stranger in the City"),
    "2-a-stranger-in-the-city",
  );
});

test("punctuation is dropped, not hyphenated", () => {
  assert.equal(
    sectionKeyFromHeading("## 3. The Boy at the Door — Limits and Conditions"),
    "3-the-boy-at-the-door-limits-and-conditions",
  );
});

test("the key is storage-safe as-is (no second normalization)", () => {
  for (const h of [
    "## How to Read a Conversation Made of Doors",
    "## 7. The Five Shares and the Long Road to the Shaykh",
  ]) {
    const key = sectionKeyFromHeading(h);
    assert.equal(safeChapterKey(key), key);
  }
});

test("it is NOT anchorKey — that one strips the ordinal", () => {
  const heading = "## 2. A Stranger in the City";
  assert.notEqual(
    sectionKeyFromHeading(heading),
    safeChapterKey(anchorKey(heading)),
  );
});

test("it matches the heading id renderMarkdown emits", () => {
  const html = renderMarkdown("## 2. A Stranger in the City\n\nBody.\n", {
    headingIds: true,
  });
  assert.match(html, /id="2-a-stranger-in-the-city"/);
});
