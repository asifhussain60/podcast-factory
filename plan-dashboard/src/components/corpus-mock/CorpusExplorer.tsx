/**
 * CorpusExplorer.tsx — MOCK "Concept Lens" explorer for the consolidated corpus.
 *
 * Concept-FIRST: you search/select a concept (English label + Arabic + translit +
 * synonyms, e.g. "mercy"); the lens then aggregates ALL evidence across every source
 * — definition + root family, then Quran / Hadith / Doctrine / Poetry as collapsible,
 * counted groups. Atoms read English-meaning-first; the source coordinate (Q 2:255) is
 * a small chip. Free-text (Orama) over atom bodies also surfaces the matching concepts.
 *
 * MOCK ONLY — client-side over ~25 sample atoms / 6 concepts. Production derives concepts
 * from atom_topic_tags + Arabic roots over the 7,036-atom knowledge.db (server-side index).
 */
import { create, insertMultiple, search } from '@orama/orama';
import { Command } from 'cmdk';
import { Plus, Check, Search, ChevronRight, BookOpen, Layers } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  CONCEPTS, SAMPLE_ATOMS, SAMPLE_PROSE, CORPUS_TOTALS, atomsForConcept,
  type MockAtom, type AtomType, type Tradition, type Concept,
} from '../../data/corpus-mock-sample';

const BOOK_TRADITION: Tradition = 'fatimid-ismaili';
const ELIGIBLE: Tradition[] = ['universal', 'fatimid-ismaili', 'ismaili'];

// Source groups, in display order. 'term'+'etymology' define the concept, so they lead.
const GROUPS: { type: AtomType; label: string }[] = [
  { type: 'etymology', label: 'Etymology (root)' },
  { type: 'term', label: 'Definitions & terms' },
  { type: 'quran', label: 'Quran' },
  { type: 'hadith', label: 'Hadith' },
  { type: 'doctrine', label: 'Doctrine (wisdom)' },
  { type: 'poetry', label: 'Poetry' },
];

function conceptAtomCount(c: Concept) { return atomsForConcept(c.id).length; }

export default function CorpusExplorer() {
  const [db, setDb] = useState<any>(null);
  const [query, setQuery] = useState('');
  const [textHits, setTextHits] = useState<Set<string>>(new Set()); // atom ids matching free-text
  const [conceptId, setConceptId] = useState<string>('mercy');
  const [typeFilter, setTypeFilter] = useState<Set<string>>(new Set());
  const [tradFilter, setTradFilter] = useState<Set<string>>(new Set());
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<MockAtom[]>([]);

  // Orama index over atoms — full-text surfaces the concept(s) a phrase belongs to.
  useEffect(() => {
    (async () => {
      const idx = await create({
        schema: { id: 'string', gloss: 'string', text_en: 'string', arabic: 'string', source_ref: 'string' },
      });
      await insertMultiple(idx, SAMPLE_ATOMS as any);
      setDb(idx);
    })();
  }, []);

  useEffect(() => {
    (async () => {
      if (!db || !query.trim()) { setTextHits(new Set()); return; }
      const res = await search(db, { term: query, properties: ['gloss', 'text_en', 'arabic'], tolerance: 1, limit: 200 });
      setTextHits(new Set(res.hits.map((h: any) => h.id)));
    })();
  }, [db, query]);

  // Concepts matching the query: by label/synonym/translit/arabic, OR by a free-text atom hit.
  const matchedConcepts = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return CONCEPTS;
    return CONCEPTS.filter((c) => {
      const direct = [c.label, c.translit, c.arabic, c.root, ...c.synonyms].some((s) => s.toLowerCase().includes(q));
      const viaAtom = atomsForConcept(c.id).some((a) => textHits.has(a.id));
      return direct || viaAtom;
    });
  }, [query, textHits]);

  const concept = useMemo(() => CONCEPTS.find((c) => c.id === conceptId) || CONCEPTS[0], [conceptId]);
  const conceptAtoms = useMemo(() => atomsForConcept(concept.id), [concept]);

  // Reset refine + open the first non-empty group when the concept changes.
  useEffect(() => {
    setTypeFilter(new Set());
    setTradFilter(new Set());
    const firstType = GROUPS.find((g) => conceptAtoms.some((a) => a.type === g.type))?.type;
    setOpenGroups(firstType ? new Set([firstType]) : new Set());
  }, [conceptId]); // eslint-disable-line react-hooks/exhaustive-deps

  const visibleAtoms = conceptAtoms.filter((a) =>
    (typeFilter.size === 0 || typeFilter.has(a.type)) &&
    (tradFilter.size === 0 || tradFilter.has(a.tradition)));

  const presentTypes = useMemo(() => {
    const m: Record<string, number> = {};
    for (const a of conceptAtoms) m[a.type] = (m[a.type] || 0) + 1;
    return m;
  }, [conceptAtoms]);
  const presentTrads = useMemo(() => {
    const m: Record<string, number> = {};
    for (const a of conceptAtoms) m[a.tradition] = (m[a.tradition] || 0) + 1;
    return m;
  }, [conceptAtoms]);

  const toggleSet = (setter: any) => (val: string) =>
    setter((prev: Set<string>) => { const n = new Set(prev); n.has(val) ? n.delete(val) : n.add(val); return n; });
  const toggleType = toggleSet(setTypeFilter);
  const toggleTrad = toggleSet(setTradFilter);
  const toggleGroup = (t: string) => setOpenGroups((prev) => { const n = new Set(prev); n.has(t) ? n.delete(t) : n.add(t); return n; });

  const isSelected = (id: string) => selected.some((s) => s.id === id);
  const addAtom = (a: MockAtom) => { if (!isSelected(a.id)) setSelected((s) => [...s, a]); };
  const removeAtom = (id: string) => setSelected((s) => s.filter((x) => x.id !== id));

  return (
    <>
      {/* ============ CONCEPT LENS ============ */}
      <section className="cm-section">
        <h2><Search size={18} className="cm-h2-ico" /> Explore by concept</h2>
        <p className="sub">
          Search a meaning — <em>mercy, worship, knowledge…</em> — and see every related verse, hadith, term,
          and teaching together, linked by Arabic root. Showing {CORPUS_TOTALS.sampleConcepts} sample concepts over
          {' '}{CORPUS_TOTALS.sampleAtoms} atoms; production derives {CORPUS_TOTALS.conceptsInProduction} concepts over {CORPUS_TOTALS.atoms.toLocaleString()} atoms.
        </p>

        <input
          className="cm-search cm-search-lg" placeholder="Search a concept — mercy · raḥma · worship · ʿilm · soul …"
          value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Concept search"
        />

        {/* concept chips (matched / browse) */}
        <div className="cm-conceptrow" role="listbox" aria-label="Concepts">
          {matchedConcepts.map((c) => (
            <button
              key={c.id} role="option" aria-selected={c.id === concept.id}
              className={`cm-conceptchip ${c.id === concept.id ? 'active' : ''}`}
              onClick={() => setConceptId(c.id)}
            >
              <span className="lbl">{c.label}</span>
              <span className="ar">{c.arabic}</span>
              <span className="cnt">{conceptAtomCount(c)}</span>
            </button>
          ))}
          {matchedConcepts.length === 0 && <p className="cm-empty">No concept matches “{query}”. Try a broader term.</p>}
        </div>

        {/* the lens */}
        <div className="cm-lens">
          <header className="cm-lenshead">
            <div className="title">
              <h3>{concept.label}</h3>
              <span className="ar">{concept.arabic}</span>
              <span className="translit">{concept.translit}</span>
              <span className="root">root {concept.root}</span>
            </div>
            <p className="def">{concept.definition}</p>
            <div className="family">
              <span className="famlbl"><Layers size={12} /> root family</span>
              {concept.family.map((f) => <span key={f} className="cm-tag">{f}</span>)}
            </div>
            <div className="count">{conceptAtoms.length} atoms across {Object.keys(presentTypes).length} sources</div>
          </header>

          {/* refine within the concept */}
          <div className="cm-refine">
            <span className="rlbl">Refine</span>
            {GROUPS.filter((g) => presentTypes[g.type]).map((g) => (
              <button key={g.type} className={`cm-pill type-${g.type} ${typeFilter.has(g.type) ? 'on' : ''}`} onClick={() => toggleType(g.type)}>
                {g.label.split(' ')[0]} <span className="n">{presentTypes[g.type]}</span>
              </button>
            ))}
            <span className="rsep" />
            {(['universal', 'fatimid-ismaili', 'ismaili'] as Tradition[]).filter((t) => presentTrads[t]).map((t) => (
              <button key={t} className={`cm-pill trad ${tradFilter.has(t) ? 'on' : ''}`} onClick={() => toggleTrad(t)}>{t} <span className="n">{presentTrads[t]}</span></button>
            ))}
          </div>

          {/* collapsible source groups */}
          <div className="cm-groups">
            {GROUPS.map((g) => {
              const atoms = visibleAtoms.filter((a) => a.type === g.type);
              if (atoms.length === 0) return null;
              const open = openGroups.has(g.type);
              return (
                <div className={`cm-grp ${open ? 'open' : ''}`} key={g.type}>
                  <button className="cm-grphead" aria-expanded={open} onClick={() => toggleGroup(g.type)}>
                    <ChevronRight size={15} className="chev" />
                    <span className={`cm-badge type-${g.type}`}>{g.type}</span>
                    <span className="gl">{g.label}</span>
                    <span className="gc">{atoms.length}</span>
                  </button>
                  {open && (
                    <div className="cm-grpbody">
                      {atoms.map((a) => (
                        <article key={a.id} className="cm-row">
                          <div className="g">{a.gloss}</div>
                          {a.arabic && a.arabic !== '—' && <div className="ar">{a.arabic}</div>}
                          <div className="m">
                            <span className="cm-chip">{a.source_ref}</span>
                            <span className="cm-badge trad">{a.tradition}</span>
                            <button className={`cm-addbtn ${isSelected(a.id) ? 'added' : ''}`} onClick={() => addAtom(a)} disabled={isSelected(a.id)}>
                              {isSelected(a.id) ? <><Check size={11} /> added</> : <><Plus size={11} /> augment</>}
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            {visibleAtoms.length === 0 && <p className="cm-empty">No atoms match the current refine. Clear a filter.</p>}
          </div>
        </div>
      </section>

      {/* ============ AUGMENTATION SELECTION ============ */}
      <section className="cm-section">
        <h2><BookOpen size={18} className="cm-h2-ico" /> Augment the prose with selected atoms</h2>
        <p className="sub">
          Atoms you add from any concept land here and inject as <code>[PRIOR DOCTRINAL CONTEXT]</code> behind a chapter
          paragraph. The tradition firewall (D5) is enforced — this book is <strong>{BOOK_TRADITION}</strong>.
        </p>

        <div className="cm-aug">
          <div className="cm-prose">
            <div className="meta">{SAMPLE_PROSE.book} · {SAMPLE_PROSE.chapter}</div>
            <p className="para" dangerouslySetInnerHTML={{ __html: highlightProse(SAMPLE_PROSE.paragraph, selected) }} />
            <AugPreview selected={selected} />
          </div>

          <div className="cm-tray">
            <h4>Quick-add by meaning</h4>
            <Command className="cm-cmdk" label="Atom search">
              <Command.Input placeholder="Type a meaning — mercy, worship, soul…" />
              <Command.List>
                <Command.Empty>No atoms found.</Command.Empty>
                {SAMPLE_ATOMS.map((a) => (
                  <Command.Item key={a.id} value={`${a.gloss} ${a.text_en} ${a.concepts.join(' ')}`} onSelect={() => addAtom(a)}>
                    <span className={`cm-badge type-${a.type}`}>{a.type}</span>
                    <span className="grow">{a.gloss}</span>
                    {isSelected(a.id) ? <Check size={13} color="var(--c-green)" /> : <Plus size={13} color="var(--c-ink-muted)" />}
                  </Command.Item>
                ))}
              </Command.List>
            </Command>

            <div className="cm-selected">
              {selected.length === 0 && <p className="cm-empty">No atoms selected. Add from a concept lens or the palette.</p>}
              {selected.map((a) => {
                const eligible = ELIGIBLE.includes(a.tradition);
                return (
                  <div className="cm-selrow" key={a.id}>
                    <span className={`cm-badge type-${a.type}`}>{a.type}</span>
                    <span className="grow">{a.gloss}</span>
                    {!eligible && <span className="cm-badge trad blocked">blocked</span>}
                    <button className="x" onClick={() => removeAtom(a.id)} aria-label={`Remove ${a.gloss}`}>×</button>
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
            <li key={a.id}><strong>{a.gloss}</strong> <span className="src">({a.type} · {a.source_ref})</span></li>
          ))}
        </ul>
      </div>
      {blocked.length > 0 && (
        <p className="cm-warn">⚠ {blocked.length} atom{blocked.length !== 1 ? 's' : ''} blocked by the tradition firewall and excluded.</p>
      )}
    </div>
  );
}

function highlightProse(text: string, selected: MockAtom[]): string {
  const keys = new Set<string>();
  for (const a of selected) for (const c of a.concepts) keys.add(c);
  const map: Record<string, string[]> = {
    knowledge: ['knowledge'], soul: ['soul', 'himself'], mercy: ['mercy'],
    worship: ['worship'], oneness: ['Lord'], love: ['love'],
  };
  let out = escapeHtml(text);
  for (const k of keys) for (const w of map[k] || []) {
    out = out.replace(new RegExp(`\\b(${w})\\b`, 'gi'), '<mark>$1</mark>');
  }
  return out;
}

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
