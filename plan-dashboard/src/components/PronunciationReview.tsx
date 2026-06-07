import { useEffect, useMemo, useState } from 'react';

/**
 * PronunciationReview — the per-book probe checklist island.
 *
 * Pinned audio player + one row per term. For each term the reviewer either
 * confirms the pre-filled house-style phonetic ("Correct"), edits it ("Fix"),
 * or marks it unspeakable ("Can't say" → English gloss). One Save POSTs to
 * /api/pronunciation, which runs the Python applier: corrections flow into the
 * cross-book library (every future Arabic book inherits them) + this book's
 * _phonetics.md / glossary / mangle-map.
 *
 * No inline styles — all visual state is class-driven (see pronunciation.css).
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
  libraryStatus: 'confirmed' | 'unfixable' | null;
  libraryPhonetic: string;
  libraryGloss: string;
}

interface RowState {
  decision: Decision;
  phonetic: string;
  gloss: string;
}

interface Props {
  slug: string;
  title: string;
  terms: ProbeTerm[];
  audioUrl: string | null;
}

const SEGMENT_LABEL: Record<string, string> = {
  names: 'Name',
  places: 'Place',
  terms: 'Term',
};

/** Pre-fill the editable phonetic: a valid intended value, else the baseline. */
function prefill(t: ProbeTerm): string {
  if (t.libraryStatus === 'confirmed' && t.libraryPhonetic) return t.libraryPhonetic;
  if (t.house_style_ok && t.phonetic) return t.phonetic;
  return t.suggested_baseline || '';
}

function initialState(terms: ProbeTerm[]): Record<string, RowState> {
  const out: Record<string, RowState> = {};
  for (const t of terms) {
    if (t.libraryStatus === 'confirmed') {
      out[t.term] = { decision: 'ok', phonetic: prefill(t), gloss: '' };
    } else if (t.libraryStatus === 'unfixable') {
      out[t.term] = { decision: 'cantsay', phonetic: '', gloss: t.libraryGloss };
    } else {
      out[t.term] = { decision: 'pending', phonetic: prefill(t), gloss: '' };
    }
  }
  return out;
}

export default function PronunciationReview({ slug, terms, audioUrl }: Props) {
  const storageKey = `pronunciation-review:${slug}`;
  const [rows, setRows] = useState<Record<string, RowState>>(() => initialState(terms));
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Restore in-progress work from a prior session.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) setRows((prev) => ({ ...prev, ...JSON.parse(raw) }));
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(rows));
    } catch {
      /* ignore */
    }
  }, [rows, storageKey]);

  const decidedCount = useMemo(
    () => Object.values(rows).filter((r) => r.decision !== 'pending').length,
    [rows],
  );

  function update(term: string, patch: Partial<RowState>) {
    setRows((prev) => ({ ...prev, [term]: { ...prev[term], ...patch } }));
    setResult(null);
  }

  async function save() {
    setSaving(true);
    setError(null);
    setResult(null);
    const corrections = terms
      .map((t) => {
        const r = rows[t.term];
        if (!r || r.decision === 'pending') return null;
        if (r.decision === 'cantsay') {
          return {
            term: t.term,
            transliteration: t.transliteration,
            status: 'unfixable' as const,
            gloss: r.gloss.trim(),
          };
        }
        const value = r.phonetic.trim();
        const unchanged = t.house_style_ok && value === (t.phonetic || '').trim();
        return {
          term: t.term,
          transliteration: t.transliteration,
          status: (unchanged ? 'ok' : 'respell') as 'ok' | 'respell',
          phonetic: value,
        };
      })
      .filter(Boolean);

    try {
      const res = await fetch('/api/pronunciation', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, corrections }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || 'save failed');
      const c = json.data.counts;
      setResult(
        `Saved — ${c.confirmed} confirmed, ${c.respelled} respelled, ${c.unfixable} unfixable. ` +
          `Library now ${json.data.library_size} entries; _phonetics.md updated ${json.data.phonetics_md_updated}.`,
      );
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
          <span className="pron-count">
            {decidedCount}/{terms.length} reviewed
          </span>
          {audioUrl ? (
            <audio className="pron-audio" controls preload="none" src={audioUrl}>
              Your browser does not support audio playback.
            </audio>
          ) : (
            <span className="pron-noaudio">No probe audio found for this book.</span>
          )}
        </div>
        <button className="pron-save" onClick={save} disabled={saving || decidedCount === 0}>
          {saving ? 'Saving…' : `Save ${decidedCount} correction${decidedCount === 1 ? '' : 's'}`}
        </button>
      </div>

      {result && <p className="pron-msg pron-msg-ok" role="status">{result}</p>}
      {error && <p className="pron-msg pron-msg-err" role="alert">{error}</p>}

      <ol className="pron-list">
        {terms.map((t) => {
          const r = rows[t.term] ?? { decision: 'pending', phonetic: prefill(t), gloss: '' };
          const known = t.libraryStatus !== null;
          return (
            <li
              key={t.term}
              className={`pron-row pron-row-${r.decision}${!t.house_style_ok ? ' pron-row-needsfix' : ''}`}
            >
              <span className="pron-n">{t.n}</span>
              <div className="pron-term">
                <span className="pron-term-name">{t.term}</span>
                <span className="pron-term-translit">{t.transliteration}</span>
                <span className="pron-chips">
                  <span className="pron-chip pron-chip-seg">{SEGMENT_LABEL[t.segment] ?? t.segment}</span>
                  {!t.house_style_ok && <span className="pron-chip pron-chip-warn">needs respelling</span>}
                  {known && <span className="pron-chip pron-chip-known">already in library</span>}
                  {t.signature.map((s) => (
                    <span key={s} className="pron-chip">{s}</span>
                  ))}
                </span>
              </div>

              <div className="pron-controls">
                <div className="pron-seg" role="group" aria-label={`Decision for ${t.term}`}>
                  <button
                    className={`pron-segbtn${r.decision === 'ok' ? ' is-on' : ''}`}
                    onClick={() => update(t.term, { decision: 'ok', phonetic: prefill(t) })}
                  >
                    ✓ Correct
                  </button>
                  <button
                    className={`pron-segbtn${r.decision === 'fix' ? ' is-on' : ''}`}
                    onClick={() => update(t.term, { decision: 'fix' })}
                  >
                    ✎ Fix
                  </button>
                  <button
                    className={`pron-segbtn${r.decision === 'cantsay' ? ' is-on' : ''}`}
                    onClick={() => update(t.term, { decision: 'cantsay' })}
                  >
                    ✗ Can’t say
                  </button>
                </div>

                {r.decision === 'cantsay' ? (
                  <input
                    className="pron-input"
                    type="text"
                    placeholder="English gloss to say instead…"
                    value={r.gloss}
                    onChange={(e) => update(t.term, { gloss: e.target.value })}
                    aria-label={`English gloss for ${t.term}`}
                  />
                ) : (
                  <input
                    className="pron-input"
                    type="text"
                    value={r.phonetic}
                    readOnly={r.decision === 'ok'}
                    placeholder="house-style respelling, e.g. gha-zaa-lee"
                    onChange={(e) => update(t.term, { decision: 'fix', phonetic: e.target.value })}
                    aria-label={`Phonetic respelling for ${t.term}`}
                  />
                )}

                <span className="pron-intended" title="what NotebookLM was told to say">
                  intended: <code>{t.house_style_ok ? t.phonetic : '—'}</code>
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
