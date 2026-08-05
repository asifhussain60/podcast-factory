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
import { create, insertMultiple, search } from "@orama/orama";
import { Command } from "cmdk";
import {
  Plus,
  Check,
  Search,
  ChevronRight,
  BookOpen,
  Layers,
} from "lucide-react";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  CONCEPTS,
  SAMPLE_ATOMS,
  SAMPLE_PROSE,
  CORPUS_TOTALS,
} from "../../data/corpus-fallback";
import { apiFetch, ApiFetchError } from "../../lib/api-fetch";
import type {
  MockAtom,
  AtomType,
  Tradition,
  Concept,
} from "../../lib/db/knowledge";

interface ProseContext {
  book: string;
  chapter: string;
  paragraph: string;
}

interface Props {
  selectedAtoms?: MockAtom[];
  onSelectedAtomsChange?: (atoms: MockAtom[]) => void;
  prose?: ProseContext;
  bookTradition?: Tradition;
  /** Real corpus data (from content/knowledge-base/_index/concepts.json). Falls back to the hardcoded sample. */
  concepts?: Concept[];
  atoms?: MockAtom[];
}

// Source groups, in display order. 'term'+'etymology' define the concept, so they lead.
const GROUPS: { type: AtomType; label: string }[] = [
  { type: "etymology", label: "Etymology (root)" },
  { type: "term", label: "Definitions & terms" },
  { type: "quran", label: "Quran" },
  { type: "hadith", label: "Hadith" },
  { type: "doctrine", label: "Doctrine (wisdom)" },
  { type: "poetry", label: "Poetry" },
];

const CHIP_LIMIT = 40; // max concept chips shown at once (783 real concepts → search to narrow)
const ROW_LIMIT = 25; // max atom rows per source group (large concepts stay calm; "+N more")

export default function CorpusExplorer({
  selectedAtoms,
  onSelectedAtomsChange,
  prose,
  bookTradition = "fatimid-ismaili",
  concepts,
  atoms,
}: Props) {
  // M-3 — inline edit state (must be first — localAtoms is used by activeAtoms below).
  const [localAtoms, setLocalAtoms] = useState<MockAtom[]>(
    () => atoms ?? SAMPLE_ATOMS,
  );
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [editLevel, setEditLevel] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [showNewForm, setShowNewForm] = useState(false);

  // Real corpus data when supplied (783 concepts / 758 atoms), else the hardcoded sample.
  const activeConcepts = concepts ?? CONCEPTS;
  const activeAtoms = localAtoms;
  const atomsFor = (id: string) =>
    activeAtoms.filter((a) => a.concepts.includes(id));
  const countFor = (c: Concept) =>
    (c as any).atom_count ?? atomsFor(c.id).length;
  const [newText, setNewText] = useState("");
  const [newType, setNewType] = useState<AtomType>("doctrine");
  const [newTradition, setNewTradition] =
    useState<Tradition>("fatimid-ismaili");
  const [newLevel, setNewLevel] = useState("");
  const [newSaving, setNewSaving] = useState(false);
  const [newError, setNewError] = useState("");

  // Sync localAtoms when the atoms prop changes (SSR re-render).
  useEffect(() => {
    if (atoms) setLocalAtoms(atoms);
  }, [atoms]);

  const [db, setDb] = useState<any>(null);
  const [query, setQuery] = useState("");
  const [textHits, setTextHits] = useState<Set<string>>(new Set()); // atom ids matching free-text
  const [conceptId, setConceptId] = useState<string>(
    () => activeConcepts[0]?.id ?? "mercy",
  );
  const [typeFilter, setTypeFilter] = useState<Set<string>>(new Set());
  const [tradFilter, setTradFilter] = useState<Set<string>>(new Set());
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());
  const [internalSelected, setInternalSelected] = useState<MockAtom[]>([]);
  const deferredQuery = useDeferredValue(query);
  const selected = selectedAtoms ?? internalSelected;
  const proseContext = prose ?? SAMPLE_PROSE;
  const eligibleTraditions = useMemo(
    () => eligibleForBook(bookTradition),
    [bookTradition],
  );

  function updateSelected(updater: (current: MockAtom[]) => MockAtom[]) {
    const next = updater(selected);
    if (onSelectedAtomsChange) {
      onSelectedAtomsChange(next);
      return;
    }
    setInternalSelected(next);
  }

  // Orama index over atoms — full-text surfaces the concept(s) a phrase belongs to.
  useEffect(() => {
    (async () => {
      const idx = create({
        schema: {
          id: "string",
          gloss: "string",
          text_en: "string",
          arabic: "string",
          source_ref: "string",
        },
      });
      await insertMultiple(idx, activeAtoms as any);
      setDb(idx);
    })();
  }, [activeAtoms]);

  useEffect(() => {
    (async () => {
      if (!db || !deferredQuery.trim()) {
        setTextHits(new Set());
        return;
      }
      const res = await search(db, {
        term: deferredQuery,
        properties: ["gloss", "text_en", "arabic"],
        tolerance: 1,
        limit: 200,
      });
      setTextHits(new Set(res.hits.map((h: any) => h.id)));
    })();
  }, [db, deferredQuery]);

  // Concepts matching the query: by label/synonym/translit/arabic, OR by a free-text atom hit.
  const matchedConcepts = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    if (!q) return activeConcepts;
    return activeConcepts.filter((c) => {
      const direct = [
        c.label,
        c.translit,
        c.arabic,
        c.root,
        ...(c.synonyms ?? []),
      ].some((s) => (s ?? "").toLowerCase().includes(q));
      const viaAtom = atomsFor(c.id).some((a) => textHits.has(a.id));
      return direct || viaAtom;
    });
  }, [deferredQuery, textHits, activeConcepts]);

  const concept = useMemo(
    () => activeConcepts.find((c) => c.id === conceptId) || activeConcepts[0],
    [conceptId, activeConcepts],
  );
  const conceptAtoms = useMemo(
    () => atomsFor(concept?.id ?? ""),
    [concept, activeAtoms],
  );

  // Reset refine + open the first non-empty group when the concept changes.
  useEffect(() => {
    setTypeFilter(new Set());
    setTradFilter(new Set());
    const firstType = GROUPS.find((g) =>
      conceptAtoms.some((a) => a.type === g.type),
    )?.type;
    setOpenGroups(firstType ? new Set([firstType]) : new Set());
  }, [conceptId]); // eslint-disable-line react-hooks/exhaustive-deps

  const visibleAtoms = conceptAtoms.filter(
    (a) =>
      (typeFilter.size === 0 || typeFilter.has(a.type)) &&
      (tradFilter.size === 0 || tradFilter.has(a.tradition)),
  );

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
    setter((prev: Set<string>) => {
      const n = new Set(prev);
      n.has(val) ? n.delete(val) : n.add(val);
      return n;
    });
  const toggleType = toggleSet(setTypeFilter);
  const toggleTrad = toggleSet(setTradFilter);
  const toggleGroup = (t: string) =>
    setOpenGroups((prev) => {
      const n = new Set(prev);
      n.has(t) ? n.delete(t) : n.add(t);
      return n;
    });

  const isSelected = (id: string) => selected.some((s) => s.id === id);
  const addAtom = (a: MockAtom) => {
    if (!isSelected(a.id)) updateSelected((current) => [...current, a]);
  };
  const removeAtom = (id: string) =>
    updateSelected((current) => current.filter((atom) => atom.id !== id));

  // M-3: start editing an atom — seed form from current atom text.
  const startEdit = (a: MockAtom) => {
    setEditingId(a.id);
    setEditText(a.text_en);
    setEditLevel((a as any).content_level ?? "");
    setEditError("");
  };
  const cancelEdit = () => {
    setEditingId(null);
    setEditError("");
  };

  const saveEdit = async (id: string) => {
    setEditSaving(true);
    setEditError("");
    try {
      await apiFetch<{ ok: boolean; atom: MockAtom }>("/api/corpus/atom", {
        method: "PATCH",
        body: {
          id,
          text_en: editText,
          content_level: editLevel || null,
        },
      });
      // Update local atom list with the saved version.
      setLocalAtoms((prev) =>
        prev.map((a) =>
          a.id === id
            ? ({
                ...a,
                text_en: editText,
                content_level: editLevel || undefined,
              } as MockAtom)
            : a,
        ),
      );
      setEditingId(null);
    } catch (e) {
      // Pre-migration display text: the route's error string for HTTP failures.
      setEditError(
        e instanceof ApiFetchError && e.status > 0 ? e.message : String(e),
      );
    } finally {
      setEditSaving(false);
    }
  };

  const saveNew = async () => {
    if (!newText.trim()) {
      setNewError("Text is required");
      return;
    }
    setNewSaving(true);
    setNewError("");
    try {
      const json = await apiFetch<{ ok: boolean; atom: MockAtom }>(
        "/api/corpus/atom",
        {
          method: "POST",
          body: {
            type: newType,
            text_en: newText,
            tradition: newTradition,
            content_level: newLevel || undefined,
          },
        },
      );
      setLocalAtoms((prev) => [json.atom, ...prev]);
      setShowNewForm(false);
      setNewText("");
      setNewLevel("");
    } catch (e) {
      // Pre-migration display text: the route's error string for HTTP failures.
      setNewError(
        e instanceof ApiFetchError && e.status > 0 ? e.message : String(e),
      );
    } finally {
      setNewSaving(false);
    }
  };

  return (
    <>
      {/* ============ CONCEPT LENS ============ */}
      <section className="cm-section">
        <h2>
          <Search size={18} className="cm-h2-ico" /> Explore by concept
        </h2>
        <p className="sub">
          Search a meaning — <em>mercy, worship, knowledge…</em> — and see every
          related verse, hadith, term, and teaching together, linked by Arabic
          root. {activeConcepts.length.toLocaleString()} concepts over{" "}
          {activeAtoms.length.toLocaleString()} concept-mapped atoms (of{" "}
          {CORPUS_TOTALS.atoms.toLocaleString()} total in knowledge.db; Quran is
          the remaining unmapped block).
        </p>

        <input
          className="cm-search cm-search-lg"
          placeholder="Search a concept — mercy · raḥma · worship · ʿilm · soul …"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Concept search"
        />

        {/* concept chips (matched / browse) — capped so 783 concepts don't overwhelm */}
        <div className="cm-conceptrow" role="listbox" aria-label="Concepts">
          {matchedConcepts.slice(0, CHIP_LIMIT).map((c) => (
            <button
              key={c.id}
              role="option"
              aria-selected={c.id === concept.id}
              className={`cm-conceptchip ${c.id === concept.id ? "active" : ""}`}
              onClick={() => startTransition(() => setConceptId(c.id))}
            >
              <span className="lbl">{c.label}</span>
              <span className="ar">{c.arabic}</span>
              <span className="cnt">{countFor(c)}</span>
            </button>
          ))}
          {matchedConcepts.length > CHIP_LIMIT && (
            <span className="cm-morechips">
              +{matchedConcepts.length - CHIP_LIMIT} more — type to narrow
            </span>
          )}
          {matchedConcepts.length === 0 && (
            <p className="cm-empty">
              No concept matches “{query}”. Try a broader term.
            </p>
          )}
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
              <span className="famlbl">
                <Layers size={12} /> root family
              </span>
              {(concept.family ?? concept.synonyms ?? [])
                .slice(0, 8)
                .map((f) => (
                  <span key={f} className="cm-tag">
                    {f}
                  </span>
                ))}
            </div>
            <div className="count">
              {conceptAtoms.length} atoms across{" "}
              {Object.keys(presentTypes).length} sources
            </div>
          </header>

          {/* refine within the concept */}
          <div className="cm-refine">
            <span className="rlbl">Refine</span>
            {GROUPS.filter((g) => presentTypes[g.type]).map((g) => (
              <button
                key={g.type}
                className={`cm-pill type-${g.type} ${typeFilter.has(g.type) ? "on" : ""}`}
                onClick={() => toggleType(g.type)}
              >
                {g.label.split(" ")[0]}{" "}
                <span className="n">{presentTypes[g.type]}</span>
              </button>
            ))}
            <span className="rsep" />
            {(["universal", "fatimid-ismaili", "ismaili"] as Tradition[])
              .filter((t) => presentTrads[t])
              .map((t) => (
                <button
                  key={t}
                  className={`cm-pill trad ${tradFilter.has(t) ? "on" : ""}`}
                  onClick={() => toggleTrad(t)}
                >
                  {t} <span className="n">{presentTrads[t]}</span>
                </button>
              ))}
          </div>

          {/* M-3: New atom form + button */}
          <div className="cm-newatom-bar">
            <button
              className="cm-newatom-btn"
              onClick={() => setShowNewForm((v) => !v)}
            >
              <Plus size={13} /> {showNewForm ? "Cancel" : "New atom"}
            </button>
          </div>
          {showNewForm && (
            <div className="cm-editform">
              <div className="cm-editrow">
                <select
                  className="cm-editsel"
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as AtomType)}
                >
                  {["doctrine", "term", "hadith", "etymology", "poetry"].map(
                    (t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ),
                  )}
                </select>
                <select
                  className="cm-editsel"
                  value={newTradition}
                  onChange={(e) => setNewTradition(e.target.value as Tradition)}
                >
                  {["universal", "fatimid-ismaili", "ismaili"].map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <select
                  className="cm-editsel"
                  value={newLevel}
                  onChange={(e) => setNewLevel(e.target.value)}
                >
                  <option value="">— level —</option>
                  {[
                    "general",
                    "advanced",
                    "taveel",
                    "mamsool",
                    "mabda_maad",
                    "haqaiq",
                  ].map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>
              <textarea
                className="cm-edittxt"
                rows={4}
                placeholder="Atom text (English)…"
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
              />
              <div className="cm-editactions">
                <button
                  className="cm-editbtn cm-editbtn--save"
                  onClick={saveNew}
                  disabled={newSaving}
                >
                  {newSaving ? "Creating…" : "Create atom"}
                </button>
                {newError && <span className="cm-editerr">{newError}</span>}
              </div>
            </div>
          )}

          {/* collapsible source groups */}
          <div className="cm-groups">
            {GROUPS.map((g) => {
              const atoms = visibleAtoms.filter((a) => a.type === g.type);
              if (atoms.length === 0) return null;
              const open = openGroups.has(g.type);
              return (
                <div className={`cm-grp ${open ? "open" : ""}`} key={g.type}>
                  <button
                    className="cm-grphead"
                    aria-expanded={open}
                    onClick={() => toggleGroup(g.type)}
                  >
                    <ChevronRight size={15} className="chev" />
                    <span className={`cm-badge type-${g.type}`}>{g.type}</span>
                    <span className="gl">{g.label}</span>
                    <span className="gc">{atoms.length}</span>
                  </button>
                  {open && (
                    <div className="cm-grpbody">
                      {atoms.slice(0, ROW_LIMIT).map((a) => (
                        <article
                          key={a.id}
                          className={`cm-row${editingId === a.id ? " cm-row--editing" : ""}`}
                        >
                          {editingId === a.id ? (
                            <div className="cm-editform">
                              <textarea
                                className="cm-edittxt"
                                rows={4}
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                              />
                              <div className="cm-editrow">
                                <select
                                  className="cm-editsel"
                                  value={editLevel}
                                  onChange={(e) => setEditLevel(e.target.value)}
                                >
                                  <option value="">— level —</option>
                                  {[
                                    "general",
                                    "advanced",
                                    "taveel",
                                    "mamsool",
                                    "mabda_maad",
                                    "haqaiq",
                                  ].map((l) => (
                                    <option key={l} value={l}>
                                      {l}
                                    </option>
                                  ))}
                                </select>
                                <button
                                  className="cm-editbtn cm-editbtn--save"
                                  onClick={() => saveEdit(a.id)}
                                  disabled={editSaving}
                                >
                                  {editSaving ? "Saving…" : "Save"}
                                </button>
                                <button
                                  className="cm-editbtn"
                                  onClick={cancelEdit}
                                >
                                  Cancel
                                </button>
                              </div>
                              {editError && (
                                <span className="cm-editerr">{editError}</span>
                              )}
                            </div>
                          ) : (
                            <>
                              <div className="g">{a.gloss}</div>
                              {a.arabic && a.arabic !== "—" && (
                                <div className="ar">{a.arabic}</div>
                              )}
                              <div className="m">
                                <span className="cm-chip">{a.source_ref}</span>
                                <span className="cm-badge trad">
                                  {a.tradition}
                                </span>
                                {(a as any).content_level && (
                                  <span className="cm-badge lvl">
                                    {(a as any).content_level}
                                  </span>
                                )}
                                <button
                                  className="cm-editbtn cm-editbtn--pencil"
                                  onClick={() => startEdit(a)}
                                  title="Edit atom"
                                  aria-label={`Edit ${a.gloss}`}
                                >
                                  ✎
                                </button>
                                <button
                                  className={`cm-addbtn ${isSelected(a.id) ? "added" : ""}`}
                                  onClick={() => addAtom(a)}
                                  disabled={isSelected(a.id)}
                                >
                                  {isSelected(a.id) ? (
                                    <>
                                      <Check size={11} /> added
                                    </>
                                  ) : (
                                    <>
                                      <Plus size={11} /> augment
                                    </>
                                  )}
                                </button>
                              </div>
                            </>
                          )}
                        </article>
                      ))}
                      {atoms.length > ROW_LIMIT && (
                        <p className="cm-empty">
                          +{atoms.length - ROW_LIMIT} more in this group —
                          refine by tradition/type to narrow.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            {visibleAtoms.length === 0 && (
              <p className="cm-empty">
                No atoms match the current refine. Clear a filter.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ============ AUGMENTATION SELECTION ============ */}
      <section className="cm-section">
        <h2>
          <BookOpen size={18} className="cm-h2-ico" /> Augment the prose with
          selected atoms
        </h2>
        <p className="sub">
          Atoms you add from any concept land here and inject as{" "}
          <code>[PRIOR DOCTRINAL CONTEXT]</code> behind a chapter paragraph. The
          tradition firewall (D5) is enforced — this book is{" "}
          <strong>{bookTradition}</strong>.
        </p>

        <div className="cm-aug">
          <div className="cm-prose">
            <div className="meta">
              {proseContext.book} · {proseContext.chapter}
            </div>
            <p
              className="para"
              dangerouslySetInnerHTML={{
                __html: highlightProse(proseContext.paragraph, selected),
              }}
            />
            <AugPreview
              selected={selected}
              eligibleTraditions={eligibleTraditions}
            />
          </div>

          <div className="cm-tray">
            <h4>Quick-add by meaning</h4>
            <Command className="cm-cmdk" label="Atom search">
              <Command.Input placeholder="Type a meaning — mercy, worship, soul…" />
              <Command.List>
                <Command.Empty>No atoms found.</Command.Empty>
                {activeAtoms.slice(0, 400).map((a) => (
                  <Command.Item
                    key={a.id}
                    value={`${a.gloss} ${a.text_en} ${a.concepts.join(" ")}`}
                    onSelect={() => addAtom(a)}
                  >
                    <span className={`cm-badge type-${a.type}`}>{a.type}</span>
                    <span className="grow">{a.gloss}</span>
                    {isSelected(a.id) ? (
                      <Check size={13} color="var(--c-green)" />
                    ) : (
                      <Plus size={13} color="var(--c-ink-muted)" />
                    )}
                  </Command.Item>
                ))}
              </Command.List>
            </Command>

            <div className="cm-selected">
              {selected.length === 0 && (
                <p className="cm-empty">
                  No atoms selected. Add from a concept lens or the palette.
                </p>
              )}
              {selected.map((a) => {
                const eligible = eligibleTraditions.includes(a.tradition);
                return (
                  <div className="cm-selrow" key={a.id}>
                    <span className={`cm-badge type-${a.type}`}>{a.type}</span>
                    <span className="grow">{a.gloss}</span>
                    {!eligible && (
                      <span className="cm-badge trad blocked">blocked</span>
                    )}
                    <button
                      className="x"
                      onClick={() => removeAtom(a.id)}
                      aria-label={`Remove ${a.gloss}`}
                    >
                      ×
                    </button>
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

function AugPreview({
  selected,
  eligibleTraditions,
}: {
  selected: MockAtom[];
  eligibleTraditions: Tradition[];
}) {
  const eligible = selected.filter((a) =>
    eligibleTraditions.includes(a.tradition),
  );
  const blocked = selected.filter(
    (a) => !eligibleTraditions.includes(a.tradition),
  );
  if (selected.length === 0) return null;
  return (
    <div className="cm-preview">
      <div className="cm-injected">
        <div className="lbl">
          [PRIOR DOCTRINAL CONTEXT — corpus] · {eligible.length} atom
          {eligible.length !== 1 ? "s" : ""}
        </div>
        <ul>
          {eligible.map((a) => (
            <li key={a.id}>
              <strong>{a.gloss}</strong>{" "}
              <span className="src">
                ({a.type} · {a.source_ref})
              </span>
            </li>
          ))}
        </ul>
      </div>
      {blocked.length > 0 && (
        <p className="cm-warn">
          ⚠ {blocked.length} atom{blocked.length !== 1 ? "s" : ""} blocked by
          the tradition firewall and excluded.
        </p>
      )}
    </div>
  );
}

function highlightProse(text: string, selected: MockAtom[]): string {
  const keys = new Set<string>();
  for (const a of selected) for (const c of a.concepts) keys.add(c);
  const map: Record<string, string[]> = {
    knowledge: ["knowledge"],
    soul: ["soul", "himself"],
    mercy: ["mercy"],
    worship: ["worship"],
    oneness: ["Lord"],
    love: ["love"],
  };
  let out = escapeHtml(text);
  for (const k of keys)
    for (const w of map[k] || []) {
      out = out.replace(new RegExp(`\\b(${w})\\b`, "gi"), "<mark>$1</mark>");
    }
  return out;
}

function escapeHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function eligibleForBook(bookTradition: Tradition): Tradition[] {
  if (bookTradition === "fatimid-ismaili")
    return ["universal", "fatimid-ismaili", "ismaili"];
  if (bookTradition === "ismaili") return ["universal", "ismaili"];
  return ["universal"];
}
