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

/** Parse a doc from ProseMirror JSON with the live schema — for asserting on
 *  structures a toolbar BUILDS, which have no markdown spelling to seed from. */
function docFromJSON(content: unknown[]): PMNode {
  return PMNode.fromJSON(getSchema(editorExtensions()), {
    type: "doc",
    content,
  });
}

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

// ── The serializer holes a richer toolbar would turn into corruption ──────────
// Each of these round-trips green today only because renderEditSeed happens not
// to emit the shape. A toolbar that can MAKE the shape needs the code invariant.

test("an ordered list starting at 3 is not renumbered to 1", () => {
  // The case markdown.ts's flushList carries `value=` for: renumbering it is the
  // faked numbering REQ-015 forbids, written straight into book.md.
  const src = ["3. the third condition", "4. the fourth condition"].join("\n");
  assert.equal(roundTrip(src), normalized(src));
});

test("an author style that repeats 1. per item survives verbatim", () => {
  const src = ["1. first", "1. second", "1. third"].join("\n");
  assert.equal(roundTrip(src), normalized(src));
});

test("a list the toolbar builds, with no stated ordinals, numbers from 1", () => {
  const item = (text: string) => ({
    type: "listItem",
    content: [{ type: "paragraph", content: [{ type: "text", text }] }],
  });
  const doc = docFromJSON([
    { type: "orderedList", content: [item("alpha"), item("beta")] },
  ]);
  assert.equal(docToMarkdown(doc), "1. alpha\n2. beta\n");
});

test("no schema type exists that docToMarkdown would silently discard", () => {
  const schema = getSchema(editorExtensions());
  // Underline and hardBreak both serialized to nothing. Removing the buttons
  // would not have been enough — Mod-U and Shift+Enter reach them regardless.
  assert.equal(schema.marks.underline, undefined);
  assert.equal(schema.nodes.hardBreak, undefined);
});

test("links are deliberate: autolink and linkOnPaste are off", () => {
  // On by default, so typing a bare domain in prose wrote [text](href) into
  // book.md and the printed PDF gained a link nobody authored.
  const link = editorExtensions()
    .flatMap((e) => ("config" in e ? [e] : [e]))
    .find((e) => e.name === "starterKit");
  assert.ok(link, "StarterKit must be present to carry the link options");
  const opts = (link as { options?: Record<string, unknown> }).options ?? {};
  assert.deepEqual(opts.link, {
    autolink: false,
    linkOnPaste: false,
    openOnClick: false,
  });
});

test("a Quranic quotation the toolbar inserts is a serialization fixed point", () => {
  // blockquote.quran > p.ar + p.tr is the ONE structure QuotationClasses
  // preserves and flushQuote re-derives — the shape the custom button must emit.
  const doc = docFromJSON([
    {
      type: "blockquote",
      attrs: { class: "quran" },
      content: [
        {
          type: "paragraph",
          attrs: { class: "ar" },
          content: [{ type: "text", text: "شُكْرُ الْعَالِمِ طَاعَتُهُ" }],
        },
        {
          type: "paragraph",
          attrs: { class: "tr" },
          content: [{ type: "text", text: "Thanks to the teacher is to obey him." }],
        },
      ],
    },
  ]);
  const once = docToMarkdown(doc);
  assert.equal(roundTrip(once), once, "second pass must equal the first");
});
