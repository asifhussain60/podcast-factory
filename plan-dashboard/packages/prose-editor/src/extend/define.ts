/**
 * define.ts — the extension points.
 *
 * The editor this package replaces registered a custom button through three
 * unlinked global calls (define the icon, register the command, register the
 * shortcut), then listed it again in a toolbar array and a fifth time in a
 * shortcut allow-list. Five places to forget one button, and two of them were
 * in fact forgotten: two shortcuts were registered and then omitted from the
 * allow-list, so they silently did nothing.
 *
 * Here a button is ONE object and its shortcut is a field on it, so a button and
 * its shortcut cannot drift apart.
 *
 * More importantly: that editor's custom commands inserted raw HTML strings with
 * no parse rule and no serializer. That was survivable only because its output
 * format WAS HTML. Against any other format it is silent data loss, so here a
 * custom node or mark cannot be constructed without saying how it serializes.
 */
import type { DOMOutputSpec, ParseRule, TagParseRule } from "@tiptap/pm/model";
import type { AttrMap, EditorApi, SelectionState } from "../types.ts";
import type {
  MarkSerializerRule,
  NodeSerializerRule,
} from "../serialize/types.ts";

/**
 * The brand.
 *
 * A `unique symbol` cannot be written by an object literal, so the ONLY values
 * assignable to RegisteredNode/RegisteredMark are those returned by the
 * factories below — whose parameter types require `toOutput`. Passing a custom
 * node with no serializer is therefore a compile error, not a runtime surprise.
 */
declare const SERIALIZER_PROVEN: unique symbol;

export interface AttrDef<T = unknown> {
  default: T;
  parseHTML?: (element: HTMLElement) => T;
  renderHTML?: (attrs: AttrMap) => AttrMap | null;
  keepOnSplit?: boolean;
}

/** What the paste sanitizer must let through for `parseHTML` to have anything
 *  to match. Declared beside the parse rule so the two cannot disagree — a
 *  custom node whose markup the sanitizer strips never survives a paste, and
 *  that failure is invisible until someone pastes. */
export interface PasteAllowance {
  tags: readonly string[];
  attributes?: Readonly<Record<string, readonly string[]>>;
  classes?: readonly string[];
}

export interface CustomNodeDef {
  name: string;
  group?: "block" | "inline";
  content?: string;
  inline?: boolean;
  atom?: boolean;
  draggable?: boolean;
  selectable?: boolean;
  defining?: boolean;
  attrs?: Record<string, AttrDef>;
  /** (a) how it parses from HTML. Tag rules: ProseMirror admits only these
   *  for a node type, so the type says so rather than failing at runtime. */
  parseHTML: readonly TagParseRule[];
  /** (b) how it renders in the editor */
  renderHTML: (ctx: { attrs: AttrMap }) => DOMOutputSpec;
  /** (c) REQUIRED — how it serializes to the host's output format. */
  toOutput: NodeSerializerRule;
  pasteAllow?: PasteAllowance;
  /** Survive "clear formatting". Nodes default to true, marks to false. */
  keepOnClearFormatting?: boolean;
}

export interface CustomMarkDef {
  name: string;
  inclusive?: boolean;
  excludes?: string;
  spanning?: boolean;
  attrs?: Record<string, AttrDef>;
  parseHTML: readonly ParseRule[];
  renderHTML: (ctx: { attrs: AttrMap }) => DOMOutputSpec;
  /** REQUIRED — see CustomNodeDef.toOutput. */
  toOutput: MarkSerializerRule;
  pasteAllow?: PasteAllowance;
  keepOnClearFormatting?: boolean;
}

export interface RegisteredNode {
  readonly [SERIALIZER_PROVEN]: true;
  readonly kind: "node";
  readonly name: string;
  readonly def: CustomNodeDef;
}

export interface RegisteredMark {
  readonly [SERIALIZER_PROVEN]: true;
  readonly kind: "mark";
  readonly name: string;
  readonly def: CustomMarkDef;
}

export type RegisteredExtension = RegisteredNode | RegisteredMark;

export function defineNode(def: CustomNodeDef): RegisteredNode {
  return {
    [SERIALIZER_PROVEN]: true,
    kind: "node",
    name: def.name,
    def,
  } as RegisteredNode;
}

export function defineMark(def: CustomMarkDef): RegisteredMark {
  return {
    [SERIALIZER_PROVEN]: true,
    kind: "mark",
    name: def.name,
    def,
  } as RegisteredMark;
}

// ── Buttons ──────────────────────────────────────────────────────────────────

/** An icon: a built-in name, an inline SVG string, or literal text ("H2"). */
export type IconSpec = { svg: string } | { text: string } | { builtin: string };

export interface ButtonDef {
  id: string;
  /** The accessible name. Announced by screen readers, so it must describe the
   *  ACTION, not the glyph. */
  label: string;
  tooltip?: string;
  icon?: IconSpec;
  /** "Mod-b" — normalized per platform at registration. */
  shortcut?: string;
  /** Lower survives longer when the toolbar overflows. Default 100. */
  priority?: number;
  isActive?: (state: SelectionState) => boolean;
  isEnabled?: (state: SelectionState) => boolean;
  isVisible?: (state: SelectionState) => boolean;
  run: (api: EditorApi) => void | Promise<void>;
  ariaHasPopup?: "dialog" | "menu" | "listbox";
}

export interface DropdownOption {
  id: string;
  label: string;
  shortcut?: string;
}

export interface DropdownDef {
  id: string;
  label: string;
  tooltip?: string;
  priority?: number;
  options: readonly DropdownOption[];
  /** Which option the current selection is in, or null. */
  current: (state: SelectionState) => string | null;
  run: (api: EditorApi, optionId: string) => void | Promise<void>;
}

export interface RegisteredButton {
  readonly kind: "button";
  readonly def: ButtonDef;
}

export interface RegisteredDropdown {
  readonly kind: "dropdown";
  readonly def: DropdownDef;
}

export function defineButton(def: ButtonDef): RegisteredButton {
  return { kind: "button", def };
}

export function defineDropdown(def: DropdownDef): RegisteredDropdown {
  return { kind: "dropdown", def };
}
