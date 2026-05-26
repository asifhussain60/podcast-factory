/**
 * QuranPopover — hover/click any `.ref-quran` span (which already
 * carries `data-surah` and `data-verse` attrs from the highlight
 * renderer) to surface a gold-themed verse panel.
 *
 * The panel renders the Uthmani Arabic in Amiri Quran (the official
 * sacred-text Naskh), the surah's Arabic + English name in Cairo,
 * and the translation in EB Garamond (matching the chapter's body
 * voice). Fetched from quran.com via our /api/quran/verse server
 * proxy. Cached forever in localStorage — verses don't drift.
 *
 * Also falls back to regex-detecting bare "2:43"-style refs in case
 * a chapter doesn't have the .ref-quran wrapping yet.
 */

import { useEffect, useRef, useState } from 'react';

interface VerseData {
  surah_number: number;
  surah_name_en: string;
  surah_name_ar: string;
  surah_name_meaning: string;
  verse_number: number;
  verse_key: string;
  verse_range: string;
  arabic: string;
  translation: string;
  translation_source: string;
  audio_url?: string | null;
}

interface State {
  anchorRect: DOMRect;
  key: string;
  data: VerseData | null;
  loading: boolean;
  error?: string;
}

const CACHE_KEY = (k: string) => `podcast-reader:quran:${k}`;

function readCache(k: string): VerseData | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY(k));
    return raw ? JSON.parse(raw) as VerseData : null;
  } catch { return null; }
}
function writeCache(k: string, v: VerseData): void {
  try { localStorage.setItem(CACHE_KEY(k), JSON.stringify(v)); } catch { /* quota */ }
}

export default function QuranPopover() {
  const [state, setState] = useState<State | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const hoverTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const article = document.querySelector('.prose-body');
    if (!article) return;

    const open = async (anchor: HTMLElement, key: string) => {
      const rect = anchor.getBoundingClientRect();
      const cached = readCache(key);
      setState({ anchorRect: rect, key, data: cached, loading: !cached });
      if (cached) return;
      try {
        const res = await fetch(`/api/quran/verse?key=${encodeURIComponent(key)}`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json() as VerseData;
        writeCache(key, data);
        setState((s) => (s && s.key === key ? { ...s, data, loading: false } : s));
      } catch (e) {
        setState((s) => (s && s.key === key ? { ...s, loading: false, error: (e as Error).message } : s));
      }
    };

    const keyFromSpan = (el: HTMLElement): string | null => {
      const s = el.dataset.surah || el.getAttribute('data-surah');
      const v = el.dataset.verse || el.getAttribute('data-verse');
      if (s && v) return `${s}:${v}`;
      // Fallback: parse the visible text "Quran 2:43" or "Q 5:93".
      const txt = (el.textContent || '').trim();
      const m = txt.match(/(\d+):(\d+(?:-\d+)?)/);
      return m ? `${m[1]}:${m[2]}` : null;
    };

    const onOver = (e: Event) => {
      const target = (e.target as HTMLElement).closest('.ref-quran') as HTMLElement | null;
      if (!target) return;
      const key = keyFromSpan(target);
      if (!key) return;
      if (hoverTimerRef.current) window.clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = window.setTimeout(() => open(target, key), 280);
    };
    const onOut = () => {
      if (hoverTimerRef.current) { window.clearTimeout(hoverTimerRef.current); hoverTimerRef.current = null; }
    };
    const onClick = (e: Event) => {
      const target = (e.target as HTMLElement).closest('.ref-quran') as HTMLElement | null;
      if (!target) return;
      const key = keyFromSpan(target);
      if (!key) return;
      e.preventDefault();
      e.stopPropagation();
      if (hoverTimerRef.current) window.clearTimeout(hoverTimerRef.current);
      open(target, key);
    };
    const onDocClick = (e: MouseEvent) => {
      if (!state) return;
      const t = e.target as HTMLElement;
      if (t.closest('.ref-quran') || t.closest('[data-quran-popover]')) return;
      setState(null);
    };
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') setState(null); };

    article.addEventListener('mouseover', onOver);
    article.addEventListener('mouseout', onOut);
    article.addEventListener('click', onClick, true);  // capture so it beats ambient-edit click
    document.addEventListener('click', onDocClick);
    document.addEventListener('keydown', onEsc);
    return () => {
      article.removeEventListener('mouseover', onOver);
      article.removeEventListener('mouseout', onOut);
      article.removeEventListener('click', onClick, true);
      document.removeEventListener('click', onDocClick);
      document.removeEventListener('keydown', onEsc);
    };
  }, [state]);

  if (!state) return null;

  // Position: prefer below the ref, but flip above if there's not enough room.
  const POPOVER_W = 420;
  const ESTIMATED_H = 280;
  const spaceBelow = window.innerHeight - state.anchorRect.bottom;
  const above = spaceBelow < ESTIMATED_H + 24 && state.anchorRect.top > ESTIMATED_H + 24;
  const top = above
    ? state.anchorRect.top + window.scrollY - ESTIMATED_H - 12
    : state.anchorRect.bottom + window.scrollY + 10;
  const left = Math.max(
    window.scrollX + 12,
    Math.min(
      state.anchorRect.left + window.scrollX - POPOVER_W / 2 + state.anchorRect.width / 2,
      window.scrollX + window.innerWidth - POPOVER_W - 12,
    ),
  );

  const verseRange = state.data?.verse_range ?? state.key;
  const surahNum = state.data?.surah_number ?? Number(state.key.split(':')[0]);

  return (
    <div
      ref={popoverRef}
      data-quran-popover
      className="quran-popover absolute z-50"
      style={{ top, left, width: POPOVER_W }}
      role="dialog"
      aria-label={`Quran ${state.key}`}
    >
      <div className="quran-popover-header">
        <div className="flex flex-col gap-0.5">
          <span className="quran-popover-surah-en">
            Surah {String(surahNum).padStart(3, '0')} · {state.data?.surah_name_en ?? '…'}
            {state.data?.surah_name_meaning && (
              <span className="ml-2 normal-case tracking-wide text-stone-500" style={{ fontWeight: 500, letterSpacing: '0.04em' }}>
                — {state.data.surah_name_meaning}
              </span>
            )}
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="quran-popover-surah-ar" lang="ar" dir="rtl">{state.data?.surah_name_ar || ' '}</span>
          <span className="quran-popover-verse-badge">{verseRange.split(':')[1] ?? '?'}</span>
        </div>
      </div>

      <div className="quran-popover-body">
        {state.loading && !state.data && (
          <div className="py-6 text-center font-ui text-[12px] text-stone-500">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full" style={{ background: 'var(--color-gold-deep)' }} /> Fetching from quran.com…
          </div>
        )}
        {state.error && !state.data && (
          <div className="py-4 text-center font-ui text-[12px] text-rose-600">
            Could not load verse: {state.error}
          </div>
        )}
        {state.data && (
          <>
            <p className="quran-arabic" lang="ar" dir="rtl">{state.data.arabic}</p>
            <div className="quran-translation">
              {state.data.translation}
              <span className="translation-attribution">— {state.data.translation_source}</span>
            </div>
          </>
        )}
      </div>

      <div className="quran-popover-footer">
        <span>Quran.com</span>
        <div className="flex items-center gap-3">
          {state.data?.audio_url && (
            <button
              onClick={() => {
                const a = new Audio(state.data!.audio_url!);
                a.play().catch(() => {});
              }}
              className="hover:underline"
              title="Play recitation"
            >▸ Recite</button>
          )}
          <a
            href={`https://quran.com/${state.key.replace(':', '/')}`}
            target="_blank" rel="noopener noreferrer"
          >Open ↗</a>
        </div>
      </div>
    </div>
  );
}
