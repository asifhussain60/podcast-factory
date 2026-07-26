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
import { markPassages } from "../lib/reader/companion/passage-match";
import { renderExplanationCard } from "../lib/reader/companion/explanation-card";

interface LiveNote {
  kind: string;
  body: string;
  anchor: string;
  /** Verbatim chapter passage this note explains (highlighted + drives the spy). */
  quote: string;
  etymology: string[];
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

  // ---- one note entry per companion note, with its passage spans (if found) --
  interface NoteEntry {
    chapterId: string;
    chapterTitle: string;
    key: string;
    note: LiveNote;
    /** Every span the passage was wrapped in — one per text node it crosses.
     *  Empty when the passage isn't in the chapter (a note about the chapter as
     *  a whole, or a quote that no longer matches the composed text). */
    spans: HTMLElement[];
  }

  const chapters = splitChapters();

  // Build note entries per chapter and tint each note's passage. The search is
  // scoped to the note's OWN chapter sheet — a sentence repeated in two chapters
  // must light in the one the note belongs to. The matcher itself is the shared
  // one (passage-match.ts), which the Composer uses over the same prose, so the
  // two surfaces can never disagree about where a note is attached.
  const notesByChapter = new Map<string, NoteEntry[]>();
  if (data) {
    for (const section of data.sections) {
      const scope =
        chapters.find((c) => c.id === section.id)?.el ?? (pages as HTMLElement);
      const keyed = section.notes.map((note, i) => ({
        key: `${section.id}::${i}`,
        note,
      }));
      const marked = markPassages(
        scope,
        keyed.map((k) => ({ id: k.key, quote: k.note.quote })),
        "lsv-hl",
      );
      notesByChapter.set(
        section.id,
        keyed.map(({ key, note }) => ({
          chapterId: section.id,
          chapterTitle: section.title,
          key,
          note,
          spans: marked.get(key) ?? [],
        })),
      );
    }
  }

  /**
   * ONE contract with the Composer: a chapter's cards are the notes whose passage
   * is FOUND in that chapter's text — no more, no less. A card with no passage
   * could not be reached by reading and could not be matched to a highlight, so
   * neither surface shows one, and the two surfaces therefore show the same set.
   */
  function anchoredIn(chapterId: string): NoteEntry[] {
    const entries = (notesByChapter.get(chapterId) ?? []).filter(
      (e) => e.spans.length,
    );
    // Reading order, not authoring order: the list runs down the chapter the way
    // you will meet the passages. Taken from the MARKS in document order — the
    // same rule the Composer uses — rather than by comparing spans pairwise,
    // because two notes can annotate the same sentence and their marks then nest
    // rather than follow one another.
    const chapterEl = chapters.find((c) => c.id === chapterId)?.el;
    const order = [
      ...new Set(
        [...(chapterEl?.querySelectorAll<HTMLElement>(".lsv-hl") ?? [])].map(
          (el) => el.dataset.note ?? "",
        ),
      ),
    ];
    return entries.sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
  }

  let currentChapter = -1;
  let currentNoteKey = "__initial__"; // sentinel so the first render always runs
  let listedChapter = "__none__"; // which chapter's cards are currently mounted

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

  // Exactly ONE passage is ever lit — the one whose card is showing. A passage
  // that crosses inline markup is several spans sharing one note key; they light
  // and go dark together, so the reader sees one continuous highlight.
  function highlightOnly(key: string | null): void {
    pages.querySelectorAll<HTMLElement>(".lsv-hl").forEach((el) => {
      el.classList.toggle("is-active", !!key && el.dataset.note === key);
    });
  }

  /**
   * Mount the chapter's cards — the SAME cards the Composer lists, built by the
   * same component, minus the edit and delete controls this surface must not have.
   * The list is the whole chapter, not just the passage you are on: you can look
   * ahead, look back, and expand anything. What the scroll does is decide which
   * card OPENS by itself as you reach its sentence.
   */
  function renderChapterCards(chapterId: string, chapterTitle: string): void {
    if (!bodyEl || !titleEl) return;
    titleEl.textContent = chapterTitle || "Explanations";
    bodyEl.textContent = "";
    const entries = anchoredIn(chapterId);
    if (!entries.length) {
      const p = document.createElement("p");
      p.className = "lsv-explain-empty";
      p.textContent = anyNotes
        ? "No companion notes for this chapter."
        : "No companion notes have been written for this book yet.";
      bodyEl.appendChild(p);
      return;
    }
    for (const entry of entries) {
      const note = entry.note;
      bodyEl.appendChild(
        renderExplanationCard(
          {
            id: entry.key,
            kind: note.kind || "note",
            body: note.body,
            anchor: note.anchor || note.quote,
            quote: note.quote,
            etymology: note.etymology,
            source: note.source
              ? { provider: "manual", label: note.source }
              : undefined,
          },
          {
            // Read-only: no onSave, no onRemove. Opening a card also lights its
            // passage, so the link runs both ways here too.
            onToggle: (id, open) => {
              if (open) highlightOnly(id);
            },
            onReveal: (id) => highlightOnly(id),
          },
        ).el,
      );
    }
  }

  /** Open one card (and only one), and light the passage it belongs to. */
  function openCard(key: string | null): void {
    bodyEl?.querySelectorAll<HTMLElement>(".xpl").forEach((card) => {
      const on = card.dataset.note === key;
      card.dataset.open = String(on);
      card
        .querySelector(".xpl-head")
        ?.setAttribute("aria-expanded", String(on));
      if (on) card.scrollIntoView({ block: "nearest" });
    });
  }

  // Follow the reading position: the chapter's cards stay listed, and the one for
  // the passage you have just reached opens itself and lights in the text.
  function setActiveNote(entry: NoteEntry | null, chapterTitle: string): void {
    const chapterId = chapters[currentChapter]?.id ?? "";
    if (chapterId !== listedChapter) {
      listedChapter = chapterId;
      currentNoteKey = "__initial__";
      renderChapterCards(chapterId, chapterTitle);
    } else if (titleEl) {
      titleEl.textContent = chapterTitle || "Explanations";
    }
    highlightOnly(entry?.spans.length ? entry.key : null);
    const key = entry?.key ?? "";
    if (key === currentNoteKey) return;
    currentNoteKey = key;
    openCard(key || null);
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
    // Already in reading order (anchoredIn sorts by document position), so the
    // last one whose passage has crossed the focus line is the one you are on.
    const ordered = anchoredIn(chapters[chIdx].id);
    // A multi-span passage is positioned by its FIRST span — where the sentence
    // starts is where the reader reaches it.
    const topOf = (e: NoteEntry) => e.spans[0].getBoundingClientRect().top;
    let active: NoteEntry | null = null;
    if (ordered.length) {
      active = ordered[0];
      for (const e of ordered) {
        if (topOf(e) <= focusY) active = e;
        else break;
      }
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
