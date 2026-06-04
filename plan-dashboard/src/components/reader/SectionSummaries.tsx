/**
 * SectionSummaries — adds a "✦ Summarize" button at each h2 in the
 * chapter. On click, inserts a small callout containing a 2-3 sentence
 * summary + key-point chips.
 *
 * No inline styles; all visual rules live in chapter-viewer.css under
 * the `.section-summary-*` family.
 */

import { useEffect, useState } from 'react';
import { getSectionSummary, setSectionSummary } from '../../lib/reader/ai-cache';

interface Props { book: string; }

interface Summary { summary?: string; keyPoints?: string[]; }

function getSectionText(h2: HTMLElement): { text: string; title: string } {
  const title = h2.textContent || '';
  const parts: string[] = [];
  let el: Element | null = h2.nextElementSibling;
  while (el && el.tagName !== 'H2' && el.tagName !== 'H1') {
    parts.push((el as HTMLElement).innerText || '');
    el = el.nextElementSibling;
  }
  return { text: parts.join('\n\n').trim(), title };
}

export default function SectionSummaries({ book }: Props) {
  const [, force] = useState(0);

  useEffect(() => {
    const article = document.querySelector('.prose-body');
    if (!article) return;
    const h2s = Array.from(article.querySelectorAll('h2')) as HTMLElement[];

    h2s.forEach((h2) => {
      if (h2.dataset.summaryMounted) return;
      h2.dataset.summaryMounted = '1';
      h2.classList.add('h2-with-summarize');

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'section-summarize-btn';
      btn.title = 'Summarize this section';
      btn.setAttribute('aria-label', 'Summarize section');
      btn.textContent = '✦';

      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        const { text, title } = getSectionText(h2);
        if (!text) return;
        const callout = document.createElement('div');
        callout.className = 'section-summary-callout';
        callout.innerHTML = '<span class="section-summary-loading">Summarizing…</span>';
        h2.parentNode?.insertBefore(callout, h2.nextSibling);
        btn.remove();

        let cached = await getSectionSummary(text) as Summary | null;
        if (cached) {
          renderSummary(callout, cached);
          return;
        }
        try {
          const res = await fetch('/api/ai/summarize-section', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ sectionText: text, sectionTitle: title, bookContext: book }),
          });
          if (!res.ok) throw new Error(`AI ${res.status}`);
          const data = await res.json() as Summary;
          await setSectionSummary(text, data);
          renderSummary(callout, data);
        } catch (err) {
          callout.innerHTML = `<span class="section-summary-error">Failed: ${escape((err as Error).message)}</span>`;
        }
      });

      h2.appendChild(btn);
    });

    force((n) => n + 1);
  }, [book]);

  return null;
}

function renderSummary(el: HTMLElement, s: Summary) {
  const parts: string[] = [];
  if (s.summary) parts.push(`<div class="section-summary-body">${escape(s.summary)}</div>`);
  if (s.keyPoints && s.keyPoints.length) {
    parts.push(
      `<div class="section-summary-keypoints">${s.keyPoints
        .map((k) => `<span class="section-summary-chip">${escape(k)}</span>`)
        .join('')}</div>`,
    );
  }
  parts.push('<div class="section-summary-attr">Gemini summary · click ✦ on other headings for more</div>');
  el.innerHTML = parts.join('');
}

function escape(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
