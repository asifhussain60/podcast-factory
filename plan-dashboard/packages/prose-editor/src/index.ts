/**
 * @asifhussain/prose-editor — public barrel.
 *
 * A rich-text toolbar and extension system for TipTap/ProseMirror whose defining
 * guarantee is that **nothing typable can be lost on save**. Every node and mark
 * reachable from this editor must declare how it serializes; anything in the
 * schema without a serializer rule is a startup error, not a silent corruption
 * discovered later in the file the editor writes.
 *
 * The package knows nothing about any host's domain — no books, no chapters, no
 * scripture, no CMS. A `domain-neutrality` test enforces that, because the editor
 * this replaces became a 4,700-line file by absorbing its host's services one
 * convenience at a time.
 *
 * Two entry points:
 *   - `attach(editor, options)` — for a host that already owns an Editor. The
 *     host keeps ownership of the schema, so the package can never widen it.
 *   - `mount(element, options)` — greenfield: builds an Editor, then attaches.
 */

export { VERSION } from "./version.ts";
export { createToolbar } from "./toolbar/toolbar.ts";
export type { Toolbar, ToolbarOptions } from "./toolbar/toolbar.ts";
