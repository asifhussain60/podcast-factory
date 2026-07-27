/**
 * The envelope-leak guard. On 2026-07-27 /api/ai/rewrite handed the Composer a
 * literal `{"options": [...]}` blob as its one "rewrite", one click from pasting
 * JSON into a book. The cause was a TRUNCATED model response: no closing brace
 * for the regex, no valid document for JSON.parse, so the raw fragment was
 * wrapped as options[0]. These cases pin the recovery.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { salvage } from "./rewrite";

test("passes clean options straight through", () => {
  assert.deepEqual(salvage(["one", "two"]), ["one", "two"]);
});

test("unwraps a COMPLETE envelope that was wrapped as a single option", () => {
  const blob = JSON.stringify({ options: ["alpha", "beta", "gamma"] });
  assert.deepEqual(salvage([blob]), ["alpha", "beta", "gamma"]);
});

test("salvages the finished rewrites from a TRUNCATED envelope", () => {
  // Exactly the shape observed live: two complete literals, third cut mid-word.
  const truncated =
    '{\n  "options": [\n    "first done",\n    "second done",\n    "third half-writ';
  assert.deepEqual(salvage([truncated]), ["first done", "second done"]);
});

test("keeps escapes intact when salvaging", () => {
  const truncated = '{"options": ["He said, \\"yes\\" — plainly.", "unfinis';
  assert.deepEqual(salvage([truncated]), ['He said, "yes" — plainly.']);
});

test("returns nothing rather than an envelope when nothing survives", () => {
  // No complete literal after `[` — the caller must report "no suggestions".
  assert.deepEqual(salvage(['{"options": ["half a th']), []);
});

test("never emits a string that is itself an envelope", () => {
  for (const input of [
    ['{"options": ["ok one"]}'],
    ['{\n "options": [\n "ok two"'],
    ["plain rewrite"],
  ]) {
    for (const out of salvage(input)) {
      assert.ok(
        !(out.trimStart().startsWith("{") && out.includes('"options"')),
        `leaked an envelope: ${out.slice(0, 40)}`,
      );
    }
  }
});
