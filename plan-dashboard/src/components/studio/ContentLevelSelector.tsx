/**
 * ContentLevelSelector.tsx — Wave L-7
 *
 * Studio intake control for an Islamic scholarly book's spiritual content level.
 * The level gates which wisdom-corpus doctrine atoms may augment the book
 * (cumulative downward: a book draws atoms at or below its own level). Shown only
 * for books that declare a tradition_affinity (Islamic); other content never sees it.
 *
 * Persists via POST /api/studio/book-meta (patches meta.yml content_level).
 * No inline styles — classes live in studio-pipeline.css.
 */
import { useState } from 'react';

interface Props {
  slug: string;
  initial: string; // current content_level or '' (none)
}

const LEVELS: { id: string; label: string; icon: string; blurb: string }[] = [
  { id: 'history', label: 'History', icon: '📜', blurb: 'Biographical & historical accounts' },
  { id: 'shariah', label: 'Shariah', icon: '⚖️', blurb: 'Law, practice, hadith-based rulings' },
  { id: 'esoteric', label: 'Esoterics', icon: '🔮', blurb: "Allegorical interpretation (Taveel)" },
  { id: 'realities', label: 'Realities', icon: '💎', blurb: "Metaphysical truths (Haqaiq, Mabda Ma'ad)" },
  { id: '', label: 'None', icon: '—', blurb: 'General / non-gated' },
];

export default function ContentLevelSelector({ slug, initial }: Props) {
  const [value, setValue] = useState(initial);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  async function choose(level: string) {
    setValue(level);
    setStatus('saving');
    try {
      const res = await fetch('/api/studio/book-meta', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, field: 'content_level', value: level }),
      });
      setStatus(res.ok ? 'saved' : 'error');
    } catch {
      setStatus('error');
    }
  }

  return (
    <div className="cl-selector">
      <div className="cl-options" role="radiogroup" aria-label="Content level">
        {LEVELS.map((lv) => (
          <button
            key={lv.id || 'none'}
            type="button"
            role="radio"
            aria-checked={value === lv.id}
            className={`cl-option${value === lv.id ? ' is-selected' : ''}`}
            onClick={() => choose(lv.id)}
          >
            <span className="cl-option-icon" aria-hidden="true">{lv.icon}</span>
            <span className="cl-option-label">{lv.label}</span>
            <span className="cl-option-blurb">{lv.blurb}</span>
          </button>
        ))}
      </div>
      <p className="cl-status" data-state={status} aria-live="polite">
        {status === 'saving' && 'Saving…'}
        {status === 'saved' && 'Saved — augmentation will respect this level.'}
        {status === 'error' && 'Could not save. Check the server and retry.'}
      </p>
    </div>
  );
}
