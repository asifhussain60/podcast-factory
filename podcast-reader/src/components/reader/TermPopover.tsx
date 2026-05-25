/**
 * TermPopover — hover/click an .ar-overlay glossary span to surface a
 * definition popover. Uses event delegation on the article so it works
 * for every glossary term without per-span hydration.
 *
 * Visual: anchored 320px card with phonetic + Arabic + audio-phonetic
 * + 1-sentence definition. "More" expands to etymology + related terms.
 *
 * Caching: localStorage forever (per book). Definitions don't drift.
 */

import { useEffect, useRef, useState } from 'react';
import { getTermDef, setTermDef } from '~/lib/ai-cache';

interface Def {
  definition?: string;
  etymology?: string;
  related?: string[];
}

interface State {
  anchorRect: DOMRect;
  phonetic: string;
  transliteration: string;
  script: string;
  audio: string;
  context: string;
  def: Def | null;
  loading: boolean;
  error?: string;
}

interface Props { book: string; }

export default function TermPopover({ book }: Props) {
  const [state, setState] = useState<State | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const hoverTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const article = document.querySelector('.prose-body');
    if (!article) return;

    const open = async (span: HTMLElement) => {
      const phonetic = span.dataset.phonetic || span.querySelector('.ar-en')?.textContent || '';
      const tr = span.dataset.transliteration || phonetic;
      const script = span.dataset.script || '';
      const audio = span.dataset.audio || '';
      const para = span.closest('p, li, blockquote');
      const ctxText = (para?.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 240);
      const rect = span.getBoundingClientRect();

      const cached = getTermDef(book, phonetic) as Def | null;
      setState({ anchorRect: rect, phonetic, transliteration: tr, script, audio, context: ctxText, def: cached, loading: !cached });

      if (cached) return;
      try {
        const res = await fetch('/api/ai/define-term', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ phonetic, transliteration: tr, arabic: script, context: ctxText, book }),
        });
        if (!res.ok) throw new Error(`AI ${res.status}`);
        const data = await res.json() as Def;
        setTermDef(book, phonetic, data);
        setState((s) => (s && s.phonetic === phonetic ? { ...s, def: data, loading: false } : s));
      } catch (e) {
        setState((s) => (s && s.phonetic === phonetic ? { ...s, loading: false, error: (e as Error).message } : s));
      }
    };

    const onOver = (e: Event) => {
      const target = (e.target as HTMLElement).closest('.ar-overlay') as HTMLElement | null;
      if (!target) return;
      if (hoverTimerRef.current) window.clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = window.setTimeout(() => open(target), 320);
    };
    const onOut = () => {
      if (hoverTimerRef.current) { window.clearTimeout(hoverTimerRef.current); hoverTimerRef.current = null; }
    };
    const onClick = (e: Event) => {
      const target = (e.target as HTMLElement).closest('.ar-overlay') as HTMLElement | null;
      if (!target) return;
      e.preventDefault();
      if (hoverTimerRef.current) window.clearTimeout(hoverTimerRef.current);
      open(target);
    };
    const onDocClick = (e: MouseEvent) => {
      if (!state) return;
      const t = e.target as HTMLElement;
      if (t.closest('.ar-overlay') || t.closest('[data-term-popover]')) return;
      setState(null);
    };
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') setState(null); };

    article.addEventListener('mouseover', onOver);
    article.addEventListener('mouseout', onOut);
    article.addEventListener('click', onClick);
    document.addEventListener('click', onDocClick);
    document.addEventListener('keydown', onEsc);
    return () => {
      article.removeEventListener('mouseover', onOver);
      article.removeEventListener('mouseout', onOut);
      article.removeEventListener('click', onClick);
      document.removeEventListener('click', onDocClick);
      document.removeEventListener('keydown', onEsc);
    };
  }, [book, state]);

  if (!state) return null;
  const top = state.anchorRect.bottom + window.scrollY + 6;
  const left = Math.min(
    state.anchorRect.left + window.scrollX,
    window.scrollX + window.innerWidth - 340,
  );

  return (
    <div
      data-term-popover
      ref={popoverRef}
      className="absolute z-50 w-[320px] rounded-lg border border-stone-200 bg-white p-3 shadow-xl dark:border-stone-700 dark:bg-stone-800"
      style={{ top, left }}
      role="dialog"
      aria-label={`Definition of ${state.phonetic}`}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <div className="font-serif text-[15px] font-semibold text-stone-900 dark:text-stone-100">{state.transliteration}</div>
          {state.audio && <div className="font-ui text-[10px] uppercase tracking-wider text-stone-500">/{state.audio}/</div>}
        </div>
        {state.script && (
          <div className="font-arabic text-[20px] text-amber-700 dark:text-amber-300" style={{ fontFamily: 'Amiri, serif' }} lang="ar" dir="rtl">
            {state.script}
          </div>
        )}
      </div>
      <hr className="my-2 border-stone-200 dark:border-stone-700" />
      {state.loading && !state.def && (
        <div className="font-ui text-[12px] text-stone-500">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-500" /> Looking up…
        </div>
      )}
      {state.error && !state.def && (
        <div className="font-ui text-[12px] text-rose-600">Could not load: {state.error}</div>
      )}
      {state.def?.definition && (
        <p className="text-[13px] leading-snug text-stone-700 dark:text-stone-200">{state.def.definition}</p>
      )}
      {state.def?.etymology && (
        <p className="mt-2 text-[11px] italic text-stone-500">{state.def.etymology}</p>
      )}
      {state.def?.related && state.def.related.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {state.def.related.map((r) => (
            <span key={r} className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">{r}</span>
          ))}
        </div>
      )}
      <div className="mt-2 flex justify-between text-[10px] text-stone-400">
        <span>via Gemini</span>
        <button onClick={() => setState(null)} className="hover:text-stone-700">close (esc)</button>
      </div>
    </div>
  );
}
