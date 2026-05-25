/**
 * SectionSummaries — adds a "✦ Summarize" button in the left gutter of
 * each h2 in the chapter. On click, replaces the button with a small
 * callout containing a 2-3 sentence summary + key-point chips.
 *
 * Cached forever by SHA-1 of section text — stable input is free on
 * re-read.
 */

import { useEffect, useState } from 'react';
import { getSectionSummary, setSectionSummary } from '~/lib/ai-cache';

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
      h2.style.position = 'relative';

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.title = 'Summarize this section';
      btn.setAttribute('aria-label', 'Summarize section');
      btn.style.cssText = 'position:absolute;left:-2.2em;top:50%;transform:translateY(-50%);width:1.6em;height:1.6em;border-radius:9999px;background:transparent;color:#b58a2a;font-size:0.9em;cursor:pointer;opacity:0;transition:opacity 150ms,background 150ms;line-height:1;display:flex;align-items:center;justify-content:center;';
      btn.textContent = '✦';
      h2.addEventListener('mouseenter', () => { btn.style.opacity = '1'; });
      h2.addEventListener('mouseleave', () => { btn.style.opacity = '0.0'; });
      btn.addEventListener('mouseenter', () => { btn.style.opacity = '1'; btn.style.background = 'rgba(217,119,6,0.1)'; });
      btn.addEventListener('mouseleave', () => { btn.style.background = 'transparent'; });

      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        const { text, title } = getSectionText(h2);
        if (!text) return;
        const callout = document.createElement('div');
        callout.className = 'section-summary-callout';
        callout.style.cssText = 'margin:0.6em 0 1.2em;padding:0.7em 1em;border-left:3px solid #b58a2a;background:color-mix(in oklab, currentColor 4%, transparent);border-radius:0 4px 4px 0;font-size:0.92em;font-style:italic;color:var(--color-ink-secondary);';
        callout.innerHTML = '<span style="opacity:0.6">Summarizing…</span>';
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
          callout.innerHTML = `<span style="color:#b91c1c">Failed: ${(err as Error).message}</span>`;
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
  if (s.summary) parts.push(`<div style="font-style:italic;">${escape(s.summary)}</div>`);
  if (s.keyPoints && s.keyPoints.length) {
    parts.push(`<div style="margin-top:0.5em;display:flex;flex-wrap:wrap;gap:0.3em;font-style:normal;">${s.keyPoints.map((k) => `<span style="background:rgba(217,119,6,0.12);color:#92400e;padding:0.1em 0.55em;border-radius:9999px;font-size:0.82em;">${escape(k)}</span>`).join('')}</div>`);
  }
  parts.push(`<div style="margin-top:0.4em;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#999;font-style:normal;">Gemini summary · click ✦ on other headings for more</div>`);
  el.innerHTML = parts.join('');
}

function escape(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
