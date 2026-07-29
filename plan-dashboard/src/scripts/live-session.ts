/**
 * live-session.ts — client for the LIVE Session reader (/studio/<slug>/live).
 *
 * Read-only (never writes book state). The reader shows ONE chapter at a time:
 * every chapter is a numbered sheet, but only the current one is in the DOM's
 * flow — the rest are hidden, so the window scrollbar governs reading WITHIN
 * that chapter, not the whole book. Concerns:
 *   1. Chapters — split the book into per-chapter sheets, number them, and give
 *      each a Prev/Next control (disabled at the book's first/last chapter).
 *   2. Reading toolbar — font / size / paper theme, persisted to localStorage.
 *   3. Table of contents — switch to any chapter via a dropdown chained right
 *      after the book picker (same popover pattern, shared open/close logic).
 *   4. Scroll-spy — WITHIN the current chapter, as its notes scroll past the
 *      reading zone the sticky companion panel swaps to follow (REQ-SC-011)
 *      and the passage lights in the text. Switching chapters (dropdown,
 *      Prev/Next, arrow keys) is a hard swap, not a scroll target.
 *   5. Anchor highlighting — a note's quoted passage is marked in the text when it
 *      appears verbatim, two-way-linked with its note card.
 *   6. Book picker — bucket filter + navigation.
 *
 * All logic lives here (external module); the .astro page carries only markup, a
 * JSON data island, and the one-line import (Cortex DoD: no inline script bodies).
 */
import { liveChapter } from "../lib/site-view-state";
import { markPassages } from "../lib/reader/companion/passage-match";
import { renderExplanationCard } from "../lib/reader/companion/explanation-card";

interface LiveNote {
  kind: string;
  body: string;
  anchor: string;
  /** Verbatim chapter passage this note explains (highlighted + drives the spy). */
  quote: string;
  etymology: string[];
  /** Verified corpus block per etymology row (SSR-computed; see live.astro). */
  morphology?: (
    import("../lib/reader/companion/types").EtymologyMorphology | null
  )[];
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
/** Width at which .lsv-viewport switches from ordinary page flow (window
 *  scroll governs it) to its own fixed, internally-scrolling box (see the
 *  "reading bar" section and the max-width:960px block in live-session.css).
 *  Mirrors that same breakpoint — the one place the two files have to agree. */
const NARROW = window.matchMedia("(max-width: 960px)");

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
  const viewport: HTMLElement = vpEl;
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
      s.appendChild(buildChapterNav(i, secs.length));
      pages.appendChild(s);
    });
    return secs.map((s) => ({
      id: s.dataset.id ?? "",
      title: s.querySelector("h1, h2, h3")?.textContent?.trim() ?? "",
      el: s,
    }));
  }

  /** Prev/Next row at the foot of a chapter sheet — the only in-page way to move
   *  chapter-to-chapter besides the Chapters dropdown and the arrow keys, since
   *  only the current chapter is ever in the DOM's flow. References `showChapter`,
   *  defined further down in this same closure — safe: both are hoisted function
   *  declarations in the same scope, and this only fires on a later click, by
   *  which time `showChapter` is long since defined. */
  function buildChapterNav(i: number, total: number): HTMLElement {
    const nav = document.createElement("div");
    nav.className = "lsv-chapter-nav";
    const build = (dir: "prev" | "next", disabled: boolean): HTMLElement => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `lsv-chapter-nav-btn lsv-chapter-nav-${dir}`;
      btn.disabled = disabled;
      const icon = document.createElement("i");
      icon.className = `fa-solid fa-chevron-${dir === "prev" ? "left" : "right"}`;
      icon.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.textContent = dir === "prev" ? "Previous chapter" : "Next chapter";
      btn.append(...(dir === "prev" ? [icon, label] : [label, icon]));
      btn.addEventListener("click", () =>
        showChapter(i + (dir === "prev" ? -1 : 1)),
      );
      return btn;
    };
    nav.append(build("prev", i === 0), build("next", i === total - 1));
    return nav;
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
      const active = el.dataset.target === id;
      el.classList.toggle("is-active", active);
      // The visual marker (accent border) isn't itself accessible — a
      // programmatic signal is what tells a screen-reader user "this is where
      // you are" while tabbing through the rail.
      if (active) el.setAttribute("aria-current", "true");
      else el.removeAttribute("aria-current");
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
      const wrap = document.createElement("div");
      wrap.className = "lsv-explain-empty";
      const icon = document.createElement("i");
      icon.className = "fa-solid fa-comment-dots";
      icon.setAttribute("aria-hidden", "true");
      const p = document.createElement("p");
      p.textContent = anyNotes
        ? "No companion notes for this chapter."
        : "No companion notes have been written for this book yet.";
      wrap.append(icon, p);
      bodyEl.appendChild(wrap);
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
            morphology: note.morphology,
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
      // "start", not "nearest": a card taller than the panel's own viewport
      // can never be FULLY on screen, so the edge that must win is the top —
      // the header that says which note this is. "nearest" could instead
      // align to the bottom when scrolling down past a tall card, leaving
      // that header scrolled out of view above the panel entirely.
      if (on) card.scrollIntoView({ block: "start" });
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

  // ---- scroll-spy: WITHIN the current chapter, which passage is being read ---
  // Only one chapter is ever in the DOM's flow (see showChapter), so there is no
  // "which chapter is in view" question left to answer here — just which note's
  // passage has scrolled past the reading zone.
  function updateActive(): void {
    if (chapters.length === 0 || currentChapter < 0) return;
    // The two widths scroll differently (see NARROW above), so "near the top
    // of the reading zone" means something different in each:
    //   - Narrow: .lsv-viewport is its own small, fixed-position box, so its
    //     live on-screen top is a stable reference regardless of how far the
    //     reader has scrolled within it.
    //   - Wide: .lsv-viewport IS the whole chapter in ordinary page flow — its
    //     "top" is wherever the chapter's first line sits, which drifts
    //     thousands of pixels above the window the moment you scroll into a
    //     long chapter. Using it here (as this used to) put focusY off-screen
    //     entirely past the first screen of any chapter, and every note after
    //     the first stopped lighting up. window.innerHeight is what's stable
    //     instead — the site's sticky nav (52px) is the only fixed point left
    //     once the bar itself scrolls away with the page.
    const focusY = NARROW.matches
      ? viewport.getBoundingClientRect().top +
        Math.min(160, viewport.clientHeight * 0.28)
      : 52 + Math.min(160, window.innerHeight * 0.28);
    // Already in reading order (anchoredIn sorts by document position), so the
    // last one whose passage has crossed the focus line is the one you are on.
    const ordered = anchoredIn(chapters[currentChapter].id);
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
      // The focus-line pass above only ever ADVANCES to a later note — it
      // never notices that the passage it landed on has since scrolled clean
      // off the screen (above OR below), which happens whenever a chapter
      // goes a long stretch after its last note before the next one. A card
      // pinned open for a passage you can no longer see is worse than no
      // card at all, so drop back to none rather than leave it stranded.
      if (active) {
        const r = active.spans[0].getBoundingClientRect();
        if (r.bottom <= 0 || r.top >= window.innerHeight) active = null;
      }
    }
    setActiveNote(active, chapters[currentChapter].title);
  }

  /** Hard-swap to another chapter — the Chapters dropdown, Prev/Next, and the
   *  arrow keys all funnel through this. Scrolls the new chapter's own top
   *  into view (its scroll-margin-top clears the site's sticky nav — the bar
   *  itself is ordinary flow now and scrolls with everything else), remembers
   *  the choice per book, updates the dropdown trigger to show the new current
   *  chapter (the way a real select displays its value), and lets
   *  `updateActive` pick up whichever note (if any) already sits at the top. */
  function showChapter(i: number): void {
    const idx = clamp(i, 0, chapters.length - 1);
    setActiveChapter(idx);
    chapters[idx].el.scrollIntoView({ block: "start", behavior: "instant" });
    if (data?.slug) liveChapter.write(chapters[idx].id, data.slug);
    const trigLabel = document.getElementById("lsv-toc-trigger-text");
    if (trigLabel) {
      // Reuse the SSR-rendered num/label already sitting in the matching TOC
      // row rather than reformatting chapters[idx].title ourselves — one
      // source for that split, not two that could drift apart. The two spans
      // are read separately (not link.textContent) because the "N. " gap
      // between them is CSS grid spacing, not a text character — textContent
      // would run the number straight into the title with no separator.
      const link = [
        ...document.querySelectorAll<HTMLElement>(".lsv-toc-link"),
      ].find((l) => l.dataset.target === chapters[idx].id);
      const num = link?.querySelector(".lsv-toc-num")?.textContent?.trim();
      const text = link?.querySelector(".lsv-toc-text")?.textContent?.trim();
      trigLabel.textContent = text
        ? `${num ? num + ". " : ""}${text}`
        : chapters[idx].title;
    }
    updateActive();
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

  // ---- table of contents (dropdown, chained after the book picker) --------
  function initToc(): void {
    const wrapper = document.getElementById("lsv-toc-picker");
    const trigger = document.getElementById(
      "lsv-toc-btn",
    ) as HTMLButtonElement | null;
    const panel = document.getElementById("lsv-toc-panel");
    if (!wrapper || !trigger || !panel || trigger.disabled) return;
    const setOpen = initDropdown(wrapper, trigger, panel);
    panel.querySelectorAll<HTMLElement>(".lsv-toc-link").forEach((link) => {
      link.addEventListener("click", () => {
        const idx = chapters.findIndex((c) => c.id === link.dataset.target);
        if (idx >= 0) showChapter(idx);
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
        showChapter(currentChapter + 1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        showChapter(currentChapter - 1);
      }
    });
  }

  // ---- go -----------------------------------------------------------------
  initToolbar();
  initToc();
  initKeyboard();
  initPicker();

  // Open at the chapter the reader had last chosen for THIS book, if it still
  // exists in the current TOC; otherwise the first chapter. No font-load
  // deferral needed here (unlike the old pixel-scroll restore) — a hard swap
  // to the top of a chapter is correct the instant it runs, reflow or not.
  const savedId = data?.slug ? liveChapter.read(data.slug) : null;
  const initialIdx = savedId
    ? chapters.findIndex((c) => c.id === savedId)
    : -1;
  showChapter(initialIdx >= 0 ? initialIdx : 0);

  // Within the current chapter, follow scroll to keep the companion in sync.
  // Two listeners because the two widths scroll differently: at desktop the
  // BAR scrolls away and the WINDOW governs reading; on a narrow screen
  // .lsv-viewport is still its own independent region (see the max-width:960
  // block in live-session.css) since the companion sits stacked above it
  // there and the two have to share one fixed-height budget.
  viewport.addEventListener("scroll", updateActive, { passive: true });
  window.addEventListener("scroll", updateActive, { passive: true });
  window.addEventListener("resize", updateActive);
  if (document.fonts && document.fonts.ready)
    document.fonts.ready.then(() => updateActive());
}

/**
 * Shared popover toggle — open state on the wrapper's `data-open`, `hidden` on
 * the panel, outside-click and Escape both close it. Powers the book picker and
 * the Chapters dropdown so the two read (and behave) as one connected control,
 * chained left-to-right: pick the book, then the chapter. Returns `setOpen` so
 * a caller can close the popover on its own actions (e.g. selecting a chapter).
 */
function initDropdown(
  wrapper: HTMLElement,
  trigger: HTMLElement,
  panel: HTMLElement,
): (open: boolean) => void {
  const setOpen = (open: boolean) => {
    wrapper.dataset.open = String(open);
    trigger.setAttribute("aria-expanded", String(open));
    panel.hidden = !open;
  };
  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    setOpen(wrapper.dataset.open !== "true");
  });
  document.addEventListener("click", (e) => {
    if (!wrapper.contains(e.target as Node)) setOpen(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && wrapper.dataset.open === "true") {
      setOpen(false);
      trigger.focus();
    }
  });
  return setOpen;
}

// ---- book picker (shared; also used on empty-state) -----------------------
function initPicker(): void {
  const picker = document.querySelector<HTMLElement>(".lsv-picker");
  const trigger = document.getElementById("lsv-picker-trigger");
  const panel = document.getElementById("lsv-picker-panel");
  if (!picker || !trigger || !panel) return;
  initDropdown(picker, trigger, panel);
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
