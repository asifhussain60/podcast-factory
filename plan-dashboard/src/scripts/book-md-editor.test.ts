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
import {
  PRESERVED_CLASSES,
  docToMarkdown,
  editorExtensions,
} from "./book-md-editor";
import { alignablePositions } from "../components/studio/editor/align-decos";
import { renderEditSeed } from "../lib/reader/markdown";
import { serveBookImages, originalBookSrc } from "../lib/reader/book-images";

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

test("alignment positions include top-level lists but skip headings and quotes", () => {
  const item = (text: string) => ({
    type: "listItem",
    content: [{ type: "paragraph", content: [{ type: "text", text }] }],
  });
  const doc = docFromJSON([
    { type: "paragraph", content: [{ type: "text", text: "First paragraph" }] },
    {
      type: "heading",
      attrs: { level: 3 },
      content: [{ type: "text", text: "A heading" }],
    },
    {
      type: "bulletList",
      content: [item("first item"), item("second item")],
    },
    {
      type: "blockquote",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "Quoted text" }],
        },
      ],
    },
    { type: "paragraph", content: [{ type: "text", text: "Final paragraph" }] },
  ]);

  const positions = alignablePositions(doc, ["a", "b", "c"]);

  assert.deepEqual(
    positions.map((p) => p.key),
    ["a", "b", "c"],
  );
  assert.equal(doc.nodeAt(positions[1].from)?.type.name, "bulletList");
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
          content: [
            { type: "text", text: "Thanks to the teacher is to obey him." },
          ],
        },
      ],
    },
  ]);
  const once = docToMarkdown(doc);
  assert.equal(roundTrip(once), once, "second pass must equal the first");
});

test("the four card classes survive the parse, and nothing else does", () => {
  // Asif photographed a Qur'anic verse in Edit set in the plain maroon this repo
  // used before the cards, while Read and the PDF drew it in gold on its own
  // plate. The seed was emitting `k-quran`; this allowlist was dropping it, and
  // it is the one place that can.
  for (const kind of ["k-quran", "k-hadith", "k-poem", "k-quote"]) {
    assert.ok(
      PRESERVED_CLASSES.has(kind),
      `${kind} must reach the edit canvas or a card renders as a plain quotation`,
    );
  }
  // The allowlist is still an allowlist: a hand-pasted class cannot ride in.
  for (const forged of ["k-anything", "onclick", "hljs", "q-band"]) {
    assert.ok(
      !PRESERVED_CLASSES.has(forged),
      `${forged} must not be preserved`,
    );
  }
});

test("a card class never reaches book.md", () => {
  // The whole reason a class is safe to carry: docToMarkdown dispatches on the
  // node type and reads exactly one attribute (heading.level), so the card is
  // presentation on the canvas and cannot be serialized into the book.
  const doc = docFromJSON([
    {
      type: "blockquote",
      attrs: { class: "quran k-quran" },
      content: [
        {
          type: "paragraph",
          attrs: { class: "ar is-quranic" },
          content: [{ type: "text", text: "ٱرْجِعِىٓ إِلَىٰ رَبِّكِ" }],
        },
      ],
    },
  ]);
  const md = docToMarkdown(doc);
  assert.ok(!md.includes("k-quran"), md);
  assert.equal(md.trim(), "> ٱرْجِعِىٓ إِلَىٰ رَبِّكِ");
});

test("edit-mode card labels are visible attributes, never markdown text", () => {
  const arabic = "أَرَءَيْتَ مَنِ ٱتَّخَذَ إِلَهَهُۥ هَوَىٰهُ";
  const html = renderEditSeed(
    `> ${arabic}\n>\n> Have you seen the one who takes his own desire as his god?`,
    new Set([arabic]),
    null,
    { [arabic]: "Al-Furqan: 43" },
  );
  assert.match(html, /data-q-label="Al-Furqan: 43"/);

  const extensions = editorExtensions();
  const json = generateJSON(html, extensions);
  const doc = PMNode.fromJSON(getSchema(extensions), json);
  const blockquote = doc.firstChild;
  assert.equal(blockquote?.attrs["data-q-label"], "Al-Furqan: 43");
  const md = docToMarkdown(doc);
  assert.ok(!md.includes("Al-Furqan: 43"), md);
  assert.equal(
    md.trim(),
    `> ${arabic}\n>\n> Have you seen the one who takes his own desire as his god?`,
  );
});

// A content image on its own line survives the round trip byte-identically.
// Found 2026-08-14: with no Image node in this schema, `renderEditSeed`'s
// `<figure class="md-figure"><img/></figure>` matched nothing on parse and
// was silently dropped — so opening a chapter with images, editing one
// unrelated word, and autosaving would have deleted every image line from
// book.md. This test is the one that would have caught it; it must be RED
// against a schema with no ChapterImage node.
test("an inline content image survives the round trip byte-identically", () => {
  const src =
    "I begin.\n\n![](images/103/eca60cad-bbc6-4834-8ec1-29abaedfcbd2.jpg)\n\nAfter the image.";
  assert.equal(roundTrip(src), normalized(src));
});

test("a chapter with no images round-trips unchanged (no-op check)", () => {
  const src =
    "First paragraph.\n\nSecond paragraph, no image anywhere in this chapter.";
  assert.equal(roundTrip(src), normalized(src));
});

test("an image is a real node in the parsed doc, not silently dropped", () => {
  const src = "![](images/103/eca60cad-bbc6-4834-8ec1-29abaedfcbd2.jpg)";
  const extensions = editorExtensions();
  const json = generateJSON(renderEditSeed(src), extensions);
  const doc = PMNode.fromJSON(getSchema(extensions), json);
  assert.equal(doc.firstChild?.type.name, "chapterImage");
  assert.equal(
    doc.firstChild?.attrs.src,
    "images/103/eca60cad-bbc6-4834-8ec1-29abaedfcbd2.jpg",
  );
});

// The "Paste & fix chapter" tool restores an image compose_articulate.py's
// _restore_images() found missing from a hand-off rewrite by re-inserting
// the SAME bare `![](path)` line book.md always had — it never carries a
// saved size, because sizing lives only in _system/image-layout.json, keyed
// by that same path. A restored image therefore seeds with NO imageLayout
// entry, exactly like a brand-new one: this pins that it gets no --img-h at
// all (attrs.heightPx is null) and no explicit align (attrs.align is null,
// which book-md-editor.ts's NodeView then defaults to "center" at mount) —
// together, book-composer.css's `height: var(--img-h, 350px)` default is
// what a reader actually sees, with no extra code needed on the restore path.
test("a restored image with no saved layout seeds with nothing to override the 350px centered default", () => {
  const src = "![](images/103/eca60cad-bbc6-4834-8ec1-29abaedfcbd2.jpg)";
  const extensions = editorExtensions();
  // No imageLayout argument passed — the exact shape a freshly-restored
  // image has, since it was never in the sidecar to begin with.
  const json = generateJSON(renderEditSeed(src), extensions);
  const doc = PMNode.fromJSON(getSchema(extensions), json);
  assert.equal(doc.firstChild?.attrs.heightPx, null);
  assert.equal(doc.firstChild?.attrs.align, null);
});

// composer.ts's real seed is NOT renderEditSeed alone — loadComposer wraps it
// in serveBookImages so the <img> the browser mounts has a src it can
// actually fetch (composer.ts:433). Found 2026-08-14: docToMarkdown wrote
// that REWRITTEN `/api/studio/book-image?...` address straight into book.md
// on the very next autosave of any chapter holding an image, because the
// node's only `src` attribute WAS the rewritten one and docToMarkdown had no
// other value to reach for. This test seeds the doc the way the real
// Composer does — through serveBookImages, not around it — and would have
// been RED before `origSrc` existed to give docToMarkdown the original path
// back.
test("book.md keeps the original path even though the browser needed the rewritten one", () => {
  const src = "![](images/103/eca60cad-bbc6-4834-8ec1-29abaedfcbd2.jpg)";
  const extensions = editorExtensions();
  const seed = serveBookImages(String(renderEditSeed(src)), "surah-al-fateha");
  assert.ok(
    seed.includes("/api/studio/book-image?"),
    "the seed must actually be rewritten, or this test proves nothing",
  );
  const json = generateJSON(seed, extensions);
  const doc = PMNode.fromJSON(getSchema(extensions), json);
  assert.equal(doc.firstChild?.attrs.src?.startsWith("/api/studio/"), true);
  assert.equal(
    doc.firstChild?.attrs.origSrc,
    "images/103/eca60cad-bbc6-4834-8ec1-29abaedfcbd2.jpg",
  );
  assert.equal(docToMarkdown(doc), normalized(src));
});

test("originalBookSrc reverses serveBookImages exactly", () => {
  const rewritten = serveBookImages(
    `<img src="images/79/9da9df6f-f8e4-4a81-9768-38023d7a120f.jpg" />`,
    "surah-al-fateha",
  );
  const match = /src="([^"]+)"/.exec(rewritten);
  assert.equal(
    originalBookSrc(match?.[1] ?? ""),
    "images/79/9da9df6f-f8e4-4a81-9768-38023d7a120f.jpg",
  );
});

test("originalBookSrc leaves a non-book src alone", () => {
  for (const s of ["https://example.com/a.jpg", "/cover.png"]) {
    assert.equal(originalBookSrc(s), s);
  }
});
