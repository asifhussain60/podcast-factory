# @asifhussain/prose-editor

A self-contained rich-text toolbar and extension system for TipTap / ProseMirror.

Its defining guarantee: **nothing typable can be lost on save.** Every node and
mark reachable from the editor must declare how it serializes to the host's
output format. A type without a serializer rule is a startup error — not a
corruption discovered weeks later in the file the editor writes.

The package knows nothing about any host's domain. No documents, no chapters, no
CMS, no scripture. A `domain-neutrality` test enforces that.

## Why it exists

It replaces a heavily customised commercial WYSIWYG whose extension model had
three unlinked global registration calls per button, plus a fourth toolbar array
and a fifth shortcut allow-list — five places to forget one button — and whose
paste cleaner was 715 lines of chained regular expressions over an HTML string.

Here a button is one object, a shortcut is a field on it, and the paste sanitizer
is an allow-list over a parsed DOM: an unanticipated paste shape is handled by
construction rather than by adding another regex.

## Install

```bash
npm install @asifhussain/prose-editor
```

`@tiptap/core`, `@tiptap/pm` and `@tiptap/starter-kit` are peer dependencies, so
the package always shares the host's single copy. React is an **optional** peer —
a vanilla consumer never pulls it in.

## Use

### Any framework, or none

```js
import { createToolbar } from "@asifhussain/prose-editor";
import "@asifhussain/prose-editor/styles.css";

const toolbar = createToolbar({ ariaLabel: "Formatting" });
document.querySelector("#toolbar-slot").append(toolbar.el);
```

### A host that already owns an Editor

Use `attach(editor, options)`. The host keeps ownership of the schema, so the
package can never widen it — which is what keeps the host's own serializer
contract intact.

### A host with no bundler (AngularJS, jQuery, server-rendered)

Use the standalone build, which bundles TipTap in and exposes `window.ProseEditor`.
See `examples/angularjs-directive.js`.

## Theming

Every colour, radius and size reads a `--rte-*` custom property, with neutral
defaults so the editor is usable with no host CSS at all. A host themes it by
aliasing its own tokens, scoped to the toolbar — never by editing the package:

```css
.my-toolbar-host {
  --rte-surface: var(--brand-bg-card);
  --rte-ink: var(--brand-ink);
  --rte-accent: var(--brand-accent);
}
```

No hardcoded colour may appear outside the defaults block, so a package release
can never override a host's palette.

## Develop

```bash
npm test        # node:test + happy-dom
npm run typecheck
npm run build   # ESM + .d.ts via tsc
```

Source files import each other with explicit `.ts` extensions; `tsc` rewrites
those to `.js` on emit, which lets `node --test` run the sources directly with no
resolver hook and no build step.
