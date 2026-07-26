/**
 * The paragraph-format control.
 *
 * The heading levels it offers are CONFIGURABLE, and that is the point: which
 * levels are authorable inside a body of text is a host's structural decision.
 * A host whose file format treats some level as a document boundary has to be
 * able to withhold it, and a generic package cannot know which level that is.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { doc as domDoc } from "./_dom.ts";

import { Editor } from "@tiptap/core";
import { attach } from "../src/attach.ts";
import { baseExtensions } from "../src/schema/base-extensions.ts";
import type { ProseEditor } from "../src/types.ts";
import type { BuiltinOptions } from "../src/toolbar/builtins.ts";

function setup(
  content = "<p>hello</p>",
  builtins?: BuiltinOptions,
): { editor: Editor; rte: ProseEditor; bar: HTMLElement } {
  const host = domDoc.createElement("div");
  domDoc.body.appendChild(host);
  const editor = new Editor({
    element: host,
    extensions: baseExtensions(),
    content,
  });
  const rte = attach(editor, {
    serializer: { kind: "markdown" },
    toolbar: {
      document: domDoc,
      items: ["paragraphFormat"],
      ...(builtins ? { builtins } : {}),
    },
  });
  return { editor, rte, bar: rte.toolbarEl as HTMLElement };
}

const options = (bar: HTMLElement): HTMLElement[] =>
  Array.from(bar.querySelectorAll<HTMLElement>('[role="option"]'));

test("it is a listbox, not a native select", () => {
  // A native <select> cannot be opened without moving focus out of the editor,
  // which collapses the selection the command is about to act on.
  const { rte, bar } = setup();
  const button = bar.querySelector("button.rte-select-button");
  assert.ok(button);
  assert.equal(button.getAttribute("aria-haspopup"), "listbox");
  assert.equal(button.getAttribute("aria-expanded"), "false");
  assert.equal(bar.querySelector('[role="listbox"]')?.tagName, "UL");
  assert.equal(bar.querySelector("select"), null);
  rte.destroy();
});

test("a host can withhold a heading level it treats as a document boundary", () => {
  const { rte, bar } = setup("<p>hello</p>", {
    headingLevels: [
      { level: 3, id: "h3", label: "Section" },
      { level: 4, id: "h4", label: "Subsection" },
    ],
    bodyLabel: "Body",
  });
  assert.deepEqual(
    options(bar).map((o) => o.textContent),
    ["Body", "Section", "Subsection"],
  );
  rte.destroy();
});

test("choosing a level applies it, and the control reports it back", () => {
  const { rte, bar } = setup("<p>hello</p>", {
    headingLevels: [{ level: 3, id: "h3", label: "Section" }],
    bodyLabel: "Body",
  });
  const value = () => bar.querySelector(".rte-select-value")?.textContent ?? "";
  assert.equal(value(), "Body");

  options(bar)
    .find((o) => o.dataset.optionId === "h3")
    ?.click();
  assert.equal(rte.serialize(), "### hello\n");
  assert.equal(value(), "Section", "the button reflects the current block");
  assert.equal(
    options(bar)
      .find((o) => o.dataset.optionId === "h3")
      ?.getAttribute("aria-selected"),
    "true",
  );
  rte.destroy();
});

test("an option id outside the configured set does nothing", () => {
  // A host withholds a level for a reason; a stray id must not be guessed into
  // a level anyway.
  const { rte, bar } = setup("<p>hello</p>", {
    headingLevels: [{ level: 3, id: "h3", label: "Section" }],
  });
  const listbox = bar.querySelector('[role="listbox"]') as HTMLElement;
  const rogue = domDoc.createElement("li");
  rogue.setAttribute("role", "option");
  rogue.dataset.optionId = "h1";
  listbox.append(rogue);
  rogue.click();
  assert.equal(rte.serialize(), "hello\n", "still a paragraph");
  rte.destroy();
});

test("Escape closes the list and returns focus to the button", () => {
  const { rte, bar } = setup();
  const button = bar.querySelector<HTMLButtonElement>(
    "button.rte-select-button",
  );
  button?.click();
  assert.equal(button?.getAttribute("aria-expanded"), "true");

  const ev = new (
    globalThis as unknown as {
      KeyboardEvent: typeof KeyboardEvent;
    }
  ).KeyboardEvent("keydown", {
    key: "Escape",
    bubbles: true,
    cancelable: true,
  });
  options(bar)[0]?.dispatchEvent(ev);

  assert.equal(button?.getAttribute("aria-expanded"), "false");
  rte.destroy();
});
