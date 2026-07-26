import { test } from "node:test";
import assert from "node:assert/strict";
import { doc as domDoc } from "./_dom.ts";

import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { attach } from "../src/attach.ts";
import { baseExtensions } from "../src/schema/base-extensions.ts";
import { SerializerCoverageError } from "../src/errors.ts";

function makeEditor(content: string, extensions = baseExtensions()): Editor {
  const host = domDoc.createElement("div");
  domDoc.body.appendChild(host);
  return new Editor({ element: host, extensions, content });
}

test("attach refuses an editor whose schema it cannot fully serialize", () => {
  // The host built its editor with an unconfigured StarterKit — underline and
  // hardBreak in the schema, neither writable. Refuse at startup rather than
  // discard on the first save.
  const editor = makeEditor("<p>hi</p>", [StarterKit]);
  try {
    assert.throws(
      () => attach(editor, { serializer: { kind: "markdown" } }),
      SerializerCoverageError,
    );
  } finally {
    editor.destroy();
  }
});

test("attach accepts a host serializer it did not write, and uses it", () => {
  // The adoption path that matters: a host with a proven serializer hands over
  // the function it already trusts rather than restaking its output on new code.
  const editor = makeEditor("<p>hi</p>");
  try {
    const rte = attach(editor, {
      serializer: {
        kind: "custom",
        serialize: () => "HOST OUTPUT",
        covers: [
          ...Object.keys(editor.schema.nodes),
          ...Object.keys(editor.schema.marks),
        ],
      },
    });
    assert.equal(rte.serialize(), "HOST OUTPUT");
    rte.destroy();
  } finally {
    editor.destroy();
  }
});

test("a custom serializer that over-claims coverage is still checked", () => {
  const editor = makeEditor("<p>hi</p>");
  try {
    assert.throws(
      () =>
        attach(editor, {
          serializer: {
            kind: "custom",
            serialize: () => "",
            covers: ["doc", "text", "paragraph"], // honest about only three
          },
        }),
      SerializerCoverageError,
    );
  } finally {
    editor.destroy();
  }
});

test("the markdown serializer round-trips through attach", () => {
  const editor = makeEditor("<h2>Title</h2><p>Some <strong>bold</strong>.</p>");
  try {
    const rte = attach(editor, { serializer: { kind: "markdown" } });
    assert.equal(rte.serialize(), "## Title\n\nSome **bold**.\n");
    rte.destroy();
  } finally {
    editor.destroy();
  }
});

test("counts report words and characters of the document text", () => {
  const editor = makeEditor("<p>one two three</p>");
  try {
    const rte = attach(editor, { serializer: { kind: "markdown" } });
    assert.deepEqual(rte.counts(), { words: 3, characters: 13 });
    rte.destroy();
  } finally {
    editor.destroy();
  }
});

test("an anchor survives edits made while the host's dialog is open", () => {
  // The failure this replaces: the previous editor wrote a literal marker
  // comment into the document, opened a modal, then searched for the marker.
  // Anything that went wrong in between left the marker in the saved file.
  const editor = makeEditor("<p>alpha</p><p>omega</p>");
  try {
    const rte = attach(editor, { serializer: { kind: "markdown" } });

    // Select "omega" (second paragraph), then capture.
    const omegaFrom = editor.state.doc.content.size - 6;
    editor.commands.setTextSelection({
      from: omegaFrom,
      to: omegaFrom + 5,
    });
    const anchor = rte.api.captureAnchor();
    const before = editor.state.doc.textBetween(anchor.from, anchor.to);
    assert.equal(before, "omega");

    // The host opens UI; meanwhile text is inserted BEFORE the anchor, which
    // shifts every position after it.
    editor.commands.insertContentAt(1, "PREFIX ");

    // Raw positions are now wrong; the mapped anchor is not.
    assert.notEqual(
      editor.state.doc.textBetween(anchor.from, anchor.to),
      "omega",
    );
    rte.api.restoreSelection(anchor);
    const { from, to } = editor.state.selection;
    assert.equal(editor.state.doc.textBetween(from, to), "omega");

    rte.destroy();
  } finally {
    editor.destroy();
  }
});

test("destroy is idempotent and safe after the editor is already gone", () => {
  const editor = makeEditor("<p>hi</p>");
  const rte = attach(editor, { serializer: { kind: "markdown" } });
  editor.destroy();
  assert.doesNotThrow(() => rte.destroy());
  assert.doesNotThrow(() => rte.destroy());
});
