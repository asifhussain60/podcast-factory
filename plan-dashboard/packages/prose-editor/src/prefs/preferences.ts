/**
 * preferences.ts — view-only editing preferences.
 *
 * Font, text size and paper tint change how the editing surface LOOKS. They are
 * not content, and there is deliberately no code path from any of them to a
 * transaction: every one is applied as a CSS custom property on the host
 * element, so a preference cannot reach the document, cannot reach the
 * serializer, and cannot reach the file. A test asserts exactly that.
 *
 * Storage is guarded throughout — localStorage throws in private modes and in
 * sandboxed frames, and a reader's font choice is not worth an exception.
 */

export interface PrefChoice {
  id: string;
  label: string;
  /** The CSS value applied for this choice. */
  value: string;
}

export interface PrefStorage {
  get(key: string): string | null;
  set(key: string, value: string): void;
}

export interface PreferencesSpec {
  /** Namespace for the stored keys. Default "rte". */
  storageKey?: string;
  storage?: PrefStorage;
  /** Applied as --rte-prose-font. */
  fonts?: readonly PrefChoice[];
  /** Applied as --rte-prose-size, in px. */
  sizes?: { min: number; max: number; default: number };
  /** Applied as --rte-paper-bg / --rte-paper-ink. `value` is "bg|ink". */
  tints?: readonly PrefChoice[];
  onChange?: (prefs: Preferences) => void;
}

export interface Preferences {
  font: string;
  size: number;
  tint: string;
}

export interface PreferencesController {
  get(): Preferences;
  setFont(id: string): void;
  setSize(px: number): void;
  setTint(id: string): void;
  /** Re-apply to the element — for a host that rebuilds its editor host node. */
  apply(): void;
}

function guardedStorage(): PrefStorage {
  return {
    get(key) {
      try {
        return globalThis.localStorage?.getItem(key) ?? null;
      } catch {
        return null;
      }
    },
    set(key, value) {
      try {
        globalThis.localStorage?.setItem(key, value);
      } catch {
        /* a preference is never worth an exception */
      }
    },
  };
}

export function createPreferences(
  element: HTMLElement,
  spec: PreferencesSpec = {},
): PreferencesController {
  const ns = spec.storageKey ?? "rte";
  const store = spec.storage ?? guardedStorage();
  const sizes = spec.sizes ?? { min: 13, max: 24, default: 17 };

  const readSize = (): number => {
    const raw = Number(store.get(`${ns}-size`));
    return Number.isFinite(raw) && raw >= sizes.min && raw <= sizes.max
      ? raw
      : sizes.default;
  };
  const readChoice = (
    key: string,
    choices: readonly PrefChoice[] | undefined,
  ): string => {
    const saved = store.get(`${ns}-${key}`);
    if (saved && choices?.some((c) => c.id === saved)) return saved;
    return choices?.[0]?.id ?? "";
  };

  const prefs: Preferences = {
    font: readChoice("font", spec.fonts),
    size: readSize(),
    tint: readChoice("tint", spec.tints),
  };

  function apply(): void {
    const font = spec.fonts?.find((f) => f.id === prefs.font);
    if (font) element.style.setProperty("--rte-prose-font", font.value);
    element.style.setProperty("--rte-prose-size", `${prefs.size}px`);
    const tint = spec.tints?.find((t) => t.id === prefs.tint);
    if (tint) {
      const [bg, ink] = tint.value.split("|");
      if (bg) element.style.setProperty("--rte-paper-bg", bg);
      if (ink) element.style.setProperty("--rte-paper-ink", ink);
    }
    // Also exposed as data attributes so a host can key its own CSS off them.
    element.dataset.rteFont = prefs.font;
    element.dataset.rteTint = prefs.tint;
    spec.onChange?.({ ...prefs });
  }

  apply();

  return {
    get: () => ({ ...prefs }),
    setFont(id) {
      prefs.font = id;
      store.set(`${ns}-font`, id);
      apply();
    },
    setSize(px) {
      prefs.size = Math.min(sizes.max, Math.max(sizes.min, px));
      store.set(`${ns}-size`, String(prefs.size));
      apply();
    },
    setTint(id) {
      prefs.tint = id;
      store.set(`${ns}-tint`, id);
      apply();
    },
    apply,
  };
}
