/**
 * fence-decos.test.ts — machine fence markers are recognised in the edit canvas.
 *
 * The contract: a paragraph that is ONLY a fence marker gets decorated (so it
 * reads as apparatus rather than as the chapter's first sentence), the author's
 * prose never does, and the document is untouched either way — a decoration that
 * altered the doc would be written into book.md by the next autosave.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { Window } from "happy-dom";

const win = new Window({ url: "http://localhost/" });
for (const k of ["window", "document", "DOMParser"] as const) {
  try {
    (globalThis as Record<string, unknown>)[k] = (
      win as unknown as Record<string, unknown>
    )[k];
  } catch {
    /* already provided by the host */
  }
}

import { generateJSON, getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";

import {
  docToMarkdown,
  editorExtensions,
} from "../../../scripts/book-md-editor";
import { renderEditSeed } from "../../../lib/reader/markdown";
import { FENCE_KINDS } from "../../../lib/reader/book-fences";
import { fenceMarkerRanges, isFenceMarkerText } from "./fence-decos";

/** Parse markdown exactly as the Composer seeds its editor. */
function docOf(markdown: string): PMNode {
  const extensions = editorExtensions();
  return PMNode.fromJSON(
    getSchema(extensions),
    generateJSON(renderEditSeed(markdown), extensions),
  );
}

test("every fence kind's begin and end marker is recognised", () => {
  for (const kind of FENCE_KINDS) {
    assert.ok(isFenceMarkerText(`${kind}:begin`), `${kind}:begin`);
    assert.ok(isFenceMarkerText(`${kind}:end`), `${kind}:end`);
  }
});

test("prose is never mistaken for a marker", () => {
  for (const text of [
    "This is a work of religious instruction cast as a story.",
    "The book's own opening",
    "edition-intro", // a kind alone is not a marker
    "editorial:middle", // not a side
    "See the editorial:begin marker below.", // marker mentioned inside a sentence
    "",
  ]) {
    assert.equal(isFenceMarkerText(text), false, JSON.stringify(text));
  }
});

test("the real chapter shape decorates only the two marker lines", () => {
  // The opening of the-master-and-the-disciple: the edition introduction is
  // fenced INSIDE the first chapter's body, which is what put a marker on screen.
  const body = [
    "<!-- edition-intro:begin -->",
    "This is a work of religious instruction cast as a story.",
    "",
    "The text is attributed to Jaʿfar ibn Manṣūr al-Yaman.",
    "",
    "### The book's own opening",
    "<!-- edition-intro:end -->",
    "",
    "It has been transmitted that a number of believers came before a Master.",
  ].join("\n");

  const doc = docOf(body);
  const ranges = fenceMarkerRanges(doc);
  assert.equal(ranges.length, 2, "exactly the begin and end lines");

  // What each decorated range actually covers.
  const covered = ranges.map((r) => doc.cut(r.from, r.to).textContent.trim());
  assert.deepEqual(covered, ["edition-intro:begin", "edition-intro:end"]);
});

test("decorating changes nothing the autosave would write", () => {
  const body = [
    "<!-- edition-intro:begin -->",
    "Intro prose.",
    "<!-- edition-intro:end -->",
    "",
    "Chapter prose.",
  ].join("\n");
  const doc = docOf(body);
  const before = docToMarkdown(doc);
  fenceMarkerRanges(doc); // decoration pass
  assert.equal(docToMarkdown(doc), before, "the document must be untouched");
  // The marker text must still be there for preserveFences step 1 to restore.
  assert.match(before, /^edition-intro:begin$/m);
  assert.match(before, /^edition-intro:end$/m);
});

test("a heading that happens to match is not decorated — only paragraphs", () => {
  const doc = docOf("## editorial:begin\n\nprose\n");
  assert.deepEqual(fenceMarkerRanges(doc), []);
});
