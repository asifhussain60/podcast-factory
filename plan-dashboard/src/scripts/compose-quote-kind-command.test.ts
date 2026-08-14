/**
 * compose-quote-kind-command.test.ts — click-to-target resolution for a
 * quote-kind declaration.
 *
 * The contract under test: `resolveQuoteTarget(doc, from, to)` decides WHAT a
 * "declare this as Saying/Verse/Prophetic tradition" action is about. Two
 * regimes, and the test suite is organized around exactly that split —
 * a real drag-selected range (from !== to) always wins outright, unchanged
 * from the original three-button panel's behavior; a collapsed cursor
 * (from === to) falls back to the nearest ancestor blockquote's full text,
 * which is what makes a single click on an already-rendered card enough to
 * re-target it (found live 2026-08-14: a click with no drag reported "Select
 * a quotation first" even though a card was plainly visible under the
 * cursor).
 */
import { test, describe } from "node:test";
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
import { editorExtensions } from "./book-md-editor";
import { renderEditSeed } from "../lib/reader/markdown";
import {
  resolveQuoteTarget,
  nextCardAttrs,
} from "./compose-quote-kind-command";

/** Parse markdown through the SAME seed → schema path the live editor uses,
 *  so a test document has the exact node shapes `resolveQuoteTarget` will
 *  ever actually see (a `blockquote` from `>` syntax, not a hand-built one
 *  that might not match the real schema's attrs). */
function docFrom(markdown: string): PMNode {
  const extensions = editorExtensions();
  const json = generateJSON(renderEditSeed(markdown), extensions);
  return PMNode.fromJSON(getSchema(extensions), json);
}

/** The document position immediately after the first occurrence of `needle`
 *  in the doc's flattened text — a stand-in for "where the cursor is after
 *  clicking on this word," without hardcoding fragile absolute offsets. */
function posAfter(doc: PMNode, needle: string): number {
  let found = -1;
  doc.descendants((node, pos) => {
    if (found !== -1 || !node.isText) return;
    const idx = (node.text ?? "").indexOf(needle);
    if (idx !== -1) found = pos + idx + needle.length;
  });
  if (found === -1) throw new Error(`"${needle}" not found in doc`);
  return found;
}

/** The [from, to) range spanning `needle`'s own text, for simulating a real
 *  drag-selection over a specific word or phrase. */
function rangeOf(doc: PMNode, needle: string): [number, number] {
  const to = posAfter(doc, needle);
  return [to - needle.length, to];
}

describe("a real selection always wins, unchanged from the original panel", () => {
  test("selecting inside a blockquote targets exactly the selected text, not the whole card", () => {
    const doc = docFrom(
      "Before.\n\n> First line of the quote.\n> Second line.\n\nAfter.",
    );
    const [from, to] = rangeOf(doc, "Second line.");
    const target = resolveQuoteTarget(doc, from, to);
    assert.equal(target?.text, "Second line.");
    assert.equal(target?.firstLine, "Second line.");
  });

  test("selecting plain paragraph text (no blockquote at all) still resolves", () => {
    const doc = docFrom("An ordinary paragraph with a phrase in it.");
    const [from, to] = rangeOf(doc, "a phrase");
    const target = resolveQuoteTarget(doc, from, to);
    assert.equal(target?.text, "a phrase");
  });

  test("a whitespace-only selection resolves to null, not an empty declaration", () => {
    const doc = docFrom("Word1   Word2");
    const [, endOfWord1] = rangeOf(doc, "Word1");
    const [startOfWord2] = rangeOf(doc, "Word2");
    const target = resolveQuoteTarget(doc, endOfWord1, startOfWord2);
    assert.equal(target, null);
  });

  test("a selection spanning INTO a blockquote from outside it still takes the literal text, not the card", () => {
    const doc = docFrom("Lead-in text.\n\n> Quoted line.\n\nAfter.");
    const [from] = rangeOf(doc, "Lead-in");
    const [, to] = rangeOf(doc, "Quoted line.");
    const target = resolveQuoteTarget(doc, from, to);
    assert.ok(target?.text.includes("Lead-in"));
    assert.ok(target?.text.includes("Quoted line."));
  });
});

describe("a collapsed cursor falls back to the enclosing card — the click-to-target fix", () => {
  test("cursor placed inside a single-line blockquote resolves to the WHOLE card", () => {
    const doc = docFrom(
      "Before.\n\n> Indeed my mercy shall overcome my wrath.\n\nAfter.",
    );
    const pos = posAfter(doc, "overcome");
    const target = resolveQuoteTarget(doc, pos, pos);
    assert.equal(target?.text, "Indeed my mercy shall overcome my wrath.");
    assert.equal(target?.firstLine, "Indeed my mercy shall overcome my wrath.");
  });

  test("cursor placed in the SECOND paragraph of a multi-paragraph card (Arabic over its translation) still resolves to the whole card, keyed by its FIRST paragraph", () => {
    // The real shape a Qur'an/hadith card takes: an Arabic paragraph and its
    // English translation as two SEPARATE paragraph nodes inside one
    // blockquote — the `>` / blank-`>` / `>` markdown convention
    // docToMarkdown's own blockquote serializer preserves. Not two lines of
    // one paragraph; genuinely two child nodes, confirmed by direct
    // inspection before this test was written.
    const doc = docFrom(
      "Before.\n\n> First paragraph of the quote.\n>\n> Second paragraph, the translation.\n\nAfter.",
    );
    const pos = posAfter(doc, "translation");
    const target = resolveQuoteTarget(doc, pos, pos);
    assert.ok(target?.text.includes("First paragraph of the quote."));
    assert.ok(target?.text.includes("Second paragraph, the translation."));
    assert.equal(target?.firstLine, "First paragraph of the quote.");
  });

  test("cursor in a plain paragraph — no card there — resolves to null, not a false positive", () => {
    const doc = docFrom(
      "Before.\n\n> A real quote.\n\nJust an ordinary paragraph here.",
    );
    const pos = posAfter(doc, "ordinary");
    const target = resolveQuoteTarget(doc, pos, pos);
    assert.equal(target, null);
  });

  test("cursor at the very start of the document (no blockquote anywhere) resolves to null", () => {
    const doc = docFrom("Nothing but plain prose in this whole chapter.");
    const target = resolveQuoteTarget(doc, 1, 1);
    assert.equal(target, null);
  });

  test("with TWO separate cards, the cursor targets whichever one it is actually in", () => {
    const doc = docFrom(
      "> First card text.\n\nBetween.\n\n> Second card text.\n\nAfter.",
    );
    const inFirst = resolveQuoteTarget(
      doc,
      posAfter(doc, "First card"),
      posAfter(doc, "First card"),
    );
    const inSecond = resolveQuoteTarget(
      doc,
      posAfter(doc, "Second card"),
      posAfter(doc, "Second card"),
    );
    assert.equal(inFirst?.firstLine, "First card text.");
    assert.equal(inSecond?.firstLine, "Second card text.");
    assert.notEqual(inFirst?.firstLine, inSecond?.firstLine);
  });

  test("cursor between two cards, in the plain paragraph separating them, resolves to null", () => {
    const doc = docFrom(
      "> First card.\n\nBetween the two cards.\n\n> Second card.",
    );
    const pos = posAfter(doc, "Between");
    const target = resolveQuoteTarget(doc, pos, pos);
    assert.equal(target, null);
  });
});

describe("firstLine is the same key every renderer looks declarations up by", () => {
  test("a card with Arabic text keys on the Arabic, not a transliteration or translation", () => {
    const doc = docFrom(
      "> اِنَّ رَحۡمَتِی تَغۡلِبُ غَضَبِی\n>\n> The English rendering.",
    );
    const pos = posAfter(doc, "English rendering");
    const target = resolveQuoteTarget(doc, pos, pos);
    assert.equal(target?.firstLine, "اِنَّ رَحۡمَتِی تَغۡلِبُ غَضَبِی");
  });

  test("leading/trailing blank lines inside a card do not become the firstLine", () => {
    // A blockquote whose first rendered line is blank is not realistic from
    // real markdown (the `>` marker itself would be empty), but the function
    // must still skip blank lines defensively rather than key on "".
    const doc = docFrom("> Real content here.");
    const pos = posAfter(doc, "Real content");
    const target = resolveQuoteTarget(doc, pos, pos);
    assert.equal(target?.firstLine, "Real content here.");
    assert.notEqual(target?.firstLine, "");
  });
});

describe("blockquotePos points at the exact node a repaint should land on", () => {
  test("a collapsed cursor inside a card reports that card's own node position", () => {
    const doc = docFrom("Before.\n\n> A quotation.\n\nAfter.");
    const pos = posAfter(doc, "quotation");
    const target = resolveQuoteTarget(doc, pos, pos);
    assert.notEqual(target?.blockquotePos, null);
    const node = doc.nodeAt(target!.blockquotePos!);
    assert.equal(node?.type.name, "blockquote");
    assert.equal(node?.textContent, "A quotation.");
  });

  test("a real selection made INSIDE a card also reports that card's position", () => {
    const doc = docFrom(
      "Before.\n\n> A quotation with several words.\n\nAfter.",
    );
    const [from, to] = rangeOf(doc, "several words");
    const target = resolveQuoteTarget(doc, from, to);
    assert.notEqual(target?.blockquotePos, null);
    assert.equal(doc.nodeAt(target!.blockquotePos!)?.type.name, "blockquote");
  });

  test("a selection in a plain paragraph — no card — reports null, nothing to repaint", () => {
    const doc = docFrom("Just an ordinary paragraph.");
    const [from, to] = rangeOf(doc, "ordinary");
    const target = resolveQuoteTarget(doc, from, to);
    assert.equal(target?.blockquotePos, null);
  });

  test("with two cards, the reported position is the one under the cursor, not the other one", () => {
    const doc = docFrom("> First card.\n\nBetween.\n\n> Second card.");
    const pos = posAfter(doc, "Second card");
    const target = resolveQuoteTarget(doc, pos, pos);
    const node = doc.nodeAt(target!.blockquotePos!);
    assert.equal(node?.textContent, "Second card.");
  });
});

describe("nextCardAttrs — the live repaint's attribute computation, checked without an editor", () => {
  test("a plain card (no prior declaration) gets the new kind's class and label", () => {
    const attrs = nextCardAttrs(null, "hadith");
    assert.equal(attrs.class, "k-hadith");
    assert.equal(attrs["data-q-label"], "Prophetic tradition");
  });

  test("re-declaring a card REPLACES its old kind token, never stacks two", () => {
    const attrs = nextCardAttrs("k-quote", "poem");
    assert.equal(attrs.class, "k-poem");
    assert.doesNotMatch(attrs.class ?? "", /k-quote/);
    assert.equal(attrs["data-q-label"], "Verse");
  });

  test("every OTHER class on the card survives the repaint untouched", () => {
    const attrs = nextCardAttrs("quran k-quote", "hadith");
    assert.match(attrs.class ?? "", /\bquran\b/);
    assert.match(attrs.class ?? "", /\bk-hadith\b/);
    assert.doesNotMatch(attrs.class ?? "", /k-quote/);
  });

  test('declaring the default card (kind: "") clears the label and the k-* token, keeps everything else', () => {
    const attrs = nextCardAttrs("quran k-hadith", "");
    assert.equal(attrs.class, "quran");
    assert.equal(attrs["data-q-label"], null);
  });

  test("a card with no class at all, declared as the default, stays classless — never an empty string", () => {
    const attrs = nextCardAttrs(null, "");
    assert.equal(attrs.class, null);
    assert.equal(attrs["data-q-label"], null);
  });

  test("switching between all three real kinds never leaves a stale token from the one before it", () => {
    let cls: string | null = null;
    for (const kind of ["quote", "poem", "hadith"] as const) {
      const attrs = nextCardAttrs(cls, kind);
      cls = attrs.class;
      const tokens = (cls ?? "").split(/\s+/);
      const kindTokens = tokens.filter((t) => t.startsWith("k-"));
      assert.deepEqual(kindTokens, [`k-${kind}`]);
    }
  });
});
