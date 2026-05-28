/**
 * Centralised localStorage key builders — prevents key collisions and typos
 * across reader components. All keys share the `pf-reader:` namespace.
 */

export const STORAGE_KEYS = {
  /** Per-book, per-chapter editor state (block edits + diff). */
  chapterEditor: (book: string, chapter: string) =>
    `pf-reader:chapter-editor:${book}:${chapter}`,

  /** Per-book, per-chapter annotation queue. */
  annotationQueue: (book: string, chapter: string) =>
    `pf-reader:annotation-queue:${book}:${chapter}`,

  /** Whether the right rail is collapsed (boolean string). */
  rightRailCollapsed: 'pf-reader:right-rail-collapsed',

  /** Reader display settings (font size, RTL mode, etc.). */
  readerSettings: 'pf-reader:settings',

  /** Per-book collapsible section states. */
  sectionCollapsed: (book: string, sectionId: string) =>
    `pf-reader:section-collapsed:${book}:${sectionId}`,
} as const;
