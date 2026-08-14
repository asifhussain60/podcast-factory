/**
 * vowel-fix.test.ts — the fix-and-vowel button's fallback decision, checked
 * without a network call.
 */
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import {
  needsSearchFallback,
  cleanModelReply,
  NEEDS_SEARCH_TOKEN,
} from "./vowel-fix";

describe("needsSearchFallback — when the primary (non-grounded) reply is not usable", () => {
  test("a real vowelled Arabic reply does not need search", () => {
    assert.equal(needsSearchFallback("رَحِیمٌ"), false);
  });

  test("an empty reply needs search", () => {
    assert.equal(needsSearchFallback(""), true);
  });

  test("whitespace-only reply needs search", () => {
    assert.equal(needsSearchFallback("   \n  "), true);
  });

  test("the model's own admission of uncertainty needs search", () => {
    assert.equal(needsSearchFallback(NEEDS_SEARCH_TOKEN), true);
  });

  test("NEEDS_SEARCH with surrounding whitespace still needs search", () => {
    assert.equal(needsSearchFallback("  NEEDS_SEARCH  "), true);
  });

  test("a reply that is English prose instead of the passage needs search", () => {
    assert.equal(
      needsSearchFallback("I'm not sure what this passage says."),
      true,
    );
  });

  test("a reply that is Arabic but wrapped in commentary elsewhere still passes — the caller cleans it first", () => {
    // needsSearchFallback only judges whether Arabic script is PRESENT; the
    // caller runs cleanModelReply BEFORE this check, so a well-formed model
    // reply never reaches here un-cleaned. This test documents that split
    // of responsibility rather than testing cleanup here too.
    assert.equal(needsSearchFallback("رَحِیمٌ — meaning merciful"), false);
  });
});

describe("cleanModelReply — extracting the passage from a raw model reply", () => {
  test("a plain one-line reply passes through trimmed", () => {
    assert.equal(cleanModelReply("رَحِیمٌ"), "رَحِیمٌ");
  });

  test("a code-fenced reply is unwrapped", () => {
    assert.equal(cleanModelReply("```\nرَحِیمٌ\n```"), "رَحِیمٌ");
  });

  test("a language-tagged code fence is unwrapped too", () => {
    assert.equal(cleanModelReply("```text\nرَحِیمٌ\n```"), "رَحِیمٌ");
  });

  test("surrounding quote marks are stripped", () => {
    assert.equal(cleanModelReply('"رَحِیمٌ"'), "رَحِیمٌ");
  });

  test("guillemets are stripped too", () => {
    assert.equal(cleanModelReply("«رَحِیمٌ»"), "رَحِیمٌ");
  });

  test("a multi-line reply takes the first line that actually has Arabic", () => {
    assert.equal(
      cleanModelReply("Here is the corrected passage:\nرَحِیمٌ\n"),
      "رَحِیمٌ",
    );
  });

  test("a reply with no Arabic anywhere returns null", () => {
    assert.equal(cleanModelReply("I don't know."), null);
  });

  test("an empty reply returns null", () => {
    assert.equal(cleanModelReply(""), null);
  });

  test("NEEDS_SEARCH (no Arabic in it) returns null from cleanModelReply — the caller must check for the token BEFORE cleaning, not after", () => {
    assert.equal(cleanModelReply(NEEDS_SEARCH_TOKEN), null);
  });
});
