/**
 * live-session.ts — client for the LIVE Session reader (/studio/<slug>/live).
 *
 * Read-only (never writes book state). The reader shows the WHOLE book as one
 * continuously-scrolling document: every chapter is a stacked, numbered sheet and a
 * single (window) scrollbar governs the view. Concerns:
 *   1. Chapters — split the book into per-chapter sheets and number them.
 *   2. Reading toolbar — font / size / paper theme, persisted to localStorage.
 *   3. Table of contents — jump (scroll) to any chapter.
 *   4. Scroll-spy — as a chapter scrolls into the reading zone it becomes "active":
 *      the sticky companion panel swaps to that chapter's Companion notes (REQ-SC-011)
 *      and the chapter sheet is highlighted, so panel/page stays visually linked.
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
  /** Verbatim chapter passage this note explains (highlighted + drives the spy). */
  quote: string;
  source: string;
}
interface LiveSection {
  id: string;
  title: string;
  notes: LiveNote[];
}
interface Chapter {
  id: string;
  title: string;
  el: HTMLElement;
}

const SIZE_MIN = 16;
const SIZE_MAX = 30;
const SIZE_DEFAULT = 20;
const FONT_DEFAULT = "serif";
const PAPER_DEFAULT = "light";
const NAV_OFFSET = 52; // height of the sticky top-nav

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
  const el = document.getElementById("lsv-explain-data");
  if (!el?.textContent) return null;
  try {
    return JSON.parse(el.textContent);
  } catch {
    return null;
  }
}

const norm = (s: string) => s.replace(/\s+/g, " ").trim();
const clamp = (n: number, lo: number, hi: number) =>
  Math.min(Math.max(lo, n), hi);
const prefersReducedMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function boot(): void {
  const rootEl = document.querySelector<HTMLElement>(".lsv");
  const vpEl = document.getElementById("lsv-viewport");
  const pgEl = document.getElementById("lsv-read");
  if (!rootEl || !vpEl || !pgEl) {
    initPicker(); // empty-state / picker-only page still gets the picker
    return;
  }
  const root: HTMLElement = rootEl;
  const pages: HTMLElement = pgEl;
  const data = readData();

  // The global snapshot footer is dashboard chrome, irrelevant on an immersive
  // reader — hide it (runtime, reversible on navigation) to reclaim reading room.
  const foot = document.querySelector<HTMLElement>(".foot");
  if (foot) foot.style.display = "none";

  const titleEl = document.getElementById("lsv-explain-title");
  const bodyEl = document.getElementById("lsv-explain-body");
  const anyNotes = !!data?.sections.some((s) => s.notes.length > 0);

  // ---- split the flat book HTML into per-chapter sheets -------------------
  function splitChapters(): Chapter[] {
    const kids = Array.from(pages.childNodes);
    const secs: HTMLElement[] = [];
    const preamble: Node[] = [];
    let cur: HTMLElement | null = null;
    for (const node of kids) {
      const el = node as HTMLElement;
      const isHeading =
        node.nodeType === 1 && /^H[12]$/.test(el.tagName) && !!el.id;
      if (isHeading) {
        cur = document.createElement("section");
        cur.className = "lsv-chapter";
        cur.dataset.id = el.id;
        if (secs.length === 0 && preamble.length)
          preamble.forEach((n) => cur!.appendChild(n));
        secs.push(cur);
        cur.appendChild(node);
      } else if (cur) {
        cur.appendChild(node);
      } else {
        preamble.push(node); // content before the first heading (rare)
      }
    }
    pages.textContent = "";
    if (secs.length === 0) {
      const only = document.createElement("section");
      only.className = "lsv-chapter";
      only.dataset.id = "__all__";
      preamble.forEach((n) => only.appendChild(n));
      secs.push(only);
    }
    secs.forEach((s, i) => {
      const num = document.createElement("span");
      num.className = "lsv-page-num";
      num.setAttribute("aria-hidden", "true");
      num.textContent = String(i + 1);
      s.appendChild(num);
      pages.appendChild(s);
    });
    return secs.map((s) => ({
      id: s.dataset.id ?? "",
      title: s.querySelector("h1, h2, h3")?.textContent?.trim() ?? "",
      el: s,
    }));
  }

  // ---- one note entry per companion note, with its passage span (if found) --
  interface NoteEntry {
    chapterId: string;
    chapterTitle: string;
    key: string;
    note: LiveNote;
    span: HTMLElement | null;
  }

  // Wrap a note's VERBATIM quote in a highlight span so its passage can be lit.
  // Returns the span, or null if the quote isn't a clean single-text-node match.
  function wrapQuote(needle: string, key: string): HTMLElement | null {
    const target = norm(needle);
    if (target.length < 4) return null;
    const low = target.toLowerCase();
    const probe = low.slice(0, 16);
    const walker = document.createTreeWalker(pages, NodeFilter.SHOW_TEXT);
    let node: Node | null;
    while ((node = walker.nextNode())) {
      const text = node.textContent ?? "";
      if (norm(text).toLowerCase().indexOf(low) < 0) continue; // whole quote lives in this node
      const raw = text.toLowerCase().indexOf(probe);
      if (raw < 0) continue;
      const end = Math.min(text.length, raw + target.length);
      const range = document.createRange();
      try {
        range.setStart(node, raw);
        range.setEnd(node, end);
      } catch {
        return null;
      }
      const mark = document.createElement("span");
      mark.className = "lsv-hl";
      mark.dataset.note = key;
      try {
        range.surroundContents(mark);
        return mark;
      } catch {
        return null; // passage straddles inline markup — can't wrap cleanly
      }
    }
    return null;
  }

  const chapters = splitChapters();

  // Build note entries per chapter, wrapping each note's quote into a span.
  const notesByChapter = new Map<string, NoteEntry[]>();
  if (data) {
    for (const section of data.sections) {
      const entries: NoteEntry[] = section.notes.map((note, i) => {
        const key = `${section.id}::${i}`;
        return {
          chapterId: section.id,
          chapterTitle: section.title,
          key,
          note,
          span: note.quote ? wrapQuote(note.quote, key) : null,
        };
      });
      notesByChapter.set(section.id, entries);
    }
  }

  let currentChapter = -1;
  let currentNoteKey = "__initial__"; // sentinel so the first render always runs

  // Mark the in-view chapter (rail + TOC), independent of which note shows.
  function setActiveChapter(idx: number): void {
    if (idx === currentChapter) return;
    currentChapter = idx;
    chapters.forEach((c, k) => c.el.classList.toggle("is-active", k === idx));
    const id = chapters[idx]?.id ?? "";
    document.querySelectorAll<HTMLElement>(".lsv-toc-link").forEach((el) => {
      el.classList.toggle("is-active", el.dataset.target === id);
    });
  }

  // Exactly ONE passage is ever lit — the one whose card is showing.
  function highlightOnly(span: HTMLElement | null): void {
    pages.querySelectorAll<HTMLElement>(".lsv-hl.is-active").forEach((el) => {
      if (el !== span) el.classList.remove("is-active");
    });
    if (span) span.classList.add("is-active");
  }

  // Render the single companion card for the active note (or an empty state).
  function renderCard(entry: NoteEntry | null, chapterTitle: string): void {
    if (!bodyEl || !titleEl) return;
    titleEl.textContent = chapterTitle || "Explanations";
    bodyEl.textContent = "";
    if (!entry) {
      const p = document.createElement("p");
      p.className = "lsv-explain-empty";
      p.textContent = anyNotes
        ? "No companion note for this passage yet."
        : "No companion notes have been written for this book yet.";
      bodyEl.appendChild(p);
      return;
    }
    const note = entry.note;
    const card = document.createElement("article");
    card.className = "lsv-note";
    card.dataset.note = entry.key;

    const head = document.createElement("div");
    head.className = "lsv-note-head";
    const kind = document.createElement("span");
    kind.className = "lsv-note-kind";
    kind.textContent = note.kind || "note";
    head.appendChild(kind);
    if (note.source) {
      const src = document.createElement("span");
      src.className = "lsv-note-source";
      src.textContent = note.source;
      head.appendChild(src);
    }
    card.appendChild(head);

    if (note.anchor) {
      const label = document.createElement("p");
      label.className = "lsv-note-anchor";
      label.textContent = note.anchor;
      card.appendChild(label);
    }
    const body = document.createElement("p");
    body.className = "lsv-note-body";
    body.textContent = note.body;
    card.appendChild(body);
    bodyEl.appendChild(card);
  }

  // Swap the shown card + lit passage only when the active note changes.
  function setActiveNote(entry: NoteEntry | null, chapterTitle: string): void {
    highlightOnly(entry?.span ?? null);
    const key = entry?.key ?? "";
    if (key === currentNoteKey) {
      if (titleEl) titleEl.textContent = chapterTitle || "Explanations";
      return;
    }
    currentNoteKey = key;
    renderCard(entry, chapterTitle);
  }

  // ---- scroll-spy: pick the in-view chapter, then the passage you're reading
  function updateActive(): void {
    if (chapters.length === 0) return;
    const focusY = NAV_OFFSET + Math.min(160, window.innerHeight * 0.28);
    let chIdx = 0;
    for (let k = 0; k < chapters.length; k++) {
      if (chapters[k].el.getBoundingClientRect().top <= focusY) chIdx = k;
      else break;
    }
    setActiveChapter(chIdx);

    // Within that chapter, the active note is the last one whose passage has
    // scrolled past the focus line (i.e. the passage you've most recently reached).
    const entries = notesByChapter.get(chapters[chIdx].id) ?? [];
    const withSpans = entries.filter((e) => e.span);
    let active: NoteEntry | null = null;
    if (withSpans.length) {
      withSpans.sort(
        (a, b) =>
          a.span!.getBoundingClientRect().top -
          b.span!.getBoundingClientRect().top,
      );
      active = withSpans[0];
      for (const e of withSpans) {
        if (e.span!.getBoundingClientRect().top <= focusY) active = e;
        else break;
      }
    } else if (entries.length) {
      active = entries[0]; // chapter has notes, but none matched a passage
    }
    setActiveNote(active, chapters[chIdx].title);
  }

  function scrollToChapter(i: number): void {
    const idx = clamp(i, 0, chapters.length - 1);
    chapters[idx].el.scrollIntoView({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
      block: "start",
    });
  }

  // ---- reading toolbar (font / size / paper) ------------------------------
  function initToolbar(): void {
    const applyFont = (id: string) => {
      root.dataset.font = id;
      store.set("lsv-reader-font", id);
    };
    const applySize = (px: number) => {
      const val = clamp(px, SIZE_MIN, SIZE_MAX);
      root.style.setProperty("--lsv-size", `${val}px`);
      const out = document.getElementById("lsv-size-val");
      if (out) out.textContent = String(val);
      store.set("lsv-reader-size", String(val));
      return val;
    };
    const applyPaper = (id: string) => {
      root.dataset.paper = id;
      store.set("lsv-reader-paper", id);
      document.querySelectorAll<HTMLElement>(".lsv-paper-btn").forEach((b) => {
        b.setAttribute("aria-pressed", String(b.dataset.paper === id));
      });
    };

    const font = store.get("lsv-reader-font", FONT_DEFAULT);
    applyFont(font);
    const fontSel = document.getElementById(
      "lsv-font",
    ) as HTMLSelectElement | null;
    if (fontSel) {
      fontSel.value = font;
      fontSel.addEventListener("change", () => applyFont(fontSel.value));
    }

    let size =
      Number(store.get("lsv-reader-size", String(SIZE_DEFAULT))) ||
      SIZE_DEFAULT;
    size = applySize(size);
    document.getElementById("lsv-size-down")?.addEventListener("click", () => {
      size = applySize(size - 1);
      updateActive();
    });
    document.getElementById("lsv-size-up")?.addEventListener("click", () => {
      size = applySize(size + 1);
      updateActive();
    });

    applyPaper(store.get("lsv-reader-paper", PAPER_DEFAULT));
    document.querySelectorAll<HTMLElement>(".lsv-paper-btn").forEach((btn) => {
      btn.addEventListener("click", () =>
        applyPaper(btn.dataset.paper ?? PAPER_DEFAULT),
      );
    });
  }

  // ---- table of contents --------------------------------------------------
  function initToc(): void {
    const toc = document.getElementById("lsv-toc");
    const scrim = document.getElementById("lsv-toc-scrim");
    const openBtn = document.getElementById("lsv-toc-btn");
    const closeBtn = document.getElementById("lsv-toc-close");
    if (!toc || !scrim || !openBtn) return;
    const setOpen = (open: boolean) => {
      toc.classList.toggle("is-open", open);
      scrim.classList.toggle("is-open", open);
      openBtn.setAttribute("aria-expanded", String(open));
      if (open) toc.querySelector<HTMLElement>(".lsv-toc-link")?.focus();
      else openBtn.focus(); // return focus to the trigger on close (mirrors the picker)
    };
    openBtn.addEventListener("click", () =>
      setOpen(!toc.classList.contains("is-open")),
    );
    closeBtn?.addEventListener("click", () => setOpen(false));
    scrim.addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && toc.classList.contains("is-open"))
        setOpen(false);
    });
    toc.querySelectorAll<HTMLElement>(".lsv-toc-link").forEach((link) => {
      link.addEventListener("click", () => {
        const idx = chapters.findIndex((c) => c.id === link.dataset.target);
        if (idx >= 0) scrollToChapter(idx);
        setOpen(false);
      });
    });
  }

  // ---- keyboard: Arrow keys jump chapter-to-chapter ------------------------
  function initKeyboard(): void {
    document.addEventListener("keydown", (e) => {
      if (isTypingTarget(e.target)) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        scrollToChapter(currentChapter + 1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        scrollToChapter(currentChapter - 1);
      }
    });
  }

  // ---- go -----------------------------------------------------------------
  initToolbar();
  initToc();
  initKeyboard();
  initPicker();
  updateActive(); // set the first active chapter + its notes

  // Update the active chapter directly on scroll. For a handful of chapters the
  // getBoundingClientRect reads are cheap, and a direct call can't latch the way an
  // rAF-throttled one can if a frame is ever dropped (hidden/throttled tab).
  window.addEventListener("scroll", updateActive, { passive: true });
  window.addEventListener("resize", updateActive);
  if (document.fonts && document.fonts.ready)
    document.fonts.ready.then(() => updateActive());
}

// ---- book picker (shared; also used on empty-state) -----------------------
function initPicker(): void {
  const picker = document.querySelector<HTMLElement>(".lsv-picker");
  const trigger = document.getElementById("lsv-picker-trigger");
  const panel = document.getElementById("lsv-picker-panel");
  if (!picker || !trigger || !panel) return;
  const setOpen = (open: boolean) => {
    picker.dataset.open = String(open);
    trigger.setAttribute("aria-expanded", String(open));
    panel.hidden = !open;
  };
  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    setOpen(picker.dataset.open !== "true");
  });
  document.addEventListener("click", (e) => {
    if (!picker.contains(e.target as Node)) setOpen(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && picker.dataset.open === "true") {
      setOpen(false);
      trigger.focus();
    }
  });
  const chips = panel.querySelectorAll<HTMLElement>(".lsv-filter-chip");
  const groups = panel.querySelectorAll<HTMLElement>(".lsv-picker-group");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const bucket = chip.dataset.bucket ?? "all";
      chips.forEach((c) => c.classList.toggle("is-active", c === chip));
      groups.forEach((g) => {
        g.hidden = bucket !== "all" && g.dataset.bucket !== bucket;
      });
    });
  });
}

// ---- helpers --------------------------------------------------------------
function isTypingTarget(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    el.isContentEditable
  );
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
