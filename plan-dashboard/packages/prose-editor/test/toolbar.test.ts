/**
 * The toolbar's accessibility contract, and the two behaviours that are easy to
 * get wrong and invisible when you do.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { doc as domDoc } from "./_dom.ts";

import { Editor } from "@tiptap/core";
import { attach } from "../src/attach.ts";
import { baseExtensions } from "../src/schema/base-extensions.ts";
import { VERSION } from "../src/version.ts";
import type { ProseEditor } from "../src/types.ts";
import type { ToolbarItem } from "../src/toolbar/toolbar.ts";

function setup(
  content = "<p>hello</p>",
  items?: readonly ToolbarItem[],
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
    toolbar: items ? { document: domDoc, items } : { document: domDoc },
  });
  return { editor, rte, bar: rte.toolbarEl as HTMLElement };
}

/** Every control the bar owns a tab stop for. Must include the dropdown's
 *  button (`.rte-select-button`), not only the plain `.rte-tool`s — the bug
 *  this selector first missed was a SECOND tab stop hiding on the dropdown. */
const tools = (bar: HTMLElement): HTMLButtonElement[] =>
  Array.from(
    bar.querySelectorAll<HTMLButtonElement>(
      "button.rte-tool, button.rte-select-button",
    ),
  );

test("the package exposes a version a host can report", () => {
  assert.match(VERSION, /^\d+\.\d+\.\d+$/);
});

test("the bar is a toolbar landmark with an accessible name", () => {
  const { rte, bar } = setup();
  assert.equal(bar.getAttribute("role"), "toolbar");
  assert.equal(bar.getAttribute("aria-label"), "Formatting");
  assert.equal(bar.getAttribute("aria-orientation"), "horizontal");
  rte.destroy();
});

test("every control is a real button with an action-describing name", () => {
  // REQ-049: a div with a click handler is unreachable by keyboard and
  // unannounced by a screen reader. And the name must be the ACTION — the
  // glyph is decorative and is hidden from assistive tech.
  const { rte, bar } = setup();
  const buttons = tools(bar);
  assert.ok(buttons.length >= 8, "expected the full bar");
  for (const b of buttons) {
    assert.equal(b.tagName, "BUTTON");
    assert.equal(b.type, "button");
    const name = b.getAttribute("aria-label") ?? "";
    assert.ok(name.length > 0, "every control needs an accessible name");
    for (const svg of Array.from(b.querySelectorAll("svg"))) {
      assert.equal(svg.getAttribute("aria-hidden"), "true");
    }
  }
  rte.destroy();
});

test("exactly one control is in the tab order at any time", () => {
  // A sixteen-button bar that takes sixteen tab presses to get past is a
  // keyboard trap in all but name; role=toolbar owes a single tab stop.
  const { rte, bar } = setup();
  const stops = tools(bar).filter((b) => b.tabIndex === 0);
  assert.equal(stops.length, 1);
  rte.destroy();
});

test("arrow keys, Home and End move the tab stop", () => {
  const { rte, bar } = setup();
  const buttons = tools(bar).filter((b) => !b.disabled && !b.hidden);
  const first = buttons[0] as HTMLButtonElement;
  assert.equal(first.tabIndex, 0);

  const press = (key: string, target: HTMLElement) => {
    const ev = new (
      globalThis as unknown as {
        KeyboardEvent: typeof KeyboardEvent;
      }
    ).KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    target.dispatchEvent(ev);
  };

  press("ArrowRight", first);
  assert.equal(buttons[1]?.tabIndex, 0, "ArrowRight moves the stop forward");
  assert.equal(first.tabIndex, -1, "and takes it off the previous control");

  press("End", buttons[1] as HTMLElement);
  assert.equal(
    buttons[buttons.length - 1]?.tabIndex,
    0,
    "End goes to the last",
  );

  press("Home", buttons[buttons.length - 1] as HTMLElement);
  assert.equal(buttons[0]?.tabIndex, 0, "Home returns to the first");
  rte.destroy();
});

test("aria-pressed tracks whether the mark is on at the caret", () => {
  const { editor, rte, bar } = setup("<p>hello</p>");
  const bold = bar.querySelector<HTMLButtonElement>('[data-rte-id="bold"]');
  assert.ok(bold);
  assert.equal(bold.getAttribute("aria-pressed"), "false");

  editor.commands.selectAll();
  editor.commands.toggleBold();
  assert.equal(bold.getAttribute("aria-pressed"), "true");
  rte.destroy();
});

test("a toolbar click does not collapse the selection", () => {
  // Without preventDefault on mousedown, clicking a button blurs the editor,
  // the selection collapses, and the command runs against nothing — while any
  // host UI keyed on "is there a selection" switches itself off.
  const { editor, rte, bar } = setup("<p>hello world</p>");
  editor.commands.setTextSelection({ from: 1, to: 6 });
  const before = editor.state.selection;

  const bold = bar.querySelector<HTMLButtonElement>('[data-rte-id="bold"]');
  const ev = new (globalThis as unknown as { Event: typeof Event }).Event(
    "mousedown",
    { bubbles: true, cancelable: true },
  );
  bold?.dispatchEvent(ev);

  assert.equal(ev.defaultPrevented, true, "mousedown must be prevented");
  assert.equal(editor.state.selection.from, before.from);
  assert.equal(editor.state.selection.to, before.to);
  rte.destroy();
});

test("clicking a control runs its command", () => {
  const { editor, rte, bar } = setup("<p>hello</p>");
  editor.commands.selectAll();
  bar.querySelector<HTMLButtonElement>('[data-rte-id="bold"]')?.click();
  assert.equal(rte.serialize(), "**hello**\n");
  rte.destroy();
});

test("destroy removes the bar and is safe to call twice", () => {
  const { editor, rte, bar } = setup();
  rte.destroy();
  assert.equal(bar.parentNode, null);
  assert.doesNotThrow(() => rte.destroy());
  editor.destroy();
});
