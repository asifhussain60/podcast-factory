/**
 * companion/types.ts — data model for the reader's private Companion notes.
 *
 * Companion notes are a PRIVATE, reader-only layer: per-chapter teaching notes
 * (analogies, explanations, questions to pose) that the reader surfaces during a
 * screen-share reading. They are NEVER written into book.md and never enter the
 * generated PDF — they live in _system/companion-notes/<chapter>.json, which is
 * git-tracked and therefore syncs across machines.
 *
 * Design intent (loose coupling + extensibility):
 *   - `kind` and `source.provider` are OPEN string types resolved through the
 *     registry (registry.ts), so a new note kind or a new source provider is ONE
 *     registry entry, not a schema change or a new renderer.
 *   - The UI depends only on these shapes and the store interface (store.client.ts),
 *     never on where the data physically lives — swap the backing store without
 *     touching a component.
 */

/** Open-ended note category. Known values live in KIND_DEFS (registry.ts). */
export type CompanionNoteKind = string;

/**
 * Where a note's content came from. Provider is open-ended (registry.ts):
 * 'notebooklm' (transcribed deep-dive), 'manual' (your own), or future providers.
 */
export interface CompanionSource {
  /** Registry provider id, e.g. 'notebooklm' | 'manual'. */
  provider: string;
  /** Coarse reference within the provider, e.g. 'EP05'. */
  ref?: string;
  /** Fine locator, e.g. a timestamp '04:12' or a page. */
  locator?: string;
  /** Optional display override; falls back to a composed label. */
  label?: string;
}

/** A single Companion note attached to one chapter. */
export interface CompanionNote {
  id: string;
  kind: CompanionNoteKind;
  /** The note text — the thing you'd say out loud. */
  body: string;
  /** Short card title / theme for the note, e.g. "spiritual infant, milk before meat".
   *  This is a display LABEL, not necessarily text found in the chapter. */
  anchor?: string;
  /** The VERBATIM chapter passage this note explains — an exact substring of the
   *  rendered chapter prose. The LIVE Session reader highlights it and uses it to
   *  show the one relevant card as you scroll. Distinct from `anchor` (the label):
   *  `anchor` is what the card is called, `quote` is where it lives in the text. */
  quote?: string;
  source?: CompanionSource;
  createdAt: string;
  updatedAt: string;
}

/** All Companion notes for one (book, chapter) pair — the on-disk unit. */
export interface CompanionChapterDoc {
  /** Book slug (content dir name). */
  slug: string;
  /** Chapter/section key this file holds notes for. */
  chapter: string;
  notes: CompanionNote[];
  updatedAt: string | null;
}

/** Lightweight per-chapter summary for the chapter switcher. */
export interface CompanionChapterSummary {
  chapter: string;
  count: number;
}

/** Fields a caller supplies to create or update a note (id optional = create). */
export type CompanionNoteInput = {
  id?: string;
  kind: CompanionNoteKind;
  body: string;
  anchor?: string;
  quote?: string;
  source?: CompanionSource;
};
