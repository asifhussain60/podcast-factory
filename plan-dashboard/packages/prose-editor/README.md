# @asifhussain/prose-editor

A self-contained rich-text toolbar and extension system for TipTap / ProseMirror.

Its defining guarantee: **nothing typable can be lost on save.** Every node and
mark reachable from the editor must declare how it serializes. A type without a
serializer rule is a startup error — not a corruption discovered weeks later in
the file the editor writes.

The package knows nothing about any host's subject matter. A test fails if that
vocabulary ever appears in `src/`.

## Why it exists

It replaces a heavily customised commercial WYSIWYG, and the design is mostly a
list of that editor's failure modes closed at the root:

| There                                                                                                                                                                                           | Here                                                                                                                                               |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| A button needed three unlinked global calls, a fourth toolbar array, and a fifth shortcut allow-list — and two shortcuts were in fact left out of that allow-list, so they silently did nothing | A button is **one object**; its shortcut is a field on it                                                                                          |
| Custom commands inserted raw HTML strings with no parse rule and no serializer — survivable only because the output format was HTML                                                             | `toOutput` is **required**, enforced at compile time by a branded type and at runtime by a schema-coverage assertion                               |
| Host UI was reached by writing a marker comment into the document, opening a modal, then searching for the marker — any failure in between left the marker in the saved content                 | `captureAnchor()` / `insertAtAnchor()`: nothing is written until there is something real to write, and the position maps through intervening edits |
| A 715-line paste cleaner: 77 chained `.replace()` calls, a deny-list over an HTML string                                                                                                        | An **allow-list over a parsed DOM** — an unanticipated paste shape is handled by construction                                                      |
| Four hand-maintained per-breakpoint toolbar arrays                                                                                                                                              | One list, with priorities; overflow moves controls into a menu and never drops them                                                                |

## Install

```bash
npm install @asifhussain/prose-editor
```

`@tiptap/core`, `@tiptap/pm` and `@tiptap/starter-kit` are peer dependencies, so
the package always shares the host's single copy. React is an **optional** peer —
a vanilla consumer never pulls it in. The package itself has **zero** runtime
dependencies, and a test keeps it that way.

## Three ways in

### 1. A host that already owns an Editor — `attach`

The primary path, and the asymmetry is deliberate: the host keeps ownership of
its schema, its editor props and its extension list.

```ts
import { attach } from "@asifhussain/prose-editor";
import "@asifhussain/prose-editor/styles.css";

const rte = attach(myExistingEditor, {
  // REQUIRED. No default — a default serializer is the same silent-loss trap
  // this package exists to close, moved up to the API.
  serializer: { kind: "custom", serialize: myWriter, covers: [...] },
  toolbar: { ariaLabel: "Formatting" },
  bubble: {},
});
document.querySelector("#toolbar-slot").append(rte.toolbarEl);
```

Because `attach` never builds the editor, a package release cannot widen your
schema, cannot replace a drop or paste handler you installed for your own
reasons, and cannot change what your serializer is asked to write.

### 2. Greenfield — `mount`

```ts
import { mount } from "@asifhussain/prose-editor";

const rte = mount(element, {
  serializer: { kind: "markdown" },
  content: "<p>Hello</p>",
  toolbar: {},
});
```

### 3. No bundler at all — the standalone build

For a host whose scripts come from a server-side bundle config and whose npm is
tooling-only. TipTap is bundled in; one global is exposed.

```html
<link rel="stylesheet" href=".../styles/prose-editor.css" />
<script src=".../dist/standalone/prose-editor.global.js"></script>
<script>
  var rte = ProseEditor.mount(el, { serializer: { kind: "markdown" } });
</script>
```

See `examples/vanilla.html` and `examples/angularjs-directive.js`.

## The serializer guarantee

```ts
assertSerializerTotal(editor.schema, serializer.covers);
```

Runs at attach against the **final** schema — not the declared extension list —
so an extension added by any route, including the raw-TipTap escape hatch, is
still covered. An uncovered type throws `SerializerCoverageError` naming it.

Two gates, deliberately redundant:

- **Compile time** — `defineNode` / `defineMark` require `toOutput` and return a
  branded type carrying a `unique symbol`, so an object literal cannot forge one.
- **Run time** — the assertion above, plus the walker itself throwing rather than
  emitting nothing for an unknown type.

The realistic first move for an existing host is `{ kind: "custom" }`, handing
over the serializer it already trusts. Nothing about what a save produces
changes on adoption day; the guarantee is about what happens _next_.

## Custom buttons and nodes

```ts
const callout = defineNode({
  name: "callout",
  content: "block+",
  parseHTML: [{ tag: "aside.callout" }],
  renderHTML: () => ["aside", { class: "callout" }, 0],
  toOutput: (ctx) => ctx.prefixLines(ctx.children(), "! "), // required
  pasteAllow: { tags: ["aside"], classes: ["callout"] },
});

const insert = defineButton({
  id: "callout",
  label: "Callout",
  shortcut: "Mod-Alt-c",
  isActive: (state) => state.isActive("callout"),
  run: async (api) => {
    const anchor = api.captureAnchor(); // no marker is written
    const answer = await api.ui.openDialog({
      kind: "callout",
      title: "Callout",
      context: {
        selectedText: api.getSelectedText(),
        selectedHTML: api.getSelectedHTML(),
      },
    });
    if (answer) api.insertAtAnchor(anchor, "callout", answer);
  },
});
```

`pasteAllow` sits beside `parseHTML` on purpose: a custom node whose markup the
sanitizer strips never survives a paste, and that failure is invisible until
someone pastes.

The package owns **no modal implementation** — `api.ui` is a port. Every real
host already has a dialog system, and two competing ones is worse than none.

## Theming

Every colour, radius and size reads a `--rte-*` custom property, with neutral
defaults so the editor is usable with no host CSS. A host themes it by aliasing
its own tokens, scoped to the toolbar — never by editing the package:

```css
.my-toolbar-host {
  --rte-surface: var(--brand-bg-card);
  --rte-ink: var(--brand-ink);
  --rte-accent: var(--brand-accent);
}
```

No hardcoded colour may appear outside the defaults block, so a package release
can never override a host's palette. A test enforces it.

## What it deliberately does not do

- **No tables, footnotes, colour or highlight.** None has a markdown spelling, so
  the coverage assertion would refuse the schema that admitted them.
- **No image or media button.** Placing media is a host concern — and a host that
  models figures _outside_ the document (so they cannot be serialized into the
  prose) must not have that undone by a generic insert.
- **No underline, and no hard break, by default.** Markdown can write neither, so
  they leave the schema entirely: hiding a button is not a fix when Mod-U and
  Shift+Enter still reach the mark.
- **Links are never automatic.** `autolink` and `linkOnPaste` are off, because a
  typed domain becoming a link nobody authored is a change to the saved file.

## Develop

```bash
npm test          # node:test + happy-dom
npm run typecheck
npm run build     # ESM + .d.ts via tsc, then the standalone IIFE via vite
```

Source files import each other with explicit `.ts` extensions; `tsc` rewrites
those to `.js` on emit, which lets `node --test` run the sources directly with no
resolver hook and no build step.
