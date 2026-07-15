/**
 * CompanionPanel — the private, reader-only Companion notes surface.
 *
 * Loose coupling by construction:
 *   - Talks only to a CompanionStore (default: API-backed) — swap persistence
 *     without touching this file.
 *   - `layout` flips docked (in-flow column) ↔ floating (fixed drawer) via ONE prop
 *     and one CSS modifier class; the toggle here just persists that choice.
 *   - Note kinds and source providers come from the registry, so this component
 *     never hard-codes the set of note types.
 *
 * It is never part of book.md or the PDF — it is a client island the reader mounts.
 */
import { useCallback, useEffect, useState } from 'react';
import CompanionCard from './CompanionCard';
import { KIND_DEFS, DEFAULT_KIND, SOURCE_PROVIDERS } from '../../../lib/reader/companion/registry';
import { defaultStore, type CompanionStore } from '../../../lib/reader/companion/store.client';
import type { CompanionNote } from '../../../lib/reader/companion/types';

export interface ChapterRef {
  key: string;
  title: string;
}

interface Props {
  slug: string;
  chapters: ChapterRef[];
  initialChapter?: string;
  layout?: LayoutMode;
  store?: CompanionStore;
}

type LayoutMode = 'docked' | 'floating';

const LAYOUT_KEY = 'pf-companion:layout';
const PRESENT_KEY = 'pf-companion:present';
const chapterKeyFor = (slug: string) => `pf-companion:chapter:${slug}`;

interface Draft {
  id?: string;
  kind: string;
  body: string;
  anchor: string;
  provider: string;
  ref: string;
  locator: string;
}

const EMPTY_DRAFT: Draft = {
  kind: DEFAULT_KIND,
  body: '',
  anchor: '',
  provider: 'manual',
  ref: '',
  locator: '',
};

function readPref(key: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback;
  return window.localStorage.getItem(key) ?? fallback;
}

export default function CompanionPanel({ slug, chapters, initialChapter, layout, store }: Props) {
  const st = store ?? defaultStore;
  const validKeys = new Set(chapters.map((c) => c.key));
  const remembered = readPref(chapterKeyFor(slug), '');
  const [chapter, setChapterState] = useState(
    (remembered && validKeys.has(remembered) && remembered) ||
      initialChapter ||
      chapters[0]?.key ||
      'general',
  );

  const setChapter = useCallback(
    (next: string) => {
      setChapterState(next);
      if (typeof window !== 'undefined') window.localStorage.setItem(chapterKeyFor(slug), next);
    },
    [slug],
  );
  const [notes, setNotes] = useState<CompanionNote[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [mode, setMode] = useState<LayoutMode>(layout ?? (readPref(LAYOUT_KEY, 'docked') as LayoutMode));
  const [present, setPresent] = useState(readPref(PRESENT_KEY, '0') === '1');
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const doc = await st.read(slug, chapter);
      setNotes(doc.notes);
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  }, [st, slug, chapter]);

  useEffect(() => {
    void load();
  }, [load]);

  function persistLayout(next: LayoutMode) {
    setMode(next);
    if (typeof window !== 'undefined') window.localStorage.setItem(LAYOUT_KEY, next);
  }
  function persistPresent(next: boolean) {
    setPresent(next);
    if (typeof window !== 'undefined') window.localStorage.setItem(PRESENT_KEY, next ? '1' : '0');
  }

  function startNew() {
    setDraft({ ...EMPTY_DRAFT });
  }
  function startEdit(note: CompanionNote) {
    setDraft({
      id: note.id,
      kind: note.kind,
      body: note.body,
      anchor: note.anchor ?? '',
      provider: note.source?.provider ?? 'manual',
      ref: note.source?.ref ?? '',
      locator: note.source?.locator ?? '',
    });
  }

  async function saveDraft() {
    if (!draft || !draft.body.trim()) return;
    const source =
      draft.provider === 'manual' && !draft.ref && !draft.locator
        ? { provider: 'manual' }
        : { provider: draft.provider, ref: draft.ref || undefined, locator: draft.locator || undefined };
    try {
      await st.upsert(slug, chapter, {
        id: draft.id,
        kind: draft.kind,
        body: draft.body,
        anchor: draft.anchor || undefined,
        source,
      });
      setDraft(null);
      await load();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }

  async function removeNote(note: CompanionNote) {
    try {
      await st.remove(slug, chapter, note.id);
      await load();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }

  const rootClass = `cpn cpn--${mode}${present ? ' cpn--present' : ''}${open ? '' : ' cpn--collapsed'}`;

  if (mode === 'floating' && !open) {
    return (
      <button type="button" className="cpn-launcher" onClick={() => setOpen(true)}>
        <i className="fa-solid fa-book-open-reader" aria-hidden="true" /> Companion
      </button>
    );
  }

  return (
    <aside className={rootClass} aria-label="Companion notes (private)">
      <header className="cpn-head">
        <div className="cpn-head-title">
          <i className="fa-solid fa-lock" aria-hidden="true" />
          <span>Companion</span>
          <span className="cpn-private">private</span>
        </div>
        <div className="cpn-head-tools">
          <button
            type="button"
            className="cpn-icon-btn"
            aria-pressed={present}
            aria-label={present ? 'Exit present mode' : 'Present mode (hide editing)'}
            onClick={() => persistPresent(!present)}
          >
            <i className={present ? 'fa-solid fa-eye' : 'fa-solid fa-eye-slash'} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="cpn-icon-btn"
            aria-label={mode === 'docked' ? 'Float panel' : 'Dock panel'}
            onClick={() => persistLayout(mode === 'docked' ? 'floating' : 'docked')}
          >
            <i
              className={mode === 'docked' ? 'fa-solid fa-up-right-from-square' : 'fa-solid fa-down-left-and-up-right-to-center'}
              aria-hidden="true"
            />
          </button>
          {mode === 'floating' && (
            <button type="button" className="cpn-icon-btn" aria-label="Close panel" onClick={() => setOpen(false)}>
              <i className="fa-solid fa-xmark" aria-hidden="true" />
            </button>
          )}
        </div>
      </header>

      {chapters.length > 0 && (
        <div className="cpn-chapter">
          <label className="cpn-field-label" htmlFor="cpn-chapter-select">
            Chapter
          </label>
          <select
            id="cpn-chapter-select"
            className="cpn-select"
            value={chapter}
            onChange={(e) => setChapter(e.target.value)}
          >
            {chapters.map((c) => (
              <option key={c.key} value={c.key}>
                {c.title}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <p className="cpn-error" role="alert">{error}</p>}

      <div className="cpn-list">
        {loading && <p className="cpn-empty">Loading…</p>}
        {!loading && notes.length === 0 && (
          <p className="cpn-empty">No notes for this chapter yet.</p>
        )}
        {!loading &&
          notes.map((n) => (
            <CompanionCard
              key={n.id}
              note={n}
              readOnly={present}
              onEdit={startEdit}
              onDelete={removeNote}
            />
          ))}
      </div>

      {!present && !draft && (
        <button type="button" className="cpn-add" onClick={startNew}>
          <i className="fa-solid fa-plus" aria-hidden="true" /> Add note
        </button>
      )}

      {!present && draft && (
        <form
          className="cpn-composer"
          onSubmit={(e) => {
            e.preventDefault();
            void saveDraft();
          }}
        >
          <div className="cpn-composer-row">
            <label className="cpn-field-label" htmlFor="cpn-kind">Kind</label>
            <select
              id="cpn-kind"
              className="cpn-select"
              value={draft.kind}
              onChange={(e) => setDraft({ ...draft, kind: e.target.value })}
            >
              {KIND_DEFS.map((k) => (
                <option key={k.id} value={k.id}>{k.label}</option>
              ))}
            </select>
          </div>

          <label className="cpn-field-label" htmlFor="cpn-anchor">Passage (optional)</label>
          <input
            id="cpn-anchor"
            className="cpn-input"
            value={draft.anchor}
            placeholder="Quote the sentence this explains"
            onChange={(e) => setDraft({ ...draft, anchor: e.target.value })}
          />

          <label className="cpn-field-label" htmlFor="cpn-body">Note</label>
          <textarea
            id="cpn-body"
            className="cpn-textarea"
            value={draft.body}
            rows={4}
            placeholder="The explanation or analogy you'd say out loud"
            onChange={(e) => setDraft({ ...draft, body: e.target.value })}
          />

          <div className="cpn-composer-row">
            <label className="cpn-field-label" htmlFor="cpn-provider">Source</label>
            <select
              id="cpn-provider"
              className="cpn-select"
              value={draft.provider}
              onChange={(e) => setDraft({ ...draft, provider: e.target.value })}
            >
              {SOURCE_PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>

          {draft.provider !== 'manual' && (
            <div className="cpn-composer-row cpn-composer-row--split">
              <input
                className="cpn-input"
                value={draft.ref}
                placeholder="Ref (e.g. EP05)"
                aria-label="Source reference"
                onChange={(e) => setDraft({ ...draft, ref: e.target.value })}
              />
              <input
                className="cpn-input"
                value={draft.locator}
                placeholder="At (e.g. 04:12)"
                aria-label="Source locator"
                onChange={(e) => setDraft({ ...draft, locator: e.target.value })}
              />
            </div>
          )}

          <div className="cpn-composer-actions">
            <button type="submit" className="cpn-btn cpn-btn--primary" disabled={!draft.body.trim()}>
              {draft.id ? 'Save' : 'Add'}
            </button>
            <button type="button" className="cpn-btn" onClick={() => setDraft(null)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <p className="cpn-foot">
        <i className="fa-solid fa-file-circle-xmark" aria-hidden="true" /> Private to you · never in the PDF
      </p>
    </aside>
  );
}
