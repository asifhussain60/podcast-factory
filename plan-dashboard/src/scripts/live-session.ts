/**
 * live-session.ts — client for the LIVE Session reading view (/studio/<slug>/live).
 *
 * Two concerns, both read-only (this surface never writes book state):
 *   1. Book picker — open/close the panel, filter the list by content bucket.
 *   2. Scroll-synced explanations — as the reader scrolls, show the current
 *      section's Companion notes in the right-hand panel (studio-composer REQ-SC-011).
 *
 * All logic lives here (external module) — the .astro page carries only markup, a
 * JSON data island, and the one-line import (Cortex DoD: no inline script bodies).
 */

interface LiveNote {
  kind: string;
  body: string;
  anchor: string;
  source: string;
}
interface LiveSection {
  id: string;
  title: string;
  notes: LiveNote[];
}

function readData(): { slug: string; sections: LiveSection[] } | null {
  const el = document.getElementById('lsv-explain-data');
  if (!el?.textContent) return null;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return null;
  }
}

// ---- book picker ----------------------------------------------------------
function initPicker(): void {
  const picker = document.querySelector<HTMLElement>('.lsv-picker');
  const trigger = document.getElementById('lsv-picker-trigger');
  const panel = document.getElementById('lsv-picker-panel');
  if (!picker || !trigger || !panel) return;

  const setOpen = (open: boolean) => {
    picker.dataset.open = String(open);
    trigger.setAttribute('aria-expanded', String(open));
    panel.hidden = !open;
  };

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    setOpen(picker.dataset.open !== 'true');
  });
  document.addEventListener('click', (e) => {
    if (!picker.contains(e.target as Node)) setOpen(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && picker.dataset.open === 'true') {
      setOpen(false);
      trigger.focus();
    }
  });

  // Bucket filter chips: show only the matching group ("all" shows every group).
  const chips = panel.querySelectorAll<HTMLElement>('.lsv-filter-chip');
  const groups = panel.querySelectorAll<HTMLElement>('.lsv-picker-group');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const bucket = chip.dataset.bucket ?? 'all';
      chips.forEach((c) => c.classList.toggle('is-active', c === chip));
      groups.forEach((g) => {
        g.hidden = bucket !== 'all' && g.dataset.bucket !== bucket;
      });
    });
  });
}

// ---- scroll-synced explanations -------------------------------------------
function initExplanations(): void {
  const data = readData();
  const body = document.getElementById('lsv-explain-body');
  const titleEl = document.getElementById('lsv-explain-title');
  if (!data || !body || !titleEl) return;

  const sectionById = new Map(data.sections.map((s) => [s.id, s]));
  const headings = Array.from(
    document.querySelectorAll<HTMLElement>('.lsv-read h2[id], .lsv-read h1[id]'),
  );
  if (headings.length === 0) return;

  const anyNotes = data.sections.some((s) => s.notes.length > 0);
  let currentId = '';

  const render = (id: string) => {
    if (id === currentId) return;
    currentId = id;
    const section = sectionById.get(id);
    titleEl.textContent = section ? section.title : 'Explanations';
    body.textContent = '';

    if (!section || section.notes.length === 0) {
      const p = document.createElement('p');
      p.className = 'lsv-explain-empty';
      p.textContent = anyNotes
        ? 'No companion notes for this section.'
        : 'No companion notes have been written for this book yet.';
      body.appendChild(p);
      return;
    }

    for (const note of section.notes) {
      const card = document.createElement('article');
      card.className = 'lsv-note';

      const head = document.createElement('div');
      head.className = 'lsv-note-head';
      const kind = document.createElement('span');
      kind.className = 'lsv-note-kind';
      kind.textContent = note.kind || 'note';
      head.appendChild(kind);
      if (note.source) {
        const src = document.createElement('span');
        src.className = 'lsv-note-source';
        src.textContent = note.source;
        head.appendChild(src);
      }
      card.appendChild(head);

      if (note.anchor) {
        const q = document.createElement('blockquote');
        q.className = 'lsv-note-anchor';
        q.textContent = note.anchor;
        card.appendChild(q);
      }

      const p = document.createElement('p');
      p.className = 'lsv-note-body';
      p.textContent = note.body;
      card.appendChild(p);

      body.appendChild(card);
    }
  };

  // Scroll-spy: the current section is the last heading whose top has crossed the
  // reading band just below the sticky header. rAF-throttled for smoothness.
  const THRESHOLD = 160;
  let ticking = false;
  const update = () => {
    ticking = false;
    let active = headings[0].id;
    for (const h of headings) {
      if (h.getBoundingClientRect().top <= THRESHOLD) active = h.id;
      else break;
    }
    render(active);
  };
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(update);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update(); // prime with the top section
}

function boot(): void {
  initPicker();
  initExplanations();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
