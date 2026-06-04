/**
 * Ref-category filter chips + keyboard navigation.
 *
 * Toggling a chip writes the enabled-set to <body data-cat-enabled> so
 * CSS can apply highlights selectively. Keyboard nav: each category has
 * shortcuts (e.g. n/N) that scroll to next/prev refs of that category.
 * No Tailwind utility classes.
 */

import { useEffect, useMemo, useState } from 'react';

export interface CategoryDescriptor {
  id: string;
  label: string;
  glyph: string;
  colorToken: string;
  shortcuts: { next: string; prev: string };
  count: number;
}

interface Props {
  categories: CategoryDescriptor[];
}

export default function ReaderControls({ categories }: Props) {
  const [enabled, setEnabled] = useState<Set<string>>(() => new Set());
  const [, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    const body = document.body;
    if (enabled.size === 0) body.removeAttribute('data-cat-enabled');
    else body.setAttribute('data-cat-enabled', [...enabled].join(' '));
  }, [enabled]);

  const keyMap = useMemo(() => {
    const m = new Map<string, { dir: 'next' | 'prev'; id: string }>();
    for (const c of categories) {
      m.set(c.shortcuts.next, { dir: 'next', id: c.id });
      m.set(c.shortcuts.prev, { dir: 'prev', id: c.id });
    }
    return m;
  }, [categories]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const entry = keyMap.get(e.key);
      if (!entry) return;

      const cat = categories.find((c) => c.id === entry.id);
      if (!cat || cat.count === 0) return;

      e.preventDefault();

      if (!enabled.has(entry.id)) {
        setEnabled((prev) => new Set([...prev, entry.id]));
      }

      const refs = Array.from(
        document.querySelectorAll<HTMLElement>(`span.ref[data-ref-type="${entry.id}"]`),
      );
      if (refs.length === 0) return;

      const viewportCenter = window.innerHeight / 2;

      let targetIdx: number;
      if (entry.dir === 'next') {
        targetIdx = refs.findIndex((r) => r.getBoundingClientRect().top > viewportCenter);
        if (targetIdx === -1) targetIdx = 0;
      } else {
        let lastAbove = -1;
        for (let i = 0; i < refs.length; i++) {
          if (refs[i].getBoundingClientRect().top < viewportCenter) lastAbove = i;
          else break;
        }
        targetIdx = lastAbove === -1 ? refs.length - 1 : lastAbove;
      }

      const target = refs[targetIdx];
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      target.classList.remove('ref-active');
      void target.offsetWidth;
      target.classList.add('ref-active');
      setActiveId(target.id);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [keyMap, enabled, categories]);

  const toggle = (id: string) => {
    setEnabled((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalRefs = categories.reduce((sum, c) => sum + c.count, 0);

  return (
    <div className="reader-controls">
      <span className="reader-controls-label">Refs:</span>
      {categories.map((c) => {
        const isEmpty = c.count === 0;
        const isOn = enabled.has(c.id) && !isEmpty;
        const state = isEmpty ? 'is-empty' : isOn ? 'is-on' : 'is-off';
        return (
          <button
            key={c.id}
            type="button"
            disabled={isEmpty}
            onClick={() => !isEmpty && toggle(c.id)}
            className={`reader-chip reader-chip--${c.colorToken} ${state}`}
            title={
              isEmpty
                ? `No ${c.label} refs on this page`
                : `${isOn ? 'Hide' : 'Show'} ${c.label} highlights (key: ${c.shortcuts.next})`
            }
            aria-pressed={isOn}
            aria-disabled={isEmpty}
          >
            <span aria-hidden className="reader-chip-glyph">{c.glyph}</span>
            <span className="reader-chip-label">{c.label}</span>
            <span className="reader-chip-count">{c.count}</span>
            <kbd className="reader-chip-kbd">{c.shortcuts.next}</kbd>
          </button>
        );
      })}
      <span className="reader-controls-total">{totalRefs} total</span>
    </div>
  );
}
