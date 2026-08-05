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
import { readFileSync } from "node:fs";
import { cardMarkdownToHtml } from "./card-markdown";
import { cardPreview } from "./explanation-card";
import { capWords, articulationGuardsPass } from "./articulate-rules";
import { surahName, SURAH_NAMES } from "./surah-names";
import { resolveQuranCitations } from "./quran-citation.server";

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

test("every surah has a name, and 18 is Al-Kahf", () => {
  assert.equal(SURAH_NAMES.length, 114);
  assert.equal(surahName(18), "Al-Kahf");
  assert.equal(surahName(1), "Al-Fatihah");
  assert.equal(surahName(114), "An-Nas");
  assert.equal(surahName(115), "");
  assert.equal(surahName(0), "");
});

// The pin. These names label companion cards here and, since 2026-08-01, are also
// what `scripts/podcast/_book_citations.py` prints into every citation in a
// composed book — so a book saying "(Al-Baqarah: 24)" while a card beside it says
// something else is the failure this prevents. Both sides assert against the same
// fixture; a one-sided edit fails here rather than drifting silently.
test("the surah names match the shared fixture the pipeline also reads", () => {
  const fixture = JSON.parse(
    readFileSync(
      new URL(
        "../../../../scripts/lib/surah-names.fixtures.json",
        import.meta.url,
      ),
      "utf8",
    ),
  ) as { names: string[] };
  assert.deepEqual([...SURAH_NAMES], fixture.names);
});

test("a citation is named, and the verse above it gets its canonical English", () => {
  const md = "> فَوَجَدَا عَبْدًا مِّنْ عِبَادِنَا\n> Q|18:65";
  const out = resolveQuranCitations(md);
  assert.match(out, /Al-Kahf 18:65/);
  assert.doesNotMatch(out, /Q\|/);
  // The rendering is looked up, not generated — and it lands between the script
  // and the citation, inside the same quotation.
  const lines = out.split("\n");
  assert.equal(lines.length, 5);
  assert.match(lines[2], /^> [A-Za-z]/);
  assert.match(lines[4], /Al-Kahf 18:65/);
});

test("a range is named but not translated, and an unknown surah is left alone", () => {
  const ranged = resolveQuranCitations("> الله\n> Q|2:5-10");
  assert.match(ranged, /Al-Baqarah 2:5-10/);
  assert.equal(ranged.split("\n").length, 2); // no rendering inserted
  assert.equal(resolveQuranCitations("Q|200:1"), "Q|200:1");
});

test("text with no citation is returned untouched", () => {
  const md = "### Heading\n\nProse with an Arabic term (برهان) in it.";
  assert.equal(resolveQuranCitations(md), md);
});

test("a verse and its citation sharing ONE line are split into three", () => {
  // What the model actually writes most of the time.
  const md =
    "> \u0648\u064e\u0643\u064e\u0623\u064e\u064a\u0651\u0650\u0646 \u0645\u0651\u0650\u0646\u0652 \u0622\u064a\u064e\u0629\u064d Q|12:105";
  const lines = resolveQuranCitations(md).split("\n");
  // arabic, gap, rendering, gap, citation — the blank quote lines are what make
  // them three PARAGRAPHS rather than one run-on line.
  assert.equal(lines.length, 5);
  assert.match(lines[0], /^> [\u0600-\u06ff]/);
  assert.equal(lines[1], ">");
  assert.match(lines[2], /^> [A-Za-z]/); // the canonical rendering
  assert.equal(lines[3], ">");
  assert.equal(lines[4].trim(), "> Yusuf 12:105");
  assert.ok(lines.every((l) => l.startsWith(">")));
});

test("a verse the model wrote as plain prose becomes a centred quotation", () => {
  // What the persona now produces: named citation, model translation, all on one
  // line, NOT in a blockquote. It must still come out as three quoted rows.
  const stored = resolveQuranCitations(
    "\u0641\u064e\u0648\u064e\u062c\u064e\u062f\u064e\u0627 \u0639\u064e\u0628\u0652\u062f\u064b\u0627 And they found a servant. Al-Kahf 18:65",
  );
  const lines = stored.split("\n");
  assert.ok(
    lines.every((l) => l.startsWith(">")),
    "pulled into a quotation",
  );
  const html = cardMarkdownToHtml(stored, { arabicSpans: true });
  assert.equal(
    (html.match(/<p>/g) ?? []).length,
    3,
    "script, rendering, citation",
  );
  // The canonical rendering replaces the model's paraphrase.
  assert.match(html, /whom We had bestowed mercy|had given mercy/);
  assert.doesNotMatch(html, /And they found a servant\./);
});

test("a resolved verse renders as three lines inside one quotation", () => {
  // The whole chain, stored-markdown to HTML: what the resolver writes is what
  // the reader draws and what seeds the editor.
  const stored = resolveQuranCitations(
    "> \u0641\u064e\u0648\u064e\u062c\u064e\u062f\u064e\u0627 \u0639\u064e\u0628\u0652\u062f\u064b\u0627 Q|18:65",
  );
  const html = cardMarkdownToHtml(stored, { arabicSpans: true });
  assert.match(html, /^<blockquote>/);
  assert.equal(
    (html.match(/<p>/g) ?? []).length,
    3,
    "script, rendering, citation",
  );
  assert.match(html, /<span class="xpl-ar"/);
  assert.match(html, /Al-Kahf 18:65<\/p><\/blockquote>$/);
});
