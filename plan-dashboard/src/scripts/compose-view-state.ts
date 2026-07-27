/**
 * compose-view-state.ts — what the Book Composer remembers between visits.
 *
 * Defined in ONE module rather than at each use site, because
 * `defineViewState` refuses a duplicate surface+field: a single definition
 * point is what makes that refusal a design guarantee instead of a trap for
 * whoever imports second.
 *
 * All four are scoped by book slug. The chapter you had open in one book must
 * never be restored into another — a restore that lands you somewhere
 * plausible but wrong is worse than no restore at all.
 *
 * These replace the previous one-shot sessionStorage handoffs
 * (`cx-restore-chapter`, `cx-restore-edit`, `cx-restore-lane:<slug>`), which
 * were written immediately before a scripted reload and deleted on read. That
 * mechanism kept your place across the editor's own refresh and lost it on a
 * plain F5, a new tab, or the next morning. One durable mechanism now covers
 * both cases, so there is no second path to drift out of step.
 */
import { defineViewState, oneOf, existing } from "../lib/view-state";

export type ComposeLaneName = "book" | "podcast";
export type ComposeMode = "read" | "edit";

/**
 * The chapter keys the currently-loaded book actually has. Populated by the
 * Composer during setup, before the first read, so a remembered chapter that a
 * re-compose has since renamed or removed fails validation inside the module
 * rather than leaving the page pointed at nothing.
 */
const knownChapters = new Set<string>();

export function registerComposeChapters(keys: Iterable<string>): void {
  knownChapters.clear();
  for (const key of keys) knownChapters.add(key);
}

/** Podcast-lane source files, kept separately: the two lanes are independently
 *  segmented and share no chapter identity. */
const knownPodcastFiles = new Set<string>();

export function registerComposePodcastFiles(files: Iterable<string>): void {
  knownPodcastFiles.clear();
  for (const file of files) knownPodcastFiles.add(file);
}

export const composeChapter = defineViewState({
  surface: "compose",
  field: "chapter",
  validate: existing((key) => knownChapters.has(key)),
});

export const composePodcastFile = defineViewState({
  surface: "compose",
  field: "podcast-file",
  validate: existing((file) => knownPodcastFiles.has(file)),
});

export const composeLane = defineViewState<ComposeLaneName>({
  surface: "compose",
  field: "lane",
  validate: oneOf(["book", "podcast"] as const),
});

/**
 * Read vs Edit. Restoring straight into the editor is only safe because
 * autosave now refuses to write a document identical to the one it loaded
 * (RCA-002 AI-1) — before that guard, landing in an armed editor on every
 * visit turned a stray keystroke into a write to book.md.
 */
export const composeMode = defineViewState<ComposeMode>({
  surface: "compose",
  field: "mode",
  validate: oneOf(["read", "edit"] as const),
});
