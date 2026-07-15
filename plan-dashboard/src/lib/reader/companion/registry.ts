/**
 * companion/registry.ts — the extensibility seam for Companion notes.
 *
 * Adding a note KIND or a source PROVIDER is a single entry here — no renderer
 * change, no schema migration. The panel and card read labels/icons/colours from
 * these registries by id and degrade gracefully for unknown ids, so data authored
 * with a future kind never breaks an older client.
 *
 * Icons are Font Awesome classes (the site already loads FA — see book.astro).
 * Colours reference existing --c-* theme tokens ONLY; no new colours introduced.
 */
import type { CompanionNoteKind } from './types';

export interface KindDef {
  id: CompanionNoteKind;
  label: string;
  /** Font Awesome class, e.g. 'fa-solid fa-lightbulb'. */
  icon: string;
  /** One-line purpose shown in the composer. */
  blurb: string;
}

/** Known note kinds, in composer/display order. Extend by appending an entry. */
export const KIND_DEFS: KindDef[] = [
  {
    id: 'analogy',
    label: 'Analogy',
    icon: 'fa-solid fa-lightbulb',
    blurb: 'A comparison that makes the passage click.',
  },
  {
    id: 'explanation',
    label: 'Explanation',
    icon: 'fa-solid fa-book-open',
    blurb: 'A plain-language unpacking of the idea.',
  },
  {
    id: 'question',
    label: 'Ask them',
    icon: 'fa-solid fa-circle-question',
    blurb: 'A question to pose to whoever you are reading with.',
  },
  {
    id: 'note',
    label: 'Aside',
    icon: 'fa-solid fa-pen',
    blurb: 'Your own note or reminder.',
  },
];

export const DEFAULT_KIND: CompanionNoteKind = 'analogy';

const KIND_MAP = new Map(KIND_DEFS.map((k) => [k.id, k]));

/** Resolve a kind def, falling back to a neutral def for unknown ids. */
export function kindDef(id: CompanionNoteKind): KindDef {
  return KIND_MAP.get(id) ?? { id, label: id, icon: 'fa-solid fa-note-sticky', blurb: '' };
}

export interface SourceProvider {
  id: string;
  label: string;
  icon: string;
  /** A --c-* token name used to tint the source pill. */
  tokenVar: string;
}

/** Known source providers. Extend by appending an entry. */
export const SOURCE_PROVIDERS: SourceProvider[] = [
  {
    id: 'notebooklm',
    label: 'NotebookLM',
    icon: 'fa-solid fa-microphone-lines',
    tokenVar: '--c-vendor-notebooklm',
  },
  {
    id: 'manual',
    label: 'You',
    icon: 'fa-solid fa-user',
    tokenVar: '--c-accent',
  },
];

const PROVIDER_MAP = new Map(SOURCE_PROVIDERS.map((p) => [p.id, p]));

export function sourceProvider(id: string): SourceProvider {
  return PROVIDER_MAP.get(id) ?? { id, label: id, icon: 'fa-solid fa-tag', tokenVar: '--c-ink-dim' };
}
