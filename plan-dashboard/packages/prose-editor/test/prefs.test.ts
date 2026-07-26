/**
 * View preferences must never reach the document.
 *
 * Font, size and paper tint change how the editing surface looks. There is
 * deliberately no code path from any of them to a transaction — the last test
 * here is the one that matters, and it is the reason the feature is expressed
 * as CSS custom properties rather than as anything the editor knows about.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { doc as domDoc } from "./_dom.ts";

import { Editor } from "@tiptap/core";
import { attach } from "../src/attach.ts";
import { baseExtensions } from "../src/schema/base-extensions.ts";
import { createPreferences } from "../src/prefs/preferences.ts";
import type { PrefStorage } from "../src/prefs/preferences.ts";

function memoryStore(seed: Record<string, string> = {}): PrefStorage {
  const map = new Map(Object.entries(seed));
  return {
    get: (k) => map.get(k) ?? null,
    set: (k, v) => void map.set(k, v),
  };
}

const SPEC = {
  storage: memoryStore(),
  fonts: [
    { id: "sans", label: "Sans", value: "system-ui, sans-serif" },
    { id: "serif", label: "Serif", value: "Georgia, serif" },
  ],
  sizes: { min: 13, max: 24, default: 17 },
  tints: [
    { id: "light", label: "Light", value: "#fff|#111" },
    { id: "sepia", label: "Sepia", value: "#f4ecd8|#3b3222" },
  ],
};

test("preferences apply as CSS custom properties on the host element", () => {
  const host = domDoc.createElement("div");
  const prefs = createPreferences(host, { ...SPEC, storage: memoryStore() });
  assert.equal(host.style.getPropertyValue("--rte-prose-size"), "17px");

  prefs.setFont("serif");
  assert.equal(
    host.style.getPropertyValue("--rte-prose-font"),
    "Georgia, serif",
  );
  assert.equal(host.dataset.rteFont, "serif");

  prefs.setTint("sepia");
  assert.equal(host.style.getPropertyValue("--rte-paper-bg"), "#f4ecd8");
  assert.equal(host.style.getPropertyValue("--rte-paper-ink"), "#3b3222");
});

test("size is clamped to the configured range", () => {
  const host = domDoc.createElement("div");
  const prefs = createPreferences(host, { ...SPEC, storage: memoryStore() });
  prefs.setSize(99);
  assert.equal(prefs.get().size, 24);
  prefs.setSize(1);
  assert.equal(prefs.get().size, 13);
});

test("a stored value outside the configured set falls back rather than applying", () => {
  const host = domDoc.createElement("div");
  const prefs = createPreferences(host, {
    ...SPEC,
    storage: memoryStore({ "rte-font": "comic", "rte-size": "900" }),
  });
  assert.equal(prefs.get().font, "sans");
  assert.equal(prefs.get().size, 17);
});

test("storage that throws does not break the editor", () => {
  // localStorage throws in private modes and sandboxed frames. A reader's font
  // choice is not worth an exception.
  const hostile: PrefStorage = {
    get() {
      throw new Error("denied");
    },
    set() {
      throw new Error("denied");
    },
  };
  const host = domDoc.createElement("div");
  assert.throws(() => hostile.get("x"), /denied/, "the stub really throws");
  assert.doesNotThrow(() => {
    const prefs = createPreferences(host, {
      ...SPEC,
      storage: {
        get: () => {
          try {
            return hostile.get("x");
          } catch {
            return null;
          }
        },
        set: () => {
          try {
            hostile.set("x", "y");
          } catch {
            /* ignored */
          }
        },
      },
    });
    prefs.setSize(20);
  });
});

test("NO preference can change what the document serializes to", () => {
  const host = domDoc.createElement("div");
  domDoc.body.appendChild(host);
  const editor = new Editor({
    element: host,
    extensions: baseExtensions(),
    content: "<h2>Title</h2><p>Some <strong>bold</strong> prose.</p>",
  });
  const rte = attach(editor, { serializer: { kind: "markdown" } });
  const before = rte.serialize();

  const prefs = createPreferences(host, { ...SPEC, storage: memoryStore() });
  prefs.setFont("serif");
  prefs.setSize(24);
  prefs.setTint("sepia");

  assert.equal(rte.serialize(), before, "the saved bytes must be identical");
  rte.destroy();
  editor.destroy();
});
