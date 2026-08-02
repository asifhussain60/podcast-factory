/**
 * ink-palette.ts — the swatch menu, shared by the two controls that pick an ink.
 *
 * Two callers, two meanings, one menu: the toolbar's text-colour button colours
 * the SELECTION (a sidecar record, see compose-colour-command.ts), and the
 * Arabic group's ink swatch sets the BOOK's default for display quotations (a
 * citation-style field). Offering two visually different menus of the same five
 * colours would be a product with two ideas of what "forest" is, so the menu
 * lives here and each caller supplies only what it means by a choice.
 */
import { TEXT_INKS } from "../lib/reader/text-ink";

/**
 * Open the swatch menu beneath `anchorSel`'s button.
 *
 * Built and torn down per invocation rather than kept mounted: the toolbar is
 * rebuilt on every chapter switch, and a menu outliving its button is a menu
 * that acts on the wrong chapter. Positioned against the button that opened it
 * via custom properties, the same division of labour icon-tooltip.ts uses — the
 * declarations live in book-composer.css, never inline.
 *
 * `clearLabel` is null for a caller that has no "off" state: the book always has
 * SOME Arabic ink, so offering to remove it would be offering nothing.
 */
export function openPalette(opts: {
  /** Where focus returns on Escape. */
  returnFocusTo: HTMLElement;
  /** The button to hang the menu under. */
  anchor: HTMLElement | null;
  active: string | null;
  /** Text for the clearing row, or null to omit it entirely. */
  clearLabel?: string | null;
  choose: (ink: string | null) => void;
}): void {
  const { returnFocusTo: editorDom, anchor: btn, active, choose } = opts;
  const clearLabel =
    opts.clearLabel === undefined ? "Remove colour" : opts.clearLabel;
  document.querySelector(".cx-ink-menu")?.remove();
  const menu = document.createElement("div");
  menu.className = "cx-ink-menu";
  menu.setAttribute("role", "menu");
  menu.setAttribute("aria-label", "Text colour");

  const close = (): void => {
    menu.remove();
    document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("pointerdown", onOutside, true);
  };
  const onKey = (e: KeyboardEvent): void => {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      editorDom.focus();
    }
  };
  const onOutside = (e: Event): void => {
    if (!menu.contains(e.target as Node)) close();
  };

  for (const ink of TEXT_INKS) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cx-ink-swatch";
    b.setAttribute("role", "menuitemradio");
    b.setAttribute("aria-checked", String(active === ink.id));
    b.dataset.ink = ink.id;
    // The colour is set as a custom property, not a style rule: the swatch's
    // declarations live in the stylesheet and only its VALUE comes from here.
    b.style.setProperty("--ink", ink.swatch);
    const name = document.createElement("span");
    name.className = "cx-ink-name";
    name.textContent = ink.name;
    b.append(name);
    b.addEventListener("click", () => {
      choose(ink.id);
      close();
    });
    menu.append(b);
  }

  // Omitted entirely when the caller has no "off" state — the book always has
  // SOME Arabic ink, and a permanently disabled row saying "No colour" invites
  // the question of why it is there.
  if (clearLabel !== null) {
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "cx-ink-clear";
    clear.setAttribute("role", "menuitem");
    clear.textContent = active ? clearLabel : "No colour";
    clear.disabled = !active;
    clear.addEventListener("click", () => {
      choose(null);
      close();
    });
    menu.append(clear);
  }

  document.body.append(menu);
  const r = (btn ?? editorDom).getBoundingClientRect();
  menu.style.setProperty("--ink-x", `${Math.round(r.left)}px`);
  menu.style.setProperty("--ink-y", `${Math.round(r.bottom + 6)}px`);
  menu.querySelector<HTMLElement>("button")?.focus();

  document.addEventListener("keydown", onKey, true);
  // Deferred: the click that opened the menu is still propagating, and binding
  // synchronously would let it close itself on the same gesture.
  setTimeout(
    () => document.addEventListener("pointerdown", onOutside, true),
    0,
  );
}
