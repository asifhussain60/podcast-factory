/**
 * counter.ts — a live word / character readout.
 *
 * `aria-live="polite"` rather than "assertive": a count that changes on every
 * keystroke and interrupts a screen reader mid-word is worse than no count.
 * Polite means it is announced when the reader is idle.
 */
import type { EditorApi } from "../types.ts";

export interface CounterOptions {
  words?: boolean;
  characters?: boolean;
  /** Soft limit — sets `data-rte-over` past it, for the stylesheet to react to.
   *  Nothing is ever blocked: a limit is guidance, not a gate. */
  limit?: number;
  format?: (counts: { words: number; characters: number }) => string;
  classNamePrefix?: string;
  document?: Document;
}

export interface Counter {
  readonly el: HTMLElement;
  update(): void;
  destroy(): void;
}

const WORD_RE = /\S+/g;

export function createCounter(
  api: EditorApi,
  options: CounterOptions = {},
): Counter {
  const doc = options.document ?? globalThis.document;
  const prefix = options.classNamePrefix ?? "rte";
  const showWords = options.words ?? true;
  const showChars = options.characters ?? true;

  const el = doc.createElement("span");
  el.className = `${prefix}-counter`;
  el.setAttribute("aria-live", "polite");

  function update(): void {
    const text = api.editor.state.doc.textContent;
    const counts = {
      words: (text.match(WORD_RE) ?? []).length,
      characters: text.length,
    };
    if (options.format) {
      el.textContent = options.format(counts);
    } else {
      const parts: string[] = [];
      if (showWords) parts.push(`${counts.words} words`);
      if (showChars) parts.push(`${counts.characters} characters`);
      el.textContent = parts.join(" · ");
    }
    if (options.limit !== undefined) {
      el.dataset.rteOver = String(counts.words > options.limit);
    }
  }

  update();

  return {
    el,
    update,
    destroy() {
      el.remove();
    },
  };
}
