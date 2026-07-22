/**
 * book-md-editor.test.ts — the Composer's seed → parse → serialize round trip.
 *
 * The contract under test: a chapter body seeded into the editor and saved
 * back WITHOUT any keystroke must return byte-identical markdown. The seed is
 * renderEditSeed (composer.ts feeds it to TipTap as editHtml); the parse uses
 * the SAME extension set the live editor mounts (editorExtensions); the
 * serialize is the SAME docToMarkdown the autosave calls. Anything this trip
 * loses, a real autosave writes into book.md as silent corruption.
 *
 * Regression anchor: the default renderMarkdown profile folds transliteration
 * for display, and that fold ate the OPENING straight apostrophe of quoted
 * phrases — "(صالح, 'the righteous')" came back "(صالح, the righteous')"
 * (found 2026-07-22). The edit seed must never run display-only folds.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { Window } from "happy-dom";

// TipTap's generateJSON parses HTML through the global DOMParser; give the
// node:test process a DOM before the round trip runs.
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

/** Seed exactly as composer.ts does, parse with the live editor's schema,
 *  serialize exactly as autosave does. */
function roundTrip(markdown: string): string {
  const extensions = editorExtensions();
  const json = generateJSON(renderEditSeed(markdown), extensions);
  const doc = PMNode.fromJSON(getSchema(extensions), json);
  return docToMarkdown(doc);
}

/** docToMarkdown normalizes to a single trailing newline; compare bodies in
 *  that form so every assertion is a byte-identity check. */
function normalized(markdown: string): string {
  return markdown.trim() + "\n";
}

test("straight-quoted phrase after Arabic + comma survives byte-identically (the repro)", () => {
  const src =
    "his name, given much later, is Salih (صالح, 'the righteous'). **His father** is al-Bakhtari (البختري).";
  assert.equal(roundTrip(src), normalized(src));
});

test("straight-quoted phrase inside parentheses adjacent to Arabic survives", () => {
  const src = `Abu Malik said to al-Bakhtari, "O Abu Salih (أبا صالح, 'father of Salih'), how is your good son?"`;
  assert.equal(roundTrip(src), normalized(src));
});

test("quoted phrase at paragraph start and after an em dash survives", () => {
  const src =
    "'The righteous' is how the book names him — 'the righteous', nothing more.";
  assert.equal(roundTrip(src), normalized(src));
});

test("English clitics and possessives are untouched alongside quoted phrases", () => {
  const src =
    "God's mercy doesn't end; the brothers' books call him 'the righteous' still.";
  assert.equal(roundTrip(src), normalized(src));
});

test("scholarly transliteration glyphs survive the edit seed unfolded", () => {
  // Display surfaces fold Kīmiyāʾ → Kimiya; the EDITOR must show and return
  // the file's actual bytes, or the fold becomes a save-time rewrite.
  const src = "He cites Kīmiyāʾ al-Saʿāda and ʿUlūm al-Dīn by name.";
  assert.equal(roundTrip(src), normalized(src));
});

test("multi-paragraph body with bold, italics and quotes round-trips", () => {
  const src = [
    "**The Master** is a Persian who came to knowledge late, after years of ignorance.",
    "",
    "**The boy** follows him, is refused, and is admitted only on conditions; his name is Salih (صالح, 'the righteous').",
    "",
    "*A single life carried well* will teach you more than a hundred maxims.",
  ].join("\n");
  assert.equal(roundTrip(src), normalized(src));
});

test("Arabic blockquote with quoted translation keeps its shape and quotes", () => {
  const src = [
    "> شُكْرُ الْعَالِمِ طَاعَتُهُ",
    ">",
    '> "Thanks to the teacher is to obey him."',
  ].join("\n");
  assert.equal(roundTrip(src), normalized(src));
});
