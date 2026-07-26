/**
 * prose-editor-differential.test.ts — does the package's markdown serializer
 * agree, byte for byte, with the one this repo already trusts?
 *
 * The Composer adopts @asifhussain/prose-editor by handing it `docToMarkdown` —
 * the function that has been writing book.md all along — so nothing about what
 * gets saved changes on adoption day. This test is the gate for the OTHER
 * direction: it is the evidence anyone would need before switching book.md's
 * writer to the package's own serializer, and until it is green over a real
 * corpus that switch must not happen.
 *
 * It lives in the host, not the package, on purpose: the package must not
 * import anything from this repo, and this comparison is a fact about the host's
 * adoption, not about the library.
 *
 * The package is imported by SOURCE path rather than by its published name so
 * this runs with no build step — the same reason its own tests do.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { Window } from "happy-dom";

const win = new Window();
Object.assign(globalThis, {
  window: win,
  document: win.document,
  DOMParser: win.DOMParser,
});

import { generateJSON, getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import { docToMarkdown, editorExtensions } from "./book-md-editor";
import { renderEditSeed } from "../lib/reader/markdown";
import { createMarkdownSerializer } from "../../packages/prose-editor/src/serialize/markdown.ts";

const extensions = editorExtensions();
const schema = getSchema(extensions);
const pkg = createMarkdownSerializer();

/** Parse with the LIVE editor schema, then run both serializers on that one
 *  document — so any difference is the serializers disagreeing, never the
 *  parse. */
function bothWays(markdown: string): { host: string; packaged: string } {
  const doc = PMNode.fromJSON(
    schema,
    generateJSON(renderEditSeed(markdown), extensions),
  );
  return { host: docToMarkdown(doc), packaged: pkg.serialize(doc) };
}

/** The host's own round-trip fixtures, plus the shapes the toolbar adds. */
const CORPUS: Array<[name: string, markdown: string]> = [
  [
    "Arabic with a straight-quoted gloss",
    "his name, given much later, is Salih (صالح, 'the righteous'). **His father** is al-Bakhtari (البختري).",
  ],
  [
    "scholarly transliteration glyphs",
    "He cites Kīmiyāʾ al-Saʿāda and ʿUlūm al-Dīn by name.",
  ],
  [
    "multi-paragraph with bold and italics",
    [
      "**The Master** is a Persian who came to knowledge late.",
      "",
      "*A single life carried well* will teach you more than a hundred maxims.",
    ].join("\n"),
  ],
  [
    "Arabic blockquote over its translation",
    [
      "> شُكْرُ الْعَالِمِ طَاعَتُهُ",
      ">",
      '> "Thanks to the teacher is to obey him."',
    ].join("\n"),
  ],
  ["heading levels", "## Chapter\n\n### Section\n\n#### Subsection"],
  ["ordered list starting at three", "3. the third\n4. the fourth"],
  ["ordered list repeating one", "1. first\n1. second\n1. third"],
  ["bullet list", "- alpha\n- beta"],
  ["horizontal rule between blocks", "before\n\n---\n\nafter"],
  [
    "inline code and a link",
    "Run `make` then read [the docs](https://x.test).",
  ],
  ["bold and italic together", "***emphatically so***"],
  ["a quote with a single line", "> one line only"],
];

for (const [name, markdown] of CORPUS) {
  test(`package and host serializers agree: ${name}`, () => {
    const { host, packaged } = bothWays(markdown);
    assert.equal(
      packaged,
      host,
      `Serializers disagree.\n  host:     ${JSON.stringify(host)}\n  packaged: ${JSON.stringify(packaged)}`,
    );
  });
}

test("the package covers every type the live editor schema can produce", () => {
  // If this fails, the package could not serve as the host's writer at all —
  // some type the editor can create has no rule.
  const covered = new Set(pkg.covers);
  const missing = [
    ...Object.keys(schema.nodes),
    ...Object.keys(schema.marks),
  ].filter((n) => !covered.has(n));
  assert.deepEqual(missing, []);
});
