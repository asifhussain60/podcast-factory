/**
 * compose-quran-command.test.ts — the Composer's custom toolbar button.
 *
 * The button exists to prove the editor package's extension point works with
 * something real, so what is tested is the thing that makes it safe: the exact
 * document structure it produces, and that structure surviving a save and a
 * reload byte-identically.
 *
 * Tested here rather than against a real book: exercising it in the live
 * Composer fires the autosave, which writes a composer-edits sidecar and thereby
 * marks that chapter as human-authored — after which the pipeline will never
 * regenerate it. That is not a side effect a verification run should have.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { Window } from "happy-dom";

const win = new Window();
Object.assign(globalThis, {
  window: win,
  document: win.document,
  DOMParser: win.DOMParser,
  HTMLElement: win.HTMLElement,
  Element: win.Element,
  Node: win.Node,
  Event: win.Event,
  CustomEvent: win.CustomEvent,
  // ProseMirror's scrollToSelection reads computed styles on every focus, so a
  // bootstrap without this throws inside the very click being tested — and the
  // failure looks like a broken command rather than a missing global.
  getComputedStyle: win.getComputedStyle.bind(win),
  requestAnimationFrame: (cb: FrameRequestCallback) => {
    cb(0);
    return 0;
  },
  cancelAnimationFrame: () => {},
});

import { Editor } from "@tiptap/core";
import { attach } from "@asifhussain/prose-editor";
import { docToMarkdown, editorExtensions } from "./book-md-editor";
import { renderEditSeed } from "../lib/reader/markdown";
import { quranQuotationButton } from "./compose-quran-command";

const COVERS = [
  "doc",
  "text",
  "paragraph",
  "heading",
  "blockquote",
  "bulletList",
  "orderedList",
  "listItem",
  "codeBlock",
  "horizontalRule",
  "bold",
  "italic",
  "code",
  "strike",
  "link",
];

function setup(content: string) {
  const host = win.document.createElement("div");
  win.document.body.appendChild(host);
  const editor = new Editor({
    element: host as unknown as HTMLElement,
    extensions: editorExtensions(),
    content,
  });
  const rte = attach(editor, {
    serializer: { kind: "custom", serialize: docToMarkdown, covers: COVERS },
    toolbar: {
      document: win.document as unknown as Document,
      items: [quranQuotationButton()],
    },
  });
  return { editor, rte, bar: rte.toolbarEl as unknown as HTMLElement };
}

test("it inserts exactly blockquote.quran > p.ar + p.tr", () => {
  // The ONE structure QuotationClasses re-admits on parse. Anything else set
  // here is dropped on the next reload, so the button would appear to forget.
  const { editor, rte, bar } = setup("<p>hello</p>");
  bar
    .querySelector<HTMLButtonElement>('[data-rte-id="quranQuotation"]')
    ?.click();

  const bq = editor.view.dom.querySelector("blockquote.quran");
  assert.ok(bq, "a quran blockquote is inserted");
  assert.deepEqual(
    Array.from(bq.children).map(
      (c) => `${c.tagName.toLowerCase()}.${c.className}`,
    ),
    ["p.ar", "p.tr"],
  );
  // dir/lang are deliberately NOT set — direction is CSS on this surface, and
  // neither attribute survives the schema anyway.
  assert.equal(bq.querySelector("p.ar")?.getAttribute("dir"), null);
  rte.destroy();
  editor.destroy();
});

test("a selection becomes the Arabic line rather than being discarded", () => {
  const { editor, rte, bar } = setup("<p>شُكْرُ الْعَالِمِ</p>");
  editor.commands.selectAll();
  bar
    .querySelector<HTMLButtonElement>('[data-rte-id="quranQuotation"]')
    ?.click();
  assert.match(rte.serialize(), /^> شُكْرُ الْعَالِمِ$/m);
  rte.destroy();
  editor.destroy();
});

test("a filled quotation is a save-and-reload fixed point", () => {
  // The real contract. docToMarkdown ignores the classes and writes a
  // blockquote with a blank `>` between its paragraphs; renderEditSeed
  // RE-DERIVES quran/ar/tr from the content coming back in. So the classes are
  // never carried in the markdown and can never disagree with it.
  const { editor, rte, bar } = setup("<p>شُكْرُ الْعَالِمِ طَاعَتُهُ</p>");
  editor.commands.selectAll();
  bar
    .querySelector<HTMLButtonElement>('[data-rte-id="quranQuotation"]')
    ?.click();
  // Fill the translation, as a user would. Locate the `tr` paragraph rather
  // than guessing an offset — the offset moves whenever the fixture does.
  let trPos: number | null = null;
  editor.state.doc.descendants((node, pos) => {
    if (node.type.name === "paragraph" && node.attrs.class === "tr") {
      trPos = pos;
      return false;
    }
    return true;
  });
  assert.ok(trPos !== null, "the scaffold has a translation line");
  editor.commands.setTextSelection(trPos + 1);
  editor.commands.insertContent("Thanks to the teacher is to obey him.");

  const saved = rte.serialize();
  // Re-open what was saved, exactly as the Composer would on the next load.
  const { editor: reopened, rte: rte2 } = setup(renderEditSeed(saved));
  assert.equal(rte2.serialize(), saved, "a reload must not change the bytes");
  assert.ok(
    reopened.view.dom.querySelector("blockquote.quran p.ar"),
    "and the verse markup is re-derived, not lost",
  );

  rte2.destroy();
  reopened.destroy();
  rte.destroy();
  editor.destroy();
});

test("an unfilled translation line is dropped on reload, losing no content", () => {
  // Insert the scaffold and save without typing the rendering. The empty line
  // serializes as a bare `>` and does not survive the next parse — worth
  // knowing, and harmless: nothing the author wrote is lost, and the file is
  // stable from that point on.
  const { editor, rte, bar } = setup("<p>شُكْرُ الْعَالِمِ</p>");
  editor.commands.selectAll();
  bar
    .querySelector<HTMLButtonElement>('[data-rte-id="quranQuotation"]')
    ?.click();

  const first = rte.serialize();
  const { editor: e2, rte: r2 } = setup(renderEditSeed(first));
  const second = r2.serialize();
  assert.equal(second, "> شُكْرُ الْعَالِمِ\n", "the Arabic survives");
  const { editor: e3, rte: r3 } = setup(renderEditSeed(second));
  assert.equal(r3.serialize(), second, "and it is stable from there");

  r3.destroy();
  e3.destroy();
  r2.destroy();
  e2.destroy();
  rte.destroy();
  editor.destroy();
});

test("aria-pressed reports when the caret is inside a quotation", () => {
  const { editor, rte, bar } = setup("<p>hello</p>");
  const btn = bar.querySelector<HTMLButtonElement>(
    '[data-rte-id="quranQuotation"]',
  );
  assert.equal(btn?.getAttribute("aria-pressed"), "false");

  btn?.click();
  assert.equal(
    btn?.getAttribute("aria-pressed"),
    "true",
    "the caret is now inside the quotation it just made",
  );
  rte.destroy();
  editor.destroy();
});
