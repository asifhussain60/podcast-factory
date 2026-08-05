/**
 * toolbar.ts — the toolbar container.
 *
 * Three things here are load-bearing rather than decorative:
 *
 * 1. `mousedown` is prevented on EVERY control. Without it, clicking a button
 *    blurs the editor, which collapses the selection — so the command runs
 *    against an empty selection, and any host UI keyed on "is there a
 *    selection" switches itself off the instant you reach for the toolbar.
 *
 * 2. `role="toolbar"` obliges arrow-key traversal with ONE tab stop. A bar of
 *    sixteen buttons that each take a tab stop is sixteen presses to get past.
 *
 * 3. Overflow moves items into a menu; it never drops them. A control that
 *    silently disappears at a narrow width is indistinguishable from one that
 *    was never built.
 */
import type { EditorApi, SelectionState } from "../types.ts";
import type {
  IconSpec,
  RegisteredButton,
  RegisteredDropdown,
} from "../extend/define.ts";
import { builtinButtons, TOOLBAR_FULL } from "./builtins.ts";
import type { BuiltinOptions } from "./builtins.ts";
import { ICONS } from "./icons.ts";
import { createDropdown } from "./dropdown.ts";
import type { DropdownControl } from "./dropdown.ts";
import { planOverflow } from "./overflow.ts";
import type { MeasurePort } from "./overflow.ts";

export type ToolbarItem = string | "|" | RegisteredButton | RegisteredDropdown;

export interface ToolbarOptions {
  /** Item ids, separators, or registered controls. Defaults to the full bar. */
  items?: readonly ToolbarItem[];
  ariaLabel?: string;
  /** Class prefix, so two editors on one page cannot collide. Default "rte". */
  classNamePrefix?: string;
  /** Document to build in. Injected so tests can drive a non-global DOM. */
  document?: Document;
  /** "menu" moves the tail into a More menu; "wrap" lets it wrap; "none" does
   *  nothing. Default "menu". */
  overflow?: "menu" | "wrap" | "none";
  /** Options for the built-in set — notably which heading levels are offered. */
  builtins?: BuiltinOptions;
  /**
   * Per-control icon overrides, keyed by item id and merged over whatever that
   * control declares for itself.
   *
   * The package ships its own dependency-free glyph set (icons.ts) so it renders
   * standing alone. A host that already loads an icon library should be able to
   * dress the WHOLE bar in it — a bar wearing two icon sets at once reads worse
   * than either — without this package acquiring a dependency on, or even a name
   * for, that library. An id with no entry keeps its default, so a partial map
   * is a partial re-skin rather than a bar with holes in it.
   */
  icons?: Readonly<Record<string, IconSpec>>;
  /** Width measurement. Injected because a headless DOM has no layout, so tests
   *  drive deterministic widths instead of fighting the shim. */
  measure?: MeasurePort;
  labels?: { more?: string };
}

export interface Toolbar {
  readonly el: HTMLElement;
  /** Re-read editor state and repaint pressed / disabled / current. */
  refresh(): void;
  /** Idempotent, and safe after the editor is destroyed. */
  destroy(): void;
}

interface Control {
  /** The element placed in the bar (a button, or a dropdown's wrapper). */
  el: HTMLElement;
  /** The element that actually takes focus. Differs from `el` for a dropdown,
   *  whose wrapper is a div and whose focusable is the button inside it — and
   *  getting this wrong leaves a second tab stop nobody notices until they try
   *  to tab past the bar. */
  focusEl: HTMLElement;
  priority: number;
  sync(state: SelectionState): void;
  dropdown?: DropdownControl;
}

export function createToolbar(
  api: EditorApi,
  options: ToolbarOptions = {},
): Toolbar {
  const doc = options.document ?? globalThis.document;
  const prefix = options.classNamePrefix ?? "rte";
  const overflowMode = options.overflow ?? "menu";
  const registry = builtinButtons(options.builtins ?? {});
  const items = options.items ?? TOOLBAR_FULL;

  const el = doc.createElement("div");
  el.className = `${prefix}-toolbar`;
  el.setAttribute("role", "toolbar");
  el.setAttribute("aria-label", options.ariaLabel ?? "Formatting");
  el.setAttribute("aria-orientation", "horizontal");

  const controls: Control[] = [];
  const cleanups: Array<() => void> = [];
  let destroyed = false;

  /** Keeps the selection alive across a click. See the header note. */
  function guardSelection(node: HTMLElement): void {
    const onMouseDown = (e: Event) => e.preventDefault();
    node.addEventListener("mousedown", onMouseDown);
    cleanups.push(() => node.removeEventListener("mousedown", onMouseDown));
  }

  function makeButton(def: RegisteredButton["def"]): Control {
    const b = doc.createElement("button");
    b.type = "button";
    b.className = `${prefix}-tool`;
    b.dataset.rteId = def.id;
    // The glyph is decorative; the accessible name is the ACTION.
    b.setAttribute("aria-label", def.label);
    b.title = def.tooltip ?? labelWithShortcut(def.label, def.shortcut);
    if (def.ariaHasPopup) b.setAttribute("aria-haspopup", def.ariaHasPopup);
    // A host override wins over the control's own glyph — see ToolbarOptions.icons.
    const icon: IconSpec | undefined = options.icons?.[def.id] ?? def.icon;
    if (icon && "svg" in icon) b.innerHTML = icon.svg;
    else if (icon && "text" in icon) b.textContent = icon.text;
    else b.textContent = def.label;
    if (def.isActive) b.setAttribute("aria-pressed", "false");

    guardSelection(b);
    const onClick = () => {
      if (destroyed) return;
      void def.run(api);
    };
    b.addEventListener("click", onClick);
    cleanups.push(() => b.removeEventListener("click", onClick));

    return {
      el: b,
      focusEl: b,
      priority: def.priority ?? 100,
      sync(state) {
        if (def.isActive) {
          b.setAttribute("aria-pressed", String(def.isActive(state)));
        }
        b.disabled = def.isEnabled ? !def.isEnabled(state) : !state.editable;
        if (def.isVisible) b.hidden = !def.isVisible(state);
      },
    };
  }

  function makeDropdown(def: RegisteredDropdown["def"]): Control {
    const control = createDropdown(api, def, { doc, prefix, guardSelection });
    return {
      el: control.el,
      focusEl: control.focusEl,
      priority: def.priority ?? 100,
      sync: control.sync,
      dropdown: control,
    };
  }

  function makeSeparator(): HTMLElement {
    const sep = doc.createElement("span");
    sep.className = `${prefix}-sep`;
    sep.setAttribute("role", "separator");
    sep.setAttribute("aria-orientation", "vertical");
    return sep;
  }

  // ── Build ──────────────────────────────────────────────────────────────────
  const rendered: Array<{ node: HTMLElement; control: Control | null }> = [];
  for (const item of items) {
    if (item === "|") {
      const sep = makeSeparator();
      el.append(sep);
      rendered.push({ node: sep, control: null });
      continue;
    }
    const resolved = typeof item === "string" ? registry[item] : item;
    if (!resolved) continue; // an id the host did not configure: skip, silently
    const control =
      resolved.kind === "dropdown"
        ? makeDropdown(resolved.def)
        : makeButton(resolved.def);
    controls.push(control);
    el.append(control.el);
    rendered.push({ node: control.el, control });
  }

  // ── Overflow ───────────────────────────────────────────────────────────────
  const overflowBtn = doc.createElement("button");
  const overflowMenu = doc.createElement("div");
  if (overflowMode === "menu") {
    overflowBtn.type = "button";
    overflowBtn.className = `${prefix}-tool ${prefix}-more`;
    overflowBtn.setAttribute(
      "aria-label",
      options.labels?.more ?? "More formatting",
    );
    overflowBtn.setAttribute("aria-haspopup", "menu");
    overflowBtn.setAttribute("aria-expanded", "false");
    // The overflow button answers to `icons.more` like any other control does.
    // It is the one glyph a host could not reach before, so a re-skinned bar
    // grew a single foreign icon at its end the first time it overflowed —
    // visible only at narrow widths, which is where nobody looks.
    const moreIcon = options.icons?.more;
    if (moreIcon && "svg" in moreIcon) overflowBtn.innerHTML = moreIcon.svg;
    else overflowBtn.innerHTML = ICONS.more ?? "";
    overflowBtn.hidden = true;
    guardSelection(overflowBtn);

    overflowMenu.className = `${prefix}-more-menu`;
    overflowMenu.setAttribute("role", "menu");
    overflowMenu.hidden = true;

    const toggle = () => {
      const open = overflowBtn.getAttribute("aria-expanded") === "true";
      overflowBtn.setAttribute("aria-expanded", String(!open));
      overflowMenu.hidden = open;
    };
    overflowBtn.addEventListener("click", toggle);
    cleanups.push(() => overflowBtn.removeEventListener("click", toggle));

    el.append(overflowBtn, overflowMenu);
  }

  function applyOverflow(): void {
    if (overflowMode !== "menu" || !options.measure) return;
    const plan = planOverflow(
      controls.map((c) => ({
        id: c.el.dataset.rteId ?? "",
        priority: c.priority,
      })),
      options.measure,
    );
    const overflowed = new Set(plan.overflowed);
    for (const control of controls) {
      const id = control.el.dataset.rteId ?? "";
      const goesToMenu = overflowed.has(id);
      const parent = goesToMenu ? overflowMenu : el;
      if (control.el.parentNode !== parent) {
        // Moved, never removed: a control that vanishes at a narrow width is
        // indistinguishable from one that was never built.
        if (goesToMenu) overflowMenu.append(control.el);
        else el.insertBefore(control.el, overflowBtn);
      }
      control.el.setAttribute("role", goesToMenu ? "menuitem" : "");
      if (!goesToMenu) control.el.removeAttribute("role");
    }
    overflowBtn.hidden = overflowed.size === 0;
  }

  // ── Roving tabindex ────────────────────────────────────────────────────────
  // `role="toolbar"` owes a SINGLE tab stop with arrow traversal.
  /** Every element the bar owns a tab stop for, in visual order. */
  function allStops(): HTMLElement[] {
    const stops = controls.map((c) => c.focusEl);
    if (overflowMode === "menu") stops.push(overflowBtn);
    return stops;
  }

  function focusables(): HTMLElement[] {
    return allStops().filter(
      (n) => !n.hidden && !(n as HTMLButtonElement).disabled,
    );
  }

  function setRovingIndex(target?: HTMLElement): void {
    // Set -1 on EVERY stop first, not just the focusable ones: a <button>
    // defaults to tabIndex 0, so a control that is merely disabled or hidden
    // would otherwise keep a tab stop the bar never granted it.
    for (const n of allStops()) n.tabIndex = -1;
    const nodes = focusables();
    if (nodes.length === 0) return;
    const active =
      target && nodes.includes(target) ? target : (nodes[0] as HTMLElement);
    active.tabIndex = 0;
  }

  const onKeyDown = (event: Event): void => {
    const e = event as KeyboardEvent;
    const nodes = focusables();
    const currentIndex = nodes.indexOf(e.target as HTMLElement);
    if (currentIndex === -1) return;
    let next = -1;
    if (e.key === "ArrowRight") next = (currentIndex + 1) % nodes.length;
    else if (e.key === "ArrowLeft")
      next = (currentIndex - 1 + nodes.length) % nodes.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = nodes.length - 1;
    if (next === -1) return;
    e.preventDefault();
    const target = nodes[next] as HTMLElement;
    setRovingIndex(target);
    target.focus();
  };
  el.addEventListener("keydown", onKeyDown);
  cleanups.push(() => el.removeEventListener("keydown", onKeyDown));

  function refresh(): void {
    if (destroyed) return;
    const state = api.state;
    for (const control of controls) control.sync(state);
    applyOverflow();
    setRovingIndex(focusables().find((n) => n.tabIndex === 0) ?? undefined);
  }

  refresh();

  return {
    el,
    refresh,
    destroy() {
      if (destroyed) return;
      destroyed = true;
      for (const control of controls) control.dropdown?.destroy();
      for (const fn of cleanups) fn();
      cleanups.length = 0;
      el.remove();
    },
  };
}

function labelWithShortcut(label: string, shortcut?: string): string {
  if (!shortcut) return label;
  const isMac =
    typeof globalThis.navigator !== "undefined" &&
    /Mac|iPhone|iPad/.test(globalThis.navigator.platform ?? "");
  const pretty = shortcut
    .replace(/Mod/g, isMac ? "⌘" : "Ctrl")
    .replace(/Shift/g, isMac ? "⇧" : "Shift")
    .replace(/-/g, isMac ? "" : "+");
  return `${label} (${pretty})`;
}
