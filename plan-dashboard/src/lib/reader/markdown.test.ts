/**
 * markdown.test.ts — list rendering in the source-bundle profile.
 *
 * Context. `renderSourceMarkdown` is the read-only renderer behind three
 * surfaces: the chapter/file viewer (`studio/[slug]/view.astro`), the Urdu
 * bilingual wisdom view (`bilingual-sections.ts`), and the Book Composer's
 * podcast lane (`scripts/compose-lane.ts`). It ran with `lists: false`, so a
 * real enumeration in a chapter source rendered as one run-together paragraph
 * with the numbering as literal text — 0 `<ol>`, 0 `<li>`.
 *
 * Turning the flag on ALONE would have been worse than leaving it off, and that
 * is what these tests pin. Two defects in the shared list handling:
 *
 *   1. A blank line between items flushed the list, so a loose `1. / 2. / 3.`
 *      became THREE separate `<ol>`s — and since the serializer dropped the
 *      source number and leaned on `<ol>`'s own counter, items 2 and 3 both
 *      DISPLAYED as "1". Loose numbered lists are the dominant style in this
 *      corpus (2,401 of them), so the flag flip would have mis-numbered content
 *      at scale.
 *   2. A list that legitimately starts at 3 renumbered itself to 1.
 *
 * Both are the faked numbering REQ-015 forbids. The fix reproduces the SOURCE
 * ordinal on every ordered item (`<li value="N">`) rather than trusting a
 * counter, and keeps a blank-line-separated list as one list.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  renderEditSeed,
  renderMarkdown,
  renderSourceMarkdown,
} from "./markdown";
import { FENCE_KINDS } from "./book-fences";

/** Ordered-item numbers as the browser would NUMBER them, read back off the
 *  markup — the only thing that matters for "did the numbering survive". */
function renderedNumbers(html: string): number[] {
  const out: number[] = [];
  let counter = 0;
  for (const m of html.matchAll(/<(ol|\/ol|li)(?:\s+value="(\d+)")?[^>]*>/g)) {
    if (m[1] === "ol" || m[1] === "/ol") counter = 0;
    else if (m[2]) out.push((counter = Number(m[2])));
    else out.push(++counter);
  }
  return out;
}

const count = (html: string, tag: string) =>
  (html.match(new RegExp(`<${tag}[\\s>]`, "g")) ?? []).length;

// ── the enumeration that was being flattened ────────────────────────────────

test("a tight numbered list becomes one real ol, numbered from the source", () => {
  const html = renderSourceMarkdown(
    [
      "1. *Retribution* (the law of recompense for bodily harm).",
      "2. *Marriage* (the law that regulates the meeting of the sexes).",
      "3. *Inheritance and division of property*.",
    ].join("\n"),
  );
  assert.equal(count(html, "ol"), 1, "exactly one list");
  assert.equal(count(html, "li"), 3);
  assert.deepEqual(renderedNumbers(html), [1, 2, 3]);
  assert.match(html, /<em>Retribution<\/em>/, "inline markup survives");
  assert.doesNotMatch(
    html,
    /<p>1\./,
    "no literal numbering left in a paragraph",
  );
});

test("a LOOSE numbered list stays ONE list and keeps 1,2,3", () => {
  // The repro: blank lines between items. Before the fix this produced three
  // <ol>s that each displayed "1", so items 2 and 3 lied about their position.
  const html = renderSourceMarkdown(
    "1. The porous body.\n\n2. The veiled era.\n\n3. The closing prayer.\n",
  );
  assert.equal(count(html, "ol"), 1, "a blank line must not split the list");
  assert.equal(count(html, "li"), 3);
  assert.deepEqual(renderedNumbers(html), [1, 2, 3]);
});

test("a list that starts at 3 is not renumbered to 1", () => {
  const html = renderSourceMarkdown("3. Third thing.\n4. Fourth thing.\n");
  assert.deepEqual(renderedNumbers(html), [3, 4]);
});

test("source numbering is reproduced even when it does not ascend", () => {
  // Authors in this corpus repeat "1." per item. Whatever the source says is
  // what the page must show — a counter would silently rewrite it to 1,2,3.
  const html = renderSourceMarkdown("1. One.\n1. Also one.\n1. Still one.\n");
  assert.deepEqual(renderedNumbers(html), [1, 1, 1]);
});

test("a loose bulleted list stays one ul", () => {
  const html = renderSourceMarkdown("- alpha\n\n- beta\n\n- gamma\n");
  assert.equal(count(html, "ul"), 1);
  assert.equal(count(html, "li"), 3);
});

// ── where a list must STOP ──────────────────────────────────────────────────

test("prose after a blank line ends the list rather than joining it", () => {
  const html = renderSourceMarkdown("1. One.\n2. Two.\n\nOrdinary prose.\n");
  assert.equal(count(html, "ol"), 1);
  assert.equal(count(html, "li"), 2);
  assert.match(html, /<p>Ordinary prose\.<\/p>/);
  assert.ok(
    html.indexOf("</ol>") < html.indexOf("<p>Ordinary prose"),
    "the list must close before the paragraph",
  );
});

test("a heading ends the list", () => {
  const html = renderSourceMarkdown("- alpha\n\n## Next section\n\n- beta\n");
  assert.equal(count(html, "ul"), 2, "two lists, split by the heading");
  assert.match(html, /<h2>Next section<\/h2>/);
});

test("switching marker kind starts a new list", () => {
  const html = renderSourceMarkdown("1. one\n\n- bullet\n");
  assert.equal(count(html, "ol"), 1);
  assert.equal(count(html, "ul"), 1);
});

test("a bulleted item may not carry a value attribute", () => {
  // `value` is only meaningful (and only valid) on an ol's items.
  const html = renderSourceMarkdown("- alpha\n- beta\n");
  const ul = html.slice(html.indexOf("<ul"), html.indexOf("</ul>"));
  assert.doesNotMatch(ul, /value=/);
});

// ── the flag still means something, and the rest of the profile is untouched ─

test("lists:false still flattens — the option is not ignored", () => {
  const html = renderMarkdown("1. one\n2. two\n", { lists: false });
  assert.equal(count(html, "ol"), 0);
  assert.equal(count(html, "li"), 0);
  assert.match(html, /1\. one/);
});

test("an italic line is prose, not a bullet", () => {
  // Every podcast chapter source opens with an italic narration-framing
  // paragraph. `*Three Thanks…*` must never be mistaken for a `*` bullet —
  // the marker needs whitespace after it.
  const html = renderSourceMarkdown(
    "*Three Thanks and the Persian Awakening, the opening of a dialogue.*\n",
  );
  assert.equal(count(html, "ul"), 0);
  assert.match(html, /<em>Three Thanks/);
});

test("a thematic break is still a break, not a bullet", () => {
  const html = renderSourceMarkdown("text\n\n---\n\nmore\n");
  assert.match(html, /<hr \/>/);
  assert.equal(count(html, "ul"), 0);
});

test("the source profile's other behaviours are unchanged", () => {
  // Guards the flag change against collateral: tables on, section markers on,
  // heading ids off, transliteration NOT folded.
  const table = renderSourceMarkdown("| a | b |\n| --- | --- |\n| 1 | 2 |\n");
  assert.match(table, /<table/);

  const marker = renderSourceMarkdown("<!-- section 3 (id=7): موضوع -->\n");
  assert.match(marker, /se-section-marker/);

  const heading = renderSourceMarkdown("## Plain Heading\n");
  assert.equal(heading.trim(), "<h2>Plain Heading</h2>");

  const translit = renderSourceMarkdown("He cites Kīmiyāʾ al-Saʿāda.\n");
  assert.match(
    translit,
    /Kīmiyāʾ al-Saʿāda/,
    "no display fold in this profile",
  );
});

// ── machine fences: hidden when displaying, KEPT when seeding the editor ────

test("display renders skip every fence marker instead of showing a chip", () => {
  // These lines delimit spans the Python phases own. Rendered as `.md-comment`
  // chips they put 16 grey `editorial:begin` / `edition-intro:begin` labels into
  // the reader at /studio/<slug>/live, reading as if they were the author's text.
  for (const kind of FENCE_KINDS) {
    const html = renderMarkdown(
      [
        `<!-- ${kind}:begin -->`,
        "The fenced prose.",
        `<!-- ${kind}:end -->`,
      ].join("\n"),
    );
    assert.doesNotMatch(
      html,
      /md-comment/,
      `${kind} rendered as a comment chip`,
    );
    assert.ok(!html.includes(kind), `${kind} leaked as visible text`);
    assert.match(html, /The fenced prose\./, `${kind} swallowed its content`);
  }
});

test("a NON-fence comment is still shown — the skip is targeted", () => {
  // `<!-- page 12 -->` in a transcript is a comment the reader deliberately
  // displays. Only the pipeline's own fence kinds are hidden.
  const html = renderMarkdown("<!-- page 12 -->\n\nProse.\n");
  assert.match(html, /md-comment/);
  assert.match(html, /page 12/);
});

test("the EDIT seed keeps fence markers — they are load-bearing there", () => {
  // TipTap has no comment node, so the marker arrives as bare text; that text is
  // exactly what preserveFences reads back to restore the comment form on save.
  // Skipping it in the seed would strip every fence on the first save.
  const seed = renderEditSeed(
    "<!-- edition-intro:begin -->\nIntro.\n<!-- edition-intro:end -->\n",
  );
  assert.match(seed, /edition-intro:begin/);
  assert.match(seed, /edition-intro:end/);
});

test("a nested blockquote marker is flattened, never printed as text", () => {
  // The augment pass once wrapped model prose that had already opened its own
  // blockquote, so the composed book carried `> > **A clarified term…**` and the
  // surviving ">" rendered mid-sentence in the reading edition. The emitter no
  // longer produces it (scripts/podcast/tests/test_editorial_block_quote_prefix.py);
  // this keeps books composed BEFORE that fix readable without re-composing them.
  const html = renderMarkdown(
    "> **Editorial note (tradition-grounded).**\n> > **A clarified term.** Umma comes from a root.\n",
  );
  assert.match(html, /<blockquote>/);
  assert.match(html, /A clarified term/);
  // The marker must not survive into the rendered text.
  assert.ok(
    !/&gt;\s*<strong>A clarified term/.test(html) && !/>\s*&gt;\s*/.test(html),
    `nested marker leaked into output: ${html}`,
  );
});
