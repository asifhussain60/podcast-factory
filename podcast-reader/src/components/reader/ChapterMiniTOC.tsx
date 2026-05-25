/**
 * Right-rail chapter-internal mini-TOC.
 *
 * Scrapes h2/h3 elements from the rendered article on mount and renders
 * them as clickable anchors. Tracks the active section via
 * IntersectionObserver so the current heading is highlighted as the user
 * scrolls — gives a sense of place in a long chapter without scrubbing.
 */

import { useEffect, useState } from 'react';

interface TOCItem { id: string; text: string; level: number; }

export default function ChapterMiniTOC() {
  const [items, setItems] = useState<TOCItem[]>([]);
  const [active, setActive] = useState<string>('');

  useEffect(() => {
    const headings = Array.from(document.querySelectorAll('.prose-body h2, .prose-body h3')) as HTMLElement[];
    const collected: TOCItem[] = headings
      .filter((h) => h.id)
      .map((h) => ({ id: h.id, text: h.textContent || '', level: h.tagName === 'H2' ? 2 : 3 }));
    setItems(collected);

    if (collected.length === 0) return;

    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.target.getBoundingClientRect().top - b.target.getBoundingClientRect().top);
        if (visible.length > 0) setActive((visible[0].target as HTMLElement).id);
      },
      { rootMargin: '-80px 0px -70% 0px', threshold: 0 },
    );
    headings.forEach((h) => obs.observe(h));
    return () => obs.disconnect();
  }, []);

  if (items.length < 2) return null;

  return (
    <nav className="text-[13.5px] leading-snug">
      <div className="mb-2 font-ui text-[10px] font-semibold uppercase tracking-wider text-stone-500">
        In this chapter
      </div>
      <ul className="max-h-[38vh] space-y-1 overflow-y-auto border-l border-stone-200 pl-3 pr-1 dark:border-stone-700">
        {items.map((it) => (
          <li key={it.id} className={it.level === 3 ? 'pl-3' : ''}>
            <a
              href={`#${it.id}`}
              className={
                'block py-0.5 transition-colors line-clamp-2 ' +
                (active === it.id
                  ? 'font-medium text-amber-700 dark:text-amber-300'
                  : 'text-stone-700 hover:text-stone-900 dark:text-stone-300 dark:hover:text-stone-100')
              }
              title={it.text}
            >
              {it.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
