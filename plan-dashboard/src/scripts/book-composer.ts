/**
 * book-composer.ts — client logic for the Book Composer view (Book Pipeline v2).
 *
 * Reads the server-rendered JSON data island, lets the human curate visual
 * placements WYSIWYG (place from the palette, drag between chapters to move the
 * anchor, set align / flow / width / caption / page_fit, delete), then persists
 * to book/visual-layout.json via the API — AUTOSAVED (see ./autosave), no
 * manual Save button. Generating the PDF itself lives on /studio/<slug>/preview,
 * not here — see book-preview.ts. All styling is class-based + the --cx-w
 * custom property (set at runtime here, never as an inline HTML attribute), so
 * the view stays lint/Cortex-clean.
 */
import { createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { anchorKey } from "../../scripts/lib/anchor-key.mjs";
import {
  mountChapterEditor,
  VISUAL_DRAG_TYPE,
  type ChapterEditor,
} from "./book-md-editor";
import { confirmDialog, noticeDialog } from "./confirm-dialog";
import {
  createAutosave,
  mountAutosaveStatus,
  type AutosaveController,
} from "./autosave";
import { createComposeEditorBridge } from "./compose-editor-bridge";
import { safeChapterKey } from "../lib/reader/companion/keys";
import { apiFetch } from "../lib/api-fetch";
import { createStudioDecos } from "../components/studio/editor/studio-decos";
import {
  createFigureDecos,
  type EditorFigure,
} from "../components/studio/editor/figure-decos";
import {
  DEFAULT_DEPTH_PROFILE,
  DEPTH_LEVELS_BY_PROFILE,
  type GlossaryEntry,
} from "../components/studio/editor/studio-editor-constants";
import ComposeAiTools from "../components/studio/compose/ComposeAiTools";
import ComposeCompanionTab from "../components/studio/compose/ComposeCompanionTab";
import { mountPanelTextSize } from "./panel-text-size";
import { mountIconTooltips } from "./icon-tooltip";
import { PROSE_RENDERED_EVENT } from "../lib/reader/companion/passage-sync";
import { GOTO_CHAPTER_EVENT } from "../components/reader/VowellingReviewPanel";
import ComposeDetailsTab from "../components/studio/compose/ComposeDetailsTab";

type Align = "left" | "center" | "right";
type Flow = "wrap" | "standalone";
type PageFit = "avoid" | "before" | "isolate-plate";

interface Visual {
  id: string;
  type: string;
  caption: string;
  file: string;
  src: string;
  suggested_anchor: string;
  chapter: string;
  cleaned: boolean;
  embedded_title: string;
}
interface Citation {
  ar: string;
  tr: string;
}
interface Chapter {
  anchor: string;
  key: string;
  title: string;
  paras: number;
  citations: Citation[];
  /** TipTap-safe seed for edit mode. Mirrors ComposerChapter.editHtml in
   *  lib/reader/composer.ts — see the bodyByKey note in boot(). */
  editHtml: string;
}
interface Placement {
  visual_id: string;
  anchor: string;
  anchor_para: number | null;
  align: Align;
  flow: Flow;
  width_pct: number;
  caption: string;
  page_fit: PageFit;
}
interface ComposerData {
  slug: string;
  chapters: Chapter[];
  visuals: Visual[];
  placements: Placement[];
  glossary: GlossaryEntry[];
  glossaryAll: GlossaryEntry[];
}

const WRAP_MAX = 50;

// anchorKey comes from the single shared implementation — see the import above.

function boot(): void {
  const rootMaybe = document.querySelector<HTMLElement>(".composer[data-slug]");
  const dataEl = document.getElementById("composer-data");
  if (!rootMaybe || !dataEl?.textContent) return;
  const root: HTMLElement = rootMaybe; // narrowed once; nested closures keep non-null
  const data = JSON.parse(dataEl.textContent) as ComposerData;
  const slug = data.slug;
  const visualsById = new Map(data.visuals.map((v) => [v.id, v]));
  const chapterByKey = new Map(data.chapters.map((c) => [c.key, c]));

  // Cache each chapter's pristine prose body so every re-render re-inserts the
  // placed figures inline (at the exact paragraph the PDF would use) without
  // accumulating them across renders.
  //
  // NOTE the two different HTML strings in play, and never conflate them:
  //   - `.cx-body`'s innerHTML is the READ render — the PDF's own renderMd()
  //     output (chapter-open block, drop cap, mushaf verses). It is for display
  //     and for figure placement only.
  //   - `chapter.editHtml` is the EDIT seed — the plain render whose element set
  //     the TipTap StarterKit schema can round-trip back to markdown.
  // Seeding the editor from the read render would silently drop everything
  // outside that schema and write the loss into book.md on the next autosave.
  const bodyByKey = new Map<string, { el: HTMLElement; html: string }>();
  root.querySelectorAll<HTMLElement>(".cx-chapter").forEach((ch) => {
    const body = ch.querySelector<HTMLElement>(".cx-body");
    if (body)
      bodyByKey.set(ch.dataset.key ?? "", { el: body, html: body.innerHTML });
  });

  let placements: Placement[] = data.placements.map(normalize);
  let selected: string | null = null;
  // Assigned once, near the bottom of setup, once slug/placements are settled —
  // markDirty() (place/update/remove) only ever runs after that in response to
  // a user action, so referencing it before assignment here is safe.
  // eslint-disable-next-line prefer-const -- declaration/assignment split is deliberate (see above)
  let layoutAutosave: AutosaveController;

  const paletteEl = root.querySelector<HTMLElement>("#cx-palette-list")!;
  const controlsEl = root.querySelector<HTMLElement>("#cx-controls")!;
  const layoutStatusEl = root.querySelector<HTMLElement>("#cx-layout-status")!;
  const chapterSelect =
    root.querySelector<HTMLSelectElement>("#cx-chapter-select");
  const scopeEl = root.querySelector<HTMLElement>("#cx-artifacts-scope");
  let selectedChapter = data.chapters[0]?.key ?? "";
  // After an autosave-triggered reload we restore the chapter the user was on
  // (the manual save used to always reset to chapter 1 — this fixes that too).
  try {
    const restore = sessionStorage.getItem("cx-restore-chapter");
    if (restore) {
      sessionStorage.removeItem("cx-restore-chapter");
      if (data.chapters.some((c) => c.key === restore))
        selectedChapter = restore;
    }
  } catch {
    /* sessionStorage best-effort */
  }

  // ── inspector tabs (Artifacts · Refinement · Citations · Details) ────────────
  // The order you work in: place what you are adding, reshape the prose, set how
  // quotations are styled, check the chapter's facts last. Companion left this
  // list on 2026-07-21 — it is a drawer SURFACE now, not a tab (see the rail).
  const TABS = [
    "artifacts",
    "refine",
    "citations",
    "type",
    "details",
  ] as const;
  type TabName = (typeof TABS)[number];
  const tabBtn = (n: TabName) =>
    root.querySelector<HTMLButtonElement>(`#cx-tab-${n}`);
  const tabPanel = (n: TabName) =>
    root.querySelector<HTMLElement>(`#cx-panel-${n}`);
  function activateTab(name: TabName, focus = false): void {
    for (const n of TABS) {
      const on = n === name;
      const btn = tabBtn(n);
      btn?.classList.toggle("is-active", on);
      btn?.setAttribute("aria-selected", String(on));
      btn?.setAttribute("tabindex", on ? "0" : "-1"); // roving tabindex (ARIA tablist)
      const panel = tabPanel(n);
      if (panel) panel.hidden = !on;
    }
    if (focus) tabBtn(name)?.focus();
  }
  TABS.forEach((n, i) => {
    const btn = tabBtn(n);
    btn?.addEventListener("click", () => activateTab(n));
    // Arrow / Home / End cycling per the ARIA tablist keyboard pattern.
    btn?.addEventListener("keydown", (e) => {
      let next = -1;
      if (e.key === "ArrowRight" || e.key === "ArrowDown")
        next = (i + 1) % TABS.length;
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp")
        next = (i - 1 + TABS.length) % TABS.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = TABS.length - 1;
      if (next >= 0) {
        e.preventDefault();
        activateTab(TABS[next], true);
      }
    });
  });
  activateTab("artifacts"); // initialize roving tabindex on the default tab

  // Each tab is an icon; its name lives in a clipped label span. The tooltip is
  // how a sighted user learns which is which — a body-level fixed node, so it
  // neither widens the tab (the bug this replaced) nor clips at the surface edge.
  const tabbar = root.querySelector<HTMLElement>(".cx-tabbar");
  if (tabbar)
    mountIconTooltips(tabbar, { trigger: ".cx-tab", label: ".cx-tab-label" });

  // ── drawer surfaces (Tools · Companion · Arabic · Scholar) ────────────────
  // ONE drawer, four surfaces, one floating button each. Clicking the lit button
  // closes the drawer and the chapter takes the full page width back. The Scholar
  // used to run a SECOND, independent slide-in that could overlap this one; it is
  // a surface here now, so only one panel can ever be open. The state is a
  // per-browser preference, not book content, so it lives in localStorage.
  const SURFACES = ["tools", "companion", "arabic", "scholar"] as const;
  type Surface = (typeof SURFACES)[number];
  type PanelState = Surface | "closed";
  const PANEL_KEY = "cx-composer-panel";
  const grid = root.querySelector<HTMLElement>(".composer-grid");
  const surfaceBtn = (n: Surface) =>
    root.querySelector<HTMLButtonElement>(`#cx-rail-${n}`);
  const surfaceEl = (n: Surface) =>
    root.querySelector<HTMLElement>(`#cx-surface-${n}`);
  const railTools = surfaceBtn("tools");
  let panelState: PanelState = (() => {
    try {
      const saved = localStorage.getItem(PANEL_KEY) ?? "";
      if (saved === "closed") return saved;
      if ((SURFACES as readonly string[]).includes(saved))
        return saved as Surface;
    } catch {
      /* preference is best-effort */
    }
    return "tools"; // first visit matches the pre-drawer layout exactly
  })();

  function setPanel(next: PanelState, persist = true): void {
    panelState = next;
    grid?.setAttribute("data-panel", next);
    for (const n of SURFACES) {
      const on = n === next;
      const btn = surfaceBtn(n);
      btn?.classList.toggle("is-active", on);
      btn?.setAttribute("aria-pressed", String(on));
      const el = surfaceEl(n);
      if (el) el.hidden = !on;
    }
    if (persist) {
      try {
        localStorage.setItem(PANEL_KEY, next);
      } catch {
        /* preference is best-effort */
      }
    }
  }
  /** Bring the WORKING ROW to the top of the viewport — the chapter picker, the
   *  Read/Edit toggle and the drawer's own text dial, all on one line just under
   *  the site nav.
   *
   *  Not `scrollTo(0)`, which is what this used to do: that put the page hero
   *  back on screen — breadcrumb, book title, the paragraph explaining what the
   *  Composer is — none of which you are working on, and it cost most of a screen
   *  before the first line of prose. The drawer is anchored to the top of the
   *  GRID, not of the page, so the grid is the thing to bring into view.
   *
   *  Measured off the sticky nav rather than hard-coded: theme-components.css
   *  owns that height and a copy of it here would drift the first time it moved. */
  function scrollToWorkingRow(): void {
    const grid = root.querySelector<HTMLElement>(".composer-grid");
    if (!grid) return;
    const navH =
      document.querySelector<HTMLElement>(".topnav")?.getBoundingClientRect()
        .height ?? 0;
    const target = Math.max(
      0,
      grid.getBoundingClientRect().top + window.scrollY - navH - 8,
    );
    // Already there — don't animate a scroll of two pixels.
    if (Math.abs(target - window.scrollY) < 4) return;
    // `smooth` unless the reader has asked for reduced motion, in which case an
    // instant jump is the accessible answer rather than no jump at all.
    const reduce = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    )?.matches;
    window.scrollTo({ top: target, behavior: reduce ? "auto" : "smooth" });
  }

  for (const n of SURFACES) {
    surfaceBtn(n)?.addEventListener("click", () => {
      setPanel(panelState === n ? "closed" : n);
      // The buttons are pinned to the bottom of the viewport but the drawer they
      // open starts at the top of the grid — so deep in a long chapter you could
      // open a panel and see nothing happen. Ride back up with it.
      scrollToWorkingRow();
    });
  }
  root.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || panelState === "closed") return;
    // Never steal Escape from a text field or a dialog inside the drawer.
    const el = document.activeElement;
    if (
      el instanceof HTMLElement &&
      el.closest("input, textarea, [role=dialog]")
    )
      return;
    setPanel("closed");
  });
  setPanel(panelState, false);

  // The panel text-size stepper. Targets the DRAWER, not a surface: all three
  // surfaces inherit --panel-fs from it, so one control moves whichever one is
  // showing and the two that are not.
  const drawer = root.querySelector<HTMLElement>("#cx-drawer");
  if (drawer) {
    // Two mounts, one preference: the stepper module broadcasts a change to
    // every mounted control, so the copy in the Typography tab (where the
    // book/screen split is explained) and the one pinned above the drawer
    // always read the same number.
    for (const id of ["#cx-panel-size", "#cx-type-size"]) {
      const host = root.querySelector<HTMLElement>(id);
      if (host) mountPanelTextSize(host, drawer);
    }
  }

  // ── chapter scoping — one chapter visible at a time; tabs follow it ────────
  function showSelectedChapter(): void {
    root.querySelectorAll<HTMLElement>(".cx-chapter").forEach((ch) => {
      ch.hidden = (ch.dataset.key ?? "") !== selectedChapter;
    });
  }
  if (chapterSelect) {
    chapterSelect.value = selectedChapter;
    chapterSelect.addEventListener("change", async () => {
      const wasEditing = !!activeEditor;
      if (wasEditing) {
        const saved = activeSaveFlush ? await activeSaveFlush() : true;
        if (!saved) {
          const leave = await confirmDialog({
            title: "Discard unsaved edits?",
            body: "This chapter has changes that didn't save. Switch chapters anyway and lose them?",
            confirmLabel: "Switch",
            cancelLabel: "Keep editing",
            danger: true,
          });
          if (!leave) {
            chapterSelect.value = selectedChapter;
            return;
          } // stay on this chapter
        } else if (contentChangedThisSession) {
          // Prose was saved → reload so the target chapter renders from fresh book.md,
          // landing back in Edit (the user was editing) on the new chapter.
          selectedChapter = chapterSelect.value;
          try {
            sessionStorage.setItem("cx-restore-edit", "1");
          } catch {
            /* best-effort */
          }
          reloadPreservingChapter();
          return;
        }
      }
      if (activeEditor) exitEdit(); // tear down the editor bound to the old chapter
      selectedChapter = chapterSelect.value;
      selected = null; // a figure selection doesn't carry across chapters
      showSelectedChapter();
      renderCitations();
      renderCompanion(); // notes follow the chapter — no picker of their own
      render();
      if (wasEditing) setMode("edit"); // stay in Edit on the newly selected chapter
    });
  }

  // A drawer surface asking for a chapter — the Arabic panel's per-passage
  // chapter labels. Driven through the SELECT rather than by setting
  // selectedChapter directly, so the request goes down the one path that already
  // handles the hard parts: flushing a pending edit, warning about unsaved
  // prose, re-rendering the citations and the Companion notes. A second way to
  // change chapter would be a second place for that logic to be missing.
  window.addEventListener(GOTO_CHAPTER_EVENT, (ev) => {
    const key = (ev as CustomEvent<{ key?: string }>).detail?.key;
    if (!chapterSelect || !key || key === selectedChapter) return;
    if (!data.chapters.some((c) => c.key === key)) return; // stale request
    chapterSelect.value = key;
    chapterSelect.dispatchEvent(new Event("change"));
  });

  // ── Edit mode — the chapter opens straight into the TipTap editor ─────────
  // Layout mode (figure placement/resize) was removed from the UI 2026-07-16;
  // the Companion notes panel that once sat behind a nav link became a tab
  // (2026-07-19) and is now a drawer surface of its own (2026-07-21), and the
  // Edit/Companion-Tool button pair is
  // gone entirely — Edit is the sole, permanent state. Figure placement has
  // no UI home until Phase 4 (Edit-canvas merge) lands.
  const bookTitle =
    root
      .closest("body")
      ?.querySelector<HTMLElement>(".lib-hero-main h1")
      ?.textContent?.trim() ?? "";
  let activeEditor: ChapterEditor | null = null;
  // Figures drawn into the open chapter's edit canvas. Deliberately a widget-
  // decoration feed and NOT editor content: see figure-decos.ts for why placing
  // them in the document would let `toMarkdown()` serialize them into book.md.
  const editorFigures: { current: EditorFigure[] } = { current: [] };
  let contentChangedThisSession = false; // a save landed → in-memory render is stale
  // Flush any pending autosave for the active editor; resolves true if the chapter
  // is safely saved (or had nothing to save), false if the save failed.
  let activeSaveFlush: (() => Promise<boolean>) | null = null;

  // Companion/AI-tools/Details tools (Studio-decos + the reused hooks) — one
  // shared bridge + two imperatively-mounted React roots per open chapter.
  // React, not Astro islands, because the editor/chapter identity changes on
  // every chapter switch, which a client:only island can't receive post-mount.
  const glossarySorted = [...data.glossary]
    .filter((e) => e.phonetic && e.arabic_script)
    .sort((a, b) => b.phonetic.length - a.phonetic.length);
  const depthLevels =
    DEPTH_LEVELS_BY_PROFILE[DEFAULT_DEPTH_PROFILE] ??
    DEPTH_LEVELS_BY_PROFILE[Object.keys(DEPTH_LEVELS_BY_PROFILE)[0]];
  let aiToolsRoot: Root | null = null;
  let detailsRoot: Root | null = null;
  let companionRoot: Root | null = null;
  const companionChapters = data.chapters.map((c) => ({
    key: c.key,
    title: c.title,
  }));

  /** Mount the private-notes panel ONCE for the page and re-render it with the
   *  chapter currently selected. It used to be a tab that was created and
   *  destroyed with the editor, which meant it (a) vanished in Read mode and (b)
   *  needed a full unmount/remount on every chapter switch just to keep its own
   *  chapter picker in step. It is a controlled component now — it takes the
   *  chapter and shows those notes, so it cannot disagree with the page, and it
   *  needs no picker of its own. */
  function renderCompanion(): void {
    const host = root.querySelector<HTMLElement>("#cx-companion-mount");
    if (!host) return;
    companionRoot ??= createRoot(host);
    companionRoot.render(
      createElement(ComposeCompanionTab, {
        slug,
        chapters: companionChapters,
        chapter: selectedChapter,
      }),
    );
  }
  renderCompanion(); // page-lifetime surface: present in Read mode too

  // A prose autosave writes book.md on disk but the page still holds the ORIGINAL
  // server render in memory; reload (preserving the chapter) to re-sync the preview.
  function reloadPreservingChapter(): void {
    try {
      sessionStorage.setItem("cx-restore-chapter", selectedChapter);
    } catch {
      /* best-effort */
    }
    window.location.reload();
  }

  function currentChapterEl(): HTMLElement | null {
    return (
      Array.from(root.querySelectorAll<HTMLElement>(".cx-chapter")).find(
        (c) => (c.dataset.key ?? "") === selectedChapter,
      ) ?? null
    );
  }

  function toolbarBtn(
    label: string,
    title: string,
    run: (ed: ChapterEditor) => void,
  ): HTMLButtonElement {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cx-edit-tool";
    b.textContent = label;
    b.title = title;
    b.setAttribute("aria-label", title); // glyph text is decorative; announce the action
    b.addEventListener("mousedown", (e) => e.preventDefault()); // keep editor selection
    b.addEventListener("click", () => {
      if (activeEditor) run(activeEditor);
    });
    return b;
  }

  function exitEdit(): void {
    aiToolsRoot?.unmount();
    aiToolsRoot = null;
    detailsRoot?.unmount();
    detailsRoot = null;
    // companionRoot is deliberately NOT torn down: the notes are a drawer
    // surface of their own now, readable in Read mode too (see renderCompanion).
    activeEditor?.destroy();
    activeEditor = null;
    activeSaveFlush = null;
    root.querySelector(".cx-edit-shell")?.remove();
    const bodyEl = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
    if (bodyEl) bodyEl.hidden = false;
    if (chapterSelect) chapterSelect.disabled = false;
    updateAiEnabled(); // no editor → AI actions disabled
  }

  function enterEdit(): void {
    const ch = currentChapterEl();
    const bodyEl = ch?.querySelector<HTMLElement>(".cx-body");
    if (!ch || !bodyEl) return;
    // The TipTap-safe seed (see the bodyByKey note above) — NOT the read render.
    const pristine = chapterByKey.get(selectedChapter)?.editHtml ?? "";
    if (!pristine) return; // no safe seed → refuse to open a lossy editor
    bodyEl.hidden = true;

    const shell = document.createElement("div");
    shell.className = "cx-edit-shell";

    const host = document.createElement("div");
    host.className = "cx-edit-host";

    const toolbar = document.createElement("div");
    toolbar.className = "cx-edit-toolbar";
    toolbar.setAttribute("role", "toolbar");
    toolbar.setAttribute("aria-label", "Editor");

    // ── Font family + text size ──────────────────────────────────────────────
    // These are EDITING-VIEW rendering preferences only: book.md carries no font
    // or size, so they change how the chapter looks while you edit (persisted per
    // user, like the paper theme) — they never restyle the printed book.
    const FONTS = [
      { id: "sans", name: "Sans" },
      { id: "serif", name: "Serif" },
      { id: "lato", name: "Lato" },
      { id: "inter", name: "Inter" },
      { id: "mono", name: "Mono" },
      { id: "dyslexic", name: "Dyslexic" },
    ] as const;
    const savedFont = (() => {
      try {
        return localStorage.getItem("cx-editor-font") ?? "sans";
      } catch {
        return "sans";
      }
    })();
    host.dataset.font = FONTS.some((f) => f.id === savedFont)
      ? savedFont
      : "sans";

    const fontGroup = document.createElement("div");
    fontGroup.className = "cx-tb-group";
    const fontSel = document.createElement("select");
    fontSel.className = "cx-font-select";
    fontSel.setAttribute("aria-label", "Editor font (view only)");
    fontSel.title =
      "Editor font — changes this editing view only, not the printed book";
    for (const f of FONTS) {
      const o = document.createElement("option");
      o.value = f.id;
      o.textContent = f.name;
      if (f.id === host.dataset.font) o.selected = true;
      fontSel.append(o);
    }
    fontSel.addEventListener("change", () => {
      host.dataset.font = fontSel.value;
      try {
        localStorage.setItem("cx-editor-font", fontSel.value);
      } catch {
        /* best-effort */
      }
    });

    const SIZE_MIN = 13;
    const SIZE_MAX = 24;
    let sizePx = (() => {
      const raw = (() => {
        try {
          return Number(localStorage.getItem("cx-editor-size"));
        } catch {
          return NaN;
        }
      })();
      return Number.isFinite(raw) && raw >= SIZE_MIN && raw <= SIZE_MAX
        ? raw
        : 17;
    })();
    const sizeWrap = document.createElement("div");
    sizeWrap.className = "cx-size";
    sizeWrap.setAttribute("role", "group");
    sizeWrap.setAttribute("aria-label", "Editor text size (view only)");
    const sizeDown = document.createElement("button");
    sizeDown.type = "button";
    sizeDown.className = "cx-size-btn";
    sizeDown.textContent = "−"; // minus sign
    sizeDown.title = "Smaller editor text";
    sizeDown.setAttribute("aria-label", "Decrease editor text size");
    const sizeVal = document.createElement("span");
    sizeVal.className = "cx-size-val";
    sizeVal.setAttribute("aria-live", "polite");
    const sizeUp = document.createElement("button");
    sizeUp.type = "button";
    sizeUp.className = "cx-size-btn";
    sizeUp.textContent = "+";
    sizeUp.title = "Larger editor text";
    sizeUp.setAttribute("aria-label", "Increase editor text size");
    const applySize = () => {
      host.style.setProperty("--prose-size", `${sizePx}px`); // runtime custom prop, in-pattern with --cx-w
      sizeVal.textContent = String(sizePx);
      try {
        localStorage.setItem("cx-editor-size", String(sizePx));
      } catch {
        /* best-effort */
      }
    };
    sizeDown.addEventListener("click", () => {
      sizePx = Math.max(SIZE_MIN, sizePx - 1);
      applySize();
    });
    sizeUp.addEventListener("click", () => {
      sizePx = Math.min(SIZE_MAX, sizePx + 1);
      applySize();
    });
    sizeWrap.append(sizeDown, sizeVal, sizeUp);
    fontGroup.append(fontSel, sizeWrap);

    // ── Formatting cluster: B / I / U + structure ────────────────────────────
    // B and I persist to book.md. U (underline) is an editing-view emphasis only
    // — the book's markdown format has no underline, so it is not saved.
    const fmtGroup = document.createElement("div");
    fmtGroup.className = "cx-tb-group";
    const bBtn = toolbarBtn("B", "Bold", (ed) =>
      ed.editor.chain().focus().toggleBold().run(),
    );
    bBtn.classList.add("cx-tool-b");
    const iBtn = toolbarBtn("I", "Italic", (ed) =>
      ed.editor.chain().focus().toggleItalic().run(),
    );
    iBtn.classList.add("cx-tool-i");
    const uBtn = toolbarBtn(
      "U",
      "Underline (editing view only — not saved to the book)",
      (ed) => ed.editor.chain().focus().toggleUnderline().run(),
    );
    uBtn.classList.add("cx-tool-u");
    fmtGroup.append(
      bBtn,
      iBtn,
      uBtn,
      toolbarBtn("H", "Heading", (ed) =>
        ed.editor.chain().focus().toggleHeading({ level: 3 }).run(),
      ),
      toolbarBtn("❝", "Quote", (ed) =>
        ed.editor.chain().focus().toggleBlockquote().run(),
      ),
      toolbarBtn("•", "Bulleted list", (ed) =>
        ed.editor.chain().focus().toggleBulletList().run(),
      ),
    );

    toolbar.append(fontGroup, fmtGroup);
    applySize(); // seed --prose-size + the readout

    // Paper picker — Kindle-style Light / Sepia / Dark tint for the writing area.
    // The choice is a per-user editor preference (not book content), so it lives
    // in localStorage and applies across chapters and books.
    const PAPERS = [
      { id: "light", name: "Light" },
      { id: "sepia", name: "Sepia" },
      { id: "dark", name: "Dark" },
    ] as const;
    const savedPaper = (() => {
      try {
        return localStorage.getItem("cx-editor-paper") ?? "light";
      } catch {
        return "light";
      }
    })();
    host.dataset.paper = PAPERS.some((p) => p.id === savedPaper)
      ? savedPaper
      : "light";
    const paperGroup = document.createElement("div");
    paperGroup.className = "cx-paper";
    paperGroup.setAttribute("role", "group");
    paperGroup.setAttribute("aria-label", "Paper colour");
    const paperLabel = document.createElement("span");
    paperLabel.className = "cx-paper-label";
    paperLabel.textContent = "Paper";
    paperGroup.append(paperLabel);
    const paperBtns: HTMLButtonElement[] = [];
    for (const p of PAPERS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cx-paper-btn";
      b.dataset.paper = p.id;
      b.textContent = p.name;
      b.setAttribute("aria-pressed", String(host.dataset.paper === p.id));
      b.addEventListener("click", () => {
        host.dataset.paper = p.id;
        try {
          localStorage.setItem("cx-editor-paper", p.id);
        } catch {
          /* preference is best-effort */
        }
        paperBtns.forEach((x) =>
          x.setAttribute("aria-pressed", String(x.dataset.paper === p.id)),
        );
      });
      paperBtns.push(b);
      paperGroup.append(b);
    }
    toolbar.append(paperGroup);

    shell.append(toolbar, host);
    bodyEl.insertAdjacentElement("afterend", shell);

    // Fresh bridge per chapter — no leaked comments/section-tags/focus state
    // across a chapter switch (see compose-editor-bridge.ts's own header note).
    const bridge = createComposeEditorBridge(depthLevels, glossarySorted);
    const chapterTitle = chapterByKey.get(selectedChapter)?.title ?? "";

    syncEditorFigures();
    activeEditor = mountChapterEditor(host, pristine, [
      createStudioDecos(bridge),
      createFigureDecos({ figuresRef: editorFigures }),
    ]);
    bridge.editorRef.current = activeEditor.editor;
    const originalTexts: string[] = [];
    activeEditor.editor.state.doc.forEach((n) =>
      originalTexts.push(n.textContent),
    );
    bridge.originalRef.current = originalTexts;
    activeEditor.editor.on("focus", () => {
      bridge.hasFocusRef.current = true;
      activeEditor?.editor.view.dispatch(activeEditor.editor.state.tr);
    });
    activeEditor.editor.on("blur", () => {
      bridge.hasFocusRef.current = false;
      bridge.activeSectionOrdinalRef.current = null;
      activeEditor?.editor.view.dispatch(activeEditor.editor.state.tr);
    });

    aiToolsRoot = createRoot(
      root.querySelector<HTMLElement>("#cx-ai-tools-mount")!,
    );
    aiToolsRoot.render(
      createElement(ComposeAiTools, {
        slug,
        chapter: selectedChapter,
        chapterTitle,
        editor: activeEditor.editor,
        bridge,
        glossaryAll: data.glossaryAll,
      }),
    );
    detailsRoot = createRoot(
      root.querySelector<HTMLElement>("#cx-details-mount")!,
    );
    detailsRoot.render(
      createElement(ComposeDetailsTab, {
        slug,
        chapter: selectedChapter,
        editor: activeEditor.editor,
        bridge,
      }),
    );

    // Autosave — no manual "Save prose" button; edits persist themselves (./autosave).
    const proseAutosave: AutosaveController = createAutosave({
      onStateChange: mountAutosaveStatus(shell, () => {
        void proseAutosave.flush();
      }),
      save: async () => {
        if (!activeEditor) return { ok: true };
        // apiFetch throws on failure; createAutosave's own catch renders the
        // same "Couldn't save — …" state the old envelope check produced.
        await apiFetch("/api/studio/book-md", {
          method: "PUT",
          body: {
            slug,
            chapterKey: selectedChapter,
            markdown: activeEditor.toMarkdown(),
          },
        });
        contentChangedThisSession = true;
        return { ok: true };
      },
    });
    activeSaveFlush = () => proseAutosave.flush();
    activeEditor.editor.on("update", () => proseAutosave.markDirty());
    activeEditor.editor.on("selectionUpdate", () => updateAiEnabled());
    updateAiEnabled();
  }

  const modeReadBtn = root.querySelector<HTMLButtonElement>("#cx-mode-read");
  const modeEditBtn = root.querySelector<HTMLButtonElement>("#cx-mode-edit");

  function setModeVisual(mode: "read" | "edit"): void {
    root.classList.toggle("is-editing", mode === "edit");
    modeReadBtn?.setAttribute("aria-pressed", String(mode === "read"));
    modeEditBtn?.setAttribute("aria-pressed", String(mode === "edit"));
    // In Read mode the Tools surface has nothing to act on — Refinement and
    // Details drive the editor, which is torn down — so it is disabled and the
    // drawer falls closed if it was showing them. Companion stays available on
    // purpose: private notes are exactly what a reading pass wants beside the
    // page. The state is NOT persisted here, so returning to Edit restores
    // whatever the reader had chosen rather than "closed".
    const reading = mode === "read";
    if (railTools) railTools.disabled = reading;
    if (reading && panelState === "tools") setPanel("closed", false);
    else if (!reading) {
      try {
        const saved = localStorage.getItem(PANEL_KEY);
        if (saved === "tools" && panelState === "closed")
          setPanel("tools", false);
      } catch {
        /* preference is best-effort */
      }
    }
  }
  function enterEditMode(): void {
    if (activeEditor) return;
    setModeVisual("edit");
    enterEdit();
  }
  // Leaving edit: flush autosave; if it FAILED, confirm before losing edits; then —
  // when prose actually changed — reload (preserving the chapter) so the Layout
  // preview re-renders from the authoritative book.md.
  async function leaveEditMode(): Promise<boolean> {
    if (!activeEditor) {
      setModeVisual("read");
      return true;
    }
    const saved = activeSaveFlush ? await activeSaveFlush() : true;
    if (!saved) {
      const leave = await confirmDialog({
        title: "Discard unsaved edits?",
        body: "The last save didn't go through. Leave anyway and lose the unsaved changes to this chapter?",
        confirmLabel: "Leave",
        cancelLabel: "Keep editing",
        danger: true,
      });
      if (!leave) return false;
    }
    if (saved && contentChangedThisSession) {
      reloadPreservingChapter();
      return true;
    }
    setModeVisual("read");
    exitEdit();
    contentChangedThisSession = false;
    return true;
  }
  // Programmatic entry point kept for callers that just want to (re)enter Edit.
  function setMode(mode: "read" | "edit"): void {
    if (mode === "edit") enterEditMode();
    else void leaveEditMode();
  }
  // Best-effort save if the tab is hidden/closed with edits still pending (the
  // ~1.2s debounce keeps this window small; there is no native "unsaved" prompt).
  window.addEventListener("pagehide", () => {
    if (activeSaveFlush) void activeSaveFlush();
  });

  // ── The book's look: the Citations tab's style family + the Typography tab's
  //    two faces. THREE radio groups across TWO forms, one artifact
  //    (book/citation-style.json) and one endpoint. They are handled together
  //    here rather than per-form because the save contract is identical for all
  //    three — send only the field that changed, let the route carry the rest
  //    over — and a second copy of that would be a second thing to get wrong.
  const citeForm = root.querySelector<HTMLFormElement>(".cx-cite-form");
  const typeForm = root.querySelector<HTMLFormElement>(".cx-type-form");
  const styleForms = [citeForm, typeForm].filter(
    (f): f is HTMLFormElement => !!f,
  );
  const citeSave = root.querySelector<HTMLElement>("#cx-cite-save");
  const typeSave = root.querySelector<HTMLElement>("#cx-type-save");
  const citeListEl = root.querySelector<HTMLElement>("#cx-citations-list");

  /** Status line for whichever panel the change came from — a save made in
   *  Typography must not report into a status line the user cannot see. */
  function setStyleStatus(
    el: HTMLElement | null,
    msg: string,
    state: "" | "saved" | "error",
  ): void {
    if (!el) return;
    el.textContent = msg;
    el.classList.toggle("is-saved", state === "saved");
    el.classList.toggle("is-error", state === "error");
  }
  /** Check the radio for `value` in whichever form holds the `name` group. */
  function checkRadio(name: string, value: string | undefined): void {
    if (!value) return;
    for (const form of styleForms) {
      const input = form.querySelector<HTMLInputElement>(
        `input[name="${name}"][value="${value}"]`,
      );
      if (input) {
        input.checked = true;
        return;
      }
    }
  }
  async function loadSavedFamily(): Promise<void> {
    try {
      const saved = await apiFetch<{
        family: string;
        translation_font?: string;
        arabic_font?: string;
      }>("/api/studio/citation-style", { query: { slug } });
      checkRadio("citation-style", saved.family);
      checkRadio("translation-font", saved.translation_font);
      checkRadio("arabic-font", saved.arabic_font);
      // The page root is server-rendered with the saved faces already, so this
      // only matters when the artifact changed under a page that was left open.
      applyStyleClasses(saved.family, saved.translation_font ?? null, saved.arabic_font ?? null);
    } catch {
      /* keep the pre-checked defaults if the fetch fails */
    }
  }
  /** Restyle the chapter you are LOOKING at, not just the swatch in the tab.
   *  The family class lives on each chapter body (server-rendered) and the two
   *  faces on the page root, so all three have to move when a chip changes.
   *  The Arabic face is the NON-Qur'anic one only: `.is-quranic` re-declares
   *  --q-ar-face on the run itself and a declaration on the consumer beats one
   *  inherited from here, so scripture stays Uthmanic whatever is picked. */
  function applyStyleClasses(
    family: string | null,
    font: string | null,
    arabic: string | null,
  ): void {
    if (family) {
      root.querySelectorAll<HTMLElement>(".cx-body").forEach((el) => {
        el.classList.forEach((c) => {
          if (c.startsWith("style-")) el.classList.remove(c);
        });
        el.classList.add(`style-${family}`);
      });
    }
    const swap = (prefix: string, value: string) => {
      root.classList.forEach((c) => {
        if (c.startsWith(prefix)) root.classList.remove(c);
      });
      root.classList.add(`${prefix}${value}`);
    };
    if (font) swap("tr-", font);
    if (arabic) swap("ar-", arabic);
  }
  /** One radio group -> one field on the artifact, one sentence of confirmation. */
  const STYLE_FIELDS: Record<
    string,
    { field: string; said: (v: string) => string }
  > = {
    "citation-style": {
      field: "family",
      said: (v) => `Saved — the book prints in the ${v} style.`,
    },
    "translation-font": {
      field: "translation_font",
      said: (v) => `Saved — English renderings print in ${v.replace(/-/g, " ")}.`,
    },
    "arabic-font": {
      field: "arabic_font",
      said: (v) =>
        `Saved — non-Qur'anic Arabic prints in ${v.replace(/-/g, " ")}. Scripture stays Uthmanic.`,
    },
  };
  for (const form of styleForms) {
    const status = form === typeForm ? typeSave : citeSave;
    form.addEventListener("change", async (ev) => {
      const t = ev.target as HTMLInputElement;
      const spec = STYLE_FIELDS[t?.name ?? ""];
      if (!spec || !t.checked) return;
      applyStyleClasses(
        t.name === "citation-style" ? t.value : null,
        t.name === "translation-font" ? t.value : null,
        t.name === "arabic-font" ? t.value : null,
      );
      setStyleStatus(status, "Saving…", "");
      try {
        // Send ONLY the field that changed — the route carries the others over
        // from disk, so saving a face cannot wipe the family (or the reverse).
        await apiFetch("/api/studio/citation-style", {
          method: "PUT",
          body: { slug, [spec.field]: t.value },
        });
        setStyleStatus(status, spec.said(t.value), "saved");
      } catch (e) {
        setStyleStatus(status, `Couldn't save: ${(e as Error).message}`, "error");
      }
    });
  }

  function renderCitations(): void {
    if (!citeListEl) return;
    citeListEl.textContent = "";
    const items = chapterByKey.get(selectedChapter)?.citations ?? [];
    if (!items.length) {
      const p = document.createElement("p");
      p.className = "cx-empty";
      p.textContent = "No Quran or hadith citations detected in this chapter.";
      citeListEl.appendChild(p);
      return;
    }
    for (const c of items) {
      const bq = document.createElement("blockquote");
      bq.className = "bs-verse cx-cite-item";
      const ar = document.createElement("p");
      ar.className = "bs-ar";
      ar.setAttribute("dir", "rtl");
      ar.setAttribute("lang", "ar");
      ar.textContent = c.ar;
      bq.appendChild(ar);
      if (c.tr) {
        const tr = document.createElement("p");
        tr.className = "bs-tr";
        tr.textContent = c.tr;
        bq.appendChild(tr);
      }
      citeListEl.appendChild(bq);
    }
  }
  void loadSavedFamily();

  function normalize(p: Placement): Placement {
    const align = (["left", "center", "right"] as Align[]).includes(p.align)
      ? p.align
      : "center";
    let flow: Flow = p.flow === "wrap" ? "wrap" : "standalone";
    const width = Math.max(1, Math.min(100, Number(p.width_pct) || 60));
    if (align === "center") flow = "standalone";
    if (flow === "wrap" && width > WRAP_MAX) flow = "standalone";
    const page_fit = (
      ["avoid", "before", "isolate-plate"] as PageFit[]
    ).includes(p.page_fit)
      ? p.page_fit
      : "avoid";
    let anchor_para: number | null =
      p.anchor_para == null
        ? null
        : Math.max(0, Math.floor(Number(p.anchor_para)));
    if (anchor_para != null && !Number.isFinite(anchor_para))
      anchor_para = null;
    return {
      visual_id: p.visual_id,
      anchor: p.anchor,
      anchor_para,
      align,
      flow,
      width_pct: width,
      caption: p.caption ?? "",
      page_fit,
    };
  }

  function markDirty(): void {
    layoutAutosave.markDirty();
  }

  function place(
    visualId: string,
    anchor: string,
    anchorPara: number | null = null,
  ): void {
    if (placements.some((p) => p.visual_id === visualId)) return;
    const v = visualsById.get(visualId);
    placements.push(
      normalize({
        visual_id: visualId,
        anchor,
        anchor_para: anchorPara,
        align: "center",
        flow: "standalone",
        width_pct: 60,
        caption: v?.caption ?? "",
        page_fit: "avoid",
      } as Placement),
    );
    selected = visualId;
    markDirty();
    render();
  }

  function remove(visualId: string): void {
    placements = placements.filter((p) => p.visual_id !== visualId);
    if (selected === visualId) selected = null;
    markDirty();
    render();
  }

  function update(visualId: string, patch: Partial<Placement>): void {
    const i = placements.findIndex((p) => p.visual_id === visualId);
    if (i < 0) return;
    placements[i] = normalize({ ...placements[i], ...patch });
    markDirty();
    render();
  }

  // ── render ──────────────────────────────────────────────────────────────
  function render(): void {
    // Reset every chapter to its pristine prose, then insert each placed figure
    // inline at the exact paragraph the renderer (applyLayout) would use.
    for (const { el, html } of bodyByKey.values()) el.innerHTML = html;
    const placedIds = new Set(placements.map((p) => p.visual_id));

    const firstKey = bodyByKey.keys().next().value ?? "";
    const byChapter = new Map<string, { idx: number; el: HTMLElement }[]>();
    for (const p of placements) {
      const v = visualsById.get(p.visual_id);
      if (!v) continue;
      const key = anchorKey(p.anchor);
      const target = bodyByKey.has(key) ? key : firstKey;
      if (!bodyByKey.has(target)) continue;
      const idx = p.anchor_para == null ? 1 : p.anchor_para; // null -> after intro (mirror)
      if (!byChapter.has(target)) byChapter.set(target, []);
      byChapter.get(target)!.push({ idx, el: figureEl(p, v) });
    }
    for (const [key, figs] of byChapter)
      insertFiguresInline(bodyByKey.get(key)!.el, figs);

    // The loop above fills the READ body, which edit mode hides. Feed the edit
    // canvas too, so a placement is visible in the mode the composer actually
    // opens in — the reason clicking a candidate used to look like a no-op.
    syncEditorFigures();

    // palette = unplaced candidates for the selected chapter (+ book-level ones,
    // which have no resolved chapter and must stay reachable from any chapter)
    paletteEl.textContent = "";
    const unplaced = data.visuals.filter(
      (v) =>
        !placedIds.has(v.id) && (v.chapter === selectedChapter || !v.chapter),
    );
    if (!unplaced.length) {
      const p = document.createElement("p");
      p.className = "cx-empty";
      p.textContent = !data.visuals.length
        ? "No visual candidates for this book yet."
        : "No unplaced candidates for this chapter.";
      paletteEl.appendChild(p);
    } else {
      unplaced.forEach((v) => paletteEl.appendChild(paletteItemEl(v)));
    }
    if (scopeEl) {
      const ch = chapterByKey.get(selectedChapter);
      scopeEl.textContent = ch ? `Candidates for “${ch.title}”.` : "";
    }
    // The innerHTML reset above drops anything a client island added to the
    // prose — the Companion panel's passage marks among them. Announce it so
    // they can be re-applied; nothing here needs to know who is listening.
    window.dispatchEvent(new CustomEvent(PROSE_RENDERED_EVENT));
  }

  // Rebuild the edit canvas's figure feed for the chapter now open, then ask the
  // editor to redraw. Safe to call when no editor is mounted (enterEdit calls it
  // to seed `editorFigures` before the first render).
  function syncEditorFigures(): void {
    editorFigures.current = placements
      .filter((p) => {
        const key = anchorKey(p.anchor);
        // A placement whose chapter no longer resolves falls to the first
        // chapter in the read render; mirror that so the two never disagree.
        const target = bodyByKey.has(key)
          ? key
          : (bodyByKey.keys().next().value ?? "");
        return target === selectedChapter;
      })
      .map((p) => {
        const v = visualsById.get(p.visual_id);
        return { p, v };
      })
      .filter((x): x is { p: Placement; v: Visual } => Boolean(x.v))
      .map(({ p, v }) => ({
        idx: p.anchor_para == null ? 1 : p.anchor_para,
        // Every property that changes how the figure draws is in the key, so an
        // untouched figure reuses its DOM (and its already-loaded <img>).
        key: `fig-${p.visual_id}-${p.anchor_para}-${p.align}-${p.flow}-${p.width_pct}-${p.page_fit}-${p.caption}-${p.visual_id === selected ? "sel" : "un"}`,
        el: () => {
          const fig = figureEl(p, v);
          // Chrome, not prose: the caret must never enter it and it must never
          // be swept into a selection that the autosave then serializes.
          fig.contentEditable = "false";
          return fig;
        },
      }));
    // An empty transaction is how this editor asks its decoration plugins to
    // recompute (same idiom as the focus/blur handlers in enterEdit).
    if (activeEditor)
      activeEditor.editor.view.dispatch(activeEditor.editor.state.tr);
  }

  // Insert figures into a chapter body at their paragraph index, mirroring the
  // renderer's applyLayout: idx<=0 => chapter top; idx=N => after the Nth top-level
  // <p>; idx beyond the paragraph count => flushed at the chapter's end. Figures
  // sharing an index keep their placement order.
  function insertFiguresInline(
    bodyEl: HTMLElement,
    figs: { idx: number; el: HTMLElement }[],
  ): void {
    const paras = Array.from(
      bodyEl.querySelectorAll<HTMLElement>(":scope > p"),
    );
    const groups = new Map<number, HTMLElement[]>();
    for (const f of figs) {
      if (!groups.has(f.idx)) groups.set(f.idx, []);
      groups.get(f.idx)!.push(f.el);
    }
    for (const [idx, els] of groups) {
      if (idx <= 0) {
        const ref = bodyEl.firstChild;
        for (const el of els) bodyEl.insertBefore(el, ref);
      } else if (idx > paras.length) {
        for (const el of els) bodyEl.appendChild(el);
      } else {
        let ref: Element = paras[idx - 1];
        for (const el of els) {
          ref.insertAdjacentElement("afterend", el);
          ref = el;
        }
      }
    }
  }

  // Number of paragraphs whose vertical midpoint is above `clientY` — the
  // anchor_para "after paragraph N" (0 => chapter top). Mirrors applyLayout's
  // top-level <p> counting so a drop lands where the PDF will place the figure.
  function paraIndexAt(
    bodyEl: HTMLElement,
    clientY: number,
  ): { idx: number; paras: HTMLElement[] } {
    const paras = Array.from(
      bodyEl.querySelectorAll<HTMLElement>(":scope > p"),
    );
    let idx = 0;
    for (const para of paras) {
      const r = para.getBoundingClientRect();
      if (clientY > r.top + r.height / 2) idx += 1;
      else break;
    }
    return { idx, paras };
  }

  // Drag the corner handle to resize a placed figure (width_pct). Delta-based so
  // it feels natural at any alignment; the growing edge is the handle's corner
  // (bottom-right normally, bottom-left when right-aligned). Live-updates the CSS
  // width during the drag and commits the snapped value on release.
  function startResize(e: PointerEvent, fig: HTMLElement, p: Placement): void {
    e.preventDefault();
    e.stopPropagation();
    const container = fig.parentElement; // the .cx-body containing block
    const refWidth = container
      ? container.clientWidth
      : fig.getBoundingClientRect().width;
    const startX = e.clientX;
    const startW = fig.getBoundingClientRect().width;
    const dir = p.align === "right" ? -1 : 1;
    const max = p.flow === "wrap" ? WRAP_MAX : 100;
    fig.draggable = false; // suspend the move-drag while resizing
    fig.classList.add("is-resizing");
    let pct = p.width_pct;
    const onMove = (ev: PointerEvent): void => {
      const w = startW + (ev.clientX - startX) * dir;
      pct = Math.max(10, Math.min(max, Math.round((w / refWidth) * 20) * 5));
      fig.style.setProperty("--cx-w", `${pct}%`);
    };
    const onUp = (): void => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      fig.classList.remove("is-resizing");
      fig.draggable = true;
      if (pct !== p.width_pct) update(p.visual_id, { width_pct: pct });
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  function figureEl(p: Placement, v: Visual): HTMLElement {
    const fig = document.createElement("figure");
    fig.className = `cx-fig flow-${p.flow} align-${p.align} page-fit-${p.page_fit}`;
    fig.style.setProperty("--cx-w", `${p.width_pct}%`);
    fig.tabIndex = 0;
    fig.setAttribute("role", "group");
    fig.setAttribute("aria-label", `Figure: ${p.caption || v.id}`);
    fig.draggable = true;
    if (p.visual_id === selected) fig.classList.add("is-selected");

    const badge = document.createElement("span");
    badge.className = "cx-fig-badge";
    badge.textContent = v.type;
    fig.appendChild(badge);

    const img = document.createElement("img");
    img.src = v.src;
    img.alt = p.caption || v.id;
    fig.appendChild(img);

    const dupTitle =
      p.caption &&
      v.embedded_title &&
      p.caption.trim().toLowerCase() === v.embedded_title.trim().toLowerCase();
    if (p.caption && !dupTitle) {
      const cap = document.createElement("figcaption");
      cap.textContent = p.caption;
      fig.appendChild(cap);
    }

    const selectFigure = (): void => {
      selected = p.visual_id;
      render();
    };
    fig.addEventListener("click", (e) => {
      if ((e.target as HTMLElement).closest(".cx-fig-card")) return; // control clicks don't reselect
      selectFigure();
    });
    fig.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        selectFigure();
      }
    });
    fig.addEventListener("dragstart", (e) => {
      e.dataTransfer?.setData(VISUAL_DRAG_TYPE, p.visual_id);
    });

    const handle = document.createElement("span");
    handle.className = "cx-fig-handle";
    handle.setAttribute("aria-hidden", "true");
    handle.title = "Drag to resize";
    handle.addEventListener("pointerdown", (e) => startResize(e, fig, p));
    handle.addEventListener("click", (e) => e.stopPropagation()); // don't select on a resize click
    fig.appendChild(handle);

    // The selected figure carries its layout controls inline (align / flow / width /
    // position / caption / page-fit / remove) instead of a side panel.
    if (p.visual_id === selected) fig.appendChild(buildFigCard(p));
    return fig;
  }

  function iconBtn(
    glyph: string,
    title: string,
    onClick: (e: MouseEvent) => void,
  ): HTMLButtonElement {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cx-icon-btn";
    b.textContent = glyph;
    b.title = title;
    b.setAttribute("aria-label", title);
    b.addEventListener("click", onClick);
    return b;
  }

  function paletteItemEl(v: Visual): HTMLElement {
    // A non-interactive group wrapping ONE place-button + sibling action buttons —
    // never a role=button containing focusable children (ambiguous for AT).
    const item = document.createElement("div");
    item.className = "cx-palette-item";
    item.draggable = true;
    item.setAttribute("role", "group");
    item.setAttribute("aria-label", v.caption || v.id);

    const placeBtn = document.createElement("button");
    placeBtn.type = "button";
    placeBtn.className = "cx-palette-place";
    placeBtn.setAttribute("aria-label", `Place ${v.caption || v.id}`);
    const img = document.createElement("img");
    img.src = v.src;
    img.alt = "";
    const meta = document.createElement("span");
    meta.className = "cx-palette-meta";
    const cap = document.createElement("p");
    cap.className = "cx-palette-cap";
    cap.textContent = v.caption || v.id;
    const type = document.createElement("p");
    type.className = "cx-palette-type";
    type.textContent = v.cleaned ? v.type : `${v.type} · uncleaned`;
    meta.append(cap, type);
    placeBtn.append(img, meta);

    const actions = document.createElement("div");
    actions.className = "cx-palette-actions";
    actions.append(
      iconBtn("✨", "Edit this image with AI", () =>
        openAiImageBox(v.file, v.caption),
      ),
      iconBtn("🗑", "Delete artifact", () => void deleteArtifact(v)),
    );
    item.append(placeBtn, actions);

    // Clicking places into the chapter ON SCREEN. The pipeline's
    // `suggested_anchor` is only a hint, and honouring it over the visible
    // chapter meant a click could file the figure into a chapter the human was
    // not looking at — it then appeared to do nothing. The suggestion is still
    // used to decide which chapter a candidate is OFFERED under (see render);
    // once offered here, the human's current position wins.
    const target =
      chapterByKey.get(selectedChapter)?.anchor ??
      (v.suggested_anchor && chapterByKey.get(anchorKey(v.suggested_anchor))
        ? v.suggested_anchor
        : (data.chapters[0]?.anchor ?? ""));
    placeBtn.addEventListener("click", () => place(v.id, target));
    item.addEventListener("dragstart", (e) =>
      e.dataTransfer?.setData(VISUAL_DRAG_TYPE, v.id),
    );
    item.addEventListener("mouseenter", () => showHoverPreview(v, item));
    item.addEventListener("mouseleave", hideHoverPreview);
    return item;
  }

  // ── hover-to-enlarge preview ──────────────────────────────────────────────
  let hoverEl: HTMLElement | null = null;
  function showHoverPreview(v: Visual, anchorEl: HTMLElement): void {
    if (!hoverEl) {
      hoverEl = document.createElement("div");
      hoverEl.className = "cx-hover-preview";
      hoverEl.appendChild(document.createElement("img"));
      document.body.appendChild(hoverEl);
    }
    (hoverEl.querySelector("img") as HTMLImageElement).src = v.src;
    const r = anchorEl.getBoundingClientRect();
    hoverEl.style.setProperty("--hx", `${Math.max(8, r.left - 372)}px`);
    hoverEl.style.setProperty(
      "--hy",
      `${Math.max(8, Math.min(window.innerHeight - 360, r.top - 40))}px`,
    );
    hoverEl.classList.add("is-visible");
  }
  function hideHoverPreview(): void {
    hoverEl?.classList.remove("is-visible");
  }

  // ── delete an artifact (index entry + file) ───────────────────────────────
  async function deleteArtifact(v: Visual): Promise<void> {
    hideHoverPreview();
    const ok = await confirmDialog({
      title: "Delete this artifact?",
      body: `“${v.caption || v.id}” will be removed from the library and disk. This can't be undone.`,
      confirmLabel: "Delete",
      cancelLabel: "Keep",
      danger: true,
    });
    if (!ok) return;
    try {
      await apiFetch("/api/studio/visual-op", {
        method: "POST",
        body: { action: "delete", slug, id: v.id },
      });
      data.visuals = data.visuals.filter((x) => x.id !== v.id);
      visualsById.delete(v.id);
      placements = placements.filter((p) => p.visual_id !== v.id); // renderer skips missing ids too
      if (selected === v.id) selected = null;
      render();
    } catch (e) {
      await noticeDialog({
        title: "Delete failed",
        body: (e as Error).message,
        danger: true,
      });
    }
  }

  // ── generate / edit an artifact with Gemini ───────────────────────────────
  function openAiImageBox(fromFile?: string, baseCaption?: string): void {
    hideHoverPreview();
    root.querySelector(".cx-aiimg-box")?.remove();
    const panel = root.querySelector<HTMLElement>("#cx-panel-artifacts");
    if (!panel) return;
    const box = document.createElement("div");
    box.className = "cx-aiimg-box";
    const head = document.createElement("p");
    head.className = "cx-aiimg-head";
    head.textContent = fromFile
      ? `Edit “${baseCaption || fromFile}” with AI`
      : "Generate a new image with AI";
    const ta = document.createElement("textarea");
    ta.className = "cx-aiimg-input";
    ta.rows = 3;
    ta.placeholder = fromFile
      ? "Describe the change to make…"
      : "Describe the image to create…";
    const actions = document.createElement("div");
    actions.className = "cx-aiimg-actions";
    const gen = document.createElement("button");
    gen.type = "button";
    gen.className = "cx-action";
    gen.textContent = "Generate";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "cx-action is-secondary";
    cancel.textContent = "Cancel";
    const status = document.createElement("p");
    status.className = "cx-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    actions.append(gen, cancel);
    box.append(head, ta, actions, status);
    panel.insertBefore(box, panel.querySelector("#cx-palette-list"));
    ta.focus();

    cancel.addEventListener("click", () => box.remove());
    gen.addEventListener("click", async () => {
      const prompt = ta.value.trim();
      if (!prompt) {
        status.textContent = "Type a description first.";
        status.classList.add("is-error");
        return;
      }
      gen.disabled = true;
      status.classList.remove("is-error");
      status.textContent =
        "Generating with Gemini… this can take a few seconds.";
      try {
        const anchor = chapterByKey.get(selectedChapter)?.anchor ?? "";
        const j = await apiFetch<{ id: string; file: string; caption: string }>(
          "/api/studio/visual-op",
          {
            method: "POST",
            body: { action: "generate", slug, prompt, fromFile, anchor },
          },
        );
        const nv: Visual = {
          id: j.id,
          type: "generated",
          caption: j.caption,
          file: j.file,
          src: `/api/studio/visual-asset?slug=${encodeURIComponent(slug)}&file=${encodeURIComponent(j.file)}`,
          suggested_anchor: anchor,
          chapter: selectedChapter,
          cleaned: true,
          embedded_title: "",
        };
        data.visuals.push(nv);
        visualsById.set(nv.id, nv);
        box.remove();
        render();
      } catch (e) {
        status.textContent = `Failed: ${(e as Error).message}`;
        status.classList.add("is-error");
        gen.disabled = false;
      }
    });
  }

  // ── inline figure controls (a floating card on the selected figure) ───────
  function buildFigCard(p: Placement): HTMLElement {
    const card = document.createElement("div");
    card.className = "cx-fig-card";
    card.addEventListener("click", (e) => e.stopPropagation());
    card.addEventListener("pointerdown", (e) => e.stopPropagation());
    card.draggable = false;
    card.append(
      alignField(p),
      flowField(p),
      widthField(p),
      anchorField(p),
      positionField(p),
      captionField(p),
      pageFitField(p),
    );
    const del = document.createElement("button");
    del.type = "button";
    del.className = "cx-delete";
    del.textContent = "Remove from book";
    del.addEventListener("click", () => remove(p.visual_id));
    card.appendChild(del);
    return card;
  }

  // ── Refinement tab: AI text actions on the editor selection ────────────────
  interface AiAction {
    kind: string;
    label: string;
    mode?: string;
    explain?: boolean;
    etymology?: boolean;
  }
  const AI_ACTIONS: AiAction[] = [
    { kind: "rewrite", label: "Rewrite", mode: "clarify" },
    { kind: "expand", label: "Expand", mode: "expand" },
    { kind: "condense", label: "Condense", mode: "tighten" },
    { kind: "simplify", label: "Simplify", mode: "simplify" },
    { kind: "explain", label: "Explain", explain: true },
    { kind: "etymology", label: "Etymology", etymology: true },
  ];
  let aiStatusEl: HTMLElement | null = null;
  let aiPopupEl: HTMLElement | null = null;

  function setAiStatus(msg: string, isError = false): void {
    if (!aiStatusEl) return;
    aiStatusEl.textContent = msg;
    aiStatusEl.classList.toggle("is-error", isError);
  }

  function selectionText(): { text: string; from: number; to: number } | null {
    if (!activeEditor) return null;
    const { from, to } = activeEditor.editor.state.selection;
    const text = activeEditor.editor.state.doc
      .textBetween(from, to, " ")
      .trim();
    return text ? { text, from, to } : null;
  }

  function updateAiEnabled(): void {
    const ok = !!selectionText();
    root.querySelectorAll<HTMLButtonElement>(".cx-ai-btn").forEach((b) => {
      b.disabled = !ok;
    });
  }

  function renderAiActions(): void {
    controlsEl.textContent = "";
    const hint = document.createElement("p");
    hint.className = "cx-hint";
    hint.textContent =
      "Select text in the chapter editor, then reshape it with AI. Each result is yours to accept or discard.";
    controlsEl.appendChild(hint);

    const row = document.createElement("div");
    row.className = "cx-ai-row";
    for (const a of AI_ACTIONS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cx-ai-btn";
      b.textContent = a.label;
      b.disabled = true;
      b.addEventListener("click", () => runAiAction(a));
      row.appendChild(b);
    }
    controlsEl.appendChild(row);

    aiStatusEl = document.createElement("p");
    aiStatusEl.className = "cx-status";
    aiStatusEl.setAttribute("role", "status");
    aiStatusEl.setAttribute("aria-live", "polite");
    controlsEl.appendChild(aiStatusEl);
    updateAiEnabled();
  }

  async function runAiAction(a: AiAction): Promise<void> {
    const sel = selectionText();
    if (!activeEditor || !sel) {
      setAiStatus("Select some text in the editor first.", true);
      return;
    }
    aiPopupEl?.remove();
    if (a.etymology) {
      await runEtymology(sel);
      return;
    }
    setAiStatus(`${a.label}…`);
    try {
      let options: string[] = [];
      if (a.explain) {
        const j = await apiFetch<{ text: string }>("/api/ai/explain", {
          method: "POST",
          body: {
            text: sel.text,
            chapter: activeEditor.editor.getText(),
            bookTitle,
          },
        });
        options = [String(j.text)];
      } else {
        // Stays on raw fetch: /api/ai/rewrite reports errors as `{error}` JSON
        // with a non-2xx status (no ok-envelope), and apiFetch would replace the
        // server's message (e.g. "rate_limited") with a generic HTTP line.
        const res = await fetch("/api/ai/rewrite", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            text: sel.text,
            mode: a.mode,
            context: activeEditor.editor.getText().slice(0, 4000),
          }),
        });
        const j = await res.json();
        if (j.error) throw new Error(j.error);
        options = (Array.isArray(j.options) ? j.options : [])
          .map((s: unknown) => String(s).trim())
          .filter(Boolean);
      }
      if (!options.length) throw new Error("no suggestions returned");
      setAiStatus("");
      showAiOptions(a.label, options, sel.from, sel.to);
    } catch (e) {
      setAiStatus(`${a.label} failed: ${(e as Error).message}`, true);
    }
  }

  function showAiOptions(
    label: string,
    options: string[],
    from: number,
    to: number,
  ): void {
    aiPopupEl?.remove();
    const pop = document.createElement("div");
    pop.className = "cx-ai-popup";
    const head = document.createElement("p");
    head.className = "cx-ai-popup-head";
    head.textContent = `${label} — pick one to replace your selection:`;
    pop.appendChild(head);
    options.forEach((opt) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "cx-ai-opt";
      card.textContent = opt;
      card.addEventListener("click", () => {
        activeEditor?.editor
          .chain()
          .focus()
          .insertContentAt({ from, to }, opt)
          .run();
        pop.remove();
        aiPopupEl = null;
        setAiStatus("Applied. Remember to Save prose.");
      });
      pop.appendChild(card);
    });
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "cx-ai-opt-cancel";
    cancel.textContent = "Discard";
    cancel.addEventListener("click", () => {
      pop.remove();
      aiPopupEl = null;
    });
    pop.appendChild(cancel);
    controlsEl.appendChild(pop);
    aiPopupEl = pop;
  }

  interface EtymologyResult {
    inline: string;
    companion: string;
    term?: string;
    arabic?: string;
    root?: string;
    rootPhonetic?: string;
    source?: string;
    uncertain?: boolean;
  }

  // Etymology is richer than the other refine actions: one AI call yields TWO
  // outputs — a compact inline insert for the PDF prose and a chapter-aware
  // teaching note for the Companion Panel. Both are shown for review; accepting
  // replaces the highlighted word inline (autosaved into book.md → the PDF) AND
  // files the companion note.
  async function runEtymology(sel: {
    text: string;
    from: number;
    to: number;
  }): Promise<void> {
    if (!activeEditor) return;
    setAiStatus("Etymology…");
    try {
      const doc = activeEditor.editor.state.doc;
      const context = doc
        .textBetween(
          Math.max(0, sel.from - 240),
          Math.min(doc.content.size, sel.to + 240),
          " ",
        )
        .trim();
      const j = await apiFetch<EtymologyResult>("/api/ai/etymology", {
        method: "POST",
        body: {
          word: sel.text,
          context,
          chapterTitle: chapterByKey.get(selectedChapter)?.title ?? "",
          book: bookTitle,
        },
      });
      setAiStatus("");
      showEtymologyResult(j, sel);
    } catch (e) {
      setAiStatus(`Etymology failed: ${(e as Error).message}`, true);
    }
  }

  function showEtymologyResult(
    r: EtymologyResult,
    sel: { text: string; from: number; to: number },
  ): void {
    aiPopupEl?.remove();
    const pop = document.createElement("div");
    pop.className = "cx-ety-card";

    const head = document.createElement("p");
    head.className = "cx-ety-head";
    head.textContent = `Etymology — ${r.term ?? sel.text}`;
    pop.appendChild(head);

    const meta = document.createElement("p");
    meta.className = "cx-ety-meta";
    meta.textContent = [
      r.root ? `root ${r.root}` : "",
      r.rootPhonetic ? `"${r.rootPhonetic}"` : "",
      r.source ? `via ${r.source}` : "",
    ]
      .filter(Boolean)
      .join(" · ");
    pop.appendChild(meta);

    if (r.uncertain) {
      const warn = document.createElement("p");
      warn.className = "cx-ety-warn";
      warn.textContent =
        "The model was not certain of this root — verify before saving.";
      pop.appendChild(warn);
    }

    const uid = `cx-ety-${Date.now()}-${Math.floor(Math.random() * 1e4)}`;
    const inlineLabel = document.createElement("label");
    inlineLabel.className = "cx-ety-label";
    inlineLabel.htmlFor = `${uid}-inline`;
    inlineLabel.textContent =
      "Inline insert (replaces the word in the PDF prose)";
    const inlineInput = document.createElement("input");
    inlineInput.type = "text";
    inlineInput.id = `${uid}-inline`;
    inlineInput.className = "cx-ety-inline";
    inlineInput.value = r.inline ?? "";
    pop.append(inlineLabel, inlineInput);

    const compLabel = document.createElement("label");
    compLabel.className = "cx-ety-label";
    compLabel.htmlFor = `${uid}-companion`;
    compLabel.textContent =
      "Companion note (teaching explanation for this chapter)";
    const compInput = document.createElement("textarea");
    compInput.id = `${uid}-companion`;
    compInput.className = "cx-ety-companion";
    compInput.rows = 5;
    compInput.value = r.companion ?? "";
    pop.append(compLabel, compInput);

    const actions = document.createElement("div");
    actions.className = "cx-ety-actions";
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "cx-ety-accept";
    accept.textContent = "Insert & file note";
    accept.addEventListener("click", () => {
      void acceptEtymology(r, sel, inlineInput.value, compInput.value, pop);
    });
    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "cx-ety-discard";
    discard.textContent = "Discard";
    discard.addEventListener("click", () => {
      pop.remove();
      aiPopupEl = null;
      setAiStatus("");
    });
    actions.append(accept, discard);
    pop.appendChild(actions);

    controlsEl.appendChild(pop);
    aiPopupEl = pop;
  }

  async function acceptEtymology(
    r: EtymologyResult,
    sel: { text: string; from: number; to: number },
    inline: string,
    companion: string,
    pop: HTMLElement,
  ): Promise<void> {
    const inlineText = inline.trim();
    if (activeEditor && inlineText) {
      activeEditor.editor
        .chain()
        .focus()
        .insertContentAt({ from: sel.from, to: sel.to }, inlineText)
        .run();
    }
    // File the companion note (best-effort; the inline insert already landed).
    const body = companion.trim();
    if (body) {
      try {
        await apiFetch("/api/studio/companion-notes", {
          method: "POST",
          body: {
            slug,
            chapter: safeChapterKey(selectedChapter),
            note: {
              kind: "etymology",
              body,
              anchor:
                `${r.term ?? sel.text} — root ${r.rootPhonetic ?? r.root ?? ""}`.trim(),
              quote: sel.text,
              source: {
                provider: "ai",
                label: `Etymology (${r.source ?? "gemini"})`,
              },
            },
          },
        });
      } catch {
        /* note failed to save; the inline edit is unaffected */
      }
    }
    pop.remove();
    aiPopupEl = null;
    setAiStatus(
      "Etymology inserted into the prose and filed to the Companion Panel.",
    );
  }

  function field(label: string, control: HTMLElement): HTMLElement {
    const wrap = document.createElement("div");
    wrap.className = "cx-field";
    const l = document.createElement("label");
    l.textContent = label;
    wrap.append(l, control);
    return wrap;
  }

  function alignField(p: Placement): HTMLElement {
    const row = document.createElement("div");
    row.className = "cx-btn-row";
    (["left", "center", "right"] as Align[]).forEach((a) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cx-toggle";
      b.textContent = a;
      b.setAttribute("aria-pressed", String(p.align === a));
      b.addEventListener("click", () => update(p.visual_id, { align: a }));
      row.appendChild(b);
    });
    return field("Alignment", row);
  }

  function flowField(p: Placement): HTMLElement {
    const row = document.createElement("div");
    row.className = "cx-btn-row";
    (["standalone", "wrap"] as Flow[]).forEach((f) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cx-toggle";
      b.textContent = f === "wrap" ? "wrap text" : "standalone";
      b.setAttribute("aria-pressed", String(p.flow === f));
      b.disabled = f === "wrap" && p.align === "center";
      // Choosing wrap clamps width into the contract (<=50%) so the user's intent
      // is honored rather than silently reverted to standalone.
      b.addEventListener("click", () =>
        update(
          p.visual_id,
          f === "wrap"
            ? { flow: f, width_pct: Math.min(p.width_pct, WRAP_MAX) }
            : { flow: f },
        ),
      );
      row.appendChild(b);
    });
    return field("Flow", row);
  }

  function widthField(p: Placement): HTMLElement {
    const input = document.createElement("input");
    input.type = "range";
    input.min = "10";
    input.max = String(p.flow === "wrap" ? WRAP_MAX : 100);
    input.step = "5";
    input.value = String(p.width_pct);
    input.setAttribute("aria-label", "Width percent");
    input.addEventListener("input", () =>
      update(p.visual_id, { width_pct: Number(input.value) }),
    );
    return field(`Width — ${p.width_pct}%`, input);
  }

  function anchorField(p: Placement): HTMLElement {
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "Anchor chapter");
    data.chapters.forEach((c) => {
      const o = document.createElement("option");
      o.value = c.anchor;
      o.textContent = c.title;
      o.selected = anchorKey(c.anchor) === anchorKey(p.anchor);
      sel.appendChild(o);
    });
    // Moving to a different chapter resets the paragraph position to the default.
    sel.addEventListener("change", () =>
      update(p.visual_id, { anchor: sel.value, anchor_para: null }),
    );
    return field("Anchor chapter", sel);
  }

  function positionField(p: Placement): HTMLElement {
    const paras = chapterByKey.get(anchorKey(p.anchor))?.paras ?? 0;
    const sel = document.createElement("select");
    const opt = (value: string, label: string, selected: boolean) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = label;
      o.selected = selected;
      sel.appendChild(o);
    };
    sel.setAttribute("aria-label", "Position in chapter");
    opt("", "After intro (default)", p.anchor_para == null);
    opt("0", "Chapter top", p.anchor_para === 0);
    for (let i = 1; i <= paras; i += 1)
      opt(String(i), `After paragraph ${i}`, p.anchor_para === i);
    sel.addEventListener("change", () =>
      update(p.visual_id, {
        anchor_para: sel.value === "" ? null : Number(sel.value),
      }),
    );
    return field("Position in chapter", sel);
  }

  function captionField(p: Placement): HTMLElement {
    const input = document.createElement("input");
    input.type = "text";
    input.value = p.caption;
    input.placeholder = "Caption (optional)";
    input.setAttribute("aria-label", "Caption");
    input.addEventListener("change", () =>
      update(p.visual_id, { caption: input.value }),
    );
    return field("Caption", input);
  }

  function pageFitField(p: Placement): HTMLElement {
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "Page fit");
    (["avoid", "before", "isolate-plate"] as PageFit[]).forEach((f) => {
      const o = document.createElement("option");
      o.value = f;
      o.textContent =
        f === "avoid"
          ? "keep together"
          : f === "before"
            ? "start on new page"
            : "own page";
      o.selected = p.page_fit === f;
      sel.appendChild(o);
    });
    sel.addEventListener("change", () =>
      update(p.visual_id, { page_fit: sel.value as PageFit }),
    );
    return field("Page fit", sel);
  }

  // ── drag targets: drop a visual onto a specific paragraph, not just a chapter ─
  let dropMarker: HTMLElement | null = null;
  function clearDropMarker(): void {
    dropMarker?.classList.remove("cx-drop-before", "cx-drop-after");
    dropMarker = null;
  }
  function showDropMarker(bodyEl: HTMLElement, clientY: number): void {
    const { idx, paras } = paraIndexAt(bodyEl, clientY);
    clearDropMarker();
    if (idx <= 0) {
      const first = bodyEl.firstElementChild as HTMLElement | null;
      if (first) {
        first.classList.add("cx-drop-before");
        dropMarker = first;
      }
    } else if (idx <= paras.length) {
      paras[idx - 1].classList.add("cx-drop-after");
      dropMarker = paras[idx - 1];
    }
  }
  root.querySelectorAll<HTMLElement>(".cx-chapter").forEach((ch) => {
    // The surface the human is actually looking at. In Edit mode — which is how
    // the composer opens — `.cx-body` is hidden, and a hidden element's
    // paragraphs all measure zero, so every drop counted as "below the last
    // paragraph" and landed at the end of the chapter no matter where it was
    // released. Measure the editor when the editor is what's on screen.
    const dropSurface = (): HTMLElement | null => {
      const body = ch.querySelector<HTMLElement>(".cx-body");
      if (body && !body.hidden) return body;
      return ch.querySelector<HTMLElement>(".cx-prose") ?? body;
    };
    ch.addEventListener("dragover", (e) => {
      e.preventDefault();
      ch.classList.add("cx-dragover");
      const surface = dropSurface();
      if (surface) showDropMarker(surface, e.clientY);
    });
    ch.addEventListener("dragleave", () => {
      ch.classList.remove("cx-dragover");
      clearDropMarker();
    });
    ch.addEventListener("drop", (e) => {
      e.preventDefault();
      ch.classList.remove("cx-dragover");
      clearDropMarker();
      const id = e.dataTransfer?.getData(VISUAL_DRAG_TYPE);
      const anchor = ch.dataset.anchor ?? "";
      if (!id || !anchor) return;
      const surface = dropSurface();
      const anchor_para = surface ? paraIndexAt(surface, e.clientY).idx : null;
      if (placements.some((p) => p.visual_id === id))
        update(id, { anchor, anchor_para });
      else place(id, anchor, anchor_para);
    });
  });

  // ── persistence — autosaved, no manual button (see ./autosave) ─────────────
  layoutAutosave = createAutosave({
    onStateChange: mountAutosaveStatus(layoutStatusEl),
    save: async () => {
      // apiFetch throws on failure; createAutosave's catch shows the message.
      await apiFetch("/api/studio/visual-layout", {
        method: "PUT",
        body: { slug, placements },
      });
      return { ok: true };
    },
  });

  showSelectedChapter();
  renderCitations();
  renderAiActions();
  render();

  // If we reloaded mid-edit (autosave re-sync), drop back into Edit on arrival.
  try {
    if (sessionStorage.getItem("cx-restore-edit")) {
      sessionStorage.removeItem("cx-restore-edit");
      enterEditMode();
    }
  } catch {
    /* sessionStorage best-effort */
  }

  // Deselect a placed figure (and hide its inline card) on an outside click.
  document.addEventListener("click", (e) => {
    if (!selected) return;
    const t = e.target as HTMLElement;
    if (t.closest(".cx-fig") || t.closest(".cx-fig-card")) return;
    selected = null;
    render();
  });

  root
    .querySelector<HTMLButtonElement>("#cx-new-ai-image")
    ?.addEventListener("click", () => openAiImageBox());

  // Read shows the chapter exactly as it prints — the same renderMd() output the
  // PDF is built from (chapter opening, drop cap, mushaf verses, citation style).
  // Edit swaps in the TipTap surface, which is seeded from the plain render its
  // schema can round-trip. Without this control the print-faithful view has no
  // way of being reached: the editor opens on boot and nothing else leaves it.
  modeReadBtn?.addEventListener("click", () => setMode("read"));
  modeEditBtn?.addEventListener("click", () => setMode("edit"));

  // The chapter opens straight in the editor, like the podcast editor.
  setMode("edit");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
