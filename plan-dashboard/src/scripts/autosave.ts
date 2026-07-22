/**
 * autosave.ts — shared debounced-autosave controller + status-pill UI.
 *
 * Extracted from the Book Composer's prose editor (the original autosave —
 * debounced PUT to /api/studio/book-md, single-flight with a trailing
 * re-save, Editing…/Saving…/Saved/Couldn't-save states) so the SAME pattern
 * backs every "this should just persist itself, no Save button" surface in
 * the app — the Composer's figure-layout save is the second consumer. New
 * surfaces that need autosave should use this instead of writing their own
 * debounce/single-flight logic.
 *
 * Two independent pieces:
 *   - createAutosave(opts)     — pure logic, no DOM. Debounces markDirty()
 *     calls, saves via the caller's own `save()`, guarantees a change made
 *     WHILE a save is in flight gets folded into a trailing re-save rather
 *     than lost or racing.
 *   - mountAutosaveStatus(container) — builds the status pill (icon + text +
 *     Retry button) this repo's editors already use (.cx-status.cx-autosave,
 *     styled in book-composer.css), and returns the onStateChange callback to
 *     wire into createAutosave.
 */

export type AutosaveState = "idle" | "editing" | "saving" | "saved" | "error";

export interface AutosaveController {
  /** Call whenever the underlying data changed — schedules a debounced save. */
  markDirty(): void;
  /** Save immediately if dirty or mid-save; resolves true once safely saved. */
  flush(): Promise<boolean>;
}

export interface AutosaveResult {
  ok: boolean;
  error?: string;
}

export interface AutosaveOptions {
  /** Persist the current state; return {ok:false, error} on failure. */
  save: () => Promise<AutosaveResult>;
  onStateChange: (state: AutosaveState, message: string) => void;
  debounceMs?: number;
}

export function createAutosave(opts: AutosaveOptions): AutosaveController {
  const debounceMs = opts.debounceMs ?? 1200;
  let saveTimer: number | undefined;
  let saving = false;
  let needsResave = false;
  let dirty = false;

  const savedTime = () =>
    new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

  async function doSave(): Promise<boolean> {
    if (saving) {
      needsResave = true;
      return false;
    } // single-flight
    saving = true;
    opts.onStateChange("saving", "Saving…");
    try {
      const result = await opts.save();
      if (!result.ok) throw new Error(result.error || "save failed");
      saving = false;
      dirty = false;
      if (needsResave) {
        needsResave = false;
        return doSave();
      } // fold in edits made mid-save
      opts.onStateChange("saved", `Saved ${savedTime()}`);
      return true;
    } catch (err) {
      saving = false;
      opts.onStateChange("error", `Couldn't save — ${(err as Error).message}`);
      return false;
    }
  }

  function scheduleSave(): void {
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(() => {
      void doSave();
    }, debounceMs);
  }

  return {
    markDirty() {
      dirty = true;
      opts.onStateChange("editing", "Editing…");
      scheduleSave();
    },
    async flush() {
      window.clearTimeout(saveTimer);
      if (!dirty && !saving) return true;
      return doSave();
    },
  };
}

const STATE_ICON: Record<AutosaveState, string> = {
  idle: "",
  editing: "",
  saving: "fa-solid fa-circle-notch cx-autosave-spin",
  saved: "fa-solid fa-circle-check",
  error: "fa-solid fa-triangle-exclamation",
};

/** Builds the shared autosave status pill inside `container` (appended as the
 *  last child) and returns the onStateChange callback to pass to createAutosave.
 *  A caller that needs the raw retry click (rather than createAutosave's own
 *  flush) can pass `onRetry`. */
export function mountAutosaveStatus(
  container: HTMLElement,
  onRetry?: () => void,
): (state: AutosaveState, message: string) => void {
  const el = document.createElement("p");
  el.className = "cx-status cx-autosave";
  el.setAttribute("role", "status");
  el.setAttribute("aria-live", "polite");

  const icon = document.createElement("i");
  icon.className = "cx-autosave-icon";
  icon.setAttribute("aria-hidden", "true");

  const text = document.createElement("span");
  text.className = "cx-autosave-text";

  const retryBtn = document.createElement("button");
  retryBtn.type = "button";
  retryBtn.className = "cx-autosave-retry";
  retryBtn.textContent = "Retry";
  retryBtn.hidden = true;
  if (onRetry) retryBtn.addEventListener("click", onRetry);

  el.append(icon, text, retryBtn);
  container.append(el);

  return (state, message) => {
    text.textContent = message;
    icon.className = `cx-autosave-icon ${STATE_ICON[state]}`.trim();
    icon.hidden = !STATE_ICON[state];
    el.classList.toggle("is-error", state === "error");
    retryBtn.hidden = state !== "error";
  };
}
