/**
 * fullscreen.ts — distraction-free editing, as a CSS state rather than the
 * Fullscreen API.
 *
 * The native API is deliberately NOT used. It takes the element out of the
 * page's stacking context entirely, which means any dialog the HOST raises —
 * including a blocking confirmation the host's own save path is waiting on —
 * renders behind it or not at all. A modal that asks a question the user cannot
 * see reads as an application that has hung.
 *
 * So this sets an attribute and lets CSS do the work, at a z-index
 * (`--rte-z-fullscreen`) deliberately BELOW where a host puts its modals.
 */

export interface FullscreenController {
  readonly active: boolean;
  toggle(): void;
  exit(): void;
  destroy(): void;
}

export function createFullscreen(
  element: HTMLElement,
  options: { onChange?: (active: boolean) => void } = {},
): FullscreenController {
  let active = false;

  const doc = element.ownerDocument;

  function set(next: boolean): void {
    active = next;
    if (active) element.setAttribute("data-rte-fullscreen", "true");
    else element.removeAttribute("data-rte-fullscreen");
    options.onChange?.(active);
  }

  // Escape leaves. Without it the only way out is a button that the state
  // itself may have moved.
  const onKeyDown = (event: Event): void => {
    if (active && (event as KeyboardEvent).key === "Escape") set(false);
  };
  doc.addEventListener("keydown", onKeyDown);

  return {
    get active() {
      return active;
    },
    toggle: () => set(!active),
    exit: () => set(false),
    destroy() {
      doc.removeEventListener("keydown", onKeyDown);
      element.removeAttribute("data-rte-fullscreen");
    },
  };
}
