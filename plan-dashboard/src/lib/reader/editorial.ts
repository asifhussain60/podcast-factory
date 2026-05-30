/**
 * editorial.ts — Editorial-decisions cockpit model for the Studio re-platform (WC8 Slice 5b).
 *
 * The Studio's right panel is a stack of EDITORIAL CARDS — the canonical editorial decisions
 * that steer how a book is voiced, enriched, and narrated. Decisions live at two scopes:
 *   - BOOK level (canonical default for every chapter):  _system/editorial/book.json
 *   - CHAPTER level (per-chapter OVERRIDE of a card):     _system/editorial/<chapter>.json
 * The effective value for a chapter is its override if present, else the book-level value.
 *
 * Persisted as JSON (NOT yaml) on purpose: the Slice-6 Python orchestrator reads the same
 * files to drive stage advancement, and stdlib `json` works in node AND python (PyYAML is not
 * installed in the pipeline venv). Mirrors the stage-review.ts persistence shape.
 *
 * Card VALUES are modelled generically by `kind` ('list' | 'pairs' | 'choice') so the cockpit
 * is tradition-agnostic and extensible: a new card or a new tradition adds a CARD_DEF entry,
 * not a new renderer. Authority: _workspace/plan/CONTINUATION-2026-05-30.md Slice 5b.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';

const REPO_ROOT = join(new URL(import.meta.url).pathname, '../../../../../');

export type CardId =
  | 'name_resolution'
  | 'key_focus'
  | 'tone_register'
  | 'forbidden_terms'
  | 'required_elements'
  | 'audience_calibration';

export type CardKind = 'list' | 'pairs' | 'choice';

/** A from->to rename pair (name_resolution). */
export interface Pair {
  from: string;
  to: string;
}

/** The stored value of a single card. Shape depends on the card's `kind`. */
export interface CardValue {
  /** kind 'list' / 'choice'-notes use this; 'pairs' uses `pairs`. */
  items?: string[];
  /** kind 'pairs'. */
  pairs?: Pair[];
  /** kind 'choice' — the selected preset key. */
  preset?: string;
  /** free-text rationale, any kind. */
  notes?: string;
}

export interface CardDef {
  id: CardId;
  title: string;
  kind: CardKind;
  /** One-line purpose, shown under the card title. */
  blurb: string;
  /** kind 'choice' — allowed presets. */
  presets?: { key: string; label: string }[];
  /** placeholder for list/pairs item entry. */
  placeholder?: string;
}

/** The six canonical editorial cards. Order is the default stack order (user-reorderable later). */
export const CARD_DEFS: CardDef[] = [
  {
    id: 'name_resolution',
    title: 'Name Resolution',
    kind: 'pairs',
    blurb: 'How names and terms render in the voiced text (source spelling → house spelling).',
    placeholder: 'al-Ghazali → Ghazali',
  },
  {
    id: 'key_focus',
    title: 'Key Focus',
    kind: 'list',
    blurb: 'The central ideas this book (or chapter) must keep in the foreground, in priority order.',
    placeholder: 'e.g. knowledge that is not acted upon is a proof against you',
  },
  {
    id: 'tone_register',
    title: 'Tone & Register',
    kind: 'choice',
    blurb: 'The house voice this content maps to during normalization (SN-1).',
    presets: [
      { key: 'editorial_modern', label: 'Editorial-modern (Stripe/MIT Press)' },
      { key: 'warm_teacherly', label: 'Warm & teacherly' },
      { key: 'plain_direct', label: 'Plain & direct' },
      { key: 'reverent_formal', label: 'Reverent & formal' },
    ],
  },
  {
    id: 'forbidden_terms',
    title: 'Forbidden Terms',
    kind: 'list',
    blurb: 'Words/phrases the voiced text must never use (e.g. lossy paraphrases of a terminus technicus — SN-7).',
    placeholder: 'e.g. esoteric interpretation (use "tawil")',
  },
  {
    id: 'required_elements',
    title: 'Required Elements',
    kind: 'list',
    blurb: 'Things that MUST survive into the final text (verbatim scripture, key stories, glosses).',
    placeholder: 'e.g. the Junayd dream; farḍ ʿayn glossed on first use',
  },
  {
    id: 'audience_calibration',
    title: 'Audience Calibration',
    kind: 'choice',
    blurb: 'Who the podcast addresses — sets how much insider vocabulary is assumed.',
    presets: [
      { key: 'general_intelligent', label: 'Intelligent general reader (no insider vocab)' },
      { key: 'curious_seeker', label: 'Curious seeker (some terms, always glossed)' },
      { key: 'student', label: 'Student of the tradition (terms assumed)' },
      { key: 'specialist', label: 'Specialist (full technical register)' },
    ],
  },
];

export const CARD_IDS: CardId[] = CARD_DEFS.map((c) => c.id);

export type Scope = 'book' | string; // 'book' or a chapter slug

export interface EditorialDoc {
  slug: string;
  scope: Scope;
  /** Only cards explicitly set at this scope appear here. Absent => inherits. */
  cards: Partial<Record<CardId, CardValue>>;
  updated_at: string | null;
}

function editorialPath(slug: string, scope: Scope): string {
  const file = scope === 'book' ? 'book.json' : `${scope}.json`;
  return join(REPO_ROOT, 'content', 'drafts', 'books', slug, '_system', 'editorial', file);
}

function emptyDoc(slug: string, scope: Scope): EditorialDoc {
  return { slug, scope, cards: {}, updated_at: null };
}

export function readEditorial(slug: string, scope: Scope): EditorialDoc {
  const p = editorialPath(slug, scope);
  if (!existsSync(p)) return emptyDoc(slug, scope);
  try {
    const parsed = JSON.parse(readFileSync(p, 'utf8')) as EditorialDoc;
    return { slug, scope, cards: parsed.cards ?? {}, updated_at: parsed.updated_at ?? null };
  } catch {
    return emptyDoc(slug, scope);
  }
}

/** Write (or clear) a single card at a scope. Passing `null` removes the override/value. */
export function setEditorialCard(
  slug: string,
  scope: Scope,
  card: CardId,
  value: CardValue | null,
): EditorialDoc {
  const doc = readEditorial(slug, scope);
  if (value === null) {
    delete doc.cards[card];
  } else {
    doc.cards[card] = value;
  }
  doc.updated_at = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  const p = editorialPath(slug, scope);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(doc, null, 2), 'utf8');
  return doc;
}

export interface ResolvedCard {
  card: CardId;
  value: CardValue | null;
  /** where the effective value comes from. */
  source: 'override' | 'book' | 'unset';
}

/**
 * Effective decisions for a chapter: per card, the chapter override if present, else book-level,
 * else unset. `chapter === 'book'` returns the book-level values directly (source 'book'/'unset').
 */
export function resolveEffective(slug: string, chapter: Scope): ResolvedCard[] {
  const book = readEditorial(slug, 'book');
  const override = chapter === 'book' ? emptyDoc(slug, 'book') : readEditorial(slug, chapter);
  return CARD_IDS.map((id) => {
    if (chapter !== 'book' && override.cards[id] !== undefined) {
      return { card: id, value: override.cards[id]!, source: 'override' as const };
    }
    if (book.cards[id] !== undefined) {
      return { card: id, value: book.cards[id]!, source: 'book' as const };
    }
    return { card: id, value: null, source: 'unset' as const };
  });
}

/** List chapter slugs that carry at least one override (for the cockpit's override badges). */
export function chaptersWithOverrides(slug: string): string[] {
  const dir = join(REPO_ROOT, 'content', 'drafts', 'books', slug, '_system', 'editorial');
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith('.json') && f !== 'book.json')
    .map((f) => f.replace(/\.json$/, ''));
}
