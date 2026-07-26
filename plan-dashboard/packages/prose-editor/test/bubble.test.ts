import { test } from "node:test";
import assert from "node:assert/strict";
import { doc as domDoc } from "./_dom.ts";

import { Editor } from "@tiptap/core";
import { attach } from "../src/attach.ts";
import { baseExtensions } from "../src/schema/base-extensions.ts";
import type { AttachOptions } from "../src/attach.ts";

function setup(extra: Partial<AttachOptions> = {}) {
  const host = domDoc.createElement("div");
  domDoc.body.appendChild(host);
  const editor = new Editor({
    element: host,
    extensions: baseExtensions(),
    content: "<p>hello world</p>",
  });
  const rte = attach(editor, {
    serializer: { kind: "markdown" },
    bubble: { document: domDoc },
    ...extra,
  });
  return { editor, rte, bubble: rte.bubbleEl as HTMLElement };
}

test("the bubble is hidden with no selection and shown with one", () => {
  const { editor, rte, bubble } = setup();
  assert.equal(bubble.hidden, true, "nothing selected");

  editor.commands.setTextSelection({ from: 1, to: 6 });
  assert.equal(bubble.hidden, false, "a range is selected");

  editor.commands.setTextSelection({ from: 1, to: 1 });
  assert.equal(bubble.hidden, true, "collapsed again");
  rte.destroy();
});

test("it carries marks, not block commands, by default", () => {
  const { editor, rte, bubble } = setup();
  editor.commands.setTextSelection({ from: 1, to: 6 });
  const ids = Array.from(
    bubble.querySelectorAll<HTMLElement>("[data-rte-id]"),
  ).map((n) => n.dataset.rteId);
  assert.deepEqual(ids, ["bold", "italic", "code", "link"]);
  rte.destroy();
});

test("a host can suppress block commands without hiding the bar", () => {
  // The case this exists for: the host is holding captured positions across
  // something asynchronous, and a block command in the meantime would shift
  // every position after it so the result lands in the wrong place.
  let busy = false;
  const { editor, rte, bubble } = setup({
    bubble: {
      document: domDoc,
      items: ["bold", "blockquote"],
      suppressBlockCommands: () => busy,
    },
  });

  editor.commands.setTextSelection({ from: 1, to: 6 });
  const quote = bubble.querySelector<HTMLElement>('[data-rte-id="blockquote"]');
  const bold = bubble.querySelector<HTMLElement>('[data-rte-id="bold"]');
  assert.equal(quote?.hidden, false);

  busy = true;
  editor.commands.setTextSelection({ from: 1, to: 7 });
  assert.equal(quote?.hidden, true, "the block command is withheld");
  assert.equal(bold?.hidden, false, "marks stay available");
  assert.equal(bubble.hidden, false, "the bar itself stays up");
  rte.destroy();
});

test("position is written as custom properties, never as style.left", () => {
  // The stylesheet decides how the bar is actually placed — it can clamp, flip
  // or ignore these at a narrow width. Hardcoding left/top takes that away.
  const { editor, rte, bubble } = setup();
  editor.commands.setTextSelection({ from: 1, to: 6 });
  assert.equal(bubble.style.left, "");
  assert.equal(bubble.style.top, "");
  assert.notEqual(bubble.style.getPropertyValue("--rte-bubble-x"), "");
  rte.destroy();
});

test("a read-only editor never shows the bar", () => {
  const { editor, rte, bubble } = setup();
  editor.setEditable(false);
  editor.commands.setTextSelection({ from: 1, to: 6 });
  assert.equal(bubble.hidden, true);
  rte.destroy();
});

test("destroy removes it and survives a second call", () => {
  const { editor, rte, bubble } = setup();
  rte.destroy();
  assert.equal(bubble.parentNode, null);
  assert.doesNotThrow(() => rte.destroy());
  editor.destroy();
});
