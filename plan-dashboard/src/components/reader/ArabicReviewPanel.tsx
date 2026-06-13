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
import { useEffect, useMemo, useState } from 'react';

type Decision = 'keep' | 'fix_phonetic' | 'correct_arabic' | 'replace_english';

interface Term {
  phonetic: string;
  transliteration?: string;
  arabic_script?: string;
  decision?: Decision;
  corrected_phonetic?: string;
  corrected_arabic?: string;
  english_override?: string;
}

interface Props { slug: string; }

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'pending', label: 'To review' },
  { id: 'curated', label: 'Curated' },
] as const;
type FilterId = (typeof FILTERS)[number]['id'];

const ACTIONS: { id: Decision; label: string; needs?: keyof Term; rtl?: boolean }[] = [
  { id: 'keep', label: 'Keep' },
  { id: 'fix_phonetic', label: 'Fix phonetic', needs: 'corrected_phonetic' },
  { id: 'correct_arabic', label: 'Correct Arabic', needs: 'corrected_arabic', rtl: true },
  { id: 'replace_english', label: 'Replace · English', needs: 'english_override' },
];

export default function ArabicReviewPanel({ slug }: Props) {
  const [terms, setTerms] = useState<Term[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterId>('all');
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [savingKey, setSavingKey] = useState<string | null>(null);

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
    if (filter === 'pending') return terms.filter((t) => !t.decision);
    if (filter === 'curated') return terms.filter((t) => !!t.decision);
    return terms;
  }, [terms, filter]);

  const pendingCount = terms?.filter((t) => !t.decision).length ?? 0;

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
    setDraft((term[action.needs] as string) || (decision === 'correct_arabic' ? term.arabic_script || '' : ''));
  }

  if (error) return <div className="arv-panel arv-error" role="alert">Could not load terms: {error}</div>;
  if (!terms) return <div className="arv-panel arv-loading">Loading terms…</div>;

  return (
    <aside className="arv-panel" aria-label="Arabic term review">
      <div className="arv-head">
        <h2 className="arv-title">Arabic terms</h2>
        <p className="arv-sub">{pendingCount} to review · {terms.length} total</p>
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
          return (
            <li key={t.phonetic} className={`arv-row${curated ? ' is-curated' : ''}`}>
              <div className="arv-term">
                <span className="arv-phon">{t.transliteration || t.phonetic}</span>
                {t.arabic_script && (
                  <span className="arv-script" lang="ar" dir="rtl">{t.corrected_arabic || t.arabic_script}</span>
                )}
                {curated && <span className="arv-badge" data-decision={t.decision}>{t.decision?.replace('_', ' ')}</span>}
              </div>
              <div className="arv-actions" role="group" aria-label={`Curate ${t.phonetic}`}>
                {ACTIONS.map((a) => (
                  <button
                    key={a.id}
                    className={`arv-act${t.decision === a.id ? ' is-chosen' : ''}`}
                    disabled={savingKey === t.phonetic}
                    onClick={() => onAction(t, a.id)}
                  >{a.label}</button>
                ))}
              </div>
              {openKey?.startsWith(`${t.phonetic}:`) && (() => {
                const decision = openKey.split(':')[1] as Decision;
                const action = ACTIONS.find((a) => a.id === decision)!;
                return (
                  <div className="arv-edit">
                    <input
                      className="arv-input"
                      lang={action.rtl ? 'ar' : undefined}
                      dir={action.rtl ? 'rtl' : undefined}
                      value={draft}
                      placeholder={action.label}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') save(t, decision, draft); }}
                    />
                    <button className="arv-save" onClick={() => save(t, decision, draft)} disabled={savingKey === t.phonetic}>
                      {savingKey === t.phonetic ? 'Saving…' : 'Save'}
                    </button>
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
