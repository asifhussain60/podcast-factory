/**
 * TermPopover — hover/click an .ar-overlay glossary span to surface a
 * definition popover. Uses event delegation on the article so it works
 * for every glossary term without per-span hydration.
 *
 * Cached in localStorage (per book). No Tailwind utility classes.
 */

import { useEffect, useRef, useState } from 'react';
import { getTermDef, setTermDef } from '../../lib/reader/ai-cache';

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

  // Position is dynamic by definition — keep as a CSS custom property on
  // the element so the visual rules in chapter-viewer.css drive layout.
  const positionStyle = { '--popover-top': `${top}px`, '--popover-left': `${left}px` } as React.CSSProperties;

  return (
    <div
      data-term-popover
      ref={popoverRef}
      className="popover-card popover-card--term"
      style={positionStyle}
      role="dialog"
      aria-label={`Definition of ${state.phonetic}`}
    >
      <div className="popover-header">
        <span>Glossary · via Gemini</span>
        <button className="popover-close" onClick={() => setState(null)} aria-label="Close">✕</button>
      </div>
      <div className="popover-body">
        <div className="popover-term-row">
          <div className="popover-term-left">
            <div className="popover-term-name">{state.transliteration}</div>
            {state.audio && <div className="popover-term-audio">/{state.audio}/</div>}
          </div>
          {state.script && (
            <div className="popover-term-script" lang="ar" dir="rtl">
              {state.script}
            </div>
          )}
        </div>
        <hr className="popover-divider" />
        {state.loading && !state.def && (
          <div className="popover-loading">
            <span className="popover-dot" aria-hidden /> Looking up…
          </div>
        )}
        {state.error && !state.def && (
          <div className="popover-error">Could not load: {state.error}</div>
        )}
        {state.def?.definition && (
          <p className="popover-definition">{state.def.definition}</p>
        )}
        {state.def?.etymology && (
          <p className="popover-etymology">{state.def.etymology}</p>
        )}
        {state.def?.related && state.def.related.length > 0 && (
          <div className="popover-related">
            {state.def.related.map((r) => (
              <span key={r} className="popover-chip">{r}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
