/**
 * types.ts — the vocabulary a host writes against.
 *
 * Everything here is deliberately domain-free. A type named after any concept
 * that belongs to a particular host's subject matter belongs in that host, not
 * here: the editor this package replaces became a 4,700-line file by accepting
 * one such convenience at a time. A test enforces this, and it is strict enough
 * to flag the vocabulary even inside a comment — including this one, which is
 * why the examples here are described rather than named.
 */
import type { ChainedCommands, Editor, JSONContent } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import type { AttrMap } from "./serialize/types.ts";

export type { AttrMap };

/** A read-only snapshot of the selection, given to every predicate so a button
 *  never has to reach into ProseMirror state to decide whether it is on. */
export interface SelectionState {
  readonly empty: boolean;
  readonly text: string;
  readonly activeMarks: ReadonlySet<string>;
  readonly activeNodes: ReadonlySet<string>;
  readonly headingLevel: number | null;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
  readonly editable: boolean;
  isActive(name: string, attrs?: AttrMap): boolean;
}

/**
 * A position in the document that survives edits made while the host's own UI
 * is open.
 *
 * This replaces the marker-comment idiom the previous editor used: it inserted
 * a literal `<!--INSERT_MARKER-->` into the document, opened a modal, then
 * searched for the marker to replace it. Any failure between those two steps
 * left the marker in the saved content. Here nothing is written until there is
 * something real to write.
 */
export interface SelectionAnchor {
  readonly from: number;
  readonly to: number;
  /** ProseMirror step count at capture time, for mapping through later edits. */
  readonly stepsAtCapture: number;
}

/** Host-supplied UI. The package owns no modal implementation — a host has its
 *  own dialog system and two competing ones is worse than none. */
export interface UiHost {
  openDialog<T = unknown>(request: DialogRequest): Promise<T | null>;
  confirm?(request: { title: string; message: string }): Promise<boolean>;
  toast?(message: string, kind?: "info" | "success" | "error"): void;
}

export interface DialogRequest {
  /** Host-extensible. Built-ins use "link"; a host's own button may use any
   *  string and render whatever it likes for it. */
  kind: string;
  title: string;
  fields?: readonly DialogField[];
  initial?: AttrMap;
  context: { selectedText: string; selectedHTML: string };
}

export type DialogField =
  | {
      name: string;
      type: "text" | "url" | "textarea";
      label: string;
      required?: boolean;
      placeholder?: string;
    }
  | { name: string; type: "checkbox"; label: string }
  | {
      name: string;
      type: "select";
      label: string;
      options: readonly { value: string; label: string }[];
    };

/** What a button's `run` receives. Everything it needs to act on the document
 *  without importing TipTap itself — though `editor` is there for the cases the
 *  surface does not cover. */
export interface EditorApi {
  readonly editor: Editor;
  readonly state: SelectionState;
  /** TipTap's chain, deliberately UNFOCUSED — a command decides for itself
   *  whether the caret should return to the document. */
  chain(): ChainedCommands;
  getSelectedText(): string;
  getSelectedHTML(): string;
  insertNode(name: string, attrs?: AttrMap, content?: JSONContent[]): boolean;
  toggleMark(name: string, attrs?: AttrMap): boolean;
  unsetMark(name: string): boolean;
  captureAnchor(): SelectionAnchor;
  insertAtAnchor(
    anchor: SelectionAnchor,
    name: string,
    attrs?: AttrMap,
    content?: JSONContent[],
  ): boolean;
  restoreSelection(anchor: SelectionAnchor): void;
  readonly ui: UiHost;
  serialize(): string;
  /** Fire a CustomEvent on the mount element; the host listens. The package
   *  never calls back into host services directly. */
  emit(name: string, detail?: unknown): void;
}

/** The mounted editor a host holds on to. */
export interface ProseEditor {
  readonly editor: Editor;
  readonly api: EditorApi;
  /** The toolbar element, if a toolbar was configured. Place it anywhere. */
  readonly toolbarEl: HTMLElement | null;
  serialize(): string;
  counts(): { words: number; characters: number };
  /** Idempotent, and safe after the editor itself is destroyed. */
  destroy(): void;
}

export type { PMNode };
