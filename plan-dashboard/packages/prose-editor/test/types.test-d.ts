/**
 * types.test-d.ts — COMPILE-TIME proofs. No assertions, no runtime.
 *
 * `@ts-expect-error` is itself the assertion: if the line below it stops being
 * an error, TypeScript reports "unused @ts-expect-error" and the typecheck
 * fails. So `astro check` / `tsc --noEmit` IS this file's test runner, and the
 * filename deliberately does not match the `*.test.ts` glob — there is nothing
 * here for node to run.
 *
 * What is being proved: a custom node or mark cannot enter the editor without
 * declaring how it serializes. The runtime coverage assertion is the backstop;
 * this is the front stop, and it fires in the author's editor rather than at
 * their user's first save.
 */
import { defineMark, defineNode } from "../src/extend/define.ts";
import type { RegisteredNode } from "../src/extend/define.ts";
import type { AttachOptions } from "../src/attach.ts";

// ── A node WITH a serializer: fine. ──────────────────────────────────────────
const callout = defineNode({
  name: "callout",
  content: "block+",
  parseHTML: [{ tag: "aside.callout" }],
  renderHTML: () => ["aside", { class: "callout" }, 0],
  toOutput: (ctx) => ctx.prefixLines(ctx.children(), "! "),
});

// ── A node WITHOUT one: refused at compile time. ─────────────────────────────
// @ts-expect-error — `toOutput` is required: a node with no serializer rule is
// a node whose content vanishes on save.
defineNode({
  name: "leaky",
  content: "block+",
  parseHTML: [{ tag: "aside.leaky" }],
  renderHTML: () => ["aside", 0],
});

// ── A mark WITHOUT one: same. ────────────────────────────────────────────────
// @ts-expect-error — `toOutput` is required for marks too.
defineMark({
  name: "leakyMark",
  parseHTML: [{ tag: "span.leaky" }],
  renderHTML: () => ["span", { class: "leaky" }, 0],
});

// ── The brand cannot be forged by an object literal. ─────────────────────────
// @ts-expect-error — only defineNode() can produce a RegisteredNode, so there
// is no way to hand-write one that skipped the factory's requirements.
const forged: RegisteredNode = {
  kind: "node",
  name: "forged",
  def: {
    name: "forged",
    parseHTML: [{ tag: "div" }],
    renderHTML: () => ["div", 0],
    toOutput: () => "",
  },
};
void forged;

// ── `serializer` is required on attach: no default, deliberately. ────────────
// @ts-expect-error — a default serializer would be the same silent-loss trap,
// moved up to the API.
const optionsWithoutSerializer: AttachOptions = { extensions: [callout] };
void optionsWithoutSerializer;

// ── A properly registered node is assignable. ────────────────────────────────
const ok: AttachOptions = {
  serializer: { kind: "markdown" },
  extensions: [callout],
};
void ok;
