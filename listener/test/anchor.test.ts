import { describe, expect, it } from "vitest";

import { normalizeText, resolveAnchor, type Anchor } from "~/lib/anchor";

/**
 * Where a highlight lands after the book underneath it changes.
 *
 * This is the one piece of the reader that can silently do the WRONG thing: an
 * anchor that fails loudly is a note the reader is told about, but an anchor
 * that lands confidently on a passage it did not come from puts someone's
 * highlight on a different sentence of a religious text and says nothing. Every
 * test below is about that distinction.
 */

const anchor = (over: Partial<Anchor> = {}): Anchor => ({
  blockIndex: 1,
  startOffset: 4,
  endOffset: 15,
  quote: "second here",
  prefix: "the ",
  ...over,
});

describe("resolving an anchor", () => {
  it("finds it where it says it is", () => {
    const blocks = ["first block", "the second here and more"];
    expect(resolveAnchor(anchor(), blocks)).toEqual({
      status: "exact",
      blockIndex: 1,
      startOffset: 4,
      endOffset: 15,
    });
  });

  it("re-finds it after words were inserted earlier in the same paragraph", () => {
    // Every offset after the insertion is now wrong; the quote is not.
    const blocks = ["first block", "and yet the second here and more"];
    expect(resolveAnchor(anchor(), blocks)).toEqual({
      status: "moved",
      blockIndex: 1,
      startOffset: 12,
      endOffset: 23,
    });
  });

  it("re-finds it after the paragraph moved to a different position", () => {
    const blocks = ["a new opening", "first block", "the second here and more"];
    const resolved = resolveAnchor(anchor(), blocks);
    expect(resolved).toEqual({
      status: "moved",
      blockIndex: 2,
      startOffset: 4,
      endOffset: 15,
    });
  });

  it("uses the prefix to choose between two identical passages", () => {
    // The same sentence twice — which this corpus does, repeatedly, with speech
    // tags. Without the prefix the two are indistinguishable and the anchor must
    // refuse; with it, only one is preceded by "the ".
    const blocks = [
      "opening",
      "and second here once",
      "the second here and more",
    ];
    expect(resolveAnchor(anchor({ blockIndex: 9 }), blocks)).toEqual({
      status: "moved",
      blockIndex: 2,
      startOffset: 4,
      endOffset: 15,
    });
  });

  it("refuses when two passages match and the prefix cannot separate them", () => {
    const blocks = [
      "opening",
      "the second here once",
      "the second here and more",
    ];
    expect(resolveAnchor(anchor({ blockIndex: 9 }), blocks)).toEqual({
      status: "orphaned",
    });
  });

  it("reports orphaned when the passage is gone", () => {
    const blocks = ["first block", "this paragraph was rewritten entirely"];
    expect(resolveAnchor(anchor(), blocks)).toEqual({ status: "orphaned" });
  });

  it("reports orphaned rather than throwing when the block index is past the end", () => {
    // A re-compose that DELETED chapters leaves anchors pointing past the last
    // block. Indexing past the end of an array is `undefined`, and reading
    // `.length` of it is the crash this guards.
    expect(
      resolveAnchor(anchor({ blockIndex: 99 }), ["only one block"]),
    ).toEqual({
      status: "orphaned",
    });
  });

  it("treats an empty quote as unresolvable rather than matching everything", () => {
    // `indexOf("")` is 0 for every string. Without the guard, an annotation with
    // an empty quote would silently anchor to the first character of the chapter.
    expect(
      resolveAnchor(anchor({ quote: "   " }), ["anything at all"]),
    ).toEqual({
      status: "orphaned",
    });
  });

  it("survives the whitespace HTML collapses but source does not", () => {
    // `textContent` keeps the newlines and runs of spaces the markdown wrapped
    // with; the rendered page shows one space. Comparing raw text would report
    // "the wording has changed" on a paragraph nobody touched.
    const blocks = ["first block", "the   second\n  here and more"];
    expect(resolveAnchor(anchor(), blocks).status).not.toBe("orphaned");
  });
});

/**
 * A Scholar Companion card knows only the SENTENCE it explains — no block, no
 * offsets, no prefix — so the reader resolves it through this same function with
 * those three left empty. These tests pin that path, because it is the one where
 * the whole-chapter search runs every time rather than as a fallback, and where
 * a wrong answer would tint the wrong sentence of a religious text.
 */
const passage = (quote: string) => ({
  blockIndex: -1,
  startOffset: 0,
  endOffset: 0,
  quote,
  prefix: "",
});

describe("resolving a companion passage, which carries only its quote", () => {
  it("finds it wherever it sits in the chapter", () => {
    const blocks = ["an opening", "the second here and more", "a third"];
    expect(resolveAnchor(passage("second here"), blocks)).toEqual({
      status: "moved",
      blockIndex: 1,
      startOffset: 4,
      endOffset: 15,
    });
  });

  it("refuses when the sentence appears twice, rather than picking the first", () => {
    // Nothing can separate them: a card carries no prefix. Unpainted and said so
    // is the only honest outcome — an explanation attached to the wrong passage
    // would be silent.
    const blocks = ["the same line here", "and the same line here again"];
    expect(resolveAnchor(passage("the same line here"), blocks)).toEqual({
      status: "orphaned",
    });
  });

  it("reports orphaned when the chapter was re-composed out from under it", () => {
    expect(
      resolveAnchor(passage("a sentence long since rewritten"), [
        "nothing like it",
      ]),
    ).toEqual({
      status: "orphaned",
    });
  });

  it("matches across the whitespace the markdown wrapped with", () => {
    expect(
      resolveAnchor(passage("the second here"), [
        "the   second\n  here and more",
      ]).status,
    ).toBe("moved");
  });
});

describe("normalizing text for comparison", () => {
  it("collapses every run of whitespace to one space and trims", () => {
    expect(normalizeText("  a \n\t b  ")).toBe("a b");
  });

  it("leaves ordinary text alone", () => {
    expect(normalizeText("a b c")).toBe("a b c");
  });
});
