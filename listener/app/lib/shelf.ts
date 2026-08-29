/**
 * What the shelf remembers between visits: how the grid is drawn, which
 * collection is showing, and which study track.
 *
 * All three are display preferences rather than data, so they stay client-side
 * — they have no business in the loader or the URL. That is exactly what makes
 * them dangerous to read carelessly: the server has no `localStorage`, so a
 * stored value reached for while the first client render is still running
 * produces a tree the server's HTML cannot match. React then discards the
 * server's DOM and rebuilds it, and `data-theme` — stamped on `<html>` by
 * THEME_INIT_SCRIPT before first paint, and owned by no React tree — does not
 * survive that. Every `[data-theme]`-scoped rule stops applying: the reader's
 * Dark or Sepia palette silently reverts, and session cards lose their violet.
 * A remembered view mode is not worth the reader's colour theme.
 *
 * So this is the same external store `lib/theme.ts` and `lib/reading.ts` use,
 * for the same reason and read the same way — through `useSyncExternalStore`,
 * whose `getServerSnapshot` is what the server AND the hydrating client render
 * from. The stored value arrives in the re-render immediately after hydration:
 * one frame of Cards / Everything / All tracks, and a document that still has
 * its theme. There is deliberately no pre-paint script for these, unlike theme
 * and typography — those set a custom property or an attribute, while these
 * three choose which elements exist, which no inline script can do.
 */
import { COLLECTIONS, type Collection } from "~/lib/collection";
import { isStudyTrack, type TrackChoice } from "~/lib/study-track";

export const VIEW_MODE_KEY = "pf-library-view";
export const COLLECTION_KEY = "pf-library-collection";
export const TRACK_KEY = "pf-library-track";

/** Cards, compact tiles, or list. */
export const VIEW_MODES = ["cards", "compact", "list"] as const;
export type ViewMode = (typeof VIEW_MODES)[number];

export interface ShelfPrefs {
  viewMode: ViewMode;
  collection: Collection;
  track: TrackChoice;
}

/** What a reader who has never chosen anything sees — on the server, always. */
export const DEFAULT_SHELF: ShelfPrefs = {
  viewMode: "cards",
  collection: "all",
  track: "all",
};

/**
 * What is stored, validated per field against the choices the controls offer.
 *
 * Same rule as `storedReading` and the player's `loadRate`: a value that is
 * merely a string is not enough. A retired view mode, or a track chip that no
 * longer exists, would light no control and draw an empty grid — which reads as
 * the shelf being broken rather than as one stale key.
 */
export function storedShelf(): ShelfPrefs {
  try {
    const view = localStorage.getItem(VIEW_MODE_KEY);
    const collection = localStorage.getItem(COLLECTION_KEY);
    const track = localStorage.getItem(TRACK_KEY);
    return {
      viewMode: (VIEW_MODES as readonly string[]).includes(view ?? "")
        ? (view as ViewMode)
        : DEFAULT_SHELF.viewMode,
      collection: (COLLECTIONS as readonly string[]).includes(collection ?? "")
        ? (collection as Collection)
        : DEFAULT_SHELF.collection,
      track:
        track === "all" || isStudyTrack(track)
          ? (track as TrackChoice)
          : DEFAULT_SHELF.track,
    };
  } catch {
    // Private browsing, or storage disabled. The shelf still works; it just
    // starts where a first-time reader starts.
    return DEFAULT_SHELF;
  }
}

/* ---------------------------------------------------------------------------
 * One copy of the three settings, for however many controls read them.
 *
 * Read lazily rather than at module load, and cached: `getSnapshot` is called
 * on every render and must return the SAME value until something actually
 * changes, or React re-renders forever. Lazily, because this module is imported
 * by the server bundle too, where touching `localStorage` at import time would
 * throw before any page rendered.
 * ------------------------------------------------------------------------- */

let snapshot: ShelfPrefs | null = null;
const listeners = new Set<() => void>();

function current(): ShelfPrefs {
  if (snapshot === null) snapshot = storedShelf();
  return snapshot;
}

export function subscribeShelf(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * The three readers. One per field rather than one for the object, because
 * `getSnapshot` is compared by identity: a getter returning `{...}` would build
 * a new object every render and never settle.
 */
export const viewModeSnapshot = (): ViewMode => current().viewMode;
export const collectionSnapshot = (): Collection => current().collection;
export const trackSnapshot = (): TrackChoice => current().track;

/** What the server renders, and what the client hydrates against. */
export const defaultViewMode = (): ViewMode => DEFAULT_SHELF.viewMode;
export const defaultCollection = (): Collection => DEFAULT_SHELF.collection;
export const defaultTrack = (): TrackChoice => DEFAULT_SHELF.track;

/**
 * Update what is rendered, best-effort mirror it to storage, and tell every
 * control on screen. A reader whose storage is full or blocked still gets the
 * change for this visit — it just doesn't survive to the next one.
 */
function set(next: ShelfPrefs, key: string, value: string) {
  snapshot = next;
  try {
    localStorage.setItem(key, value);
  } catch {
    // See the doc comment above.
  }
  for (const listener of listeners) listener();
}

export function setViewMode(viewMode: ViewMode) {
  set({ ...current(), viewMode }, VIEW_MODE_KEY, viewMode);
}

export function setCollection(collection: Collection) {
  set({ ...current(), collection }, COLLECTION_KEY, collection);
}

export function setTrack(track: TrackChoice) {
  set({ ...current(), track }, TRACK_KEY, track);
}
