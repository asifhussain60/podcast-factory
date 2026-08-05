import { test } from "node:test";
import assert from "node:assert/strict";
import "./_dom.ts";

import { generateJSON, getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import { createMarkdownSerializer } from "../src/serialize/markdown.ts";
import { baseExtensions } from "../src/schema/base-extensions.ts";

const extensions = baseExtensions();
const schema = getSchema(extensions);
const md = createMarkdownSerializer();

/** Parse HTML the way a seeded editor would, then serialize. */
const from = (html: string): string =>
  md.serialize(PMNode.fromJSON(schema, generateJSON(html, extensions)));

test("headings, paragraphs and rules", () => {
  assert.equal(from("<h2>Title</h2>"), "## Title\n");
  assert.equal(from("<h3>Sub</h3>"), "### Sub\n");
  assert.equal(from("<p>plain</p>"), "plain\n");
  assert.equal(from("<hr>"), "---\n");
});

test("marks nest innermost-first so bold+italic composes to ***", () => {
  assert.equal(from("<p><strong>a</strong></p>"), "**a**\n");
  assert.equal(from("<p><em>a</em></p>"), "*a*\n");
  assert.equal(from("<p><strong><em>a</em></strong></p>"), "***a***\n");
  assert.equal(from("<p><code>a</code></p>"), "`a`\n");
  assert.equal(from("<p><s>a</s></p>"), "~~a~~\n");
  assert.equal(
    from('<p><a href="https://x.test">a</a></p>'),
    "[a](https://x.test)\n",
  );
});

test("a blockquote keeps the blank > that separates its paragraphs", () => {
  // Not cosmetic: without it a reader re-parsing this merges the paragraphs,
  // which is how a quoted line and its translation become one run.
  assert.equal(
    from("<blockquote><p>one</p><p>two</p></blockquote>"),
    "> one\n>\n> two\n",
  );
});

test("an ordered list keeps the ordinal each item STATES", () => {
  assert.equal(
    from('<ol><li value="3">c</li><li value="4">d</li></ol>'),
    "3. c\n4. d\n",
  );
  // A repeated "1." is an author style, not a mistake to correct.
  assert.equal(
    from('<ol><li value="1">a</li><li value="1">b</li></ol>'),
    "1. a\n1. b\n",
  );
  // With nothing stated, count.
  assert.equal(from("<ol><li>a</li><li>b</li></ol>"), "1. a\n2. b\n");
});

test("a bullet list uses the configured marker", () => {
  assert.equal(from("<ul><li>a</li><li>b</li></ul>"), "- a\n- b\n");
  const starred = createMarkdownSerializer({ bullet: "*" });
  const doc = PMNode.fromJSON(
    schema,
    generateJSON("<ul><li>a</li></ul>", extensions),
  );
  assert.equal(starred.serialize(doc), "* a\n");
});

test("blocks are separated by a blank line and the file ends with exactly one newline", () => {
  assert.equal(from("<p>a</p><p>b</p>"), "a\n\nb\n");
});

test("a code block carries its language when one is set", () => {
  assert.equal(
    from('<pre><code class="language-js">x = 1</code></pre>'),
    "```js\nx = 1\n```\n",
  );
});
