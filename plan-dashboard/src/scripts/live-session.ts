/**
 * live-session.ts — client for the LIVE Session e-reader (/studio/<slug>/live).
 *
 * Read-only (never writes book state). Concerns:
 *   1. Paginator — flow the book into screen-sized pages (CSS multi-column) and
 *      turn one page at a time with a slide animation (buttons / keys / swipe).
 *   2. Reading toolbar — font / size / paper theme, persisted to localStorage.
 *   3. Table of contents — jump to any chapter's page.
 *   4. Explanation panel — follows the pages; shows the current section's Companion
 *      notes (studio-composer REQ-SC-011).
 *   5. Anchor highlighting — a note's quoted passage is marked in the text when it
 *      appears verbatim, two-way-linked with its note card.
 *   6. Book picker — bucket filter + navigation.
 *
 * All logic lives here (external module); the .astro page carries only markup, a
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

const GAP = 64; // px between page columns (hidden; only one page shows)
const SIZE_MIN = 16;
const SIZE_MAX = 30;
const SIZE_DEFAULT = 20;
const FONT_DEFAULT = 'serif';
const PAPER_DEFAULT = 'light';

const store = {
  get(key: string, fallback: string): string {
    try {
      return localStorage.getItem(key) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set(key: string, val: string): void {
    try {
      localStorage.setItem(key, val);
    } catch {
      /* best-effort */
    }
  },
};

function readData(): { slug: string; sections: LiveSection[] } | null {
  const el = document.getElementById('lsv-explain-data');
  if (!el?.textContent) return null;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return null;
  }
}

const norm = (s: string) => s.replace(/\s+/g, ' ').trim();

function boot(): void {
  const rootEl = document.querySelector<HTMLElement>('.lsv');
  const vpEl = document.getElementById('lsv-viewport');
  const pgEl = document.getElementById('lsv-read');
  if (!rootEl || !vpEl || !pgEl) {
    initPickerOnly(); // empty-state or picker-only page still gets the picker
    return;
  }
  // Narrowed non-null aliases so the nested (hoisted) helpers below type-check.
  const root: HTMLElement = rootEl;
  const viewport: HTMLElement = vpEl;
  const pages: HTMLElement = pgEl;
  const data = readData();

  // ---- paginator state ----------------------------------------------------
  let pageStep = 1;
  let pageCount = 1;
  let current = 0;
  let headingPage = new Map<string, number>(); // section id -> page index
  let sectionOrder: { id: string; page: number }[] = [];
  let activeId = '';

  const pageInd = document.getElementById('lsv-pageind');
  const prevBtn = document.getElementById('lsv-prev') as HTMLButtonElement | null;
  const nextBtn = document.getElementById('lsv-next') as HTMLButtonElement | null;
  const titleEl = document.getElementById('lsv-explain-title');
  const bodyEl = document.getElementById('lsv-explain-body');
  const anyNotes = !!data?.sections.some((s) => s.notes.length > 0);

  // ---- anchor highlighting (wrap verbatim quoted passages once) ------------
  function wrapAnchors(): void {
    if (!data) return;
    for (const section of data.sections) {
      section.notes.forEach((note, i) => {
        const needle = norm(note.anchor);
        if (needle.length < 6) return;
        const key = `${section.id}::${i}`;
        wrapFirst(needle, key);
      });
    }
  }
  function wrapFirst(needle: string, key: string): void {
    const walker = document.createTreeWalker(pages, NodeFilter.SHOW_TEXT);
    const low = needle.toLowerCase();
    let node: Node | null;
    while ((node = walker.nextNode())) {
      const text = node.textContent ?? '';
      const idx = norm(text).toLowerCase().indexOf(low);
      if (idx < 0) continue;
      // Map normalized index back to the raw text (best-effort: exact substring).
      const raw = text.toLowerCase().indexOf(low.slice(0, 12));
      if (raw < 0) continue;
      const end = Math.min(text.length, raw + needle.length);
      const range = document.createRange();
      try {
        range.setStart(node, raw);
        range.setEnd(node, end);
      } catch {
        return;
      }
      const mark = document.createElement('span');
      mark.className = 'lsv-hl';
      mark.dataset.note = key;
      try {
        range.surroundContents(mark);
      } catch {
        /* spans multiple nodes — skip (best-effort) */
      }
      return;
    }
  }

  // ---- pagination ---------------------------------------------------------
  function fitViewportHeight(): void {
    const top = viewport.getBoundingClientRect().top;
    const bar = document.querySelector<HTMLElement>('.lsv-pagebar');
    const barH = bar ? bar.offsetHeight + 8 : 34;
    const avail = window.innerHeight - top - barH - 8;
    viewport.style.height = `${Math.max(360, avail)}px`;
  }

  function paginate(): void {
    fitViewportHeight();
    const cs = getComputedStyle(viewport);
    const padL = parseFloat(cs.paddingLeft) || 0;
    const padR = parseFloat(cs.paddingRight) || 0;
    const padT = parseFloat(cs.paddingTop) || 0;
    const padB = parseFloat(cs.paddingBottom) || 0;
    const pageW = Math.max(200, viewport.clientWidth - padL - padR);
    const pageH = Math.max(200, viewport.clientHeight - padT - padB);

    // Measure at translate 0 with NO transition, else getBoundingClientRect would
    // read a mid-animation position and mis-map headings/highlights to pages.
    pages.classList.add('is-instant');
    pages.style.transform = 'none';
    pages.style.height = `${pageH}px`;
    pages.style.columnWidth = `${pageW}px`;
    pages.style.columnGap = `${GAP}px`;
    pageStep = pageW + GAP;

    // Force reflow, then measure.
    void pages.offsetWidth;
    pageCount = Math.max(1, Math.round((pages.scrollWidth + GAP) / pageStep));

    // Map each section heading + each highlight to its page.
    const pagesLeft = pages.getBoundingClientRect().left;
    headingPage = new Map();
    sectionOrder = [];
    if (data) {
      for (const s of data.sections) {
        const h = pages.querySelector<HTMLElement>(`#${cssEscape(s.id)}`);
        if (!h) continue;
        const p = clampPage(Math.round((h.getBoundingClientRect().left - pagesLeft) / pageStep));
        headingPage.set(s.id, p);
        sectionOrder.push({ id: s.id, page: p });
      }
      sectionOrder.sort((a, b) => a.page - b.page);
    }
    pages.querySelectorAll<HTMLElement>('.lsv-hl').forEach((hl) => {
      const p = clampPage(Math.round((hl.getBoundingClientRect().left - pagesLeft) / pageStep));
      hl.dataset.page = String(p);
    });

    goTo(clampPage(current), true);
  }

  const clampPage = (p: number) => Math.min(Math.max(0, p), Math.max(0, pageCount - 1));

  function goTo(i: number, instant = false): void {
    current = clampPage(i);
    if (instant) pages.classList.add('is-instant');
    pages.style.transform = `translateX(${-(current * pageStep)}px)`;
    if (instant) void pages.offsetWidth, pages.classList.remove('is-instant');
    if (pageInd) pageInd.textContent = `Page ${current + 1} of ${pageCount}`;
    if (prevBtn) prevBtn.disabled = current === 0;
    if (nextBtn) nextBtn.disabled = current >= pageCount - 1;
    updateActiveSection();
  }
  const next = () => goTo(current + 1);
  const prev = () => goTo(current - 1);

  // ---- explanation panel (follows the active section) ---------------------
  function updateActiveSection(): void {
    let active = sectionOrder[0]?.id ?? '';
    for (const s of sectionOrder) {
      if (s.page <= current) active = s.id;
      else break;
    }
    if (active === activeId) {
      markActiveHighlights();
      return;
    }
    activeId = active;
    renderNotes(active);
    markActiveHighlights();
    document.querySelectorAll('.lsv-toc-link').forEach((el) => {
      el.classList.toggle('is-active', (el as HTMLElement).dataset.target === active);
    });
  }

  function renderNotes(id: string): void {
    if (!bodyEl || !titleEl || !data) return;
    const section = data.sections.find((s) => s.id === id);
    titleEl.textContent = section ? section.title : 'Explanations';
    bodyEl.textContent = '';
    if (!section || section.notes.length === 0) {
      const p = document.createElement('p');
      p.className = 'lsv-explain-empty';
      p.textContent = anyNotes
        ? 'No companion notes for this section.'
        : 'No companion notes have been written for this book yet.';
      bodyEl.appendChild(p);
      return;
    }
    section.notes.forEach((note, i) => {
      const key = `${id}::${i}`;
      const card = document.createElement('article');
      card.className = 'lsv-note';
      card.dataset.note = key;
      const hasHl = !!pages.querySelector(`.lsv-hl[data-note="${cssAttr(key)}"]`);
      if (hasHl) {
        // Clickable note → keyboard-operable interactive control (REQ-048/049): it
        // performs an action (jump to the highlighted passage), so it must be
        // focusable and Enter/Space-activatable, not mouse-only.
        card.classList.add('has-anchor');
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.setAttribute('aria-label', 'Go to the highlighted passage for this note');
      }

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

      if (hasHl) {
        const activate = () => {
          const hl = pages.querySelector<HTMLElement>(`.lsv-hl[data-note="${cssAttr(key)}"]`);
          if (hl?.dataset.page) {
            goTo(Number(hl.dataset.page));
            setHighlightActive(key, true);
            window.setTimeout(() => setHighlightActive(key, false), 1600);
          }
        };
        // Preview the highlight on both pointer hover and keyboard focus.
        card.addEventListener('mouseenter', () => setHighlightActive(key, true));
        card.addEventListener('mouseleave', () => setHighlightActive(key, false));
        card.addEventListener('focus', () => setHighlightActive(key, true));
        card.addEventListener('blur', () => setHighlightActive(key, false));
        card.addEventListener('click', activate);
        card.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            activate();
          }
        });
      }
      bodyEl.appendChild(card);
    });
  }

  function setHighlightActive(key: string, on: boolean): void {
    pages.querySelectorAll<HTMLElement>(`.lsv-hl[data-note="${cssAttr(key)}"]`).forEach((hl) => {
      hl.classList.toggle('is-active', on);
    });
  }
  function markActiveHighlights(): void {
    pages.querySelectorAll<HTMLElement>('.lsv-hl').forEach((hl) => {
      hl.classList.toggle('on-page', Number(hl.dataset.page) === current);
    });
  }

  // ---- reading toolbar (font / size / paper) ------------------------------
  function initToolbar(): void {
    const applyFont = (id: string) => {
      root.dataset.font = id;
      store.set('lsv-reader-font', id);
    };
    const applySize = (px: number) => {
      const val = Math.min(SIZE_MAX, Math.max(SIZE_MIN, px));
      root.style.setProperty('--lsv-size', `${val}px`);
      const out = document.getElementById('lsv-size-val');
      if (out) out.textContent = String(val);
      store.set('lsv-reader-size', String(val));
      return val;
    };
    const applyPaper = (id: string) => {
      root.dataset.paper = id;
      store.set('lsv-reader-paper', id);
      document.querySelectorAll<HTMLElement>('.lsv-paper-btn').forEach((b) => {
        b.setAttribute('aria-pressed', String(b.dataset.paper === id));
      });
    };

    const font = store.get('lsv-reader-font', FONT_DEFAULT);
    applyFont(font);
    const fontSel = document.getElementById('lsv-font') as HTMLSelectElement | null;
    if (fontSel) {
      fontSel.value = font;
      fontSel.addEventListener('change', () => {
        applyFont(fontSel.value);
        paginate();
      });
    }

    let size = Number(store.get('lsv-reader-size', String(SIZE_DEFAULT))) || SIZE_DEFAULT;
    size = applySize(size);
    document.getElementById('lsv-size-down')?.addEventListener('click', () => {
      size = applySize(size - 1);
      paginate();
    });
    document.getElementById('lsv-size-up')?.addEventListener('click', () => {
      size = applySize(size + 1);
      paginate();
    });

    applyPaper(store.get('lsv-reader-paper', PAPER_DEFAULT));
    document.querySelectorAll<HTMLElement>('.lsv-paper-btn').forEach((btn) => {
      btn.addEventListener('click', () => applyPaper(btn.dataset.paper ?? PAPER_DEFAULT));
    });
  }

  // ---- table of contents --------------------------------------------------
  function initToc(): void {
    const toc = document.getElementById('lsv-toc');
    const scrim = document.getElementById('lsv-toc-scrim');
    const openBtn = document.getElementById('lsv-toc-btn');
    const closeBtn = document.getElementById('lsv-toc-close');
    if (!toc || !scrim || !openBtn) return;
    const setOpen = (open: boolean) => {
      // CSS animates via .is-open (transform + visibility); no hidden toggling so
      // the slide transition runs and closed links stay out of the tab order.
      toc.classList.toggle('is-open', open);
      scrim.classList.toggle('is-open', open);
      openBtn.setAttribute('aria-expanded', String(open));
      if (open) toc.querySelector<HTMLElement>('.lsv-toc-link')?.focus();
      else openBtn.focus(); // return focus to the trigger on close (mirrors the picker)
    };
    openBtn.addEventListener('click', () => setOpen(!toc.classList.contains('is-open')));
    closeBtn?.addEventListener('click', () => setOpen(false));
    scrim.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && toc.classList.contains('is-open')) setOpen(false);
    });
    toc.querySelectorAll<HTMLElement>('.lsv-toc-link').forEach((link) => {
      link.addEventListener('click', () => {
        const target = link.dataset.target ?? '';
        if (headingPage.has(target)) goTo(headingPage.get(target)!);
        setOpen(false);
      });
    });
  }

  // ---- input: keyboard + swipe --------------------------------------------
  function initInput(): void {
    prevBtn?.addEventListener('click', prev);
    nextBtn?.addEventListener('click', next);
    document.addEventListener('keydown', (e) => {
      if (isTypingTarget(e.target)) return;
      if (e.key === 'ArrowRight' || e.key === 'PageDown') {
        e.preventDefault();
        next();
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        prev();
      }
    });
    let startX = 0;
    let startY = 0;
    viewport.addEventListener('touchstart', (e) => {
      startX = e.changedTouches[0].clientX;
      startY = e.changedTouches[0].clientY;
    }, { passive: true });
    viewport.addEventListener('touchend', (e) => {
      const dx = e.changedTouches[0].clientX - startX;
      const dy = e.changedTouches[0].clientY - startY;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy)) {
        if (dx < 0) next();
        else prev();
      }
    }, { passive: true });
  }

  // ---- re-pagination + reveal ---------------------------------------------
  let revealed = false;
  const reveal = () => {
    if (!revealed && viewport.clientWidth > 120) {
      pages.classList.add('is-ready');
      revealed = true;
    }
  };
  function repaginate(): void {
    const keep = activeId;
    paginate();
    if (keep && headingPage.has(keep)) goTo(headingPage.get(keep)!, true);
    reveal();
  }

  initToolbar();
  wrapAnchors();
  initToc();
  initInput();
  initPicker();

  // Re-paginate whenever the reader's WIDTH changes — the reliable signal for
  // "layout is settled" (initial paint, font metrics, window resize). Observe
  // .lsv-reader (NOT the viewport, whose height WE set) and guard on width so a
  // set-height never re-triggers the observer (no feedback loop).
  const readerEl = document.querySelector<HTMLElement>('.lsv-reader');
  let lastW = 0;
  let roTimer = 0;
  if ('ResizeObserver' in window && readerEl) {
    const ro = new ResizeObserver((entries) => {
      const w = Math.round(entries[0].contentRect.width);
      if (w === lastW) return; // ignore height-only changes
      lastW = w;
      if (!revealed) {
        paginate();
        reveal();
      } else {
        window.clearTimeout(roTimer);
        roTimer = window.setTimeout(repaginate, 150);
      }
    });
    ro.observe(readerEl);
  } else {
    paginate();
    reveal();
  }

  // Fonts change text metrics (column fill) without changing the reader WIDTH, so
  // the observer won't fire — re-paginate once fonts are ready to be exact.
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(repaginate);
  // Window resize also changes height (not always width) — refit either way.
  let hTimer = 0;
  window.addEventListener('resize', () => {
    window.clearTimeout(hTimer);
    hTimer = window.setTimeout(repaginate, 160);
  });
}

// ---- book picker (shared; also used on empty-state) -----------------------
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
function initPickerOnly(): void {
  initPicker();
}

// ---- helpers --------------------------------------------------------------
function isTypingTarget(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
}
// CSS.escape for querySelector by id; fall back for older engines.
function cssEscape(id: string): string {
  const c = (window as unknown as { CSS?: { escape?: (s: string) => string } }).CSS;
  return c?.escape ? c.escape(id) : id.replace(/[^a-zA-Z0-9_-]/g, '\\$&');
}
// Escape a value for use inside an attribute selector [data-note="..."].
function cssAttr(v: string): string {
  return v.replace(/["\\]/g, '\\$&');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
