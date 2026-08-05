/**
 * dropdown.ts — the paragraph-format control, as an ARIA listbox.
 *
 * A native `<select>` would be less code and is the wrong tool: it cannot be
 * opened without moving focus out of the editor, which collapses the selection
 * the command is about to act on. A button plus a listbox keeps focus
 * management in our hands — and REQ-049's "real controls, never a div with a
 * click handler" is satisfied either way.
 */
import type { EditorApi, SelectionState } from "../types.ts";
import type { DropdownDef } from "../extend/define.ts";
import { ICONS } from "./icons.ts";

export interface DropdownControl {
  el: HTMLElement;
  /** The element that takes focus — the button, not the wrapper div. */
  focusEl: HTMLElement;
  sync(state: SelectionState): void;
  close(): void;
  destroy(): void;
}

export function createDropdown(
  api: EditorApi,
  def: DropdownDef,
  ctx: {
    doc: Document;
    prefix: string;
    guardSelection: (node: HTMLElement) => void;
  },
): DropdownControl {
  const { doc, prefix, guardSelection } = ctx;
  const cleanups: Array<() => void> = [];

  const wrap = doc.createElement("div");
  wrap.className = `${prefix}-select`;
  wrap.dataset.rteId = def.id;

  const button = doc.createElement("button");
  button.type = "button";
  button.className = `${prefix}-select-button`;
  button.setAttribute("aria-haspopup", "listbox");
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-label", def.label);
  if (def.tooltip) button.title = def.tooltip;

  const valueEl = doc.createElement("span");
  valueEl.className = `${prefix}-select-value`;
  const chevron = doc.createElement("span");
  chevron.className = `${prefix}-select-chevron`;
  chevron.innerHTML = ICONS.chevron ?? "";
  button.append(valueEl, chevron);

  const list = doc.createElement("ul");
  list.className = `${prefix}-select-list`;
  list.setAttribute("role", "listbox");
  list.setAttribute("aria-label", def.label);
  list.hidden = true;

  const optionEls: HTMLElement[] = [];
  for (const option of def.options) {
    const li = doc.createElement("li");
    li.className = `${prefix}-select-option`;
    li.setAttribute("role", "option");
    li.setAttribute("aria-selected", "false");
    li.dataset.optionId = option.id;
    li.textContent = option.label;
    li.tabIndex = -1;
    guardSelection(li);
    const onClick = () => {
      close();
      void def.run(api, option.id);
    };
    li.addEventListener("click", onClick);
    cleanups.push(() => li.removeEventListener("click", onClick));
    optionEls.push(li);
    list.append(li);
  }

  wrap.append(button, list);
  guardSelection(button);

  let open = false;

  function setOpen(next: boolean): void {
    open = next;
    button.setAttribute("aria-expanded", String(open));
    list.hidden = !open;
    if (open) {
      const selected =
        optionEls.find((o) => o.getAttribute("aria-selected") === "true") ??
        optionEls[0];
      selected?.focus();
    }
  }

  function close(): void {
    if (open) setOpen(false);
  }

  const onButtonClick = () => setOpen(!open);
  button.addEventListener("click", onButtonClick);
  cleanups.push(() => button.removeEventListener("click", onButtonClick));

  const onKeyDown = (event: Event): void => {
    const e = event as KeyboardEvent;
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }
    const index = optionEls.indexOf(e.target as HTMLElement);
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      button.focus();
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      const id = (e.target as HTMLElement).dataset?.optionId;
      close();
      button.focus();
      if (id) void def.run(api, id);
      return;
    }
    if (index === -1) return;
    let next = -1;
    if (e.key === "ArrowDown") next = (index + 1) % optionEls.length;
    else if (e.key === "ArrowUp")
      next = (index - 1 + optionEls.length) % optionEls.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = optionEls.length - 1;
    if (next === -1) return;
    e.preventDefault();
    optionEls[next]?.focus();
  };
  wrap.addEventListener("keydown", onKeyDown);
  cleanups.push(() => wrap.removeEventListener("keydown", onKeyDown));

  // A click anywhere else closes it. Registered on the document, which is
  // exactly the kind of listener a teardown would otherwise leak — hence the
  // matching removal in destroy().
  const onDocClick = (event: Event): void => {
    if (!open) return;
    if (!wrap.contains(event.target as globalThis.Node)) close();
  };
  doc.addEventListener("click", onDocClick, true);
  cleanups.push(() => doc.removeEventListener("click", onDocClick, true));

  return {
    el: wrap,
    focusEl: button,
    sync(state) {
      const currentId = def.current(state);
      const current =
        def.options.find((o) => o.id === currentId) ?? def.options[0];
      valueEl.textContent = current?.label ?? "";
      for (const li of optionEls) {
        li.setAttribute(
          "aria-selected",
          String(li.dataset.optionId === currentId),
        );
      }
      button.disabled = !state.editable;
    },
    close,
    destroy() {
      for (const fn of cleanups) fn();
      cleanups.length = 0;
      wrap.remove();
    },
  };
}
