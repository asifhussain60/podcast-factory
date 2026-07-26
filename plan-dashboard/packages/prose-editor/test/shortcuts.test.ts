import { test } from "node:test";
import assert from "node:assert/strict";
import "./_dom.ts";

import {
  createShortcutRegistry,
  normalizeShortcut,
} from "../src/input/shortcuts.ts";
import { ShortcutConflictError } from "../src/errors.ts";
import type { EditorApi } from "../src/types.ts";

test("modifier order and case do not create two different bindings", () => {
  assert.equal(
    normalizeShortcut("Mod-Shift-z"),
    normalizeShortcut("Shift-Mod-Z"),
  );
  assert.equal(normalizeShortcut("Mod-b"), "mod-b");
});

test("a duplicate binding throws instead of silently winning", () => {
  // Silent last-wins is how a shortcut ends up doing something other than what
  // its own tooltip advertises.
  const reg = createShortcutRegistry({ isApple: false });
  reg.register({ shortcut: "Mod-b", id: "bold", run: () => {} });
  assert.throws(
    () =>
      reg.register({ shortcut: "Mod-B", id: "somethingElse", run: () => {} }),
    ShortcutConflictError,
  );
});

test("re-registering the SAME id is fine — a rebuild is not a conflict", () => {
  const reg = createShortcutRegistry({ isApple: false });
  reg.register({ shortcut: "Mod-b", id: "bold", run: () => {} });
  assert.doesNotThrow(() =>
    reg.register({ shortcut: "Mod-b", id: "bold", run: () => {} }),
  );
});

test("a bound combination runs its command and stops the browser default", () => {
  const reg = createShortcutRegistry({ isApple: false });
  let ran = 0;
  reg.register({ shortcut: "Mod-b", id: "bold", run: () => void ran++ });

  const target = globalThis.document.createElement("div");
  const detach = reg.listen(target, {} as EditorApi);

  const ev = new (
    globalThis as unknown as {
      KeyboardEvent: typeof KeyboardEvent;
    }
  ).KeyboardEvent("keydown", {
    key: "b",
    ctrlKey: true,
    bubbles: true,
    cancelable: true,
  });
  target.dispatchEvent(ev);

  assert.equal(ran, 1);
  assert.equal(ev.defaultPrevented, true);

  detach();
  target.dispatchEvent(
    new (
      globalThis as unknown as { KeyboardEvent: typeof KeyboardEvent }
    ).KeyboardEvent("keydown", { key: "b", ctrlKey: true, bubbles: true }),
  );
  assert.equal(ran, 1, "detaching really detaches");
});

test("an unbound combination is left entirely alone", () => {
  const reg = createShortcutRegistry({ isApple: false });
  const target = globalThis.document.createElement("div");
  reg.listen(target, {} as EditorApi);
  const ev = new (
    globalThis as unknown as {
      KeyboardEvent: typeof KeyboardEvent;
    }
  ).KeyboardEvent("keydown", {
    key: "p",
    ctrlKey: true,
    bubbles: true,
    cancelable: true,
  });
  target.dispatchEvent(ev);
  assert.equal(ev.defaultPrevented, false, "Ctrl+P must still print");
});

test("Mod is Cmd on Apple and Ctrl elsewhere", () => {
  const mk = (init: KeyboardEventInit) =>
    new (
      globalThis as unknown as { KeyboardEvent: typeof KeyboardEvent }
    ).KeyboardEvent("keydown", { bubbles: true, cancelable: true, ...init });

  for (const isApple of [true, false]) {
    const reg = createShortcutRegistry({ isApple });
    let ran = 0;
    reg.register({ shortcut: "Mod-b", id: "bold", run: () => void ran++ });
    const target = globalThis.document.createElement("div");
    reg.listen(target, {} as EditorApi);
    target.dispatchEvent(
      mk(isApple ? { key: "b", metaKey: true } : { key: "b", ctrlKey: true }),
    );
    assert.equal(ran, 1, isApple ? "Cmd on Apple" : "Ctrl elsewhere");
  }
});
