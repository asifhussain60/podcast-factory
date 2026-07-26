/**
 * @asifhussain/prose-editor — public barrel.
 *
 * A rich-text toolbar and extension system for TipTap/ProseMirror whose defining
 * guarantee is that **nothing typable can be lost on save**. Every node and mark
 * reachable from this editor must declare how it serializes; anything in the
 * schema without a serializer rule is a startup error, not a silent corruption
 * discovered later in the file the editor writes.
 *
 * The package knows nothing about any host's domain — no documents, no chapters,
 * no CMS. A domain-neutrality test enforces that, because the editor this
 * replaces became a 4,700-line file by absorbing its host's services one
 * convenience at a time.
 *
 * Two entry points:
 *   - `attach(editor, options)` — for a host that already owns an Editor. The
 *     host keeps ownership of the schema, so the package can never widen it.
 *   - `mount(element, options)` — greenfield: builds an Editor, then attaches.
 */

export { VERSION } from "./version.ts";

export { attach } from "./attach.ts";
export type { AttachOptions } from "./attach.ts";
export { mount } from "./mount.ts";
export type { MountOptions } from "./mount.ts";

export { baseExtensions } from "./schema/base-extensions.ts";
export type { BaseExtensionOptions } from "./schema/base-extensions.ts";

export {
  defineButton,
  defineDropdown,
  defineMark,
  defineNode,
} from "./extend/define.ts";
export type {
  AttrDef,
  ButtonDef,
  CustomMarkDef,
  CustomNodeDef,
  DropdownDef,
  DropdownOption,
  IconSpec,
  PasteAllowance,
  RegisteredButton,
  RegisteredDropdown,
  RegisteredExtension,
  RegisteredMark,
  RegisteredNode,
} from "./extend/define.ts";

export { createSerializer } from "./serialize/serializer.ts";
export {
  createMarkdownRules,
  createMarkdownSerializer,
  MARKDOWN_MARK_ORDER,
} from "./serialize/markdown.ts";
export { assertSerializerTotal } from "./serialize/coverage.ts";
export type {
  AttrMap,
  MarkdownOptions,
  MarkSerializerRule,
  NodeSerializeContext,
  NodeSerializerRule,
  Serializer,
  SerializerRules,
  SerializerSpec,
} from "./serialize/types.ts";

export {
  DuplicateRegistrationError,
  ProseEditorError,
  SerializerCoverageError,
  ShortcutConflictError,
} from "./errors.ts";

export { createFallbackUiHost } from "./ui/fallback-ui-host.ts";

export { createToolbar } from "./toolbar/toolbar.ts";
export type {
  Toolbar,
  ToolbarItem,
  ToolbarOptions,
} from "./toolbar/toolbar.ts";
export {
  builtinButtons,
  TOOLBAR_FULL,
  TOOLBAR_INLINE,
} from "./toolbar/builtins.ts";
export type { BuiltinOptions } from "./toolbar/builtins.ts";
export { planOverflow } from "./toolbar/overflow.ts";
export type { MeasurePort, OverflowPlan } from "./toolbar/overflow.ts";
export { ICONS } from "./toolbar/icons.ts";

export type {
  DialogField,
  DialogRequest,
  EditorApi,
  ProseEditor,
  SelectionAnchor,
  SelectionState,
  UiHost,
} from "./types.ts";
