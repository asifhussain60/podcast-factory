import { useEffect, useMemo, useState } from 'react';

/**
 * PronunciationReview — per-book probe checklist island.
 *
 * Each row: Arabic script input (inline, right of term name) + Correct/Fix
 * toggle + "Use English translation" checkbox (replaces the old Can't say
 * button) + phonetic or gloss text input. Tab-off the Arabic field
 * auto-suggests a house-style phonetic via /api/phonetic-generate.
 *
 * No inline styles — all visual state is class-driven (pronunciation.css).
 */

type Decision = 'pending' | 'ok' | 'fix' | 'cantsay';

interface ProbeTerm {
  n: number;
  term: string;
  transliteration: string;
  phonetic: string;
  house_style_ok: boolean;
  suggested_baseline: string;
  signature: string[];
  segment: string;
  freq: number;
  reasons: string[];
  arabicScript: string;
  meaning: string;
  libraryStatus: 'confirmed' | 'unfixable' | null;
  libraryPhonetic: string;
  libraryGloss: string;
}

interface RowState {
  decision: Decision;
  phonetic: string;
  gloss: string;
  arabic: string;
  phoneSuggested?: boolean;
}

interface Props {
  slug: string;
  title: string;
  terms: ProbeTerm[];
}

const SEGMENT_LABEL: Record<string, string> = {
  names: 'Name',
  places: 'Place',
  terms: 'Term',
};

function prefill(t: ProbeTerm): string {
  if (t.libraryStatus === 'confirmed' && t.libraryPhonetic) return t.libraryPhonetic;
  if (t.house_style_ok && t.phonetic) return t.phonetic;
  return t.suggested_baseline || '';
}

function initialState(terms: ProbeTerm[]): Record<string, RowState> {
  const out: Record<string, RowState> = {};
  for (const t of terms) {
    const base = { arabic: t.arabicScript || '', phoneSuggested: false };
    if (t.libraryStatus === 'confirmed') {
      out[t.term] = { ...base, decision: 'ok', phonetic: prefill(t), gloss: '' };
    } else if (t.libraryStatus === 'unfixable') {
      out[t.term] = { ...base, decision: 'cantsay', phonetic: '', gloss: t.libraryGloss };
    } else {
      out[t.term] = { ...base, decision: 'pending', phonetic: prefill(t), gloss: '' };
    }
  }
  return out;
}

export default function PronunciationReview({ slug, terms }: Props) {
  const storageKey = `pronunciation-review:${slug}`;
  const [rows, setRows] = useState<Record<string, RowState>>(() => initialState(terms));
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const stored = JSON.parse(raw) as Record<string, RowState>;
      const savedKeys = new Set(terms.filter((t) => t.libraryStatus !== null).map((t) => t.term));
      const merged: Record<string, RowState> = {};
      for (const [term, st] of Object.entries(stored)) {
        if (!savedKeys.has(term)) merged[term] = st;
      }
      setRows((prev) => ({ ...prev, ...merged }));
    } catch { /* ignore */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(rows)); } catch { /* ignore */ }
  }, [rows, storageKey]);

  function isDecided(r: RowState): boolean {
    if (r.decision === 'ok' || r.decision === 'fix') return !!r.phonetic.trim();
    if (r.decision === 'cantsay') return !!r.gloss.trim();
    return false;
  }

  const decidedCount = useMemo(() => Object.values(rows).filter(isDecided).length, [rows]);
  const acceptableCount = useMemo(
    () => terms.filter((t) => { const r = rows[t.term]; return r && r.decision === 'pending' && r.phonetic.trim(); }).length,
    [rows, terms],
  );

  function update(term: string, patch: Partial<RowState>) {
    setRows((prev) => ({ ...prev, [term]: { ...prev[term], ...patch } }));
    setResult(null);
  }

  function acceptAllSuggestions() {
    setRows((prev) => {
      const next = { ...prev };
      for (const t of terms) {
        const r = next[t.term];
        if (r && r.decision === 'pending' && r.phonetic.trim()) {
          next[t.term] = { ...r, decision: 'ok', phoneSuggested: false };
        }
      }
      return next;
    });
    setResult(null);
  }

  async function handleArabicBlur(term: string, arabicValue: string) {
    const r = rows[term];
    if (!r || r.decision !== 'pending') return;
    const text = arabicValue.trim();
    if (!text) return;
    try {
      const res = await fetch('/api/phonetic-generate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ word: text }),
      });
      const json = await res.json();
      if (json.ok && json.data?.phonetic) {
        setRows((prev) => ({
          ...prev,
          [term]: { ...prev[term], phonetic: json.data.phonetic, phoneSuggested: true },
        }));
      }
    } catch { /* silent */ }
  }

  async function save() {
    setSaving(true);
    setError(null);
    setResult(null);
    const corrections = terms.map((t) => {
      const r = rows[t.term];
      if (!r || r.decision === 'pending') return null;
      if (r.decision === 'cantsay') {
        if (!r.gloss.trim()) return null;
        return { term: t.term, transliteration: t.transliteration, status: 'unfixable' as const, gloss: r.gloss.trim() };
      }
      const value = r.phonetic.trim();
      const unchanged = t.house_style_ok && value === (t.phonetic || '').trim();
      return { term: t.term, transliteration: t.transliteration, status: (unchanged ? 'ok' : 'respell') as 'ok' | 'respell', phonetic: value };
    }).filter(Boolean);

    try {
      const res = await fetch('/api/pronunciation', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, corrections }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || 'save failed');
      const c = json.data.counts;
      setResult(`Saved — ${c.confirmed} confirmed, ${c.respelled} respelled, ${c.unfixable} unfixable. Library now ${json.data.library_size} entries; _phonetics.md updated ${json.data.phonetics_md_updated}.`);
      try { localStorage.removeItem(storageKey); } catch { /* ignore */ }
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="pron">
      <div className="pron-bar">
        <div className="pron-bar-info">
          <span className="pron-count">{decidedCount}/{terms.length} reviewed</span>
        </div>
        <div className="pron-bar-actions">
          {acceptableCount > 0 && (
            <button className="pron-acceptall" onClick={acceptAllSuggestions} disabled={saving}>
              Accept {acceptableCount} suggestion{acceptableCount === 1 ? '' : 's'}
            </button>
          )}
        </div>
      </div>

      <ol className="pron-list">
        {terms.map((t) => {
          const r = rows[t.term] ?? { decision: 'pending' as Decision, phonetic: prefill(t), gloss: '', arabic: t.arabicScript || '' };
          const known = t.libraryStatus !== null;
          const useGloss = r.decision === 'cantsay';

          return (
            <li
              key={t.term}
              className={`pron-row pron-row-${r.decision}${!t.house_style_ok ? ' pron-row-needsfix' : ''}`}
            >
              <span className="pron-n">{t.n}</span>

              {/* Left: term name + Arabic inline (grid), transliteration, chips */}
              <div className="pron-term">
                <span className="pron-term-name">{t.term}</span>
                <input
                  className="pron-term-arabic"
                  type="text"
                  dir="rtl"
                  value={r.arabic || ''}
                  onChange={(e) => update(t.term, { arabic: e.target.value, phoneSuggested: false })}
                  onBlur={(e) => handleArabicBlur(t.term, e.target.value)}
                  placeholder="Arabic…"
                  aria-label={`Arabic script for ${t.term}`}
                />
                {t.transliteration !== t.term && (
                  <span className="pron-term-translit">{t.transliteration}</span>
                )}
                <span className="pron-chips">
                  <span className="pron-chip pron-chip-seg">{SEGMENT_LABEL[t.segment] ?? t.segment}</span>
                  {t.freq > 0 && <span className="pron-chip pron-chip-count">×{t.freq}</span>}
                  {!t.house_style_ok && <span className="pron-chip pron-chip-warn">needs respelling</span>}
                  {known && <span className="pron-chip pron-chip-known">in library</span>}
                  {t.signature.map((s) => <span key={s} className="pron-chip">{s}</span>)}
                </span>
                {t.meaning && (
                  <span className="pron-term-meaning">{t.meaning}</span>
                )}
              </div>

              {/* Right: decision toggle + English gloss checkbox (same row), then input */}
              <div className="pron-controls">
                <div className="pron-decision-row">
                  {/* Correct / Fix toggle */}
                  <div className="pron-seg" role="group" aria-label={`Decision for ${t.term}`}>
                    <button
                      className={`pron-segbtn${r.decision === 'ok' ? ' is-on' : ''}`}
                      onClick={() => update(t.term, { decision: 'ok', phonetic: prefill(t), phoneSuggested: false })}
                    >✓ Correct</button>
                    <button
                      className={`pron-segbtn${r.decision === 'fix' ? ' is-on' : ''}`}
                      onClick={() => update(t.term, { decision: 'fix', phoneSuggested: false })}
                    >✎ Fix</button>
                  </div>

                  {/* English translation checkbox — inline with buttons */}
                  <label className="pron-gloss-label">
                    <input
                      type="checkbox"
                      className="pron-gloss-check"
                      checked={useGloss}
                      onChange={(e) => {
                        if (e.target.checked) {
                          // Pre-fill gloss with the predetermined meaning if the field is still empty.
                          const currentGloss = rows[t.term]?.gloss ?? '';
                          update(t.term, {
                            decision: 'cantsay',
                            gloss: currentGloss.trim() || t.meaning || '',
                            phoneSuggested: false,
                          });
                        } else {
                          update(t.term, { decision: 'pending', phonetic: prefill(t), gloss: '', phoneSuggested: false });
                        }
                      }}
                      aria-label={`Use English translation for ${t.term}`}
                    />
                    Use English translation instead
                  </label>
                </div>

                {/* Phonetic input OR English gloss input */}
                {useGloss ? (
                  <input
                    className="pron-input"
                    type="text"
                    placeholder="English phrase NotebookLM will say instead…"
                    value={r.gloss}
                    onChange={(e) => update(t.term, { gloss: e.target.value })}
                    aria-label={`English gloss for ${t.term}`}
                  />
                ) : (
                  <>
                    <input
                      className={`pron-input${r.phoneSuggested ? ' pron-input-suggested' : ''}`}
                      type="text"
                      value={r.phonetic}
                      readOnly={r.decision === 'ok'}
                      placeholder="house-style respelling, e.g. gha-zaa-lee"
                      onChange={(e) => update(t.term, { decision: 'fix', phonetic: e.target.value, phoneSuggested: false })}
                      aria-label={`Phonetic respelling for ${t.term}`}
                    />
                    {r.phoneSuggested && (
                      <span className="pron-suggested-note">AI suggestion — confirm or edit</span>
                    )}
                  </>
                )}

                <span className="pron-intended" title="what NotebookLM was told to say">
                  intended: <code>{t.house_style_ok ? t.phonetic : '—'}</code>
                </span>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="pron-footer">
        {result && <p className="pron-msg pron-msg-ok" role="status">{result}</p>}
        {error && <p className="pron-msg pron-msg-err" role="alert">{error}</p>}
        <button className="pron-save" onClick={save} disabled={saving || decidedCount === 0}>
          {saving ? 'Saving…' : `Save ${decidedCount} correction${decidedCount === 1 ? '' : 's'}`}
        </button>
      </div>
    </div>
  );
}
