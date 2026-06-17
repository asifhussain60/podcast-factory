/**
 * ArabicReviewPanel — right-rail curation table for a book's Arabic terms.
 *
 * Lists every glossary term and lets the reviewer choose, per term:
 *   keep · fix-phonetic · correct-Arabic · replace-with-English
 * Decisions are written to _system/glossary.yml (schema v2) via
 * /api/studio/arabic-review — the SAME source the audio render and the page
 * overlay read, so curation drives both. Stays in sync with the inline
 * TermPopover via the `arabic-curation:saved` window event.
 *
 * Reader component (html-view-lint exempt). No Tailwind; classes live in
 * arabic-review.css. The only inline style is a dynamic CSS variable.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

type Decision = 'keep' | 'fix_phonetic' | 'correct_arabic' | 'replace_english';
type TeachingRelevance = 'teaching' | 'name' | 'incidental' | 'referential';

interface Term {
  phonetic: string;
  transliteration?: string;
  arabic_script?: string;
  audio_phonetic?: string;
  decision?: Decision;
  corrected_phonetic?: string;
  corrected_arabic?: string;
  english_override?: string;
  teaching_relevance?: TeachingRelevance;
}

interface Props { slug: string; }

// NotebookLM's TTS spells out capital letters (VOIP -> "V-O-I-P") and stumbles on
// apostrophes, so the academic caps-for-stress respelling backfires. Coerce any
// phonetic to the speakable form: all lowercase, no apostrophes, single-spaced.
function notebookSafePhonetic(s: string): string {
  return (s || '').toLowerCase().replace(/['’`ʼ]/g, '').replace(/\s+/g, ' ').trim();
}

// The phonetic currently spoken for a term: the human correction wins, else the
// baked audio phonetic, else the plain transliteration — always NotebookLM-safe.
function currentPhonetic(t: Term): string {
  return notebookSafePhonetic(t.corrected_phonetic || t.audio_phonetic || t.transliteration || t.phonetic);
}

// Teaching terms first so the curator's eye lands on what carries the doctrine,
// before the referential/historical noise.
const REL_ORDER: Record<TeachingRelevance, number> = {
  teaching: 0, referential: 1, name: 2, incidental: 3,
};
const REL_LABEL: Record<TeachingRelevance, string> = {
  teaching: 'teaching', referential: 'referential', name: 'name', incidental: 'incidental',
};

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'teaching', label: 'Teaching' },
  { id: 'referential', label: 'Referential' },
  { id: 'pending', label: 'To review' },
  { id: 'curated', label: 'Curated' },
] as const;
type FilterId = (typeof FILTERS)[number]['id'];

// Short labels so all four fit one row; `full` is the tooltip with the real action.
const ACTIONS: { id: Decision; label: string; full?: string; needs?: keyof Term; rtl?: boolean }[] = [
  { id: 'keep', label: 'Keep' },
  { id: 'fix_phonetic', label: 'Phonetic', full: 'Fix phonetic — click to accept, double-click to edit', needs: 'corrected_phonetic' },
  { id: 'correct_arabic', label: 'Arabic', full: 'Correct Arabic', needs: 'corrected_arabic', rtl: true },
  { id: 'replace_english', label: 'English', full: 'Replace with English', needs: 'english_override' },
];

export default function ArabicReviewPanel({ slug }: Props) {
  const [terms, setTerms] = useState<Term[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterId>('all');
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  // Live mirror of openKey so an in-flight English suggestion only fills the box
  // that is still open (the user may have moved to another term meanwhile).
  const openKeyRef = useRef<string | null>(null);
  useEffect(() => { openKeyRef.current = openKey; }, [openKey]);

  // Ask Gemini for a speakable English rendering and drop it into the edit box —
  // only if the box is still empty and still open for this term.
  async function suggestEnglish(term: Term, key: string) {
    setSuggesting(true);
    try {
      const res = await fetch('/api/ai/english-term', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: term.transliteration || term.phonetic, arabic: term.arabic_script || '', bookTitle: slug }),
      });
      const d = await res.json();
      if (res.ok && d?.ok && d.english && openKeyRef.current === key) {
        setDraft((prev) => prev || (d.english as string));
      }
    } catch { /* leave the box empty — the curator can type it */ }
    finally { setSuggesting(false); }
  }

  useEffect(() => {
    let live = true;
    fetch(`/api/studio/arabic-review?slug=${encodeURIComponent(slug)}`)
      .then((r) => r.json())
      .then((d) => { if (live) setTerms((d?.data?.entries ?? d?.entries ?? []) as Term[]); })
      .catch((e) => { if (live) setError(String(e)); });
    return () => { live = false; };
  }, [slug]);

  // Stay in sync when the inline popover saves a decision.
  useEffect(() => {
    const onSaved = (e: Event) => {
      const d = (e as CustomEvent).detail as Term | undefined;
      if (!d?.phonetic) return;
      setTerms((prev) => prev?.map((t) => (t.phonetic === d.phonetic ? { ...t, ...d } : t)) ?? prev);
    };
    window.addEventListener('arabic-curation:saved', onSaved);
    return () => window.removeEventListener('arabic-curation:saved', onSaved);
  }, []);

  const shown = useMemo(() => {
    if (!terms) return [];
    let list = terms;
    if (filter === 'pending') list = terms.filter((t) => !t.decision);
    else if (filter === 'curated') list = terms.filter((t) => !!t.decision);
    else if (filter === 'teaching') list = terms.filter((t) => t.teaching_relevance === 'teaching');
    else if (filter === 'referential')
      list = terms.filter((t) => t.teaching_relevance && t.teaching_relevance !== 'teaching');
    // Stable teaching-first ordering so the doctrine surfaces above the noise.
    return list
      .map((t, i) => ({ t, i }))
      .sort((a, b) =>
        (REL_ORDER[a.t.teaching_relevance ?? 'referential'] -
         REL_ORDER[b.t.teaching_relevance ?? 'referential']) || (a.i - b.i))
      .map(({ t }) => t);
  }, [terms, filter]);

  const pendingCount = terms?.filter((t) => !t.decision).length ?? 0;
  const teachingCount = terms?.filter((t) => t.teaching_relevance === 'teaching').length ?? 0;
  const classified = (terms?.some((t) => t.teaching_relevance)) ?? false;

  async function save(term: Term, decision: Decision, value: string) {
    setSavingKey(term.phonetic);
    const body: Record<string, string> = { slug, phonetic: term.phonetic, decision };
    const action = ACTIONS.find((a) => a.id === decision);
    if (action?.needs) body[action.needs] = value;
    try {
      const res = await fetch('/api/studio/arabic-review', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`save ${res.status}`);
      const d = await res.json();
      const updated = (d?.data ?? d) as Term;
      setTerms((prev) => prev?.map((t) => (t.phonetic === term.phonetic ? { ...t, ...updated } : t)) ?? prev);
      window.dispatchEvent(new CustomEvent('arabic-curation:saved', { detail: { ...term, ...updated } }));
      setOpenKey(null);
      setDraft('');
    } catch (e) {
      setError(String(e));
    } finally {
      setSavingKey(null);
    }
  }

  function onAction(term: Term, decision: Decision) {
    const action = ACTIONS.find((a) => a.id === decision);
    if (!action?.needs) { save(term, decision, ''); return; }
    const key = `${term.phonetic}:${decision}`;
    if (openKey === key) { setOpenKey(null); return; }
    setOpenKey(key);
    // Pre-fill the box so the curator edits a value instead of typing from blank.
    if (decision === 'fix_phonetic') {
      // Current spoken phonetic, NotebookLM-safe (lowercase, no apostrophes).
      setDraft(term.corrected_phonetic ? notebookSafePhonetic(term.corrected_phonetic) : currentPhonetic(term));
    } else if (decision === 'correct_arabic') {
      setDraft(term.corrected_arabic || term.arabic_script || '');
    } else if (decision === 'replace_english') {
      // Saved override wins; otherwise fetch a Gemini suggestion into the box.
      if (term.english_override) { setDraft(term.english_override); }
      else { setDraft(''); void suggestEnglish(term, key); }
    } else {
      setDraft('');
    }
  }

  // "Phonetic" button: single-click accepts the current spoken phonetic as the
  // decision; double-click opens the editor to change it. A short timer tells the
  // two apart (every other action stays a plain single-click).
  const clickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  function handleActionClick(term: Term, decision: Decision) {
    if (decision !== 'fix_phonetic') { onAction(term, decision); return; }
    if (clickTimer.current) {           // 2nd click within the window -> edit
      clearTimeout(clickTimer.current);
      clickTimer.current = null;
      onAction(term, 'fix_phonetic');   // opens the box, pre-filled + selected
      return;
    }
    clickTimer.current = setTimeout(() => {   // single click -> accept current
      clickTimer.current = null;
      void save(term, 'fix_phonetic', currentPhonetic(term));
    }, 220);
  }

  if (error) return <div className="arv-panel arv-error" role="alert">Could not load terms: {error}</div>;
  if (!terms) return <div className="arv-panel arv-loading">Loading terms…</div>;

  return (
    <aside className="arv-panel" aria-label="Arabic term review">
      <div className="arv-head">
        <h2 className="arv-title">Arabic terms</h2>
        <p className="arv-sub">
          {pendingCount} to review · {terms.length} total
          {classified && <> · <strong>{teachingCount} recited in Arabic</strong> (teaching)</>}
        </p>
        <div className="arv-filters" role="tablist" aria-label="Filter terms">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              role="tab"
              aria-selected={filter === f.id}
              className={`arv-filter${filter === f.id ? ' is-active' : ''}`}
              onClick={() => setFilter(f.id)}
            >{f.label}</button>
          ))}
        </div>
      </div>
      <ul className="arv-list">
        {shown.map((t) => {
          const curated = !!t.decision;
          const rel = t.teaching_relevance;
          const muted = !!rel && rel !== 'teaching';
          return (
            <li
              key={t.phonetic}
              className={`arv-row${curated ? ' is-curated' : ''}${muted ? ' is-muted' : ''}`}
            >
              <div className="arv-term">
                <span className="arv-phon">{t.transliteration || t.phonetic}</span>
                {t.arabic_script && (
                  <span className="arv-script" lang="ar" dir="rtl">{t.corrected_arabic || t.arabic_script}</span>
                )}
                <span className="arv-say" title="How NotebookLM will say it">say: {currentPhonetic(t)}</span>
                {rel && (
                  <span className="arv-rel" data-rel={rel} title={
                    rel === 'teaching'
                      ? 'Teaching term — recited in Arabic'
                      : 'Referential — spoken in plain English, not recited'
                  }>{REL_LABEL[rel]}</span>
                )}
                {curated && <span className="arv-badge" data-decision={t.decision}>{t.decision?.replace('_', ' ')}</span>}
              </div>
              <div className="arv-actions" role="group" aria-label={`Curate ${t.phonetic}`}>
                {ACTIONS.map((a) => (
                  <button
                    key={a.id}
                    className={`arv-act${t.decision === a.id ? ' is-chosen' : ''}`}
                    title={a.full || a.label}
                    disabled={savingKey === t.phonetic}
                    onClick={() => handleActionClick(t, a.id)}
                  >{a.label}</button>
                ))}
              </div>
              {openKey?.startsWith(`${t.phonetic}:`) && (() => {
                const decision = openKey.split(':')[1] as Decision;
                const action = ACTIONS.find((a) => a.id === decision)!;
                const isEnglish = decision === 'replace_english';
                const isPhon = decision === 'fix_phonetic';
                return (
                  <div className="arv-edit">
                    <div className="arv-edit-row">
                      <input
                        className="arv-input"
                        lang={action.rtl ? 'ar' : undefined}
                        dir={action.rtl ? 'rtl' : undefined}
                        value={draft}
                        placeholder={isEnglish && suggesting ? 'Suggesting…' : isPhon ? 'lowercase, e.g. kur-aan' : action.label}
                        autoFocus
                        onFocus={(e) => e.target.select()}
                        onChange={(e) => setDraft(isPhon ? notebookSafePhonetic(e.target.value) : e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') save(t, decision, draft); }}
                      />
                      <button className="arv-save" onClick={() => save(t, decision, draft)} disabled={savingKey === t.phonetic}>
                        {savingKey === t.phonetic ? 'Saving…' : 'Save'}
                      </button>
                    </div>
                    {isPhon && <p className="arv-edit-hint">Lowercase, hyphenate syllables, no capitals or apostrophes — that's what the voice pronounces cleanly.</p>}
                    {isEnglish && suggesting && <p className="arv-edit-hint">Asking Gemini for a suggestion…</p>}
                  </div>
                );
              })()}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
