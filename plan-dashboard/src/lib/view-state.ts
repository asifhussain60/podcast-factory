/**
 * view-state.ts — durable "where I was" state for the Podcast Factory Astro Site.
 *
 * Two kinds of client state already live in this app and they behave
 * differently on purpose:
 *
 *   - View PREFERENCES (font, text size, paper tint, preview zoom, panel
 *     width) persist to localStorage and always have. They describe the
 *     person, not the work, and they carry across books and visits.
 *   - View SELECTIONS (which chapter, which lane, which tab, where I had
 *     scrolled to) mostly did not persist. Where they did, it was a one-shot
 *     sessionStorage handoff written immediately before a scripted reload and
 *     deleted on read — so the editor's own refresh kept your place while a
 *     plain F5, a new tab, or coming back tomorrow did not.
 *
 * This module is the home for the second kind. It exists so that surfaces stop
 * inventing their own key strings, and so three things are true everywhere at
 * once rather than per-page:
 *
 *   1. Storage access is guarded. localStorage throws in private modes and in
 *      sandboxed frames; remembering a selection is never worth an exception,
 *      and a blocked store degrades to "this page opens at its default".
 *   2. Keys are namespaced by surface AND scope. A scope is normally a book
 *      slug, so the chapter you had open in one book can never be restored
 *      into another — the failure that makes a "helpful" restore worse than
 *      none at all.
 *   3. Every read is validated by the caller. What comes back from storage is
 *      untrusted: it may name a chapter that has since been renamed, deleted,
 *      or re-composed. A value that does not validate is discarded and the
 *      caller's default is used, so a stale entry can never leave a page blank
 *      or pointed at content that no longer exists.
 *
 * Duplicate registration throws at module-evaluation time rather than letting
 * two surfaces quietly share one key and overwrite each other — the same
 * bargain the prose-editor package's shortcut registry makes.
 */

export interface ViewStateStorage {
  get(key: string): string | null;
  set(key: string, value: string): void;
  remove(key: string): void;
}

export interface ViewStateSpec<T> {
  /** The page or component that owns this value, e.g. "compose". */
  surface: string;
  /** What is being remembered, e.g. "chapter". */
  field: string;
  /**
   * Turn a stored string into a usable value, or return null to discard it.
   * This is where an allow-list or an existence check belongs — a remembered
   * chapter that no longer exists must fail here, not downstream.
   */
  validate: (raw: string) => T | null;
  /** Serialize for storage. Defaults to String(value). */
  serialize?: (value: T) => string;
}

export interface ViewState<T> {
  /** The stored value, or null when absent, unreadable, or invalid. */
  read(scope?: string): T | null;
  write(value: T, scope?: string): void;
  clear(scope?: string): void;
  /** The fully-qualified storage key — exposed for tests and debugging. */
  keyFor(scope?: string): string;
}

const PREFIX = "pf";

/**
 * Wrap any store so that no access can escape. Applied to the caller's store
 * as well as the default one: "a selection is never worth an exception" is a
 * property of this module, not of whichever store happens to be underneath.
 */
function harden(inner: ViewStateStorage): ViewStateStorage {
  return {
    get(key) {
      try {
        return inner.get(key);
      } catch {
        return null;
      }
    },
    set(key, value) {
      try {
        inner.set(key, value);
      } catch {
        /* a remembered selection is never worth an exception */
      }
    },
    remove(key) {
      try {
        inner.remove(key);
      } catch {
        /* as above */
      }
    },
  };
}

/**
 * localStorage itself is reached through a getter that can throw before any
 * method is called — a sandboxed frame denies the property, not just the
 * operation — so each access sits inside its own try.
 */
const localStorageBacked: ViewStateStorage = {
  get: (key) => globalThis.localStorage?.getItem(key) ?? null,
  set: (key, value) => void globalThis.localStorage?.setItem(key, value),
  remove: (key) => void globalThis.localStorage?.removeItem(key),
};

/** Every key defined so far, so a collision is a startup error not a data bug. */
const registered = new Set<string>();

/** Test-only: forget every registration so a suite can re-import definitions. */
export function __resetViewStateRegistry(): void {
  registered.clear();
}

export function defineViewState<T>(
  spec: ViewStateSpec<T>,
  storage: ViewStateStorage = localStorageBacked,
): ViewState<T> {
  const store = harden(storage);
  const base = `${PREFIX}:${spec.surface}:${spec.field}`;
  if (registered.has(base))
    throw new Error(
      `view-state: "${base}" is already defined. Two surfaces sharing one key ` +
        `would silently overwrite each other — give one of them a distinct field.`,
    );
  registered.add(base);

  const serialize = spec.serialize ?? ((v: T) => String(v));
  // A scope (normally a book slug) sits at the END so the un-scoped key stays a
  // clean prefix of the scoped one, which keeps them legible in devtools.
  const keyFor = (scope?: string) => (scope ? `${base}:${scope}` : base);

  return {
    keyFor,
    read(scope) {
      const raw = store.get(keyFor(scope));
      if (raw === null) return null;
      try {
        return spec.validate(raw);
      } catch {
        // A validator that throws on malformed input is treated as a rejection:
        // the whole point of this layer is that bad stored data cannot break a page.
        return null;
      }
    },
    write(value, scope) {
      store.set(keyFor(scope), serialize(value));
    },
    clear(scope) {
      store.remove(keyFor(scope));
    },
  };
}

/**
 * The common case: a value that must be one of a known set of strings.
 * Anything else stored under the key — a stale option, hand-edited junk — is
 * discarded on read.
 */
export function oneOf<T extends string>(
  allowed: readonly T[],
): (raw: string) => T | null {
  return (raw) => (allowed.includes(raw as T) ? (raw as T) : null);
}

/**
 * A non-empty string whose validity depends on data the page only has at
 * runtime — a chapter key, a file path. The caller supplies the existence
 * check; `null` from it means "this no longer exists, open at the default".
 */
export function existing(
  exists: (raw: string) => boolean,
): (raw: string) => string | null {
  return (raw) => (raw.length > 0 && exists(raw) ? raw : null);
}
