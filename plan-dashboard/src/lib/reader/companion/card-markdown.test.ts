/**
 * card-markdown.test.ts — the card's markdown renders, and the trip is closed.
 *
 * The renderer seeds a rich-text editor whose save writes markdown back. If what
 * it renders and what the editor writes disagree, the first save silently rewrites
 * a note — the one failure mode in this feature that loses an author's words.
 * These fixtures pin the shapes the Scholar actually emits.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { cardMarkdownToHtml } from "./card-markdown";
import { cardPreview } from "./explanation-card";
import { capWords, articulationGuardsPass } from "./articulate-rules";

test("a heading becomes a heading, clamped into the card's range", () => {
  assert.equal(
    cardMarkdownToHtml("### Longing for the Source"),
    "<h3>Longing for the Source</h3>",
  );
  // An h1 inside a card would out-shout the card's own title.
  assert.equal(cardMarkdownToHtml("# Top"), "<h3>Top</h3>");
  assert.equal(cardMarkdownToHtml("##### Deep"), "<h4>Deep</h4>");
});

test("both list kinds render, and an ordered list keeps where it started", () => {
  assert.equal(
    cardMarkdownToHtml("- one\n- two"),
    "<ul><li><p>one</p></li><li><p>two</p></li></ul>",
  );
  assert.equal(
    cardMarkdownToHtml("3. third\n4. fourth"),
    '<ol start="3"><li><p>third</p></li><li><p>fourth</p></li></ol>',
  );
});

test("a heading is not fused with the paragraph under it", () => {
  const html = cardMarkdownToHtml("### Title\nThe body follows.");
  assert.equal(html, "<h3>Title</h3><p>The body follows.</p>");
});

test("emphasis and inline code survive; a lone asterisk does not become italics", () => {
  assert.equal(
    cardMarkdownToHtml("**proof** and *longing* and `code`"),
    "<p><strong>proof</strong> and <em>longing</em> and <code>code</code></p>",
  );
});

test("Arabic is wrapped for the reader and left bare for the editor", () => {
  const md = "He needs a proof (برهان), not an argument.";
  assert.match(
    cardMarkdownToHtml(md, { arabicSpans: true }),
    /<span class="xpl-ar" dir="rtl" lang="ar">برهان<\/span>/,
  );
  assert.doesNotMatch(cardMarkdownToHtml(md), /<span/);
});

test("model output cannot inject markup", () => {
  const html = cardMarkdownToHtml('<img src=x onerror="alert(1)"> & <b>no</b>');
  assert.doesNotMatch(html, /<img|<b>/);
  assert.match(html, /&lt;img/);
});

test("the collapsed preview skips the heading and shows the prose", () => {
  const md =
    "### The Awakening of the Soul\n\nThis profound statement captures.";
  assert.equal(cardPreview(md), "This profound statement captures.");
});

test("capWords trims whole blocks, never mid-sentence", () => {
  const md = "### One\n\nalpha beta gamma\n\n### Two\n\ndelta epsilon zeta";
  const capped = capWords(md, 6);
  assert.equal(capped, "### One\n\nalpha beta gamma");
  // A heading with nothing under it is worse than no heading.
  assert.doesNotMatch(capWords(md, 5), /### Two/);
  assert.equal(capWords(md, 500), md);
});

test("articulation may not drop Arabic, a citation, or grow", () => {
  const before = "The proof (برهان) matters.\nQ|2:10\nIt matters twice.";
  assert.equal(
    articulationGuardsPass(before, "The proof (برهان) matters.\nQ|2:10"),
    true,
  );
  // Arabic dropped
  assert.equal(
    articulationGuardsPass(before, "The proof matters.\nQ|2:10"),
    false,
  );
  // citation dropped
  assert.equal(
    articulationGuardsPass(before, "The proof (برهان) matters."),
    false,
  );
  // longer than it started
  assert.equal(
    articulationGuardsPass(before, `${before} And more words.`),
    false,
  );
  assert.equal(articulationGuardsPass(before, "   "), false);
});
