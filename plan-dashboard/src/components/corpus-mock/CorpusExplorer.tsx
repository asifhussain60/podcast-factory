/**
 * CorpusExplorer.tsx — MOCK interactive explorer for the consolidated corpus.
 *
 * Two linked surfaces over the hardcoded sample (src/data/corpus-mock-sample.ts):
 *   1. Faceted full-text search — powered by Orama (@orama/orama), an in-memory
 *      full-text + facets engine. Facets: type · tradition · corpus · topic tag.
 *   2. Augmentation selection — a cmdk command palette to find + pick atoms, a
 *      selection tray, and a live preview of the "PRIOR DOCTRINAL CONTEXT" block
 *      injected into the prose, with the tradition firewall enforced.
 *
 * MOCK ONLY — client-side over ~17 sample atoms; production runs this against the
 * 7,036-atom knowledge.db (Orama index or SQLite FTS, server-side + virtualized).
 */
import { create, insertMultiple, search } from '@orama/orama';
import { Command } from 'cmdk';
import { Plus, Check, X, Search, Filter } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  SAMPLE_ATOMS, SAMPLE_PROSE, CORPUS_TOTALS,
  type MockAtom, type AtomType, type Tradition, type CorpusId,
} from '../../data/corpus-mock-sample';

const BOOK_TRADITION: Tradition = 'fatimid-ismaili';
// Tradition firewall (D5/D15): a book may only be augmented by same-tradition atoms
// plus tradition-neutral 'universal' scripture. 'ismaili' is within the fatimid-ismaili family.
const ELIGIBLE: Tradition[] = ['universal', 'fatimid-ismaili', 'ismaili'];

const TYPE_ORDER: AtomType[] = ['quran', 'hadith', 'term', 'doctrine', 'etymology', 'poetry'];
const TRAD_ORDER: Tradition[] = ['universal', 'fatimid-ismaili', 'ismaili'];
const CORPUS_ORDER: CorpusId[] = ['quran', 'wisdom', 'hadith', 'ksessions'];

type Facets = { type: Set<string>; tradition: Set<string>; corpus: Set<string>; tag: Set<string> };

function emptyFacets(): Facets {
  return { type: new Set(), tradition: new Set(), corpus: new Set(), tag: new Set() };
}

export default function CorpusExplorer() {
  const [db, setDb] = useState<any>(null);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<MockAtom[]>(SAMPLE_ATOMS);
  const [facets, setFacets] = useState<Facets>(emptyFacets);
  const [selected, setSelected] = useState<MockAtom[]>([]);

  // Build the Orama index once.
  useEffect(() => {
    (async () => {
      const idx = await create({
        schema: {
          // string/string[] so all are full-text searchable; faceting is done in JS.
          id: 'string', title: 'string', text_en: 'string', arabic: 'string',
          type: 'string', tradition: 'string', corpus: 'string', topic_tags: 'string[]',
        },
      });
      await insertMultiple(idx, SAMPLE_ATOMS as any);
      setDb(idx);
    })();
  }, []);

  // Run the full-text query (Orama) whenever the query changes; facet filtering
  // is applied in JS so per-facet counts stay visible regardless of selection.
  useEffect(() => {
    (async () => {
      if (!db) return;
      if (!query.trim()) { setHits(SAMPLE_ATOMS); return; }
      const res = await search(db, { term: query, properties: ['title', 'text_en', 'arabic', 'topic_tags'], limit: 200, tolerance: 1 });
      const ranked = res.hits.map((h: any) => h.document as MockAtom);
      setHits(ranked);
    })();
  }, [db, query]);

  const passesFacets = (a: MockAtom) =>
    (facets.type.size === 0 || facets.type.has(a.type)) &&
    (facets.tradition.size === 0 || facets.tradition.has(a.tradition)) &&
    (facets.corpus.size === 0 || facets.corpus.has(a.corpus)) &&
    (facets.tag.size === 0 || a.topic_tags.some((t) => facets.tag.has(t)));

  const filtered = useMemo(() => hits.filter(passesFacets), [hits, facets]);

  // Facet counts computed over the text-search result set (before facet filtering).
  const counts = useMemo(() => {
    const c = { type: {} as Record<string, number>, tradition: {} as Record<string, number>, corpus: {} as Record<string, number>, tag: {} as Record<string, number> };
    for (const a of hits) {
      c.type[a.type] = (c.type[a.type] || 0) + 1;
      c.tradition[a.tradition] = (c.tradition[a.tradition] || 0) + 1;
      c.corpus[a.corpus] = (c.corpus[a.corpus] || 0) + 1;
      for (const t of a.topic_tags) c.tag[t] = (c.tag[t] || 0) + 1;
    }
    return c;
  }, [hits]);

  const allTags = useMemo(() => Object.keys(counts.tag).sort((a, b) => counts.tag[b] - counts.tag[a]).slice(0, 12), [counts]);

  const toggle = (group: keyof Facets, val: string) => {
    setFacets((prev) => {
      const next = { ...prev, [group]: new Set(prev[group]) } as Facets;
      next[group].has(val) ? next[group].delete(val) : next[group].add(val);
      return next;
    });
  };
  const clearFacets = () => setFacets(emptyFacets());
  const activeFacetCount = facets.type.size + facets.tradition.size + facets.corpus.size + facets.tag.size;

  const isSelected = (id: string) => selected.some((s) => s.id === id);
  const addAtom = (a: MockAtom) => { if (!isSelected(a.id)) setSelected((s) => [...s, a]); };
  const removeAtom = (id: string) => setSelected((s) => s.filter((x) => x.id !== id));

  return (
    <>
      {/* ============ SEARCH / FILTER EXPLORER ============ */}
      <section className="cm-section">
        <h2><Search size={18} className="cm-h2-ico" /> Search &amp; filter the corpus</h2>
        <p className="sub">
          Full-text query (Orama, with typo tolerance) + faceted filters. Showing {CORPUS_TOTALS.sampleShown} sample atoms —
          production queries the {CORPUS_TOTALS.atoms.toLocaleString()}-atom corpus the same way.
        </p>

        <div className="cm-explorer">
          <aside className="cm-facets">
            <input
              className="cm-search" placeholder="Search verses, teachings, terms…"
              value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Full-text search"
            />
            <div className="cm-facetbar">
              <span className="lbl">
                <Filter size={12} /> Facets {activeFacetCount > 0 && `(${activeFacetCount})`}
              </span>
              {activeFacetCount > 0 && <button className="cm-addbtn" onClick={clearFacets}>clear</button>}
            </div>

            <FacetGroup title="Type" group="type" order={TYPE_ORDER} counts={counts.type} facets={facets} toggle={toggle} swatch />
            <FacetGroup title="Tradition" group="tradition" order={TRAD_ORDER} counts={counts.tradition} facets={facets} toggle={toggle} />
            <FacetGroup title="Corpus" group="corpus" order={CORPUS_ORDER} counts={counts.corpus} facets={facets} toggle={toggle} />
            <FacetGroup title="Topic tag" group="tag" order={allTags} counts={counts.tag} facets={facets} toggle={toggle} />
          </aside>

          <div>
            <p className="cm-resultmeta">{filtered.length} {filtered.length === 1 ? 'atom' : 'atoms'}{query && <> matching “{query}”</>}</p>
            <div className="cm-results">
              {filtered.map((a) => (
                <article key={a.id} className="cm-atom">
                  <div className="top">
                    <span className={`cm-badge type-${a.type}`}>{a.type}</span>
                    <span className="cm-badge trad">{a.tradition}</span>
                    <span className="title">{a.title}</span>
                    <span className="id">{a.id}</span>
                  </div>
                  {a.arabic && a.arabic !== '—' && <div className="ar">{a.arabic}</div>}
                  <div className="en">{a.text_en}</div>
                  <div className="tags">
                    {a.topic_tags.map((t) => <span key={t} className="cm-tag">#{t}</span>)}
                    <button className={`cm-addbtn ${isSelected(a.id) ? 'added' : ''}`} onClick={() => addAtom(a)} disabled={isSelected(a.id)}>
                      {isSelected(a.id) ? <><Check size={11} /> added</> : <><Plus size={11} /> augment</>}
                    </button>
                  </div>
                </article>
              ))}
              {filtered.length === 0 && <p className="cm-empty">No atoms match. Loosen a facet or clear the query.</p>}
            </div>
          </div>
        </div>
      </section>

      {/* ============ AUGMENTATION SELECTION ============ */}
      <section className="cm-section">
        <h2>Select atoms to augment the prose</h2>
        <p className="sub">
          Pick corpus atoms to inject as <code>[PRIOR DOCTRINAL CONTEXT]</code> behind a chapter paragraph. The tradition
          firewall (D5) is enforced: this book is <strong>{BOOK_TRADITION}</strong>, so only <em>universal</em> scripture +
          same-tradition teachings are eligible.
        </p>

        <div className="cm-aug">
          <div className="cm-prose">
            <div className="meta">{SAMPLE_PROSE.book} · {SAMPLE_PROSE.chapter}</div>
            <p className="para" dangerouslySetInnerHTML={{ __html: highlightProse(SAMPLE_PROSE.paragraph, selected) }} />
            <AugPreview selected={selected} />
          </div>

          <div className="cm-tray">
            <h4>Find &amp; add atoms</h4>
            <Command className="cm-cmdk" label="Atom search">
              <Command.Input placeholder="Type a theme — knowledge, soul, tawhid…" />
              <Command.List>
                <Command.Empty>No atoms found.</Command.Empty>
                {SAMPLE_ATOMS.map((a) => (
                  <Command.Item key={a.id} value={`${a.title} ${a.text_en} ${a.topic_tags.join(' ')}`} onSelect={() => addAtom(a)}>
                    <span className={`cm-badge type-${a.type}`}>{a.type}</span>
                    <span className="grow">{a.title}</span>
                    {isSelected(a.id) ? <Check size={13} color="var(--c-green)" /> : <Plus size={13} color="var(--c-ink-muted)" />}
                  </Command.Item>
                ))}
              </Command.List>
            </Command>

            <div className="cm-selected">
              {selected.length === 0 && <p className="cm-empty">No atoms selected yet. Add from search results or the palette above.</p>}
              {selected.map((a) => {
                const eligible = ELIGIBLE.includes(a.tradition);
                return (
                  <div className="cm-selrow" key={a.id}>
                    <span className={`cm-badge type-${a.type}`}>{a.type}</span>
                    <span>{a.title}</span>
                    {!eligible && <span className="cm-badge trad blocked">blocked: {a.tradition}</span>}
                    <button className="x" onClick={() => removeAtom(a.id)} aria-label={`Remove ${a.title}`}>×</button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function FacetGroup(props: {
  title: string; group: keyof Facets; order: string[];
  counts: Record<string, number>; facets: Facets;
  toggle: (g: keyof Facets, v: string) => void; swatch?: boolean;
}) {
  const { title, group, order, counts, facets, toggle, swatch } = props;
  const opts = order.filter((o) => counts[o] !== undefined || facets[group].has(o));
  if (opts.length === 0) return null;
  return (
    <div className="cm-facet">
      <h4>{title}</h4>
      {opts.map((o) => (
        <label className="cm-facetopt" key={o}>
          <input type="checkbox" checked={facets[group].has(o)} onChange={() => toggle(group, o)} />
          {swatch && <span className={`swatch s-${o}`} />}
          <span>{o}</span>
          <span className="cnt">{counts[o] || 0}</span>
        </label>
      ))}
    </div>
  );
}

function AugPreview({ selected }: { selected: MockAtom[] }) {
  const eligible = selected.filter((a) => ELIGIBLE.includes(a.tradition));
  const blocked = selected.filter((a) => !ELIGIBLE.includes(a.tradition));
  if (selected.length === 0) return null;
  return (
    <div className="cm-preview">
      <div className="cm-injected">
        <div className="lbl">[PRIOR DOCTRINAL CONTEXT — corpus] · {eligible.length} atom{eligible.length !== 1 ? 's' : ''}</div>
        <ul>
          {eligible.map((a) => (
            <li key={a.id}><strong>{a.title}</strong> ({a.type}/{a.tradition}) — {truncate(a.text_en, 90)}</li>
          ))}
        </ul>
      </div>
      {blocked.length > 0 && (
        <p className="cm-warn">⚠ {blocked.length} atom{blocked.length !== 1 ? 's' : ''} blocked by the tradition firewall and excluded from injection.</p>
      )}
    </div>
  );
}

function truncate(s: string, n: number) { return s.length > n ? s.slice(0, n).trimEnd() + '…' : s; }

function highlightProse(text: string, selected: MockAtom[]): string {
  // Light-touch: bold any prose token that appears as a selected atom's topic tag.
  const tags = new Set(selected.flatMap((a) => a.topic_tags.map((t) => t.toLowerCase())));
  const keywords = ['knowledge', 'action', 'soul', 'lord', 'himself', 'ascends'];
  let out = escapeHtml(text);
  for (const k of keywords) {
    if (tags.has(k) || selected.some((a) => a.text_en.toLowerCase().includes(k))) {
      out = out.replace(new RegExp(`\\b(${k})\\b`, 'gi'), '<mark>$1</mark>');
    }
  }
  return out;
}

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
