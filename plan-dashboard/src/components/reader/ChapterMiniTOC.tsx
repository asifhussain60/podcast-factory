/**
 * Right-rail chapter-internal mini-TOC.
 *
 * Scrapes h2/h3 from the rendered article and tracks the active section
 * via IntersectionObserver. No Tailwind utility classes.
 */

import { useEffect, useState } from 'react';

interface TOCItem { id: string; text: string; level: number; }

export default function ChapterMiniTOC() {
  const [items, setItems] = useState<TOCItem[]>([]);
  const [active, setActive] = useState<string>('');

  useEffect(() => {
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
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.target.getBoundingClientRect().top - b.target.getBoundingClientRect().top);
        if (visible.length > 0) setActive((visible[0].target as HTMLElement).id);
      },
      { rootMargin: '-80px 0px -70% 0px', threshold: 0 },
    );
    headings.forEach((h) => obs.observe(h));
    return () => obs.disconnect();
  }, []);

  if (items.length < 2) return null;

  return (
    <nav className="mini-toc">
      <div className="mini-toc-label">In this chapter</div>
      <ul className="mini-toc-list">
        {items.map((it) => (
          <li
            key={it.id}
            className={`mini-toc-item mini-toc-item--l${it.level}`}
          >
            <a
              href={`#${it.id}`}
              className={`mini-toc-link ${active === it.id ? 'is-active' : ''}`}
              title={it.text}
            >
              <span className="mini-toc-dot" aria-hidden="true" />
              {it.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
