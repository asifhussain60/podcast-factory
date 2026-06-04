/**
 * TopicPopover — Wave J (J5): hover/click a .ref-topic span to surface a
 * Wisdom topic panel showing topic name, binder/chapter provenance, content
 * preview, and linked Quran ayats.
 *
 * Data from GET /api/wisdom/topic?id=N (wired in J2).
 * Identical event-delegation pattern to QuranPopover + TermPopover:
 *   320 ms hover delay, localStorage cache, dismiss on outside click + Escape.
 * No new frontend libraries.
 */

import { useEffect, useRef, useState } from 'react';

interface LinkedAyat {
  surah: number;
  ayat: number;
  arabic?: string;
  pickthall?: string;
}

interface TopicData {
  topic_id: number;
  binder_slug: string;
  chapter_slug: string;
  topic: string;
  content: string;
  linked_ayats?: LinkedAyat[];
}

interface State {
  anchorRect: DOMRect;
  topicId: number;
  data: TopicData | null;
  loading: boolean;
  error?: string;
}

const CACHE_KEY = (id: number) => `pf-reader:topic:${id}`;

function readCache(id: number): TopicData | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY(id));
    return raw ? JSON.parse(raw) as TopicData : null;
  } catch { return null; }
}
function writeCache(id: number, v: TopicData): void {
  try { localStorage.setItem(CACHE_KEY(id), JSON.stringify(v)); } catch { /* quota */ }
}

export default function TopicPopover() {
  const [state, setState] = useState<State | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const hoverTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const article = document.querySelector('.prose-body');
    if (!article) return;

    const open = async (anchor: HTMLElement, topicId: number) => {
      const rect = anchor.getBoundingClientRect();
      const cached = readCache(topicId);
      setState({ anchorRect: rect, topicId, data: cached, loading: !cached });
      if (cached) return;
      try {
        const res = await fetch(`/api/wisdom/topic?id=${topicId}`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json() as TopicData;
        writeCache(topicId, data);
        setState((s) => (s && s.topicId === topicId ? { ...s, data, loading: false } : s));
      } catch (e) {
        setState((s) => (s && s.topicId === topicId ? { ...s, loading: false, error: (e as Error).message } : s));
      }
    };

    const idFromSpan = (el: HTMLElement): number | null => {
      const raw = el.dataset.topicId ?? el.getAttribute('data-topic-id');
      const n = Number(raw);
      return Number.isInteger(n) && n > 0 ? n : null;
    };

    const onOver = (e: Event) => {
      const target = (e.target as HTMLElement).closest('.ref-topic') as HTMLElement | null;
      if (!target) return;
      const id = idFromSpan(target);
      if (!id) return;
      if (hoverTimerRef.current) window.clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = window.setTimeout(() => open(target, id), 320);
    };
    const onOut = () => {
      if (hoverTimerRef.current) { window.clearTimeout(hoverTimerRef.current); hoverTimerRef.current = null; }
    };
    const onClick = (e: Event) => {
      const target = (e.target as HTMLElement).closest('.ref-topic') as HTMLElement | null;
      if (!target) return;
      const id = idFromSpan(target);
      if (!id) return;
      e.preventDefault();
      e.stopPropagation();
      if (hoverTimerRef.current) window.clearTimeout(hoverTimerRef.current);
      open(target, id);
    };
    const onDocClick = (e: MouseEvent) => {
      if (!state) return;
      const t = e.target as HTMLElement;
      if (t.closest('.ref-topic') || t.closest('[data-topic-popover]')) return;
      setState(null);
    };
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') setState(null); };

    article.addEventListener('mouseover', onOver);
    article.addEventListener('mouseout', onOut);
    article.addEventListener('click', onClick, true);
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

  const POPOVER_W = 400;
  const ESTIMATED_H = 260;
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

  const positionStyle = {
    '--popover-top': `${top}px`,
    '--popover-left': `${left}px`,
    '--popover-width': `${POPOVER_W}px`,
  } as React.CSSProperties;

  const d = state.data;

  return (
    <div
      ref={popoverRef}
      data-topic-popover
      className="popover-card popover-card--topic"
      style={positionStyle}
      role="dialog"
      aria-label={d ? `Wisdom topic: ${d.topic}` : 'Wisdom topic'}
    >
      <div className="popover-header">
        <span>Wisdom corpus · topic cross-reference</span>
        <button className="popover-close" onClick={() => setState(null)} aria-label="Close">✕</button>
      </div>

      <div className="popover-body">
        {state.loading && !d && (
          <div className="popover-loading">
            <span className="popover-dot" aria-hidden /> Looking up topic…
          </div>
        )}
        {state.error && !d && (
          <div className="popover-error">Could not load topic: {state.error}</div>
        )}
        {d && (
          <>
            <div className="topic-popover-name">{d.topic}</div>
            <div className="topic-popover-provenance">
              {d.binder_slug}{d.chapter_slug ? ` · ${d.chapter_slug}` : ''}
            </div>
            <hr className="popover-divider" />
            <p className="topic-popover-content">
              {d.content.length > 380 ? d.content.slice(0, 380) + '…' : d.content}
            </p>
            {d.linked_ayats && d.linked_ayats.length > 0 && (
              <div className="topic-popover-ayats">
                <span className="topic-popover-ayats-label">Linked verses</span>
                {d.linked_ayats.slice(0, 3).map((a) => (
                  <div key={`${a.surah}:${a.ayat}`} className="topic-popover-ayat">
                    <span className="topic-popover-ayat-key">Q{a.surah}:{a.ayat}</span>
                    {a.pickthall && (
                      <span className="topic-popover-ayat-text">{a.pickthall.slice(0, 120)}{a.pickthall.length > 120 ? '…' : ''}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
