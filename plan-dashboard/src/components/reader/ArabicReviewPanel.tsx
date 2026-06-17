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
  decided_by?: string;
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

  const englishCount = terms?.filter((t) => t.decision === 'replace_english').length ?? 0;
  const arabicCount = (terms?.length ?? 0) - englishCount;

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

  // The Arabic|English toggle. "Arabic" = recite (keep, preserving any phonetic
  // fix); "English" = speak plain English (replace_english, using the term's
  // english_override, fetching one if it's somehow missing). Either click is a
  // human decision, so it overrides an auto default.
  async function setLang(term: Term, lang: 'arabic' | 'english') {
    if (savingKey === term.phonetic) return;
    if (lang === 'arabic') {
      const dec: Decision = term.corrected_phonetic ? 'fix_phonetic' : 'keep';
      void save(term, dec, term.corrected_phonetic || '');
      return;
    }
    let eng = term.english_override || '';
    if (!eng) {
      setSavingKey(term.phonetic);
      try {
        const res = await fetch('/api/ai/english-term', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ text: term.transliteration || term.phonetic, arabic: term.arabic_script || '', bookTitle: slug }),
        });
        const d = await res.json();
        if (d?.ok && d.english) eng = d.english as string;
      } catch { /* save with empty english — the term simply stays as-is in the prose */ }
      finally { setSavingKey(null); }
    }
    void save(term, 'replace_english', eng);
  }

  if (error) return <div className="arv-panel arv-error" role="alert">Could not load terms: {error}</div>;
  if (!terms) return <div className="arv-panel arv-loading">Loading terms…</div>;

  return (
    <aside className="arv-panel" aria-label="Arabic term review">
      <div className="arv-head">
        <h2 className="arv-title">Arabic terms</h2>
        <p className="arv-sub">
          <strong>{arabicCount} recited in Arabic</strong> · {englishCount} spoken in English · {terms.length} terms.
          Smart defaults applied — flip any term or fix a spelling.
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
          const isEnglish = t.decision === 'replace_english';
          const isAuto = (t.decided_by || '').toLowerCase() === 'auto';
          const english = t.english_override || '';
          const busy = savingKey === t.phonetic;
          return (
            <li
              key={t.phonetic}
              className={`arv-row${isEnglish ? ' is-english' : ''}`}
            >
              <div className="arv-term">
                <span className="arv-phon">{t.transliteration || t.phonetic}</span>
                {t.arabic_script && (
                  <span className="arv-script" lang="ar" dir="rtl">{t.corrected_arabic || t.arabic_script}</span>
                )}
                {isAuto && <span className="arv-auto" title="Auto-suggested default — change it anytime">auto</span>}
                <span className="arv-toggle" role="group" aria-label={`Recite ${t.phonetic} in Arabic or speak it in English`}>
                  <button type="button" className={`arv-seg${!isEnglish ? ' is-on' : ''}`} disabled={busy}
                    onClick={() => setLang(t, 'arabic')} title="Recite in Arabic">Arabic</button>
                  <button type="button" className={`arv-seg${isEnglish ? ' is-on' : ''}`} disabled={busy}
                    onClick={() => setLang(t, 'english')} title="Speak in plain English">English</button>
                </span>
              </div>
              <div className="arv-meta">
                {!isEnglish ? (
                  <>
                    <button type="button" className="arv-chip arv-chip--say" title="Click to fix the spoken spelling"
                      disabled={busy} onClick={() => onAction(t, 'fix_phonetic')}>
                      say: {currentPhonetic(t)} <i className="fa-solid fa-pen" aria-hidden="true" />
                    </button>
                    {english && (
                      <button type="button" className="arv-chip arv-chip--en" title="Speak this English instead"
                        disabled={busy} onClick={() => setLang(t, 'english')}>
                        <i className="fa-solid fa-language" aria-hidden="true" /> "{english}"
                      </button>
                    )}
                    {t.arabic_script && (
                      <button type="button" className="arv-chip arv-chip--ar" title="Correct the Arabic script"
                        disabled={busy} onClick={() => onAction(t, 'correct_arabic')}>
                        <i className="fa-solid fa-pen" aria-hidden="true" /> Arabic
                      </button>
                    )}
                  </>
                ) : (
                  <button type="button" className="arv-chip arv-chip--en is-active" title="Click to edit the English"
                    disabled={busy} onClick={() => onAction(t, 'replace_english')}>
                    <i className="fa-solid fa-volume-high" aria-hidden="true" /> spoken as "{english || '…'}" <i className="fa-solid fa-pen" aria-hidden="true" />
                  </button>
                )}
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
