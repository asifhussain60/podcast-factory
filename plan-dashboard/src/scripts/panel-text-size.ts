/**
 * panel-text-size.ts — the reader's text-size control for the right-hand panels.
 *
 * One preference, one control, every panel. The Composer's drawer (Tools /
 * Companion / Scholar) and the Arabic Review vowelling panel all size their content
 * from a single custom property, `--panel-fs`, so a stepper that writes that
 * property moves all of them together — there is no per-panel setting to get out of
 * step with the others.
 *
 * Storage is `localStorage`, deliberately. This is a per-person, per-device DISPLAY
 * preference, not book content: it must not travel into `book.md`, into the
 * Composer's edit sidecar, or into git, and it should be allowed to differ between
 * a laptop and an external monitor. It is also the pattern this surface already
 * uses for exactly this kind of choice — `cx-editor-size`, `cx-editor-paper`,
 * `cx-composer-panel` — so a reader's preferences all live in one place.
 *
 * The title tier is DERIVED rather than stored (`--panel-fs-title` = content + 2px).
 * Storing it separately would let a reader step content past headings and invert the
 * hierarchy; deriving it means the relationship holds at every stop on the dial.
 */
const KEY = "pf-panel-fs";
const MIN = 11;
const MAX = 24;
const DEFAULT = 15; // settled on sight 2026-07-21 — see the note in book-composer.css

function read(): number {
  try {
    const raw = Number(localStorage.getItem(KEY));
    return Number.isFinite(raw) && raw >= MIN && raw <= MAX ? raw : DEFAULT;
  } catch {
    return DEFAULT; // private browsing / storage disabled — the default still works
  }
}

function persist(px: number): void {
  try {
    localStorage.setItem(KEY, String(px));
  } catch {
    /* preference is best-effort; the session still honours the change */
  }
}

/** Push the size onto a target element as the two panel custom properties. */
function paint(target: HTMLElement, px: number): void {
  target.style.setProperty("--panel-fs", `${px}px`);
  target.style.setProperty("--panel-fs-title", `${px + 2}px`);
}

/**
 * Fired on `window` after the size changes, with the new px in `detail`.
 *
 * Painting a custom property is enough for anything sized purely in CSS, but
 * not for a surface that MEASURES its own text — a field grown to fit its
 * content has a height computed at the old size, and nothing in a CSS variable
 * tells it to measure again. The stepper is shared by every panel, so the
 * notification belongs here rather than in each surface that needs it.
 */
export const PANEL_TEXT_SIZE_EVENT = "pf:panel-text-size";

/** Every mounted stepper, so a change in one repaints the others on the page. */
const mounted = new Set<{ target: HTMLElement; readout: HTMLElement }>();

function broadcast(px: number): void {
  for (const m of mounted) {
    paint(m.target, px);
    m.readout.textContent = String(px);
  }
  window.dispatchEvent(
    new CustomEvent(PANEL_TEXT_SIZE_EVENT, { detail: { px } }),
  );
}

/**
 * Mount a −/+ stepper into `host` that resizes `target`'s panel text.
 *
 * Idempotent: mounting twice into the same host replaces the previous control
 * rather than stacking a second one, which matters because the React panels
 * re-render and the Composer re-mounts its drawer contents on a chapter switch.
 *
 * Returns a dispose function. React callers MUST call it on cleanup — without it
 * the broadcast registry keeps a reference to a detached node and every remount
 * adds another, so one click would repaint a growing list of dead panels.
 */
export function mountPanelTextSize(
  host: HTMLElement,
  target: HTMLElement,
): () => void {
  host.textContent = "";
  let px = read();

  const wrap = document.createElement("div");
  wrap.className = "cx-psize";
  wrap.setAttribute("role", "group");
  wrap.setAttribute("aria-label", "Panel text size");

  const label = document.createElement("span");
  label.className = "cx-psize-label";
  label.textContent = "Text";

  const down = document.createElement("button");
  down.type = "button";
  down.className = "cx-psize-btn";
  down.textContent = "−"; // MINUS SIGN, not a hyphen
  down.title = "Smaller panel text";
  down.setAttribute("aria-label", "Decrease panel text size");

  const readout = document.createElement("span");
  readout.className = "cx-psize-val";
  // Announce the new value to a screen reader without moving focus.
  readout.setAttribute("aria-live", "polite");
  readout.textContent = String(px);

  const up = document.createElement("button");
  up.type = "button";
  up.className = "cx-psize-btn";
  up.textContent = "+";
  up.title = "Larger panel text";
  up.setAttribute("aria-label", "Increase panel text size");

  const entry = { target, readout };
  mounted.add(entry);

  const step = (delta: number) => () => {
    px = Math.min(MAX, Math.max(MIN, px + delta));
    persist(px);
    broadcast(px); // every panel on the page, not just this one
    down.disabled = px <= MIN;
    up.disabled = px >= MAX;
  };
  down.addEventListener("click", step(-1));
  up.addEventListener("click", step(+1));
  down.disabled = px <= MIN;
  up.disabled = px >= MAX;

  wrap.append(label, down, readout, up);
  host.append(wrap);
  paint(target, px);

  return () => {
    mounted.delete(entry);
    wrap.remove();
  };
}

/** Apply the stored size to a target without rendering a control. For panels that
 *  should honour the preference but do not host the stepper themselves. */
export function applyPanelTextSize(target: HTMLElement): void {
  paint(target, read());
}
