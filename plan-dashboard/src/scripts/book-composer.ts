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
import { attach } from "@asifhussain/prose-editor";
import type { ProseEditor } from "@asifhussain/prose-editor";
import { quranQuotationButton } from "./compose-quran-command";
import { anchorKey } from "../../scripts/lib/anchor-key.mjs";
import {
  docToMarkdown,
  PRESERVED_CLASSES,
  mountChapterEditor,
  VISUAL_DRAG_TYPE,
  type ChapterEditor,
} from "./book-md-editor";
import { confirmDialog, noticeDialog } from "./confirm-dialog";
import { imageLightbox } from "./image-lightbox";
import {
  createAutosave,
  mountAutosaveStatus,
  type AutosaveController,
} from "./autosave";
import { createComposeEditorBridge } from "./compose-editor-bridge";
import {
  createComposeLane,
  pendingLane,
  type ComposeLane,
  type PodcastChapterMeta,
} from "./compose-lane";
import { safeChapterKey } from "../lib/reader/companion/keys";
import { apiFetch } from "../lib/api-fetch";
import { createStudioDecos } from "../components/studio/editor/studio-decos";
import {
  createFigureDecos,
  type EditorFigure,
} from "../components/studio/editor/figure-decos";
import { createFenceDecos } from "../components/studio/editor/fence-decos";
import {
  DEFAULT_DEPTH_PROFILE,
  DEPTH_LEVELS_BY_PROFILE,
  type GlossaryEntry,
} from "../components/studio/editor/studio-editor-constants";
import ComposeAiTools from "../components/studio/compose/ComposeAiTools";
import ComposeCompanionTab from "../components/studio/compose/ComposeCompanionTab";
import { mountPanelTextSize } from "./panel-text-size";
import { mountIconTooltips } from "./icon-tooltip";
import { enhanceSelect } from "./select-menu";
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
  /** RCA-001 AI-3 — chapterKey -> why a save would freeze machine text.
   *  Mirrors ComposerView.articulationWarnings in lib/reader/composer.ts. */
  articulationWarnings?: Record<string, string>;
  /** The read-only Podcast lane's chapter list (metadata only). Mirrors
   *  ComposerView.podcastChapters; absent for a book with no podcast source. */
  podcastChapters?: PodcastChapterMeta[];
}

const WRAP_MAX = 50;

// anchorKey comes from the single shared implementation — see the import above.

/**
 * Everything `docToMarkdown` actually knows how to write.
 *
 * Declared by hand rather than derived from the schema on purpose: deriving it
 * would make the package's coverage assertion agree with itself and check
 * nothing. Adding a node to editorExtensions without also teaching the
 * serializer about it must fail loudly here, not quietly in book.md.
 */
const DOC_TO_MARKDOWN_COVERS = [
  "doc",
  "text",
  "paragraph",
  "heading",
  "blockquote",
  "bulletList",
  "orderedList",
  "listItem",
  "codeBlock",
  "horizontalRule",
  "bold",
  "italic",
  "code",
  "strike",
  "link",
];

/**
 * The formatting bar, in order.
 *
 * `strike` and `codeBlock` are deliberately ABSENT even though docToMarkdown
 * writes both: neither `~~x~~` nor a fence has a parse rule on the way back in
 * (renderMarkdown has no rule for either, and neither does the print renderer),
 * so a click would survive one save and then come back as literal punctuation —
 * in the editor, in the reader, AND in the printed page. A button whose output
 * degrades on the second save is worse than no button.
 */
const COMPOSE_TOOLBAR_ITEMS = [
  "undo",
  "redo",
  "|",
  "paragraphFormat",
  "|",
  "bold",
  "italic",
  "code",
  "link",
  "|",
  "bulletList",
  "orderedList",
  "blockquote",
  quranQuotationButton(),
  "|",
  "horizontalRule",
  "clearFormatting",
];

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
  // A native <select> paints its open list through the OS, so the chapter list
  // dropped out of an editorial control as a grey system panel. This swaps in a
  // list we draw ourselves; the <select> stays as the state holder, so every
  // `chapterSelect.value` / `.disabled` / `change` usage below is unaffected.
  const chapterMenu = enhanceSelect(chapterSelect);
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

  // ── Articulation guard (RCA-001 AI-3) ─────────────────────────────────────
  // A save persists the ENTIRE chapter body as a durable human edit, and the
  // pipeline then never re-voices that chapter. For a chapter whose current
  // base never passed articulation, that save freezes machine text — the exact
  // failure that shipped 8 calqued chapters on 2026-07-20. The guard is
  // ADVISORY: a confirmed save always proceeds. Confirmations persist for the
  // session (per book) because autosave routinely reloads the page; a decline
  // is remembered in-memory only, and the status pill's Retry re-asks.
  const articulationWarnings: Record<string, string> =
    data.articulationWarnings ?? {};
  const ARTICULATION_OK_KEY = `cx-articulation-ok:${slug}`;
  const articulationConfirmed = new Set<string>(
    (() => {
      try {
        const raw = sessionStorage.getItem(ARTICULATION_OK_KEY);
        const parsed: unknown = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed.map(String) : [];
      } catch {
        return [];
      }
    })(),
  );
  const articulationDeclined = new Set<string>();
  function confirmArticulationFreeze(chapterKey: string): void {
    articulationConfirmed.add(chapterKey);
    try {
      sessionStorage.setItem(
        ARTICULATION_OK_KEY,
        JSON.stringify([...articulationConfirmed]),
      );
    } catch {
      /* sessionStorage best-effort */
    }
  }

  // ── inspector tabs (Artifacts · Refine & Notes) ───────────────────────────
  // Two tabs, both chapter work: place what you are adding, then reshape and
  // annotate the prose (the former Details tab is merged into Refine). The
  // one-time book-wide decisions — citation style, typography — left the list
  // on 2026-07-22 for the gear's settings dialog: a setting touched once per
  // book should not occupy a daily tab. Companion left earlier (2026-07-21)
  // for the drawer rail.
  const TABS = ["artifacts", "refine"] as const;
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

  // ── Book settings dialog (citation style + typography, behind the gear) ───
  // Same modal contract as confirm-dialog/image-lightbox: Esc, backdrop, X,
  // focus in on open and restored on close. The forms inside were bound at
  // init by class/id exactly as when they were tabs — only their home moved.
  {
    const scrim = root.querySelector<HTMLElement>("#cx-settings-scrim");
    const openBtn = root.querySelector<HTMLButtonElement>("#cx-settings-open");
    const closeBtn =
      root.querySelector<HTMLButtonElement>("#cx-settings-close");
    if (scrim && openBtn && closeBtn) {
      let prevFocus: HTMLElement | null = null;
      const focusables = (): HTMLElement[] =>
        Array.from(
          scrim.querySelectorAll<HTMLElement>(
            "button, input, select, textarea, [href], [tabindex]:not([tabindex='-1'])",
          ),
        ).filter((el) => el.offsetParent !== null);
      const onKey = (e: KeyboardEvent): void => {
        if (e.key === "Escape") {
          e.preventDefault();
          close();
        } else if (e.key === "Tab") {
          // Trap focus inside the dialog: cycle off either end back around.
          const f = focusables();
          if (!f.length) return;
          const i = f.indexOf(document.activeElement as HTMLElement);
          if (e.shiftKey && (i <= 0 || i === -1)) {
            e.preventDefault();
            f[f.length - 1].focus();
          } else if (!e.shiftKey && (i === f.length - 1 || i === -1)) {
            // i === -1: focus fell to <body> (a click on dialog dead space) —
            // without this, forward Tab would walk out behind the scrim.
            e.preventDefault();
            f[0].focus();
          }
        }
      };
      const open = (): void => {
        prevFocus = document.activeElement as HTMLElement | null;
        scrim.hidden = false;
        document.addEventListener("keydown", onKey, true);
        closeBtn.focus();
      };
      const close = (): void => {
        scrim.hidden = true;
        document.removeEventListener("keydown", onKey, true);
        prevFocus?.focus();
      };
      openBtn.addEventListener("click", open);
      closeBtn.addEventListener("click", close);
      scrim.addEventListener("mousedown", (e) => {
        if (e.target === scrim) close();
      });
    }
  }

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
    chapterMenu?.sync();
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
            chapterMenu?.sync();
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
    chapterMenu?.sync();
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
  let composerRte: ProseEditor | null = null;

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

  function exitEdit(): void {
    aiToolsRoot?.unmount();
    aiToolsRoot = null;
    detailsRoot?.unmount();
    detailsRoot = null;
    // companionRoot is deliberately NOT torn down: the notes are a drawer
    // surface of their own now, readable in Read mode too (see renderCompanion).
    // Before the editor: the package holds document-level listeners, and a
    // chapter switch runs this on every change.
    composerRte?.destroy();
    composerRte = null;
    activeEditor?.destroy();
    activeEditor = null;
    activeSaveFlush = null;
    root.querySelector(".cx-edit-shell")?.remove();
    const bodyEl = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
    if (bodyEl) bodyEl.hidden = false;
    if (chapterSelect) chapterSelect.disabled = false;
    chapterMenu?.sync();
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

    // Articulation guard (RCA-001 AI-3), passive half: say so the moment the
    // editor opens on an at-risk chapter, before the first keystroke. The
    // active half — the explicit confirm — sits in the autosave's save().
    const articulationReason = articulationWarnings[selectedChapter];
    if (articulationReason) {
      const warn = document.createElement("p");
      warn.className = "cx-articulation-warn";
      warn.setAttribute("role", "note");
      const warnIcon = document.createElement("i");
      warnIcon.className = "fa-solid fa-triangle-exclamation";
      warnIcon.setAttribute("aria-hidden", "true");
      const warnText = document.createElement("span");
      warnText.textContent =
        `This chapter's prose has not been articulated — ${articulationReason}. ` +
        "Saving freezes the whole chapter as human-authored machine text; the pipeline will never re-voice it.";
      warn.append(warnIcon, warnText);
      shell.append(warn);
    }

    const host = document.createElement("div");
    host.className = "cx-edit-host";

    // The editing-chrome ROW. The formatting toolbar the package builds is
    // inserted at its head once the editor exists (it reads editor state, so it
    // cannot be built before there is an editor); the font/size/paper controls
    // that follow are view preferences, not formatting, and stay host-owned.
    // Deliberately NOT role="toolbar" itself — the package's bar carries that
    // landmark, and nesting two of them would announce a toolbar inside a
    // toolbar.
    const toolbar = document.createElement("div");
    toolbar.className = "cx-edit-toolbar";
    toolbar.setAttribute("role", "group");
    toolbar.setAttribute("aria-label", "Editing view preferences");

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

    // Font, size and paper are all VIEW preferences — none of them reaches
    // book.md. Grouping them into one cluster, pushed to the trailing edge,
    // balances the row and says what they have in common; scattered across two
    // wrapped rows they read as leftovers.
    const viewPrefs = document.createElement("div");
    viewPrefs.className = "cx-view-prefs";
    viewPrefs.setAttribute("role", "group");
    viewPrefs.setAttribute("aria-label", "Editing view preferences");
    viewPrefs.append(fontGroup);
    toolbar.append(viewPrefs);
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
    viewPrefs.append(paperGroup);

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
      // A pipeline fence marker arrives here as bare text (TipTap has no
      // HTML-comment node) and must STAY in the document for preserveFences to
      // restore it — so it is decorated, never removed. See fence-decos.ts.
      createFenceDecos(),
    ]);
    // ── The formatting toolbar ────────────────────────────────────────────────
    // attach(), never mount(): mountChapterEditor above stays the sole owner of
    // the schema (the one the round-trip test parses with), of the `cx-prose`
    // class, and of the handleDrop that swallows a palette drag so it cannot be
    // inserted as prose. The package reads state and contributes UI; it cannot
    // widen or restyle any of that.
    //
    // The serializer handed over is book.md's OWN writer, unchanged, so adopting
    // the package changes nothing about what a save produces. `covers` is the
    // honest list of what that writer actually handles — not a reflection of the
    // schema, which would make the assertion vacuous. Add a node to
    // editorExtensions without teaching docToMarkdown about it and the editor
    // refuses to open, which is the entire point.
    try {
      composerRte = attach(activeEditor.editor, {
        serializer: {
          kind: "custom",
          serialize: docToMarkdown,
          covers: DOC_TO_MARKDOWN_COVERS,
        },
        toolbar: {
          items: COMPOSE_TOOLBAR_ITEMS,
          ariaLabel: "Formatting",
          builtins: {
            // H2 is the CHAPTER boundary in book.md — writeChapterBody splits
            // the file on /^##\s+/ — so an H2 typed inside a chapter body would
            // create a new chapter on save. Only levels below it are offered,
            // and named for what they do rather than for their tag.
            bodyLabel: "Body",
            headingLevels: [
              { level: 3, id: "h3", label: "Section" },
              { level: 4, id: "h4", label: "Subsection" },
            ],
          },
        },
        paste: {
          // The three classes QuotationClasses re-admits. Without these, pasting
          // a verse copied from elsewhere in the book silently loses its shape.
          allowClasses: [...PRESERVED_CLASSES],
        },
      });
      toolbar.prepend(composerRte.toolbarEl as HTMLElement);
    } catch (err) {
      // A failed toolbar must degrade to NO TOOLBAR, never to no editor: this
      // page boots straight into Edit mode, so a throw here would take the whole
      // route down with it.
      console.error("Formatting toolbar unavailable:", err);
    }

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
        // The follow-up queue's way back into this file's machinery: jump to a
        // mark's anchored text, or run a text-transform mark through the SAME
        // immediate-AI path as the toolbar (accepting the result clears the
        // mark via onApplied). Only the transforms are runnable — the
        // knowledge/visual marks wait for the pipeline drain pass.
        queueOps: {
          jumpTo: (anchor: string) => void selectAnchor(anchor),
          runNow: (kind: string, anchor: string, onApplied: () => void) => {
            if (!selectAnchor(anchor)) {
              setAiStatus(
                "Couldn't find the marked text — the chapter may have changed since it was marked.",
                true,
              );
              return;
            }
            const a = AI_ACTIONS.find((x) => x.kind === kind);
            if (a) void runAiAction(a, onApplied);
          },
          runnableKinds: ["rewrite", "expand", "condense", "simplify"],
          // After the instruction box applies its edits, persist and re-render
          // the way every other content change does: flush the prose autosave,
          // then reload preserving chapter + Edit mode. (Painting the edits
          // in-place was abandoned: the tracked-changes decoration layer
          // reliably fails to repaint a replaced block whenever the same
          // transaction also inserts a paragraph.) The note survives the
          // reload via sessionStorage and is re-shown by the remounted tab.
          applyAndSync: async (note: string): Promise<boolean> => {
            try {
              // Scoped to book + chapter so the remounted tab can verify the
              // note belongs to it before showing it.
              sessionStorage.setItem(
                "cx-instruct-note",
                JSON.stringify({ slug, chapter: selectedChapter, note }),
              );
            } catch {
              /* best-effort */
            }
            const saved = activeSaveFlush ? await activeSaveFlush() : true;
            if (!saved) {
              try {
                sessionStorage.removeItem("cx-instruct-note");
              } catch {
                /* best-effort */
              }
              return false;
            }
            try {
              sessionStorage.setItem("cx-restore-edit", "1");
            } catch {
              /* best-effort */
            }
            reloadPreservingChapter();
            return true;
          },
        },
      }),
    );

    // Autosave — no manual "Save prose" button; edits persist themselves (./autosave).
    const proseAutosave: AutosaveController = createAutosave({
      onStateChange: mountAutosaveStatus(shell, () => {
        // An explicit Retry is the deliberate act the articulation guard waits
        // for after a decline — clear the decline so the confirm re-asks.
        articulationDeclined.delete(selectedChapter);
        void proseAutosave.flush();
      }),
      save: async () => {
        if (!activeEditor) return { ok: true };
        // Articulation guard (RCA-001 AI-3), active half: the first save of an
        // at-risk chapter must be a deliberate act. Confirm once per chapter
        // per session; a decline parks the autosave in the error state (the
        // pill's Retry re-asks) rather than nagging on every debounce tick.
        const chapterKey = selectedChapter;
        const freezeReason = articulationWarnings[chapterKey];
        if (freezeReason && !articulationConfirmed.has(chapterKey)) {
          const declinedMsg =
            "the chapter isn't articulated; press Retry to save anyway";
          if (articulationDeclined.has(chapterKey))
            return { ok: false, error: declinedMsg };
          const freeze = await confirmDialog({
            title: "Freeze un-articulated machine text?",
            body:
              `This save would freeze machine text that has not been articulated — ${freezeReason}. ` +
              "The pipeline treats a Composer save as human-authored, so this chapter will never be re-voiced. Save anyway?",
            confirmLabel: "Save anyway",
            cancelLabel: "Don't save",
            danger: true,
          });
          if (!freeze) {
            articulationDeclined.add(chapterKey);
            return { ok: false, error: declinedMsg };
          }
          confirmArticulationFreeze(chapterKey);
        }
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
      applyStyleClasses(
        saved.family,
        saved.translation_font ?? null,
        saved.arabic_font ?? null,
      );
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
      said: (v) =>
        `Saved — English renderings print in ${v.replace(/-/g, " ")}.`,
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
        setStyleStatus(
          status,
          `Couldn't save: ${(e as Error).message}`,
          "error",
        );
      }
    });
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
    flashPlaced(visualId);
  }

  // One-shot arrival highlight on the figure a drop just created, on whichever
  // surface (read body or edit canvas — both build through figureEl) is
  // showing. The class removes itself when its animation ends, so a later
  // re-render never replays it; under prefers-reduced-motion the class simply
  // has no animation and is inert.
  function flashPlaced(visualId: string): void {
    // A short timer, not requestAnimationFrame: in Edit mode the figure is
    // drawn by the editor's own decoration redraw a beat after render()
    // returns, and rAF never fires at all in a hidden/backgrounded tab.
    window.setTimeout(() => {
      const fig = root.querySelector<HTMLElement>(
        `.cx-fig[data-visual-id="${CSS.escape(visualId)}"]`,
      );
      if (!fig) return;
      fig.classList.add("cx-fig-arrived");
      fig.addEventListener(
        "animationend",
        () => fig.classList.remove("cx-fig-arrived"),
        { once: true },
      );
    }, 60);
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
      scopeEl.textContent = ch
        ? `Candidates for “${ch.title}”. Click to read one full size; drag it into the chapter to place it.`
        : "";
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
    fig.dataset.visualId = p.visual_id; // lets the arrival flash find its figure
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
    placeBtn.setAttribute("aria-label", `View ${v.caption || v.id} full size`);
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
      // A pencil, not a sparkle: the sparkle read as "AI magic", and nobody
      // recognized it as the EDIT affordance (the tooltip still says AI).
      iconBtn("✏️", "Edit this image with AI", () =>
        openAiImageBox(v.file, v.caption),
      ),
      iconBtn("🗑", "Delete artifact", () => void deleteArtifact(v)),
    );
    item.append(placeBtn, actions);

    // CLICK reads, DRAG places — two gestures, two meanings (Asif 2026-07-22).
    // Clicking used to place the figure into the chapter, which made "let me
    // look at this first" impossible: the only readable view is the lightbox,
    // and the only way to place is now the drag, whose drop marker says exactly
    // which paragraph the figure will follow. The hover-to-enlarge card that
    // used to shadow the pointer is gone for the same reason — it was too small
    // to read and it covered the list while you moved.
    placeBtn.addEventListener(
      "click",
      () => void imageLightbox({ src: v.src, caption: v.caption || v.id }),
    );
    item.addEventListener("dragstart", (e) => {
      e.dataTransfer?.setData(VISUAL_DRAG_TYPE, v.id);
      item.classList.add("is-dragging"); // ghost the card while it travels
    });
    item.addEventListener("dragend", () =>
      item.classList.remove("is-dragging"),
    );
    return item;
  }

  // ── delete an artifact (index entry + file) ───────────────────────────────
  async function deleteArtifact(v: Visual): Promise<void> {
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

  // Scroll to and select a follow-up mark's anchored text. The mark stores a
  // drift-proof COPY of the target text (anchor_text), so this searches the
  // live document rather than trusting a paragraph ordinal. Offsets map 1:1
  // from a textblock's textContent to ProseMirror positions for inline text
  // (marks included), which is all book.md prose contains.
  function selectAnchor(anchor: string): boolean {
    const ed = activeEditor?.editor;
    const needle = (anchor ?? "").trim();
    if (!ed || !needle) return false;
    let found: { from: number; to: number } | null = null;
    ed.state.doc.descendants((node, pos) => {
      if (found) return false;
      if (!node.isTextblock) return true;
      const i = node.textContent.indexOf(needle);
      if (i >= 0)
        found = { from: pos + 1 + i, to: pos + 1 + i + needle.length };
      return !found;
    });
    if (!found) return false;
    ed.chain().focus().setTextSelection(found).scrollIntoView().run();
    return true;
  }

  async function runAiAction(
    a: AiAction,
    // Fires when the human ACCEPTS a result — the queue's "Run now" passes it
    // so the accepted mark clears itself; toolbar runs pass nothing. Threaded
    // through showAiOptions as a CLOSURE, never module state: two runs whose
    // fetches interleave each keep their own callback bound to their own
    // popup, so accepting one run's result can never clear the other's mark.
    onApplied: (() => void) | null = null,
  ): Promise<void> {
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
      showAiOptions(a.label, options, sel.from, sel.to, onApplied);
    } catch (e) {
      setAiStatus(`${a.label} failed: ${(e as Error).message}`, true);
    }
  }

  function showAiOptions(
    label: string,
    options: string[],
    from: number,
    to: number,
    onApplied: (() => void) | null = null,
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
        // A queue-run mark clears itself once ITS result is accepted — the
        // callback is closed over this popup, so interleaved runs stay safe.
        onApplied?.();
      });
      pop.appendChild(card);
    });
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "cx-ai-opt-cancel";
    cancel.textContent = "Discard";
    cancel.addEventListener("click", () => {
      pop.remove();
      aiPopupEl = null; // discarded — the mark stays queued
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
  //
  // `userMode` remembers the choice the human actually made, so returning from
  // the Podcast lane restores it. It is NOT read off setModeVisual: the flip's
  // own leave() drops the view to Read on its way out, which would make every
  // return land in Read regardless of where the user came from.
  let userMode: "read" | "edit" = "edit";
  modeReadBtn?.addEventListener("click", () => {
    userMode = "read";
    setMode("read");
  });
  modeEditBtn?.addEventListener("click", () => {
    userMode = "edit";
    setMode("edit");
  });

  // ── The lane switch — Reading edition ⇄ Podcast source ────────────────────
  // See compose-lane.ts for why the podcast lane is read-only by construction
  // rather than by intent. `leave` is leaveEditMode, which flushes the pending
  // autosave and destroys the editor BEFORE the pane swaps: a keystroke typed a
  // moment before the flip lands in book.md, and nothing editable survives
  // behind the toggle. Mounted only when the book has a podcast source AND the
  // page rendered the pane for it.
  const podcastPane = root.querySelector<HTMLElement>("#cx-podcast-lane");
  const podcastBody = root.querySelector<HTMLElement>("#cx-podcast-body");
  const podcastSelect =
    root.querySelector<HTMLSelectElement>("#cx-podcast-select");
  // Drawn list, not the OS dropdown — the same treatment the book chapter
  // picker gets above, so the two pickers look like one control in two lanes
  // instead of an editorial list beside a grey system panel.
  const podcastMenu = enhanceSelect(podcastSelect);
  let composeLane: ComposeLane | null = null;
  if (podcastPane && podcastBody && (data.podcastChapters?.length ?? 0) > 0) {
    composeLane = createComposeLane({
      slug,
      chapters: data.podcastChapters ?? [],
      root,
      pane: podcastPane,
      body: podcastBody,
      select: podcastSelect,
      syncSelect: () => podcastMenu?.sync(),
      status: root.querySelector<HTMLElement>("#cx-podcast-status"),
      bookBtn: root.querySelector<HTMLButtonElement>("#cx-lane-book"),
      podcastBtn: root.querySelector<HTMLButtonElement>("#cx-lane-podcast"),
      book: {
        leave: () => leaveEditMode(),
        enter: () => setMode(userMode),
      },
    });
  }

  // A flip whose leave() reloaded the page (prose had changed, so the preview
  // re-renders from the authoritative book.md) left its intent in
  // sessionStorage; honour it here instead of dropping the user back in Edit.
  const restoreLane = pendingLane(slug); // consumed either way — never left stale
  if (composeLane && restoreLane === "podcast") {
    void composeLane.setLane("podcast");
  } else {
    // The chapter opens straight in the editor, like the podcast editor.
    setMode("edit");
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
