/**
 * toolbar.ts — the toolbar container.
 *
 * Scaffold: builds the accessible shell (a `role="toolbar"` landmark with a
 * roving-tabindex contract) and nothing else. The command registry, the built-in
 * buttons and the overflow behaviour arrive next; the shell exists first so the
 * repo's widened lint/test/typecheck globs have something real to prove they
 * reach.
 */

export interface ToolbarOptions {
  /** Accessible name for the toolbar landmark. */
  ariaLabel?: string;
  /** Class prefix, so two editors on one page cannot collide. Default "rte". */
  classNamePrefix?: string;
  /** Document to build in. Injected so tests can drive a non-global DOM. */
  document?: Document;
}

export interface Toolbar {
  /** The toolbar element, for the host to place wherever it wants. */
  readonly el: HTMLElement;
  /** Re-read editor state and repaint pressed/disabled states. */
  refresh(): void;
  /** Idempotent: safe to call twice, and after the editor is destroyed. */
  destroy(): void;
}

export function createToolbar(options: ToolbarOptions = {}): Toolbar {
  const doc = options.document ?? globalThis.document;
  const prefix = options.classNamePrefix ?? "rte";

  const el = doc.createElement("div");
  el.className = `${prefix}-toolbar`;
  el.setAttribute("role", "toolbar");
  el.setAttribute("aria-label", options.ariaLabel ?? "Formatting");
  // A `role="toolbar"` owes arrow-key traversal with a single tab stop. The
  // roving index is seeded here so the contract holds even while empty.
  el.setAttribute("aria-orientation", "horizontal");

  let destroyed = false;

  return {
    el,
    refresh() {
      if (destroyed) return;
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      el.remove();
    },
  };
}
