/**
 * Client island: ref-category filter chips + keyboard navigation.
 *
 * Renders one chip per registered category (label, glyph, count, toggle).
 * Toggling a chip writes the disabled-set to `<body data-cat-disabled>`,
 * which CSS uses to drop the per-category styling. The DOM spans stay in
 * place (Phase 4 still wants them for comment anchoring), they just lose
 * their visual treatment.
 *
 * Keyboard nav: each category declares `shortcuts.next` / `shortcuts.prev`
 * (e.g. `n` / `N`). Pressing the key jumps to the next/prev `<span>` of
 * that category, scrolling it into view and pulsing it.
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

// Chip styling when ENABLED — matches the highlight colour applied to refs.
const COLOR_CHIP_ON: Record<string, { bg: string; text: string; ring: string }> = {
  yellow:  { bg: 'bg-yellow-200',  text: 'text-yellow-900',  ring: 'ring-yellow-400' },
  orange:  { bg: 'bg-orange-200',  text: 'text-orange-900',  ring: 'ring-orange-400' },
  emerald: { bg: 'bg-emerald-200', text: 'text-emerald-900', ring: 'ring-emerald-400' },
  // Reserved for future categories
  indigo:  { bg: 'bg-indigo-200',  text: 'text-indigo-900',  ring: 'ring-indigo-400' },
  amber:   { bg: 'bg-amber-200',   text: 'text-amber-900',   ring: 'ring-amber-400' },
  sky:     { bg: 'bg-sky-200',     text: 'text-sky-900',     ring: 'ring-sky-400' },
  purple:  { bg: 'bg-purple-200',  text: 'text-purple-900',  ring: 'ring-purple-400' },
  stone:   { bg: 'bg-stone-200',   text: 'text-stone-800',   ring: 'ring-stone-400' },
};

function chipClassesOn(token: string): string {
  const c = COLOR_CHIP_ON[token] ?? COLOR_CHIP_ON.stone;
  return `${c.bg} ${c.text} ${c.ring}`;
}

export default function ReaderControls({ categories }: Props) {
  // Inverted semantics: refs are OFF by default. Categories live in the
  // `enabled` set only when the user explicitly toggles them on.
  const [enabled, setEnabled] = useState<Set<string>>(() => new Set());
  const [activeId, setActiveId] = useState<string | null>(null);

  // Sync the enabled set onto <body data-cat-enabled> so CSS can apply
  // highlights selectively. No attribute when empty (avoids stale state).
  useEffect(() => {
    const body = document.body;
    if (enabled.size === 0) body.removeAttribute('data-cat-enabled');
    else body.setAttribute('data-cat-enabled', [...enabled].join(' '));
  }, [enabled]);

  // Build a flat keyboard map: { 'n': {dir:'next', cat:'quran'}, ... }
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
      // Don't capture when typing in a form field or contentEditable.
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const entry = keyMap.get(e.key);
      if (!entry) return;

      // Skip the shortcut entirely when this category has no refs on the
      // page — otherwise we'd auto-enable a category that highlights nothing.
      const cat = categories.find((c) => c.id === entry.id);
      if (!cat || cat.count === 0) return;

      e.preventDefault();

      // Auto-enable this category if it's off — pressing the shortcut is a
      // clear intent to navigate, so unhide highlights as a side-effect.
      if (!enabled.has(entry.id)) {
        setEnabled((prev) => new Set([...prev, entry.id]));
      }

      const refs = Array.from(
        document.querySelectorAll<HTMLElement>(`span.ref[data-ref-type="${entry.id}"]`)
      );
      if (refs.length === 0) return;

      // Jump from the user's CURRENT scroll position (viewport centre),
      // not from the last-active ref. So pressing `n` while scrolled
      // halfway down always jumps to the next Quran ref below that point.
      const viewportCenter = window.innerHeight / 2;

      let targetIdx: number;
      if (entry.dir === 'next') {
        // First ref whose top edge is below the viewport centre.
        targetIdx = refs.findIndex((r) => r.getBoundingClientRect().top > viewportCenter);
        // None below → wrap to first.
        if (targetIdx === -1) targetIdx = 0;
      } else {
        // Last ref whose top edge is above the viewport centre.
        let lastAbove = -1;
        for (let i = 0; i < refs.length; i++) {
          if (refs[i].getBoundingClientRect().top < viewportCenter) lastAbove = i;
          else break;
        }
        // None above → wrap to last.
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
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="font-ui mr-1 text-stone-400 uppercase tracking-wider">Refs:</span>
      {categories.map((c) => {
        const isEmpty = c.count === 0;
        const isOn = enabled.has(c.id) && !isEmpty;
        const onClasses = chipClassesOn(c.colorToken);

        let stateClasses: string;
        if (isEmpty) {
          stateClasses = 'bg-stone-50 text-stone-300 ring-stone-200 cursor-not-allowed';
        } else if (isOn) {
          stateClasses = `${onClasses} shadow-sm`;
        } else {
          stateClasses = 'bg-white text-stone-500 ring-stone-300 hover:bg-stone-50 hover:text-stone-700 hover:ring-stone-500';
        }

        return (
          <button
            key={c.id}
            type="button"
            disabled={isEmpty}
            onClick={() => !isEmpty && toggle(c.id)}
            className={`font-ui inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 ring-1 transition ${stateClasses}`}
            title={
              isEmpty
                ? `No ${c.label} refs on this page`
                : `${isOn ? 'Hide' : 'Show'} ${c.label} highlights (key: ${c.shortcuts.next})`
            }
            aria-pressed={isOn}
            aria-disabled={isEmpty}
          >
            <span aria-hidden>{c.glyph}</span>
            <span>{c.label}</span>
            <span className={isEmpty ? 'text-stone-300' : isOn ? 'opacity-70' : 'text-stone-400'}>
              {c.count}
            </span>
            <kbd
              className={`ml-0.5 hidden rounded border px-1 text-[10px] sm:inline ${
                isEmpty
                  ? 'border-stone-200 text-stone-300'
                  : isOn
                  ? 'border-current/30 opacity-60'
                  : 'border-stone-300 text-stone-500'
              }`}
            >
              {c.shortcuts.next}
            </kbd>
          </button>
        );
      })}
      <span className="font-ui ml-2 text-stone-400">
        {totalRefs} total
      </span>
    </div>
  );
}
