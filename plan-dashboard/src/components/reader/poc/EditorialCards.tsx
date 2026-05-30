/**
 * EditorialCards — the Studio re-platform's editorial cockpit (WC8 Slice 5b).
 *
 * A vertical stack of editorial-decision cards (Name Resolution, Key Focus, Tone & Register,
 * Forbidden Terms, Required Elements, Audience Calibration). Decisions are canonical at BOOK
 * scope and overridable per CHAPTER. The cockpit follows the editor's chapter (via the
 * `studio:chapter-change` window event) and persists each card to /api/studio/editorial, which
 * the Slice-6 orchestrator reads to steer stage advancement.
 *
 * v1 is dependency-free: items reorder with up/down controls (dnd-kit sortable + cmdk corpus
 * search are the planned enhancement, layered later without changing this model). No Tailwind /
 * no inline styles — classes are defined in studio-poc.css (Cortex HTML-view standard).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';

type CardKind = 'list' | 'pairs' | 'choice';
interface Pair { from: string; to: string }
interface CardValue { items?: string[]; pairs?: Pair[]; preset?: string; notes?: string }
interface CardDef {
  id: string;
  title: string;
  kind: CardKind;
  blurb: string;
  presets?: { key: string; label: string }[];
  placeholder?: string;
}
interface ResolvedCard { card: string; value: CardValue | null; source: 'override' | 'book' | 'unset' }
interface Chapter { id: string; title: string }
interface Props { slug: string; chapters: Chapter[]; cardDefs: CardDef[] }

const BOOK = 'book';

export default function EditorialCards({ slug, chapters, cardDefs }: Props) {
  const [scope, setScope] = useState<string>(BOOK);
  const [resolved, setResolved] = useState<Record<string, ResolvedCard>>({});
  const [overriddenChapters, setOverriddenChapters] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingCard, setSavingCard] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (scope === BOOK) {
        const r = await fetch(`/api/studio/editorial?slug=${slug}&scope=book`).then((x) => x.json());
        const doc = r.data ?? r;
        const map: Record<string, ResolvedCard> = {};
        for (const d of cardDefs) {
          const v = doc.cards?.[d.id] ?? null;
          map[d.id] = { card: d.id, value: v, source: v ? 'book' : 'unset' };
        }
        setResolved(map);
        setOverriddenChapters(doc.overriddenChapters ?? []);
      } else {
        const r = await fetch(`/api/studio/editorial?slug=${slug}&chapter=${scope}&resolve=1`).then((x) => x.json());
        const list: ResolvedCard[] = (r.data ?? r).resolved ?? [];
        const map: Record<string, ResolvedCard> = {};
        for (const rc of list) map[rc.card] = rc;
        setResolved(map);
      }
    } finally {
      setLoading(false);
    }
    // cardDefs is a stable module constant captured by closure; it is not a fetch input.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, slug]);

  useEffect(() => { void load(); }, [load]);

  // Follow the editor's chapter switcher.
  useEffect(() => {
    const onChange = (e: Event) => {
      const id = (e as CustomEvent<{ chapter: string }>).detail?.chapter;
      if (id) setScope(id);
    };
    window.addEventListener('studio:chapter-change', onChange);
    return () => window.removeEventListener('studio:chapter-change', onChange);
  }, []);

  const save = useCallback(async (card: string, value: CardValue | null) => {
    setSavingCard(card);
    try {
      await fetch('/api/studio/editorial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, scope, card, value }),
      });
      await load();
    } finally {
      setSavingCard(null);
    }
  }, [slug, scope, load]);

  const isChapterScope = scope !== BOOK;

  return (
    <aside className="ec-cockpit" aria-label="Editorial decisions">
      <header className="ec-head">
        <h2 className="ec-title">Editorial cockpit</h2>
        <p className="ec-sub">Canonical decisions for the book; override any card per chapter.</p>
        <label className="ec-scope" htmlFor="ec-scope-sel">Scope</label>
        <select id="ec-scope-sel" className="ec-scope-sel" value={scope} onChange={(e) => setScope(e.target.value)}>
          <option value={BOOK}>Book (canonical)</option>
          {chapters.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}{overriddenChapters.includes(c.id) ? ' •' : ''}
            </option>
          ))}
        </select>
      </header>

      {loading && <p className="ec-loading">Loading…</p>}

      <div className="ec-stack">
        {cardDefs.map((def) => (
          <EditorialCard
            key={def.id}
            def={def}
            resolved={resolved[def.id]}
            isChapterScope={isChapterScope}
            saving={savingCard === def.id}
            onSave={(v) => save(def.id, v)}
          />
        ))}
      </div>
    </aside>
  );
}

function EditorialCard({
  def, resolved, isChapterScope, saving, onSave,
}: {
  def: CardDef;
  resolved?: ResolvedCard;
  isChapterScope: boolean;
  saving: boolean;
  onSave: (v: CardValue | null) => void;
}) {
  const value = resolved?.value ?? null;
  const source = resolved?.source ?? 'unset';
  // Local draft so typing doesn't round-trip on every keystroke. Reset when the resolved value
  // changes (stable string key — raw JSON.stringify in a dep array breaks under Strict Mode).
  const [draft, setDraft] = useState<CardValue>(() => seed(def, value));
  const valueKey = useMemo(() => JSON.stringify(value), [value]);
  useEffect(() => { setDraft(seed(def, value)); }, [def.id, valueKey]);

  const badge = isChapterScope
    ? source === 'override' ? <span className="ec-badge ec-badge--ovr">override</span>
    : source === 'book' ? <span className="ec-badge ec-badge--inh">inherited</span>
    : <span className="ec-badge ec-badge--unset">unset</span>
    : source === 'unset' ? <span className="ec-badge ec-badge--unset">unset</span> : null;

  return (
    <section className="ec-card">
      <div className="ec-card-head">
        <h3 className="ec-card-title">{def.title}</h3>
        {badge}
      </div>
      <p className="ec-card-blurb">{def.blurb}</p>

      {def.kind === 'list' && (
        <ListEditor items={draft.items ?? []} placeholder={def.placeholder}
          onChange={(items) => setDraft({ ...draft, items })} />
      )}
      {def.kind === 'pairs' && (
        <PairsEditor pairs={draft.pairs ?? []} placeholder={def.placeholder}
          onChange={(pairs) => setDraft({ ...draft, pairs })} />
      )}
      {def.kind === 'choice' && (
        <ChoiceEditor defId={def.id} presets={def.presets ?? []} preset={draft.preset} notes={draft.notes ?? ''}
          onChange={(preset, notes) => setDraft({ ...draft, preset, notes })} />
      )}

      <div className="ec-card-actions">
        <button className="ec-btn ec-btn--save" disabled={saving} onClick={() => onSave(normalize(def, draft))}>
          {saving ? 'Saving…' : isChapterScope ? 'Set override' : 'Save'}
        </button>
        {isChapterScope && source === 'override' && (
          <button className="ec-btn ec-btn--reset" disabled={saving} onClick={() => onSave(null)}>
            Reset to book
          </button>
        )}
      </div>
    </section>
  );
}

function seed(def: CardDef, value: CardValue | null): CardValue {
  if (value) return { items: value.items, pairs: value.pairs, preset: value.preset, notes: value.notes };
  if (def.kind === 'list') return { items: [] };
  if (def.kind === 'pairs') return { pairs: [] };
  return { preset: def.presets?.[0]?.key, notes: '' };
}

function normalize(def: CardDef, d: CardValue): CardValue {
  if (def.kind === 'list') return { items: (d.items ?? []).filter((s) => s.trim()) };
  if (def.kind === 'pairs') return { pairs: (d.pairs ?? []).filter((p) => p.from.trim() && p.to.trim()) };
  return { preset: d.preset, notes: (d.notes ?? '').trim() };
}

function ListEditor({ items, placeholder, onChange }: { items: string[]; placeholder?: string; onChange: (v: string[]) => void }) {
  const set = (i: number, v: string) => onChange(items.map((x, j) => (j === i ? v : x)));
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= items.length) return;
    const next = [...items];
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  };
  return (
    <div className="ec-list">
      {items.map((it, i) => (
        <div className="ec-list-row" key={i}>
          <input className="ec-input" value={it} placeholder={placeholder} onChange={(e) => set(i, e.target.value)} />
          <div className="ec-list-ctl">
            <button className="ec-mini" aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
            <button className="ec-mini" aria-label="Move down" disabled={i === items.length - 1} onClick={() => move(i, 1)}>↓</button>
            <button className="ec-mini ec-mini--del" aria-label="Remove" onClick={() => onChange(items.filter((_, j) => j !== i))}>×</button>
          </div>
        </div>
      ))}
      <button className="ec-add" onClick={() => onChange([...items, ''])}>+ Add</button>
    </div>
  );
}

function PairsEditor({ pairs, placeholder, onChange }: { pairs: Pair[]; placeholder?: string; onChange: (v: Pair[]) => void }) {
  const set = (i: number, k: keyof Pair, v: string) => onChange(pairs.map((p, j) => (j === i ? { ...p, [k]: v } : p)));
  return (
    <div className="ec-list">
      {pairs.map((p, i) => (
        <div className="ec-pair-row" key={i}>
          <input className="ec-input" value={p.from} placeholder="source" onChange={(e) => set(i, 'from', e.target.value)} />
          <span className="ec-arrow" aria-hidden="true">→</span>
          <input className="ec-input" value={p.to} placeholder="house" onChange={(e) => set(i, 'to', e.target.value)} />
          <button className="ec-mini ec-mini--del" aria-label="Remove" onClick={() => onChange(pairs.filter((_, j) => j !== i))}>×</button>
        </div>
      ))}
      <button className="ec-add" onClick={() => onChange([...pairs, { from: '', to: '' }])}>+ Add{placeholder ? ` (${placeholder})` : ''}</button>
    </div>
  );
}

function ChoiceEditor({ defId, presets, preset, notes, onChange }: {
  defId: string;
  presets: { key: string; label: string }[];
  preset?: string;
  notes: string;
  onChange: (preset: string, notes: string) => void;
}) {
  return (
    <div className="ec-choice">
      {presets.map((p) => (
        <label className="ec-radio" key={p.key}>
          <input type="radio" name={`ec-${defId}`} checked={preset === p.key} onChange={() => onChange(p.key, notes)} />
          <span>{p.label}</span>
        </label>
      ))}
      <textarea className="ec-notes" value={notes} aria-label="Notes" placeholder="Notes (optional)…" onChange={(e) => onChange(preset ?? '', e.target.value)} />
    </div>
  );
}
