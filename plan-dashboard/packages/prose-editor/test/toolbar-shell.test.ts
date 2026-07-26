import { test } from "node:test";
import assert from "node:assert/strict";
import { doc } from "./_dom.ts";
import { createToolbar, VERSION } from "../src/index.ts";

test("the package exposes a version a host can report", () => {
  assert.match(VERSION, /^\d+\.\d+\.\d+$/);
});

test("the toolbar is an accessible landmark, not a div of buttons", () => {
  const tb = createToolbar({ document: doc, ariaLabel: "Editor" });
  assert.equal(tb.el.getAttribute("role"), "toolbar");
  assert.equal(tb.el.getAttribute("aria-label"), "Editor");
  assert.equal(tb.el.getAttribute("aria-orientation"), "horizontal");
});

test("the class prefix is configurable so two editors cannot collide", () => {
  const a = createToolbar({ document: doc });
  const b = createToolbar({ document: doc, classNamePrefix: "cx" });
  assert.equal(a.el.className, "rte-toolbar");
  assert.equal(b.el.className, "cx-toolbar");
});

test("destroy is idempotent — a chapter switch must not throw on double teardown", () => {
  const tb = createToolbar({ document: doc });
  tb.destroy();
  assert.doesNotThrow(() => tb.destroy());
  assert.doesNotThrow(() => tb.refresh());
});
