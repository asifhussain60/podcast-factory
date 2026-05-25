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
    // Read heading text from the leading text nodes only — SectionSummaries
    // appends a ✦ summarize button into each h2 that we must NOT include.
    const headingText = (h: HTMLElement): string => {
      const clone = h.cloneNode(true) as HTMLElement;
      clone.querySelectorAll('button, .edit-block-actions, [contenteditable="false"]').forEach((n) => n.remove());
      return (clone.textContent || '').replace(/\s+/g, ' ').trim();
    };
    const headings = Array.from(document.querySelectorAll('.prose-body h2, .prose-body h3')) as HTMLElement[];
    const collected: TOCItem[] = headings
      .filter((h) => h.id)
      .map((h) => ({ id: h.id, text: headingText(h), level: h.tagName === 'H2' ? 2 : 3 }));
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
      <div className="mb-3 font-ui text-[11px] font-semibold tracking-wide text-stone-500">
        In this chapter
      </div>
      <ul className="max-h-[42vh] space-y-1.5 overflow-y-auto border-l border-stone-200 pl-3 pr-1 dark:border-stone-700">
        {items.map((it) => (
          <li key={it.id} className={'relative ' + (it.level === 3 ? 'pl-4' : '')}>
            <a
              href={`#${it.id}`}
              className={
                'block py-0.5 pl-4 transition-colors line-clamp-2 relative ' +
                (active === it.id
                  ? 'font-medium text-amber-700 dark:text-amber-300'
                  : 'text-stone-700 hover:text-stone-900 dark:text-stone-300 dark:hover:text-stone-100')
              }
              title={it.text}
            >
              <span className={
                'absolute left-0 top-[0.55em] inline-block h-1.5 w-1.5 rounded-full transition-colors ' +
                (active === it.id ? 'bg-amber-600' : 'bg-stone-300 dark:bg-stone-600')
              } aria-hidden="true" />
              {it.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
