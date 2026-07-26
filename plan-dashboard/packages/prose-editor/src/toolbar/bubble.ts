/**
 * bubble.ts — the formatting bar that follows a selection.
 *
 * Two rules, both learned from how this goes wrong:
 *
 * 1. It is a PURE OBSERVER. It reads selection state to decide whether to show
 *    and where; it never calls focus() in response, because that fires the very
 *    event it is reacting to and the two chase each other.
 *
 * 2. A host can suppress its BLOCK-level commands. Marks are safe on any
 *    selection, but a block command restructures the document and shifts every
 *    position after it — and a host that is holding captured positions across
 *    some async operation of its own needs a way to say "not right now" without
 *    hiding the bar entirely.
 *
 * Position is written as CSS custom properties, never `style.left`, so the
 * stylesheet keeps control of how the bar is actually placed.
 */
import type { EditorApi, SelectionState } from "../types.ts";
import { createToolbar } from "./toolbar.ts";
import type { Toolbar, ToolbarItem } from "./toolbar.ts";
import { TOOLBAR_INLINE } from "./builtins.ts";
import type { BuiltinOptions } from "./builtins.ts";

/** Commands that restructure the document rather than mark a range. */
const BLOCK_LEVEL = new Set([
  "paragraphFormat",
  "bulletList",
  "orderedList",
  "blockquote",
  "codeBlock",
  "horizontalRule",
]);

export interface BubbleOptions {
  items?: readonly ToolbarItem[];
  /** Show the bar at all. Default: a non-empty selection in an editable doc. */
  showOn?: (state: SelectionState) => boolean;
  /**
   * Suppress block-level commands while this returns true.
   *
   * The case it exists for: a host has captured a document range, handed it to
   * something asynchronous, and is going to apply a result back at that range.
   * A block command in the meantime shifts every position after it, so the
   * result lands in the wrong place.
   */
  suppressBlockCommands?: () => boolean;
  classNamePrefix?: string;
  document?: Document;
  builtins?: BuiltinOptions;
  /** Gap between the selection and the bar, in px. Default 8. */
  offset?: number;
}

export interface Bubble {
  readonly el: HTMLElement;
  /** Re-evaluate visibility, position and pressed state. */
  update(): void;
  destroy(): void;
}

export function createBubble(
  api: EditorApi,
  options: BubbleOptions = {},
): Bubble {
  const doc = options.document ?? globalThis.document;
  const prefix = options.classNamePrefix ?? "rte";
  const offset = options.offset ?? 8;
  const items = options.items ?? TOOLBAR_INLINE;

  const el = doc.createElement("div");
  el.className = `${prefix}-bubble`;
  el.hidden = true;

  const toolbar: Toolbar = createToolbar(api, {
    document: doc,
    items,
    ariaLabel: "Selection formatting",
    overflow: "none",
    ...(options.classNamePrefix ? { classNamePrefix: prefix } : {}),
    ...(options.builtins ? { builtins: options.builtins } : {}),
  });
  el.append(toolbar.el);

  let destroyed = false;

  function visible(state: SelectionState): boolean {
    if (options.showOn) return options.showOn(state);
    return !state.empty && state.editable;
  }

  function position(): void {
    const view = api.editor.view;
    const { from, to } = api.editor.state.selection;
    // coordsAtPos is viewport-relative; the bar is positioned against the
    // document, so add the scroll offsets.
    const start = view.coordsAtPos(from);
    const end = view.coordsAtPos(to);
    const left = (start.left + end.left) / 2 + (globalThis.scrollX ?? 0);
    const top = start.top + (globalThis.scrollY ?? 0) - offset;
    // Custom properties, not style.left: the stylesheet decides how these are
    // used (and can clamp, flip, or ignore them at a narrow width).
    el.style.setProperty("--rte-bubble-x", `${Math.round(left)}px`);
    el.style.setProperty("--rte-bubble-y", `${Math.round(top)}px`);
  }

  function update(): void {
    if (destroyed) return;
    const state = api.state;
    if (!visible(state)) {
      el.hidden = true;
      return;
    }
    const suppressed = options.suppressBlockCommands?.() ?? false;
    for (const node of Array.from(
      el.querySelectorAll<HTMLElement>("[data-rte-id]"),
    )) {
      const id = node.dataset.rteId ?? "";
      node.hidden = suppressed && BLOCK_LEVEL.has(id);
    }
    el.hidden = false;
    toolbar.refresh();
    try {
      position();
    } catch {
      // coordsAtPos throws if the view is mid-teardown. A bar that fails to
      // position is a cosmetic problem; a throw here would break the editor.
    }
  }

  return {
    el,
    update,
    destroy() {
      if (destroyed) return;
      destroyed = true;
      toolbar.destroy();
      el.remove();
    },
  };
}
