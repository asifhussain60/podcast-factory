/**
 * Client island: header toggle for the Arabic-script overlay.
 *
 * When ON, sets <body data-arabic="on">. CSS in global.css reads that
 * attribute and renders the `data-script` value (Arabic) inline next to
 * each `.ar-overlay` span emitted by lib/glossary.ts wrapPhoneticTokens().
 *
 * Persists choice to localStorage so the toggle state survives navigation
 * across chapters within the same session.
 */

import { useEffect, useState } from 'react';

const STORAGE_KEY = 'podcast-reader:arabic-overlay';

export default function ArabicToggle() {
  const [on, setOn] = useState(false);

  // Initialize from localStorage on mount; reflect to <body>.
  useEffect(() => {
    const stored = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null;
    const initial = stored === 'on';
    setOn(initial);
    document.body.dataset.arabic = initial ? 'on' : 'off';
  }, []);

  // Reflect changes to <body> + localStorage.
  useEffect(() => {
    document.body.dataset.arabic = on ? 'on' : 'off';
    try {
      window.localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off');
    } catch {
      /* private-mode: ignore */
    }
  }, [on]);

  return (
    <button
      type="button"
      onClick={() => setOn((v) => !v)}
      className={
        'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-medium transition ' +
        (on
          ? 'border-amber-400 bg-amber-50 text-amber-900 shadow-sm'
          : 'border-stone-300 bg-white text-stone-600 hover:border-stone-400 hover:text-stone-900')
      }
      aria-pressed={on}
      title={on ? 'Hide Arabic script overlay' : 'Show Arabic script next to each phonetic term'}
    >
      <span aria-hidden style={{ fontFamily: 'serif' }}>ع</span>
      <span>{on ? 'Arabic on' : 'Show Arabic'}</span>
    </button>
  );
}
