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
import { textColourButton } from "./compose-colour-command";
import { alignButtons } from "./compose-align-command";
import { DEFAULT_TEXT_ALIGN } from "../lib/reader/text-align";
import {
  createColourDecos,
  type ColourSpan,
} from "../components/studio/editor/colour-decos";
import {
  createAlignDecos,
  alignablePositions,
} from "../components/studio/editor/align-decos";
import { TOOLBAR_ICONS } from "./toolbar-icons";
import {
  ARABIC_FACES,
  ARABIC_SIZES,
  DEFAULT_ARABIC_FACE,
  DEFAULT_ARABIC_SIZE,
} from "../lib/reader/arabic-typography";
import { anchorKey } from "../../scripts/lib/anchor-key.mjs";
import {
  docToMarkdown,
  PRESERVED_CLASSES,
  mountChapterEditor,
  VISUAL_DRAG_TYPE,
  type ChapterEditor,
} from "./book-md-editor";
import { busyDialog, confirmDialog, noticeDialog } from "./confirm-dialog";
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
// NB: the module also exports `composeLane`, deliberately NOT imported here —
// this file already binds that name to its ComposeLane controller instance.
import { composeChapter, registerComposeChapters } from "./compose-view-state";
import {
  safeChapterKey,
  sectionKeyFromHeading,
} from "../lib/reader/companion/keys";
import { apiFetch } from "../lib/api-fetch";
import { createStudioDecos } from "../components/studio/editor/studio-decos";
import {
  createFigureDecos,
  type EditorFigure,
} from "../components/studio/editor/figure-decos";
import { createFenceDecos } from "../components/studio/editor/fence-decos";
import {
  createCompanionDecos,
  companionRanges,
  type CompanionMark,
} from "../components/studio/editor/companion-decos";
import {
  markPassages,
  normalizeQuote,
  foldText,
} from "../lib/reader/companion/passage-match";
import { defaultStore as defaultCompanionStore } from "../lib/reader/companion/store.client";
import { alignmentGroups } from "../lib/reader/arabic-groups";
import GemCompanionPanel from "../components/reader/companion/GemCompanionPanel";
import {
  DEFAULT_DEPTH_PROFILE,
  DEPTH_LEVELS_BY_PROFILE,
  EDITOR_FONTS,
  type GlossaryEntry,
} from "../components/studio/editor/studio-editor-constants";
import ComposeAiTools from "../components/studio/compose/ComposeAiTools";
import { mountPanelTextSize } from "./panel-text-size";
import { mountIconTooltips } from "./icon-tooltip";
import { enhanceSelect } from "./select-menu";
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
  /** A stable name per prose paragraph, in order — the key the Arabic-source
   *  alignment is stored under. Mirrors ComposerChapter.paraKeys in
   *  lib/reader/composer.ts, computed there by the shared block splitter. */
  paraKeys: string[];
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
 * The text-colour button's two hooks into the page.
 *
 * Module scope because COMPOSE_TOOLBAR_ITEMS is built once, at load, while the
 * chapter the button acts on changes underneath it on every chapter switch.
 * `boot()` assigns both; until it does, the button is inert rather than wrong.
 */
let colourApply: ((quote: string, ink: string | null) => void) | null = null;
let colourActive: (() => string | null) | null = null;
/** The alignment buttons' hooks, assigned by boot for the same reason. */
let alignApply: ((align: string) => void) | null = null;
let alignActive: (() => string | null) | null = null;

/**
 * The formatting bar, in order.
 *
 * `strike` and `codeBlock` are deliberately ABSENT even though docToMarkdown
 * writes both: neither `~~x~~` nor a fence has a parse rule on the way back in
 * (renderMarkdown has no rule for either, and neither does the print renderer),
 * so a click would survive one save and then come back as literal punctuation —
 * in the editor, in the reader, AND in the printed page. A button whose output
 * degrades on the second save is worse than no button.
 *
 * GROUPING (revised 2026-08-02). The separators used to fall where controls had
 * happened to be added. Each group now answers one question, in the order Word
 * and Docs have trained everyone to expect:
 *
 *   history · what block is this · what marks are on the text · what block
 *   structure to make · what to insert
 *
 * `code` and `clearFormatting` were dropped from the bar on Asif's call the same
 * day. Inline code has no use in a scholarly reading edition — this corpus has
 * never contained a literal string — and Clear formatting is a repair tool for
 * pasted-in styling that the paste sanitizer already strips. NOTE that `code`
 * remains in the SCHEMA and in docToMarkdown: backticks round-trip through
 * renderMarkdown, and removing the mark would silently eat any that a chapter
 * already carries on its next save. Only the button is gone; Mod-E still works.
 */
const COMPOSE_TOOLBAR_ITEMS = [
  // History
  "undo",
  "redo",
  "|",
  // What block is this
  "paragraphFormat",
  "|",
  // What marks are on the text — and what colour it is set in
  "bold",
  "italic",
  textColourButton({
    onApply: (quote, ink) => colourApply?.(quote, ink),
    getActive: () => colourActive?.() ?? null,
  }),
  "|",
  // What block structure to make, and how it sits on the page
  ...alignButtons({
    onApply: (a) => alignApply?.(a),
    getActive: () => alignActive?.() ?? null,
  }),
  "bulletList",
  "orderedList",
  "blockquote",
  quranQuotationButton(),
  "|",
  // What to insert
  "link",
  "horizontalRule",
];

/**
 * The bar, dressed in the icons a reader has met in Word, Docs and every CMS.
 *
 * Why an override rather than the package's glyphs: the package ships a
 * dependency-free 16px stroke set so it renders standing alone, and those
 * strokes were being read wrong on this bar — the divider's three stacked lines
 * say "align", and the mark-stripper's slashed J says nothing at all. Font
 * Awesome's editor set is the one everyone already knows, and `book-quran` is
 * what separates the two quotation buttons at a glance: the generic quote mark
 * stays with the generic blockquote, and scripture gets a glyph that says
 * scripture.
 *
 * ALL of them are overridden, deliberately. Font Awesome's solid set is filled
 * and the package's is stroked; re-skinning half a bar would put two drawing
 * styles on one row, which reads worse than either set used alone.
 *
 * The glyphs are VENDORED as inline SVG (toolbar-icons.ts, generated by
 * scripts/vendor-toolbar-icons.mjs) rather than reached by CSS class. The site
 * loads Font Awesome's stylesheet from a CDN, and taking the classes would have
 * made this bar unreadable — every control an empty button — the moment that
 * request failed or had not landed yet. A formatting bar is not a place to
 * accept a glyph that only usually arrives.
 */
const COMPOSE_TOOLBAR_ICONS = TOOLBAR_ICONS;

/**
 * What each control does, and how to use it — the text of the custom tooltip.
 *
 * The browser's own `title` tooltip was the previous answer and it failed twice
 * over: it waits about a second before appearing, and it can only repeat the
 * name you already read off the glyph. These say what the button PRODUCES and
 * what it expects to be selected first, which is the part that is not guessable.
 * Keyed by the package's `data-rte-id`.
 */
const COMPOSE_TOOLBAR_TIPS = {
  undo: { title: "Undo", detail: "Step back through your last edits. ⌘Z." },
  redo: { title: "Redo", detail: "Reapply an edit you undid. ⇧⌘Z." },
  paragraphFormat: {
    title: "Paragraph style",
    detail:
      "Body, Section or Subsection for the paragraph the cursor is in. Chapter headings are not offered — those are the book's own structure.",
  },
  bold: { title: "Bold", detail: "Select text and click. ⌘B." },
  italic: {
    title: "Italic",
    detail:
      "Select text and click. Used for book titles and emphasis. ⌘I. Arabic never slants — it is left upright.",
  },
  bulletList: {
    title: "Bulleted list",
    detail: "Turns the selected paragraphs into a list. Click again to undo.",
  },
  orderedList: {
    title: "Numbered list",
    detail:
      "Turns the selected paragraphs into a numbered list. A list that starts at a number the source states keeps that number.",
  },
  blockquote: {
    title: "Quotation",
    detail:
      "Sets the selected paragraphs as an indented quotation — for a passage quoted from elsewhere. For scripture use the one to the right.",
  },
  quranQuotation: {
    title: "Qur'anic quotation",
    detail:
      "Select the Arabic first, then click: it drops in as a centred Arabic line with an empty line beneath for the English rendering. Prints as the book's verse style.",
  },
  link: {
    title: "Link",
    detail: "Select the words to link, click, then type the address.",
  },
  horizontalRule: {
    title: "Divider",
    detail:
      "Inserts a horizontal rule at the cursor — a break between two passages inside one chapter, not a new chapter.",
  },
};

/** Left by a reload that is really a chapter switch, so the next boot knows to
 *  open the new chapter at its beginning rather than where the last one ended. */
const SCROLL_TOP_ON_BOOT = "cx-scroll-top-on-boot";

function boot(): void {
  // A chapter switch that had to save first reloads the page, and the browser
  // RESTORES scroll across a reload — so the new chapter opened at the foot of
  // the one you left. `reloadPreservingChapter` suppresses that restoration for
  // its one reload; this hands the setting back afterwards.
  //
  // On a TIMER, which is not the first thing anyone would reach for, so: three
  // other shapes were tried against this page and each was measured failing.
  // Scrolling to the top here is overwritten; handing the setting back here, or
  // on `load`, re-enables restoration in time to undo it (the page is heavy
  // enough that `readyState` is already "complete" when this runs, and the
  // restore still comes later); and pinning the top across animation frames is
  // outrun by it too. Suppression is the only thing measured to hold — so the
  // question is only when it is safe to give back, and the honest answer is
  // "after the restore, whenever that was". Three seconds clears it comfortably.
  //
  // The bounded cost, stated plainly: reload the Composer again within those
  // three seconds and that reload also opens at the top.
  try {
    if (sessionStorage.getItem(SCROLL_TOP_ON_BOOT) === "1") {
      sessionStorage.removeItem(SCROLL_TOP_ON_BOOT);
      window.setTimeout(() => {
        if ("scrollRestoration" in history) history.scrollRestoration = "auto";
      }, 3000);
    }
  } catch {
    /* private mode — the reload simply keeps its scroll position */
  }
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
  // Reopen on the chapter this book was last left on — across the editor's own
  // autosave-triggered reload, and equally across a plain F5, a new tab, or
  // tomorrow morning. Registering the live chapter keys first is what makes a
  // remembered chapter that a re-compose has since renamed fall back to the
  // first chapter instead of leaving the page pointed at nothing.
  registerComposeChapters(data.chapters.map((c) => c.key));
  selectedChapter = composeChapter.read(slug) ?? selectedChapter;

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
  // Order MATTERS: the roving tabindex and the arrow-key cycling below read it,
  // so it must match the order the buttons appear in. Refine leads since
  // 2026-07-27 (Asif) — reshaping prose is the daily job; placing artifacts is
  // occasional. Artifacts stays the tab that OPENS, which is unchanged.
  const TABS = ["refine", "artifacts"] as const;
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
  // Refine & Notes opens (Asif, 2026-07-27). It is the daily job — reshaping and
  // annotating prose — while placing artifacts is occasional, so the tab you land
  // on is the one you were going to click. The markup ships in this state too, so
  // the server-rendered panel already matches and there is no flash of Artifacts
  // before this line runs.
  activateTab("refine"); // initialize roving tabindex on the default tab

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

  // ── drawer surfaces (Scholar · Tools) ─────────────────────────────────────
  // ONE drawer, two surfaces, one floating button each. Clicking the lit button
  // closes the drawer and the chapter takes the full page width back. The Scholar
  // used to run a SECOND, independent slide-in that could overlap this one; it is
  // a surface here now, so only one panel can ever be open. The state is a
  // per-browser preference, not book content, so it lives in localStorage — and a
  // preference saved as a retired surface ("companion", and since 2026-07-29
  // "arabic") simply fails the membership test below and falls back to the
  // default.
  const SURFACES = ["scholar", "tools"] as const;
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
    // The Companion is the surface the Composer opens on (Asif, 2026-07-29):
    // the panel is bound to the chapter beside it and lights up as you read, so
    // it is the one that has something to say before you touch anything.
    return "scholar";
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
      // Deliberately does NOT scroll (2026-07-27, Asif). It used to call
      // scrollToWorkingRow() so the drawer — anchored to the top of the grid —
      // could not open off-screen. But that moved the chapter out from under you
      // every time you reached for a tool, and losing your place costs more than
      // an off-screen panel does. Scrolling back up is the #cx-rail-top button
      // beside these, asked for explicitly.
    });
  }

  // The one control whose job IS to move the page. It lands on the working row
  // rather than at scrollY 0 for the reason scrollToWorkingRow documents: the
  // page hero is not what you are working on.
  root
    .querySelector<HTMLButtonElement>("#cx-rail-top")
    ?.addEventListener("click", scrollToWorkingRow);
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

  /** The one place `selectedChapter` moves, so remembering it cannot be
   *  forgotten on a path that sets it directly. */
  function selectChapter(key: string): void {
    selectedChapter = key;
    composeChapter.write(key, slug);
    // A reveal belongs to the chapter it was opened in. Carrying the key across
    // would not merely be untidy: paragraph fingerprints REPEAT — a book of
    // dialogue reuses "The boy said:" in every chapter — so a stale key can match
    // a paragraph here and spring a panel open that nobody asked for.
    arabicRevealed = null;
    // A different chapter has a different alignment; fetched once and cached.
    void syncArabicForChapter();
    // ...and its own coloured runs and paragraph alignments. Already in memory
    // from the one load each, so these only point the live boxes at them.
    syncChapterColours();
    syncChapterAlign();
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
          // landing back in Edit on the new chapter (every load does, since
          // 2026-08-01 — this used to have to ask for it).
          selectChapter(chapterSelect.value);
          reloadPreservingChapter();
          return;
        }
      }
      if (activeEditor) exitEdit(); // tear down the editor bound to the old chapter
      selectChapter(chapterSelect.value);
      selected = null; // a figure selection doesn't carry across chapters
      showSelectedChapter();
      renderScholar(); // explanations follow the chapter — no picker of their own
      render();
      if (wasEditing) setMode("edit"); // stay in Edit on the newly selected chapter
      scrollToChapterTop();
    });
  }

  // Prev/next at the foot of the chapter. Delegated from the root because every
  // chapter renders its own pair and only the visible one can be clicked, so one
  // listener beats N.
  //
  // This deliberately does NOT call selectChapter(): that function moves the key
  // and nothing else, while the picker's `change` handler above owns the autosave
  // flush, the discard confirmation, the editor teardown and the stay-in-Edit
  // restore. Driving the picker and dispatching its event reuses all of it — the
  // alternative is a second way to leave a chapter, which is a second way to lose
  // an unsaved one. `chapterMenu.sync()` is required alongside: the native
  // <select> is only the state holder, and select-menu.ts draws the visible list.
  root.addEventListener("click", (ev) => {
    const btn = (ev.target as HTMLElement | null)?.closest<HTMLButtonElement>(
      ".cx-chapter-nav-btn",
    );
    if (!btn || btn.disabled || !chapterSelect) return;
    const key = btn.dataset.gotoChapter;
    // Absent at the two ends, where the button is also disabled. Checked anyway:
    // `disabled` is a DOM state a stray script could clear, the key is the thing
    // that has to exist, and a missing one would otherwise blank the picker.
    if (!key || key === selectedChapter) return;
    chapterSelect.value = key;
    chapterMenu?.sync();
    chapterSelect.dispatchEvent(new Event("change"));
  });

  // The GOTO_CHAPTER_EVENT listener that used to sit here went with the Arabic
  // drawer surface on 2026-07-29 — the vowelling panel's per-passage chapter
  // links were its only emitter. The event itself still exists on the component,
  // so a future host can wire it again; nothing on this page listens now.

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
  /** Teardown for the formatting bar's tooltips. Re-mounted per chapter, so it
   *  must be released per chapter too — see exitEdit. */
  let disposeToolbarTips: (() => void) | null = null;
  /** Teardown for the paper picker's tooltips — same lifecycle as the bar's. */
  let disposePaperTips: (() => void) | null = null;
  /** Teardown for the Show-changes tooltip — same lifecycle as the bar's. */
  let disposeDiffTip: (() => void) | null = null;

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

  /** The chapter key a Companion note is filed under — the rendered TOC id,
   *  derived from the chapter's raw heading by the one shared rule. This is a
   *  data contract: it is the key the notes already on disk are stored under, so
   *  the rule cannot change without migrating them.
   *
   *  NOT `safeChapterKey(selectedChapter)`, which is what this used to be: the
   *  Composer's own chapter key comes from `anchorKey`, which strips the leading
   *  "N." — so an etymology note for chapter 2 was filed as
   *  `a-stranger-in-the-city` while the reader looked under
   *  `2-a-stranger-in-the-city` and showed nothing. */
  function companionChapterKey(): string {
    const anchor =
      data.chapters.find((c) => c.key === selectedChapter)?.anchor ?? "";
    return sectionKeyFromHeading(anchor) || safeChapterKey(selectedChapter);
  }

  // ── Companion explanations: the panel, and the tint on the passages ────────
  // The panel is mounted HERE rather than as an Astro island because it is a
  // controlled component: the chapter it lists explanations for is the one in the
  // picker, and an island cannot be handed a new prop after mount. The notes it
  // loads come straight back through onNotesChanged, because the same list drives
  // the tint over the prose — one fetch, two consumers, no chance of the panel and
  // the page disagreeing about which sentences are annotated.
  let scholarRoot: Root | null = null;
  const companionNotes: { current: CompanionMark[] } = { current: [] };
  /** The OPEN chapter's coloured runs. A live box, read by the decoration
   *  plugin on every repaint, so colouring a selection shows at once. */
  const colourSpans: { current: ColourSpan[] } = { current: [] };
  /** Every chapter's spans, by anchorKey — one fetch per page load. */
  let colourByChapter: Record<string, ColourSpan[]> = {};
  /** The OPEN chapter's paragraph alignments, and its ordered prose-block keys.
   *  Both live boxes: the decoration plugin reads them on every repaint. */
  const alignSpans: { current: Record<string, string> } = { current: {} };
  const alignKeys: { current: string[] } = { current: [] };
  let alignByChapter: Record<string, Record<string, string>> = {};
  let focusNote: { id: string; nonce: number } | null = null;
  let focusNonce = 0;
  /** Notes whose passage was actually found in the open chapter. The panel lists
   *  only these (Asif, 2026-07-26): a chapter's file also holds reading notes
   *  written against earlier drafts, and after a re-compose most of them quote
   *  sentences the text no longer contains — cards that can never point at
   *  anything. They stay on disk and stay in the LIVE Session. */
  let anchoredIds: string[] = [];
  /** Read mode gets the SAME panel — same cards, same tint, same follow-the-
   *  chapter sync — with the writing withheld (Asif, 2026-07-30). Read is a
   *  reading surface on both sides of the page: a card that mounts a rich-text
   *  editor beside a rendered chapter offers an edit the prose next to it will
   *  not accept. Kept as one boolean set from `setModeVisual`, so the panel can
   *  never disagree with which mode the toggle says it is in. */
  let scholarReadOnly = false;
  /** Of those, the ones whose passage is ON SCREEN right now, in reading order.
   *  The panel expands and lights exactly these — see the scroll sweep below. */
  let inViewIds: string[] = [];

  /** Load every chapter's colours once, then keep the open chapter's box in
   *  step. One fetch rather than one per chapter switch: the file is small, and
   *  a switch that waits on the network paints the chapter uncoloured first and
   *  then flickers into colour. */
  async function loadColours(): Promise<void> {
    try {
      const doc = await apiFetch<{ chapters: Record<string, ColourSpan[]> }>(
        "/api/studio/text-colour",
        { query: { slug } },
      );
      colourByChapter = doc.chapters ?? {};
    } catch {
      colourByChapter = {}; // a book renders uncoloured, never not at all
    }
    syncChapterColours();
  }
  /** Point the live box at the open chapter and repaint both surfaces. */
  function syncChapterColours(): void {
    colourSpans.current = colourByChapter[selectedChapter] ?? [];
    repaintColours();
  }

  /** The alignment half of the same idea. `alignKeys` is the chapter's ordered
   *  prose-block keys, which the decoration matches against by position. */
  function syncChapterAlign(): void {
    alignSpans.current = alignByChapter[selectedChapter] ?? {};
    alignKeys.current = chapterByKey.get(selectedChapter)?.paraKeys ?? [];
    repaintColours(); // one dispatch repaints every decoration plugin
    markAlignedParagraphs();
  }
  async function loadAlign(): Promise<void> {
    try {
      const doc = await apiFetch<{
        chapters: Record<string, Record<string, string>>;
      }>("/api/studio/text-align", { query: { slug } });
      alignByChapter = doc.chapters ?? {};
    } catch {
      alignByChapter = {}; // a book renders left-aligned, never not at all
    }
    syncChapterAlign();
  }
  /** Read mode is rendered HTML, and its top-level `<p>` elements line up with
   *  `paraKeys` one for one — the same correspondence `applyArabicReveals`
   *  relies on, with the same length guard: if they disagree, say nothing. */
  function markAlignedParagraphs(): void {
    const body = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
    if (!body) return;
    body.querySelectorAll(":scope > p").forEach((p) => {
      p.classList.remove("align-center", "align-right");
    });
    const keys = alignKeys.current;
    const paras = [...body.querySelectorAll<HTMLElement>(":scope > p")];
    if (!keys.length || keys.length !== paras.length) return;
    paras.forEach((p, i) => {
      const want = alignSpans.current[keys[i]];
      if (want) p.classList.add(`align-${want}`);
    });
  }
  /** Nudge the editor (its decorations read the box) and re-mark Read mode. */
  function repaintColours(): void {
    const ed = activeEditor?.editor;
    if (ed && !ed.isDestroyed) ed.view.dispatch(ed.state.tr);
    markColourPassages();
  }
  /** Read mode is rendered HTML, not a ProseMirror doc, so it is marked with the
   *  DOM half of the same matcher — exactly as the Companion tint is. */
  function markColourPassages(): void {
    const body = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
    if (!body) return;
    body
      .querySelectorAll(".cx-ink-mark")
      .forEach((el) => el.replaceWith(...el.childNodes));
    for (const span of colourSpans.current) {
      markPassages(
        body,
        [{ id: span.ink, quote: span.quote }],
        `cx-ink-mark ink-${span.ink}`,
      );
    }
  }

  /** Stable identities, declared ONCE. A fresh arrow function per render would
   *  change the panel's props on every re-render, and the panel keys its chapter
   *  load on those props — so passing new ones re-fetched the chapter and reset
   *  which cards were expanded, a beat after a click had just expanded one. */
  const onNotesChanged = (notes: { id: string; quote?: string }[]): void => {
    companionNotes.current = notes.map((n) => ({ id: n.id, quote: n.quote }));
    markCompanionPassages();
  };

  function renderScholar(): void {
    const host = root.querySelector<HTMLElement>("#cx-scholar-mount");
    if (!host) return;
    scholarRoot ??= createRoot(host);
    scholarRoot.render(
      createElement(GemCompanionPanel, {
        slug,
        bookTitle,
        proseSelector: ".cx-chapter",
        docked: true,
        chapter: companionChapterKey(),
        focusNote,
        anchoredIds,
        inViewIds,
        readOnly: scholarReadOnly,
        onNotesChanged,
        onReveal: revealPassage,
      }),
    );
  }

  // ── The Arabic source, above the English, on demand ──────────────────────
  // The alignment is computed offline (scripts/podcast/align_arabic_paragraphs.py)
  // and addressed by paragraph FINGERPRINT, so a paragraph the Composer has since
  // rewritten simply has no entry and offers no control — it never points at the
  // wrong Arabic. Read mode only: the whole surface is display, and nothing here
  // may reach book.md.
  type ArabicPair = {
    fp: string;
    source_paras: number[];
    confidence: "verified" | "bracketed";
  };
  type ArabicChapter = {
    available: boolean;
    vowelled?: boolean;
    pairs: ArabicPair[];
    paragraphs: { number: number; text: string }[];
  };
  const arabicByChapter = new Map<string, ArabicChapter | null>();
  /** The ONE open reveal, by group key (Asif, 2026-07-30).
   *
   *  A single value rather than a set: opening a second panel pushed the first one's
   *  English further from the Arabic above it, and with a few open the column was
   *  more source than translation. One at a time keeps the pairing readable and
   *  makes the control behave like every other accordion on the page — the same
   *  one-card-at-a-time rule the Companion panel already follows.
   *
   *  Not consulted in العربية mode, where every panel is open by definition. */
  let arabicRevealed: string | null = null;
  let arabicMode: "english" | "only" = "english";
  const arabicToggle = root.querySelector<HTMLElement>("#cx-arabic-toggle");
  const arabicEnglishBtn =
    root.querySelector<HTMLButtonElement>("#cx-arabic-english");
  const arabicOnlyBtn =
    root.querySelector<HTMLButtonElement>("#cx-arabic-only");

  async function ensureArabicData(key: string): Promise<ArabicChapter | null> {
    if (arabicByChapter.has(key)) return arabicByChapter.get(key) ?? null;
    let data: ArabicChapter | null;
    try {
      const res = await fetch(
        `/api/studio/arabic-source?slug=${encodeURIComponent(slug)}&chapter=${encodeURIComponent(key)}`,
      );
      const json = await res.json();
      const payload = (json?.data ?? json) as ArabicChapter;
      data = payload?.available ? payload : null;
    } catch {
      data = null; // the reveal is an affordance, never a reason to break the page
    }
    arabicByChapter.set(key, data);
    return data;
  }

  /** Take our asides out. Called before the Companion re-marks, so its text-node
   *  walk and `normalize()` never see the Arabic we injected. */
  function stripArabicReveals(body: HTMLElement): void {
    body.querySelectorAll(".cx-ar-reveal").forEach((el) => el.remove());
    // The group bracket lives on the PARAGRAPHS, which are not ours to remove — so
    // it has to be cleared here too, or a chapter change leaves the previous
    // chapter's grouping drawn around this one's prose.
    body.querySelectorAll<HTMLElement>("[data-ar-part]").forEach((el) => {
      delete el.dataset.arPart;
      delete el.dataset.arOpen;
    });
  }

  function arabicParagraphHtml(
    data: ArabicChapter,
    pair: ArabicPair,
    span = 1,
  ): string {
    const byNumber = new Map(data.paragraphs.map((p) => [p.number, p.text]));
    const blocks = pair.source_paras
      .map((n) => byNumber.get(n))
      .filter(Boolean)
      .map(
        (t) => `<p class="ar" lang="ar" dir="rtl">${escapeHtml(String(t))}</p>`,
      )
      .join("");
    const source =
      pair.confidence === "verified"
        ? `Source ${pair.source_paras.length > 1 ? "paragraphs" : "paragraph"} ${pair.source_paras.join(", ")}`
        : `Somewhere in source paragraphs ${pair.source_paras[0]}–${pair.source_paras[pair.source_paras.length - 1]}`;
    // Say how much English this Arabic became, so a long block of script above two
    // short paragraphs reads as deliberate rather than as a mismatch.
    const label =
      span > 1 ? `${source} — the ${span} paragraphs below` : source;
    return (
      `<div class="cx-ar-body">` +
      `<p class="cx-ar-note" data-confidence="${pair.confidence}">${escapeHtml(label)}</p>` +
      blocks +
      `</div>`
    );
  }

  /** Put an aside before every paragraph the alignment knows about.
   *
   *  An `<aside>`, never a `<p>`: `paraIndexAt` counts `:scope > p` to decide where
   *  a dragged figure anchors, and that number is PERSISTED to visual-layout.json
   *  and drives the printed page. An injected paragraph would move figures in the
   *  book. The control also sits in the aside rather than inside the paragraph, so
   *  the paragraph's own text nodes — which the Companion's matcher walks by
   *  offset — are left exactly as they were. */
  function applyArabicReveals(): void {
    const chapterEl = currentChapterEl();
    const body = chapterEl?.querySelector<HTMLElement>(".cx-body");
    if (!body) return;
    const data = arabicByChapter.get(selectedChapter);
    const keys = chapterByKey.get(selectedChapter)?.paraKeys ?? [];
    if (!data) {
      body.removeAttribute("data-arabic");
      return;
    }
    const paras = [...body.querySelectorAll<HTMLElement>(":scope > p")];
    if (keys.length !== paras.length) {
      // Two different computations that are only ASSUMED to agree — the shared
      // block splitter over the markdown, and what the renderer emitted. If they
      // ever disagree the mapping is meaningless, so say nothing rather than
      // point at the wrong paragraph.
      body.removeAttribute("data-arabic");
      return;
    }
    // The grouping and the positional lookup both live in `alignmentGroups`
    // (lib/reader/arabic-source.ts), where they are unit-tested — including the
    // repeated-speech-tag case that used to collapse thirteen paragraphs onto one
    // source. Read that function's header for why position is the key and the
    // fingerprint is only the edit guard.
    const groups = alignmentGroups(data.pairs, keys);
    if (!groups.length && data.pairs.length !== keys.length) {
      body.removeAttribute("data-arabic");
      return;
    }

    for (const group of groups) {
      const pair = group.pair;
      const span = group.end - group.start + 1;
      const fp = keys[group.start];
      const open = arabicMode === "only" || arabicRevealed === fp;
      const aside = document.createElement("aside");
      aside.className = "cx-ar-reveal";
      aside.dataset.fp = fp;
      if (span > 1) aside.dataset.span = String(span);
      if (open) aside.dataset.open = "1";
      const label =
        span > 1
          ? `Show the Arabic these ${span} paragraphs were translated from`
          : "Show the Arabic this paragraph was translated from";
      aside.innerHTML =
        `<button type="button" class="cx-ar-tab" aria-expanded="${open}" ` +
        `title="${label}" aria-label="${label}">ع</button>` +
        (open ? arabicParagraphHtml(data, pair, span) : "");
      paras[group.start].before(aside);
      // Bracket the English this Arabic produced. Only worth drawing when the
      // group is more than one paragraph — a 1:1 pair needs no bracket to be read
      // as a pair.
      for (let i = group.start; i <= group.end; i++) {
        delete paras[i].dataset.arPart;
        if (span < 2) continue;
        paras[i].dataset.arPart =
          i === group.start ? "first" : i === group.end ? "last" : "mid";
        if (open) paras[i].dataset.arOpen = "1";
        else delete paras[i].dataset.arOpen;
      }
    }
    body.dataset.arabic = arabicMode;
  }

  function escapeHtml(s: string): string {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function setArabicMode(next: "english" | "only"): void {
    arabicMode = next;
    arabicEnglishBtn?.setAttribute("aria-pressed", String(next === "english"));
    arabicOnlyBtn?.setAttribute("aria-pressed", String(next === "only"));
    const body = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
    if (body) {
      stripArabicReveals(body);
      applyArabicReveals();
    }
  }

  arabicEnglishBtn?.addEventListener("click", () => setArabicMode("english"));
  arabicOnlyBtn?.addEventListener("click", () => setArabicMode("only"));

  /** Load this chapter's alignment, then draw. The control stays hidden until the
   *  answer comes back available, so a book without a numbered Arabic edition
   *  never shows a toggle that would do nothing. */
  async function syncArabicForChapter(): Promise<void> {
    const key = selectedChapter;
    const data = await ensureArabicData(key);
    if (key !== selectedChapter) return; // the reader moved on while we fetched
    // Whole-chapter Arabic replaces the text on screen, which is a reading mode,
    // not an editing one — and swapping the content under a surface that autosaves
    // is the RCA-002 shape. Read mode only.
    const usable = Boolean(data) && !activeEditor;
    if (arabicToggle) arabicToggle.hidden = !usable;
    if (!usable && arabicMode === "only") setArabicMode("english");
    const body = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
    if (body) {
      stripArabicReveals(body);
      applyArabicReveals();
    }
  }

  /** Tint every annotated passage in the chapter's READ body, and ask the edit
   *  canvas to redraw its own (decoration-based) tint for the same notes. */
  function markCompanionPassages(): void {
    const body = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
    if (body) {
      // Ours come out first and go back last: the unwrap, `normalize()` and
      // `markPassages` below all walk this subtree, and none of them should ever
      // see the Arabic we injected.
      stripArabicReveals(body);
      body
        .querySelectorAll<HTMLElement>(".cx-note-hl")
        .forEach((el) => el.replaceWith(...el.childNodes));
      body.normalize(); // re-fuse the text nodes an earlier wrap split
      // The READ body is marked even while the editor is open (it is hidden, not
      // removed), so which notes are anchored is answered the same way in both
      // modes — from the prose, never from whichever tint happens to be drawn.
      markPassages(body, companionNotes.current, "cx-note-hl");
      markColourPassages();
      // Read back in DOM order, so the panel lists cards the way the chapter
      // meets them — the same order the LIVE Session lists them in.
      const found = [
        ...new Set(
          [...body.querySelectorAll<HTMLElement>(".cx-note-hl")]
            .map((el) => el.dataset.note ?? "")
            .filter(Boolean),
        ),
      ];
      if (found.join("|") !== anchoredIds.join("|")) {
        anchoredIds = found;
        renderScholar(); // the panel lists only what is anchored
      }
      // …and ours go back, after every walk above has finished. `render()` wipes
      // this body on any figure placement or outside click and then lands here, so
      // this is the one place the reveals need restoring from.
      applyArabicReveals();
    }
    // Same idiom as syncEditorFigures: an empty transaction asks the decoration
    // plugins to recompute against the notes they now see.
    if (activeEditor)
      activeEditor.editor.view.dispatch(activeEditor.editor.state.tr);
    // The tint just moved — which passages are on screen is now a different
    // question, and nobody has scrolled to ask it. Loading a chapter, switching
    // chapters and flipping Read/Edit all land here, so this is the one place the
    // sync needs re-running from besides the scroll itself. Next frame, after the
    // marks have been laid out.
    scheduleSweep();
  }

  // ── Scroll sync, the prose→card direction (Asif, 2026-07-29) ──────────────
  // The Scholar panel TRACKS the chapter. As a tinted passage scrolls into view
  // its card lights up (an accent ring) and expands itself; when that passage
  // leaves the viewport the card goes dark and shuts again. The panel scrolls so
  // the topmost lit card sits at the top of the list.
  //
  // This supersedes the scroll-only sync of 2026-07-28, which moved the list but
  // never opened anything: with every card shut, arriving at the right card still
  // showed only its title, and the one-card-at-a-time rule meant the single open
  // card was almost never the one whose sentence was on screen. Expanding is the
  // whole point of pairing the two columns; the one thing it must not do is close
  // a card someone is typing in, and the panel guards that by skipping the sync
  // while the caret is inside the list.
  //
  // A scroll SWEEP rather than an IntersectionObserver, deliberately: the tint
  // exists twice — spans in the read body, decorations in the edit canvas,
  // whichever is visible — and both are torn down and rebuilt on every re-mark
  // and every decoration redraw, so registered observations go stale in both
  // modes. Sweeping whatever `.cx-note-hl` is visible AT scroll time needs no
  // registration and is mode-blind.
  let syncFrame = 0;
  /** The last in-view set synced for, joined. Re-sweeps that compute the same set
   *  — including the ones the panel's OWN scrolling triggers through the capture
   *  listener — do nothing, so the sync can never fight the reader for the panel. */
  let lastSyncedMarks = "";

  /**
   * After a chapter saves, re-point every explanation whose sentence was edited
   * at the wording that sentence now carries (Asif, 2026-08-02).
   *
   * A note stores a COPY of the sentence it explains, and the tint is found by
   * searching the chapter for that copy. Before this, rewording an explained
   * sentence therefore orphaned its note the instant the first character landed
   * — the highlight vanished, the card dropped off the panel, and nothing in the
   * UI could ever point it back, so the only way out was to delete the note and
   * write it again. The tint now MAPS through edits (companion-decos.ts), which
   * means the editor still knows where each note sits; this writes that back.
   *
   * Runs only after the prose itself is safely on disk, so the wording filed
   * here is the wording the chapter actually has.
   *
   * The guards all fail in the same direction — leave the note ALONE — because a
   * card confidently pointing at the wrong passage is worse than one that has
   * plainly come unstuck:
   *   - no mapped range: the text was deleted outright. Never guess where it went.
   *   - unchanged wording: the edit was elsewhere; nothing to file.
   *   - too short to be a passage: below the floor `findPassage` will match on
   *     (4 folded characters), so filing it would anchor the note to noise.
   */
  async function reanchorEditedNotes(): Promise<void> {
    if (!activeEditor) return;
    const { doc } = activeEditor.editor.state;
    const ranges = companionRanges(activeEditor.editor.state);
    const chapter = companionChapterKey();
    for (const note of companionNotes.current) {
      if (!note.quote) continue;
      const range = ranges.get(note.id);
      if (!range || range.to <= range.from) continue;
      const now = normalizeQuote(
        doc.textBetween(range.from, range.to, " ", " "),
      );
      if (!now || now === normalizeQuote(note.quote)) continue;
      if (foldText(now).length < 4) continue;
      // Sequential, not in parallel: every one of these rewrites the SAME
      // chapter file, and the store is a read-modify-write.
      await defaultCompanionStore.reanchor(slug, chapter, note.id, now);
      // Keep our own copy in step, so the tint's next rebuild derives from the
      // wording now on disk rather than from the wording it replaced.
      note.quote = now;
    }
  }

  /** Scroll the panel so this note's card sits at the top of the card list. */
  function syncCardToMark(noteId: string): void {
    const surface = root.querySelector<HTMLElement>("#cx-surface-scholar");
    if (!surface || surface.hidden) return; // Scholar surface not showing
    const card = surface.querySelector<HTMLElement>(
      `.xpl[data-note="${CSS.escape(noteId)}"]`,
    );
    if (!card) return;
    // The drawer's scroll contract lives on whichever ancestor actually
    // scrolls — found rather than named, so a drawer re-layout cannot silently
    // strand this at a non-scrolling node.
    let scroller: HTMLElement | null = null;
    for (let p = card.parentElement; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (
        /(auto|scroll)/.test(cs.overflowY) &&
        p.scrollHeight > p.clientHeight
      ) {
        scroller = p;
        break;
      }
    }
    if (!scroller) return;
    const delta =
      card.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
    scroller.scrollTo({
      top: scroller.scrollTop + delta,
      behavior: "smooth",
    });
  }

  /** Every tint mark visible in the viewport, in reading order, drives the panel.
   *
   *  All of them, not just the topmost: a passage that is on screen has a card
   *  that should be open, and picking one winner would leave the reader looking
   *  at two lit sentences and one open card. Reading order comes free — the marks
   *  are read in DOM order and a passage cannot be tinted twice — and it is the
   *  order the panel already lists cards in, so the open ones stay in place
   *  instead of the list reshuffling under them. */
  function sweepVisibleMarks(): void {
    const scope = root.querySelector<HTMLElement>(".composer-preview");
    if (!scope) return;
    const vh = window.innerHeight;
    const seen = new Set<string>();
    const found: string[] = [];
    for (const el of scope.querySelectorAll<HTMLElement>(".cx-note-hl")) {
      if (el.offsetParent === null) continue; // the hidden twin of the tint
      const r = el.getBoundingClientRect();
      if (r.bottom <= 0 || r.top >= vh) continue;
      const id = el.dataset.note;
      if (!id || seen.has(id)) continue;
      seen.add(id);
      found.push(id);
    }
    const key = found.join("|");
    if (key === lastSyncedMarks) return;
    lastSyncedMarks = key;
    inViewIds = found;
    renderScholar(); // expands + lights exactly these cards
    // Two frames, not one. React commits the re-render on its own scheduler, and
    // a card that is still shut when it is measured is a fraction of its open
    // height — scrolling to it then lands somewhere else entirely once it opens.
    // The first frame lets the commit land, the second measures the result.
    if (found.length)
      requestAnimationFrame(() =>
        requestAnimationFrame(() => syncCardToMark(found[0])),
      );
  }

  /** One sweep per frame, whatever asked for it. */
  function scheduleSweep(): void {
    cancelAnimationFrame(syncFrame);
    syncFrame = requestAnimationFrame(sweepVisibleMarks);
  }

  // Capture phase, so the sweep hears every scroller — the page, the preview
  // column, whichever the layout uses. Coalesced to one sweep per frame.
  document.addEventListener("scroll", scheduleSweep, {
    capture: true,
    passive: true,
  });
  // A resize reflows the prose, so different passages are on screen afterwards
  // even though nothing scrolled.
  window.addEventListener("resize", scheduleSweep, { passive: true });

  /** Bring a note's passage into view and flash it — the card→prose direction. */
  function revealPassage(noteId: string): void {
    const scope = root.querySelector<HTMLElement>(".composer-preview");
    const marks = Array.from(
      scope?.querySelectorAll<HTMLElement>(
        `.cx-note-hl[data-note="${CSS.escape(noteId)}"]`,
      ) ?? [],
    );
    scope
      ?.querySelectorAll<HTMLElement>(".cx-note-hl.is-active")
      .forEach((el) => el.classList.remove("is-active"));
    // Flag BOTH twins (read span + edit decoration) so the flash survives a
    // mode toggle — but scroll to the VISIBLE one. The tint exists twice and
    // `marks[0]` is the read body's span, which in Edit mode is hidden and
    // scrollIntoView on it is a silent no-op — the click appeared to do
    // nothing, which is exactly how it presented.
    marks.forEach((el) => el.classList.add("is-active"));
    marks
      .find((el) => el.offsetParent !== null)
      ?.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  // A prose autosave writes book.md on disk but the page still holds the ORIGINAL
  // server render in memory; reload (preserving the chapter) to re-sync the preview.
  // The chapter is already persisted by `selectChapter`, but write it here too:
  // the very first chapter of a session was never *selected*, only defaulted to.
  function reloadPreservingChapter(): void {
    composeChapter.write(selectedChapter, slug);
    // Land the new chapter at its beginning. Without this the reload restores the
    // old scroll position and opens at the foot of the chapter just left — the
    // same complaint the in-page switch had, arriving by a different route.
    //
    // Suppress the browser's scroll restoration for this one reload, so the new
    // chapter opens at its beginning. The flag is not what scrolls — it tells the
    // next boot that this page owes the setting back, which is what keeps every
    // ORDINARY reload of the Composer restoring its position as before.
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
    try {
      sessionStorage.setItem(SCROLL_TOP_ON_BOOT, "1");
    } catch {
      /* best-effort; the reload still works, it just keeps its position */
    }
    window.location.reload();
  }

  /**
   * Put the reader at the start of the chapter that just loaded.
   *
   * Called at the END of the picker's change handler rather than from the
   * prev/next buttons, and that placement is the point: the handler has four
   * ways to bail out early — a failed autosave the human declined to discard, a
   * save that triggers a full reload, an unchanged key, no picker — and only the
   * path that actually completed a switch reaches this line. Wired to the
   * buttons instead, it would have scrolled away from a chapter you had just
   * chosen to stay on.
   *
   * It covers the picker too, harmlessly: that control sits at the top of the
   * page, so a reader using it is already here.
   *
   * INSTANT, not smooth. A chapter switch replaces everything on the page — it
   * is a navigation, and animating a long scroll back up from the foot of a
   * chapter would make the reader watch the old text fly past on their way to
   * new text. Nothing to guard for reduced motion, because there is no motion.
   */
  function scrollToChapterTop(): void {
    window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
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
    // Before the editor: the package holds document-level listeners, and a
    // chapter switch runs this on every change.
    // Tooltips first — they hold window-level listeners and a body-level node,
    // and their triggers are about to be removed from under them.
    disposeToolbarTips?.();
    disposeToolbarTips = null;
    disposePaperTips?.();
    disposePaperTips = null;
    disposeDiffTip?.();
    disposeDiffTip = null;
    // The Arabic controls live in the toolbar being removed below. Dropped here
    // so a later sync repaints nothing rather than a detached element.
    arabicFaceSel = null;
    arabicSizeVal = null;
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
    // The SAME list the Studio editor offers, imported rather than restated. The two
    // editors already share one localStorage key by design, so a face listed in only
    // one of them is a value the other rejects on load — a private copy here was a
    // drift waiting to happen, and adding Lexend and Cinzel is exactly the change
    // that would have caused it.
    const FONTS = EDITOR_FONTS;
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
    // Deliberately NOT labelled, though its Arabic neighbour is. Naming the
    // exception is enough: everything on this row is a screen preference EXCEPT
    // the Arabic pair, so one accent-coloured "ARABIC" plus the hairline between
    // the groups draws the line, and a matching "SCREEN" only spent 63px saying
    // the same thing twice — which was the difference between this cluster
    // fitting on one row and spilling onto a third. Each control still carries
    // its own name and tooltip.
    fontGroup.title =
      "Font and size for this editing view only — never the printed book";
    fontGroup.append(fontSel, sizeWrap);

    // Font, size and paper are all VIEW preferences — none of them reaches
    // book.md. Grouping them into one cluster, pushed to the trailing edge,
    // balances the row and says what they have in common; scattered across two
    // wrapped rows they read as leftovers.
    const viewPrefs = document.createElement("div");
    viewPrefs.className = "cx-view-prefs";
    viewPrefs.setAttribute("role", "group");
    viewPrefs.setAttribute("aria-label", "Editing view preferences");
    // ── The BOOK's Arabic face and size ──────────────────────────────────────
    // Deliberately its own labelled cluster, and deliberately FIRST, ahead of
    // the screen preferences: it is the pair that changes the book, so it should
    // not read as a footnote to the pair that changes nothing.
    //
    // The face and size are also chips in the Typography panel, and that is
    // not a duplicate implementation — both call setArabicStyle(), which is the
    // one place that applies the class, writes the artifact and re-checks the
    // other surface's control. Change the save contract there, not here.
    viewPrefs.append(buildArabicGroup(), fontGroup);
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
    // No "Paper" caption and no button text: three swatches in the three paper
    // colours ARE the control, the way every reading app draws it, and the words
    // were costing ~180px on a row that had none to spare. Each name survives as
    // the button's accessible name (visually hidden, not removed) and as its
    // tooltip, so nothing here is carried by colour alone.
    paperGroup.title = "Paper colour for this editing view — never the PDF";
    const paperBtns: HTMLButtonElement[] = [];
    for (const p of PAPERS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cx-paper-btn";
      b.dataset.paper = p.id;
      b.title = `${p.name} paper`;
      const bName = document.createElement("span");
      bName.className = "cx-vh"; // the accessible name, off-screen not absent
      bName.textContent = p.name;
      b.append(bName);
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
    // These three lost their words to make the row fit, so their meaning now
    // rests on a tooltip — which makes the browser's own, a second late and
    // unstyled, the wrong one to leave them with. Same module and same prompt
    // delay as the formatting bar; `dropNativeTitle` is what stops both
    // appearing. Torn down with the toolbar in exitEdit.
    disposePaperTips = mountIconTooltips(paperGroup, {
      trigger: ".cx-paper-btn",
      content: {
        light: { title: "Light paper", detail: "White page, black text." },
        sepia: {
          title: "Sepia paper",
          detail: "Warm cream page — closest to how the book prints.",
        },
        dark: {
          title: "Dark paper",
          detail: "Dark page for low light. Arabic ink lifts to stay readable.",
        },
      },
      keyOf: (el) => el.dataset.paper ?? "",
      delayIn: 120,
      dropNativeTitle: true,
    });

    // ── Show changes ─────────────────────────────────────────────────────────
    // Word-level track changes for HUMAN edits, off by default. Compose is a
    // writing surface: with it always on, accepting an AI rewrite repainted the
    // whole paragraph as strikethrough-plus-underline, so the version you had
    // just chosen was the hardest one to read. The edited blocks still carry the
    // para-dirty tint, so "changed and unsaved" never depended on this.
    const diffToggle = document.createElement("button");
    diffToggle.type = "button";
    diffToggle.className = "cx-diff-toggle";
    // Icon-only, like the paper swatches: the words cost 126px on the row that
    // the colour button had just pushed back to three lines, and this is a
    // toggle whose meaning a tooltip carries as well as a caption does. The
    // caption survives off-screen as the accessible name.
    diffToggle.innerHTML = TOOLBAR_ICONS.showChanges.svg;
    const diffName = document.createElement("span");
    diffName.className = "cx-vh";
    diffName.textContent = "Show changes";
    diffToggle.append(diffName);
    let showDiff = false;
    try {
      showDiff = localStorage.getItem("cx-editor-show-changes") === "1";
    } catch {
      /* preference is best-effort */
    }
    const paintDiffToggle = (): void => {
      bridge.showEditDiffRef.current = showDiff;
      diffToggle.setAttribute("aria-pressed", String(showDiff));
      // `decorations()` reads the box live, so ANY dispatch repaints. An empty
      // transaction is the cheapest one that is not an edit — it must not touch
      // the document, or toggling a VIEW would dirty the chapter.
      const ed = activeEditor?.editor;
      if (ed && !ed.isDestroyed) ed.view.dispatch(ed.state.tr);
    };
    diffToggle.addEventListener("click", () => {
      showDiff = !showDiff;
      try {
        localStorage.setItem("cx-editor-show-changes", showDiff ? "1" : "0");
      } catch {
        /* preference is best-effort */
      }
      paintDiffToggle();
    });
    // Row 2, with the view preferences — which is what it is. It sat on row 1
    // between 2026-08-02 morning and afternoon, to buy the preference cluster
    // the width it needed for one line; the three alignment buttons then took
    // row 1 past its own width, and this is the 45px that brings it back. The
    // toggle is a display preference either way, so the row it lives on is a
    // budget question rather than a semantic one.
    viewPrefs.append(diffToggle);
    disposeDiffTip = mountIconTooltips(toolbar, {
      trigger: ".cx-diff-toggle",
      content: {
        diff: {
          title: "Show changes",
          detail:
            "Marks what you have changed in this chapter since it loaded, word by word. A working view — it never reaches the book.",
        },
      },
      keyOf: () => "diff",
      delayIn: 120,
      dropNativeTitle: true,
    });

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
      // The Companion tint, as a DECORATION: an annotated passage is visible
      // while you edit, and cannot reach book.md on the next autosave.
      createCompanionDecos({ notesRef: companionNotes }),
      // Per-selection text colour, from the sidecar. A decoration for the same
      // reason the Companion tint is one: it is visible while you edit and
      // cannot reach book.md on the next autosave.
      createColourDecos({ spansRef: colourSpans }),
      // Paragraph alignment, from the sidecar. A node decoration for the same
      // reason the colour is an inline one: it cannot reach book.md.
      createAlignDecos({ alignRef: alignSpans, keysRef: alignKeys }),
      // A pipeline fence marker arrives here as bare text (TipTap has no
      // HTML-comment node) and must STAY in the document for preserveFences to
      // restore it — so it is decorated, never removed. See fence-decos.ts.
      createFenceDecos(),
    ]);
    paintDiffToggle();

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
          icons: COMPOSE_TOOLBAR_ICONS,
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
      // Our own tooltip, replacing the browser's. `dropNativeTitle` is what
      // makes it a replacement rather than a second one appearing a second
      // later on top of it. The bar's dropdown button is included: it carries a
      // `data-rte-id` too, so one selector covers the whole row.
      disposeToolbarTips = mountIconTooltips(
        composerRte.toolbarEl as HTMLElement,
        {
          trigger: "button[data-rte-id], .rte-select[data-rte-id] > button",
          content: COMPOSE_TOOLBAR_TIPS,
          // The dropdown's focusable is a button INSIDE the id-bearing wrapper,
          // so read the id from whichever of the two actually has it.
          keyOf: (el) =>
            el.dataset.rteId ?? el.parentElement?.dataset.rteId ?? "",
          delayIn: 120,
          dropNativeTitle: true,
        },
      );
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
            reloadPreservingChapter();
            return true;
          },
        },
      }),
    );

    // Autosave — no manual "Save prose" button; edits persist themselves (./autosave).
    const proseAutosave: AutosaveController = createAutosave({
      // RCA-002 AI-1. markDirty() below is wired to the editor's `update`
      // event, which fires for things that are not edits — a stray keystroke,
      // a pointer-drag that lands where it started, a normalisation on mount.
      // Fingerprinting the serialized chapter means such an event writes
      // nothing at all, and — since docToMarkdown's round trip is not
      // byte-exact on real content — that reflow of untouched paragraphs never
      // reaches book.md on its own. A genuine edit still saves; see autosave.ts.
      fingerprint: () => activeEditor?.toMarkdown() ?? "",
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
        // The prose is on disk; now keep the explanations attached to it. Never
        // allowed to fail the save — the chapter is already safe, and an
        // explanation that stayed on its old wording is a note to re-point, not
        // a reason to tell the author their work did not persist.
        try {
          await reanchorEditedNotes();
        } catch {
          /* best-effort; the tint still shows where the note sits */
        }
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
    // The Arabic toggle is a Read-mode control; entering Edit withdraws it and
    // drops back to English so the editor is never showing a swapped chapter.
    void syncArabicForChapter();
    // In Read mode the Tools surface has nothing to act on — Refinement and
    // Details drive the editor, which is torn down — so it is disabled and the
    // drawer falls closed if it was showing them. Companion stays available on
    // purpose: private notes are exactly what a reading pass wants beside the
    // page. The state is NOT persisted here, so returning to Edit restores
    // whatever the reader had chosen rather than "closed".
    const reading = mode === "read";
    // The Companion follows the mode: read-only cards in Read, editable in Edit.
    // Re-rendered here rather than left to the next sweep, because the mode can
    // change without a scroll and a stale editable card would still take a
    // keystroke.
    if (scholarReadOnly !== reading) {
      scholarReadOnly = reading;
      renderScholar();
    }
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
        arabic_size?: string;
        arabic_ink?: string;
      }>("/api/studio/citation-style", { query: { slug } });
      checkRadio("citation-style", saved.family);
      checkRadio("translation-font", saved.translation_font);
      checkRadio("arabic-font", saved.arabic_font);
      checkRadio("arabic-size", saved.arabic_size);
      checkRadio("arabic-ink", saved.arabic_ink);
      // The page root is server-rendered with the saved faces already, so this
      // only matters when the artifact changed under a page that was left open.
      applyStyleClasses(
        saved.family,
        saved.translation_font ?? null,
        saved.arabic_font ?? null,
        saved.arabic_size ?? null,
        saved.arabic_ink ?? null,
      );
      syncArabicToolbar();
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
    arabicSize: string | null = null,
    arabicInk: string | null = null,
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
    // The DEFAULT step and ink stamp no class — they are the :root declaration
    // in quote-typography.css, so `swap` here only clears (see swapOrClear).
    if (arabicSize) swapOrClear("ars-", arabicSize, "standard");
    if (arabicInk) swapOrClear("ari-", arabicInk, "maroon");
  }
  /** Like `swap`, but a value equal to the DEFAULT removes the class rather than
   *  adding one for it. Keeps the live page in exact agreement with what the
   *  server-side class list and the printed body carry: one declaration for the
   *  default, never two that have to agree. */
  function swapOrClear(prefix: string, value: string, dflt: string): void {
    root.classList.forEach((c) => {
      if (c.startsWith(prefix)) root.classList.remove(c);
    });
    if (value !== dflt) root.classList.add(`${prefix}${value}`);
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
    "arabic-size": {
      field: "arabic_size",
      said: (v) =>
        `Saved — all Arabic prints at the ${v} size, terms included.`,
    },
    "arabic-ink": {
      field: "arabic_ink",
      said: (v) => `Saved — Arabic prints in ${v}.`,
    },
  };
  /**
   * Apply one style choice everywhere it shows, then persist it.
   *
   * The single entry point for all five settings, from BOTH surfaces that offer
   * them — the chips in the settings dialog and the Arabic face/size controls on
   * the editor toolbar. It restyles the live page, re-checks the other surface's
   * control so the two can never disagree about what the book is set to, and
   * PUTs only the field that changed (the route carries the rest over from disk,
   * so saving a face cannot wipe the family).
   *
   * `group` is the radio-group name, which is also the key into STYLE_FIELDS —
   * one name per setting, whichever control the human actually touched.
   */
  async function setArabicStyle(
    group: string,
    value: string,
    status: HTMLElement | null,
  ): Promise<void> {
    const spec = STYLE_FIELDS[group];
    if (!spec) return;
    applyStyleClasses(
      group === "citation-style" ? value : null,
      group === "translation-font" ? value : null,
      group === "arabic-font" ? value : null,
      group === "arabic-size" ? value : null,
      group === "arabic-ink" ? value : null,
    );
    checkRadio(group, value); // the dialog's chip, when the toolbar was the source
    syncArabicToolbar(); // ...and the toolbar, when the chip was
    setStyleStatus(status, "Saving…", "");
    try {
      await apiFetch("/api/studio/citation-style", {
        method: "PUT",
        body: { slug, [spec.field]: value },
      });
      setStyleStatus(status, spec.said(value), "saved");
    } catch (e) {
      setStyleStatus(status, `Couldn't save: ${(e as Error).message}`, "error");
    }
  }

  for (const form of styleForms) {
    const status = form === typeForm ? typeSave : citeSave;
    form.addEventListener("change", (ev) => {
      const t = ev.target as HTMLInputElement;
      if (!STYLE_FIELDS[t?.name ?? ""] || !t.checked) return;
      void setArabicStyle(t.name, t.value, status);
    });
  }

  /** The toolbar's face dropdown and size stepper, if an editor is open. Held
   *  here rather than passed around because the toolbar is rebuilt on every
   *  chapter switch while this closure lives for the page. */
  let arabicFaceSel: HTMLSelectElement | null = null;
  let arabicSizeVal: HTMLElement | null = null;

  /** The book's current face/size, read from the page root — the same classes
   *  the server stamped and `swapOrClear` maintains, so there is no second copy
   *  of the state to fall out of step. Absent class = the default. */
  function currentArabic(prefix: string, dflt: string): string {
    const hit = Array.from(root.classList).find(
      (c) => c.startsWith(prefix) && c !== prefix,
    );
    return hit ? hit.slice(prefix.length) : dflt;
  }

  /** Repaint the toolbar controls from the page root. Safe when no editor is
   *  open — both refs are null between chapters. */
  function syncArabicToolbar(): void {
    const face = currentArabic("ar-", DEFAULT_ARABIC_FACE);
    const size = currentArabic("ars-", DEFAULT_ARABIC_SIZE);
    if (arabicFaceSel) arabicFaceSel.value = face;
    if (arabicSizeVal) {
      arabicSizeVal.textContent =
        ARABIC_SIZES.find((s) => s.id === size)?.name ?? size;
    }
  }

  /**
   * The toolbar's Arabic pair: the book's face, and its size as a −/+ stepper
   * over the four named steps.
   *
   * A stepper rather than a second dropdown because it sits beside the screen
   * text-size stepper and does the same KIND of thing to a different text — the
   * shape says "bigger/smaller" without being read. It shows the step's NAME
   * rather than a number: the underlying values are two measurements, not one,
   * and a number would invite arithmetic that does not apply.
   */
  function buildArabicGroup(): HTMLElement {
    const group = document.createElement("div");
    group.className = "cx-tb-group cx-arabic-group";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "The book's Arabic typography");

    const label = document.createElement("span");
    label.className = "cx-tb-label";
    label.textContent = "Arabic";
    label.title =
      "The book's own Arabic face and size — saved with the edition and printed into the PDF";

    const sel = document.createElement("select");
    sel.className = "cx-font-select cx-arabic-face";
    sel.setAttribute("aria-label", "Arabic face for the printed book");
    sel.title =
      "Non-Qur'anic Arabic face. Scripture is always the Uthmanic script and is not affected.";
    for (const f of ARABIC_FACES) {
      const o = document.createElement("option");
      o.value = f.id;
      o.textContent = f.name;
      o.title = f.tagline;
      sel.append(o);
    }
    sel.addEventListener("change", () => {
      void setArabicStyle("arabic-font", sel.value, typeSave);
    });
    arabicFaceSel = sel;

    const wrap = document.createElement("div");
    wrap.className = "cx-size cx-arabic-size";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "Arabic size for the printed book");
    const down = document.createElement("button");
    down.type = "button";
    down.className = "cx-size-btn";
    down.textContent = "−"; // minus sign, matching the screen stepper
    down.title = "Smaller Arabic throughout the book";
    down.setAttribute("aria-label", "Decrease the book's Arabic size");
    const val = document.createElement("span");
    val.className = "cx-size-val cx-arabic-size-val";
    val.setAttribute("aria-live", "polite");
    const up = document.createElement("button");
    up.type = "button";
    up.className = "cx-size-btn";
    up.textContent = "+";
    up.title = "Larger Arabic throughout the book";
    up.setAttribute("aria-label", "Increase the book's Arabic size");
    arabicSizeVal = val;

    const step = (delta: number) => {
      const now = currentArabic("ars-", DEFAULT_ARABIC_SIZE);
      const i = ARABIC_SIZES.findIndex((s) => s.id === now);
      const next =
        ARABIC_SIZES[
          Math.max(
            0,
            Math.min(ARABIC_SIZES.length - 1, (i < 0 ? 1 : i) + delta),
          )
        ];
      // Ends of the scale are a no-op rather than a wrap: a stepper that jumps
      // from largest back to smallest is a stepper you cannot hold down.
      if (!next || next.id === now) return;
      void setArabicStyle("arabic-size", next.id, typeSave);
    };
    down.addEventListener("click", () => step(-1));
    up.addEventListener("click", () => step(1));

    wrap.append(down, val, up);
    group.append(label, sel, wrap);
    syncArabicToolbar(); // seed both from the classes already on the root
    return group;
  }

  void loadSavedFamily();
  void loadColours();
  void loadAlign();

  // ── The text-colour button's hooks ────────────────────────────────────────
  // Colouring is a SIDECAR edit, never a document edit: the selected words are
  // recorded verbatim and the canvas is repainted from that record. Nothing
  // reaches book.md, so nothing can be lost by the next autosave.
  colourApply = (quote: string, ink: string | null): void => {
    const key = quote.replace(/\s+/g, " ").toLowerCase();
    const rest = colourSpans.current.filter(
      (s) => s.quote.replace(/\s+/g, " ").toLowerCase() !== key,
    );
    const next = ink ? [...rest, { quote, ink }] : rest;
    colourSpans.current = next;
    colourByChapter[selectedChapter] = next;
    repaintColours();
    void apiFetch("/api/studio/text-colour", {
      method: "PUT",
      body: { slug, chapterKey: selectedChapter, spans: next },
    }).catch((e) => {
      void noticeDialog({
        title: "Colour not saved",
        body: `The colour is showing but did not reach the book: ${(e as Error).message}`,
      });
    });
  };
  // ── The alignment buttons' hooks ──────────────────────────────────────────
  // Alignment is a SIDECAR edit too: the paragraph the cursor is in is recorded
  // by its key and the canvas is repainted from that record.
  alignApply = (align: string): void => {
    const key = alignKeyAtCursor();
    if (!key) return;
    const next = { ...alignSpans.current };
    // `left` is the default, so choosing it REMOVES the entry rather than
    // writing one — see text-align.ts for why absence is the representation.
    if (align === DEFAULT_TEXT_ALIGN) delete next[key];
    else next[key] = align;
    alignSpans.current = next;
    alignByChapter[selectedChapter] = next;
    repaintColours();
    markAlignedParagraphs();
    void apiFetch("/api/studio/text-align", {
      method: "PUT",
      body: { slug, chapterKey: selectedChapter, paras: next },
    }).catch((e) => {
      void noticeDialog({
        title: "Alignment not saved",
        body: `The paragraph is showing aligned but that did not reach the book: ${(e as Error).message}`,
      });
    });
  };
  alignActive = (): string | null => {
    const key = alignKeyAtCursor();
    // null, not "left": the buttons disable on null, which is the honest state
    // when the paragraph mapping is unavailable. Saying "left" would let a click
    // write an alignment against a key that does not describe this paragraph.
    if (!key) return null;
    return alignSpans.current[key] ?? DEFAULT_TEXT_ALIGN;
  };
  /** The key of the prose paragraph the cursor sits in, or null when the
   *  position mapping does not hold (see alignablePositions). */
  function alignKeyAtCursor(): string | null {
    const ed = activeEditor?.editor;
    if (!ed || ed.isDestroyed) return null;
    const at = ed.state.selection.from;
    const hit = alignablePositions(ed.state.doc, alignKeys.current).find(
      (p) => at >= p.from && at <= p.to,
    );
    return hit?.key ?? null;
  }

  colourActive = (): string | null => {
    const ed = activeEditor?.editor;
    if (!ed || ed.isDestroyed) return null;
    const { from, to } = ed.state.selection;
    const sel = ed.state.doc
      .textBetween(from, to, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
    if (!sel) return null;
    return (
      colourSpans.current.find(
        (s) => s.quote.replace(/\s+/g, " ").toLowerCase() === sel,
      )?.ink ?? null
    );
  };

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

    // The innerHTML reset above dropped every Companion tint with it. Re-mark:
    // an annotated passage must stay visible across a figure placement.
    markCompanionPassages();
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
    /** Vowel the selected Arabic and replace it. Its own branch in runAiAction:
     *  it neither rewrites English nor offers alternatives to choose between. */
    diacritics?: boolean;
    /** Enabled only when the selection is BARE ARABIC, not on any selection. */
    arabicOnly?: boolean;
    /** FA classes shown at the centre of the busy modal's ring spinner. */
    icon?: string;
  }
  const AI_ACTIONS: AiAction[] = [
    {
      kind: "rewrite",
      label: "Rewrite",
      mode: "clarify",
      icon: "fa-solid fa-pen-nib",
    },
    {
      kind: "expand",
      label: "Expand",
      mode: "expand",
      icon: "fa-solid fa-up-right-and-down-left-from-center",
    },
    {
      kind: "condense",
      label: "Condense",
      mode: "tighten",
      icon: "fa-solid fa-down-left-and-up-right-to-center",
    },
    {
      kind: "simplify",
      label: "Simplify",
      mode: "simplify",
      icon: "fa-solid fa-wand-magic-sparkles",
    },
    {
      kind: "explain",
      label: "Explain",
      explain: true,
      icon: "fa-solid fa-lightbulb",
    },
    {
      kind: "etymology",
      label: "Etymology",
      etymology: true,
      icon: "fa-solid fa-book-open",
    },
    // Vowel the selected Arabic in place (Asif, 2026-07-29). Last in the row
    // because it is the only one that acts on Arabic rather than on English —
    // and it is the only one that stays dark until the selection is Arabic, so
    // its own disabled state tells you when it applies.
    {
      kind: "diacritics",
      label: "Diacritics",
      diacritics: true,
      arabicOnly: true,
      icon: "fa-solid fa-marker",
    },
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

  /** Arabic script, excluding the combining marks themselves. */
  const ARABIC_LETTER_RE = /[ؠ-ي٠-ٯٱ-ۓ]/;
  /** The combining marks a vowelled run carries. Mirrors MARKS_RE in
   *  scripts/lib/vowelling.mjs — the server re-checks with the real thing, so a
   *  drift here can only mis-enable a button, never admit a bad edit. */
  const TASHKEEL_RE = /[\u064b-\u065f\u0670\u06d6-\u06ed\u0640]/g;

  /** Is this selection Arabic that still needs its vowel marks?
   *
   *  Deliberately generous on the "still needs" half: a run the scan left with a
   *  couple of disambiguating marks is bare for this purpose. The authority is
   *  `isVowellingCandidate` on the server, which refuses an already-vowelled run
   *  (every Qur'anic one included — those carry the canonical mushaf's marks) with
   *  a message. This only decides whether the button looks available. */
  function isBareArabic(text: string): boolean {
    if (!ARABIC_LETTER_RE.test(text)) return false;
    // Predominantly Arabic, not merely containing some. Mirrors the ratio the
    // route's own candidate collector uses: a paragraph of English that quotes
    // three Arabic words is not a passage to vowel, and sending it would ask the
    // model to hand back English it must not touch.
    const latin = (text.match(/[A-Za-z]/g) || []).length;
    const arabicAll = (text.match(/[؀-ۿ]/g) || []).length;
    if (latin > 2 || arabicAll < latin * 4) return false;
    const letters = (text.match(/[؀-ۿ]/g) || []).filter(
      (c) => !c.match(TASHKEEL_RE),
    ).length;
    if (letters < 8) return false;
    const marks = (text.match(TASHKEEL_RE) || []).length;
    return marks / letters < 0.15;
  }

  function updateAiEnabled(): void {
    const sel = selectionText();
    const ok = !!sel;
    const arabic = ok && isBareArabic(sel.text);
    // Rearticulate acts on the whole chapter, not the selection — it opts out.
    root
      .querySelectorAll<HTMLButtonElement>(".cx-ai-btn:not(.cx-rearticulate)")
      .forEach((b) => {
        b.disabled = b.classList.contains("cx-ai-arabic") ? !arabic : !ok;
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
      b.className = a.arabicOnly ? "cx-ai-btn cx-ai-arabic" : "cx-ai-btn";
      b.textContent = a.label;
      if (a.arabicOnly)
        b.title =
          "Add Arabic vowel marks to the selected passage — select Arabic script to enable";
      b.disabled = true;
      b.addEventListener("click", () => runAiAction(a));
      row.appendChild(b);
    }
    // Rearticulate — whole-chapter, selection-independent. Rewrites the open
    // chapter in place through the pipeline's gated engine (REQ-BA contract,
    // docs/standards/book-articulation.md); a window that fails a fidelity
    // gate reverts, so the worst outcome is a no-op.
    const rearticulate = document.createElement("button");
    rearticulate.type = "button";
    rearticulate.className = "cx-ai-btn cx-rearticulate";
    rearticulate.textContent = "Rearticulate chapter";
    rearticulate.addEventListener("click", () => runRearticulate(rearticulate));
    row.appendChild(rearticulate);
    controlsEl.appendChild(row);

    aiStatusEl = document.createElement("p");
    aiStatusEl.className = "cx-status";
    aiStatusEl.setAttribute("role", "status");
    aiStatusEl.setAttribute("aria-live", "polite");
    controlsEl.appendChild(aiStatusEl);
    updateAiEnabled();
  }

  // ── Rearticulate: whole-chapter rewrite through the pipeline's gated engine ──
  // The flow is deliberately page-reload-shaped (the Composer's normal re-sync
  // pattern, see reloadPreservingChapter): flush pending edits so the engine
  // reads what the author sees, lock the editor, shimmer while the detached
  // Python worker runs, then reload from disk. NO editor-document surgery — the
  // RCA-002 lesson is that live-editor writes racing book.md are how corruption
  // happens, so the editor is read-only for the whole run.
  let rearticulating = false;

  async function runRearticulate(btn: HTMLButtonElement): Promise<void> {
    if (!activeEditor || rearticulating) return;
    const title = chapterByKey.get(selectedChapter)?.title ?? selectedChapter;
    const go = await confirmDialog({
      title: "Rearticulate this chapter?",
      titleIcon: "fa-solid fa-feather-pointed",
      body: `“${title}” is rewritten in place as simple, articulate English.`,
      points: [
        {
          icon: "fa-solid fa-quote-left",
          text: "Speeches and quotations keep their speakers and their content.",
        },
        {
          icon: "fa-solid fa-mountain-sun",
          text: "Imagery stays imagery — nothing is flattened into abstraction.",
        },
        {
          icon: "fa-solid fa-language",
          text: "Arabic script is preserved verbatim, never romanized away.",
        },
        {
          icon: "fa-solid fa-shield-halved",
          text: "A result that fails the fidelity gates reverts automatically.",
        },
      ],
      footnote:
        "Takes a few minutes. The chapter is locked while the rewrite runs.",
      confirmLabel: "Rearticulate",
    });
    if (!go) return;
    const flushed = await (activeSaveFlush?.() ?? Promise.resolve(true));
    if (!flushed) {
      setAiStatus(
        "Autosave is failing — resolve that before rearticulating.",
        true,
      );
      return;
    }
    rearticulating = true;
    btn.disabled = true;
    const editorDom = activeEditor.editor.view.dom as HTMLElement;
    activeEditor.editor.setEditable(false);
    editorDom.classList.add("cx-rearticulating");
    // Blocking progress modal for the whole run — on success it stays up
    // through the page reload, so the page never looks interactive while its
    // content is stale.
    const busy = busyDialog({
      title: "Rearticulating the chapter…",
      status: `“${title}”`,
      icon: "fa-solid fa-feather-pointed",
      note: "Rewriting as simple, articulate English behind the fidelity gates — this can take a few minutes.",
    });

    const unlock = (msg: string, isError: boolean) => {
      busy.close();
      rearticulating = false;
      btn.disabled = false;
      editorDom.classList.remove("cx-rearticulating");
      activeEditor?.editor.setEditable(true);
      setAiStatus(msg, isError);
    };

    try {
      await apiFetch("/api/studio/rearticulate", {
        method: "POST",
        body: { slug, chapterKey: selectedChapter },
      });
    } catch (e) {
      unlock(`Rearticulate failed to start: ${String(e)}`, true);
      return;
    }

    // Poll the worker. A long chapter windows into several claude calls at up
    // to 900 s each, so the ceiling is generous; the GET converts a dead worker
    // into state:"error", so this loop cannot shimmer forever.
    const DEADLINE = Date.now() + 120 * 60 * 1000;
    const poll = async (): Promise<void> => {
      if (Date.now() > DEADLINE) {
        unlock(
          "Rearticulate timed out — check the book before retrying.",
          true,
        );
        return;
      }
      let status: Record<string, unknown>;
      try {
        status = (await apiFetch(
          `/api/studio/rearticulate?slug=${encodeURIComponent(slug)}`,
        )) as Record<string, unknown>;
      } catch {
        window.setTimeout(poll, 5000); // transient poll failure — keep waiting
        return;
      }
      if (status.state === "running" || status.state === "none") {
        const secs = Math.round(
          (Date.now() - (DEADLINE - 120 * 60 * 1000)) / 1000,
        );
        busy.update(
          `“${title}” — ${Math.floor(secs / 60)}m ${secs % 60}s elapsed`,
        );
        window.setTimeout(poll, 4000);
        return;
      }
      if (status.state === "error") {
        unlock(
          `Rearticulate failed: ${String(status.error ?? "unknown error")}`,
          true,
        );
        return;
      }
      const record = (status.record ?? {}) as Record<string, unknown>;
      if (record.status === "reverted") {
        const gates = Array.isArray(record.gates) ? record.gates : [];
        unlock(
          `Rearticulation reverted by the fidelity gates — the chapter is unchanged. ${String(gates[0] ?? "")}`,
          true,
        );
        return;
      }
      // adapted or partial: book.md changed on disk; re-sync the page the
      // Composer's normal way. The editor and the modal stay up — the page's
      // content is stale until the reload lands.
      busy.update("Done — reloading the chapter…");
      setAiStatus("Rearticulated. Reloading the chapter…");
      reloadPreservingChapter();
    };
    window.setTimeout(poll, 4000);
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
    // Blocking progress modal for every AI action — the page is inert while
    // the model works; every exit path below closes it in the finally.
    const busy = busyDialog({
      title: `${a.label}…`,
      status:
        sel.text.length > 90 ? `“${sel.text.slice(0, 90)}…”` : `“${sel.text}”`,
      icon: a.icon,
      note: "The AI is working on your selection — a few seconds.",
    });
    if (a.etymology) {
      try {
        await runEtymology(sel);
      } finally {
        busy.close();
      }
      return;
    }
    if (a.diacritics) {
      try {
        await runDiacritics(sel);
      } finally {
        busy.close();
      }
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
    } finally {
      busy.close();
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
  /**
   * Vowel the selected Arabic and put it back, in place.
   *
   * No options popup and no accept step, unlike every other action in this row
   * (Asif, 2026-07-29): the others offer a REWRITE, where choosing between
   * phrasings is the point, and this one adds marks to letters that do not
   * change. There is nothing to choose between, and nothing to weigh — Asif does
   * not read Arabic, so a bare run is unreadable to him and withholding the marks
   * pending a decision helps nobody. The server refuses any answer whose
   * consonantal skeleton differs from the source, so what lands can only be the
   * same letters, marked.
   *
   * It replaces the selection in the OPEN EDITOR rather than writing book.md
   * directly, which is what puts it on the Composer's own edit path: the prose
   * autosave records it in composer-edits.json, the replay restores it after a
   * re-compose, "Show changes" displays it as a human edit, and Cmd+Z undoes it
   * like any other.
   */
  async function runDiacritics(sel: {
    text: string;
    from: number;
    to: number;
  }): Promise<void> {
    if (!activeEditor) return;
    setAiStatus("Adding diacritics…");
    try {
      const j = await apiFetch<{ vowelled: string; marksAdded: number }>(
        "/api/studio/vowelling",
        { method: "POST", body: { slug, action: "run", text: sel.text } },
      );
      const vowelled = String(j.vowelled ?? "").trim();
      if (!vowelled) throw new Error("nothing came back");
      activeEditor.editor
        .chain()
        .focus()
        .insertContentAt({ from: sel.from, to: sel.to }, vowelled)
        .run();
      setAiStatus(
        `Added ${j.marksAdded} vowel mark${j.marksAdded === 1 ? "" : "s"}. Remember to Save prose.`,
      );
    } catch (e) {
      setAiStatus(`Diacritics failed: ${(e as Error).message}`, true);
    }
  }

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
            chapter: companionChapterKey(),
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
    // Same guard as the prose editor: a drag that returns a figure to where it
    // already was must not spend a request re-writing an identical layout.
    fingerprint: () => JSON.stringify(placements),
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
  renderScholar(); // page-lifetime surface: loads the chapter's explanations
  render();

  // ── Generate PDF (header) — same contract as the Preview page's button ─────
  // The renderer reads book.md from DISK, so the open chapter's pending edits
  // are flushed first: what you see is what prints. Same themed confirm and
  // endpoint as /studio/<slug>/preview; the page is fully usable while the
  // render runs (only the button itself locks).
  const genPdfBtn =
    document.querySelector<HTMLButtonElement>("#cx-generate-pdf");
  genPdfBtn?.addEventListener("click", async () => {
    if (genPdfBtn.disabled) return;
    const flushed = await (activeSaveFlush?.() ?? Promise.resolve(true));
    if (!flushed) {
      await noticeDialog({
        title: "Unsaved edits could not be saved",
        body: "The open chapter has edits that failed to autosave. Resolve the save error first — otherwise the PDF would print without them.",
        danger: true,
      });
      return;
    }
    const go = await confirmDialog({
      title: "Generate the PDF?",
      titleIcon: "fa-solid fa-file-pdf",
      body: "The reading edition is rendered from the chapters exactly as saved right now.",
      points: [
        {
          icon: "fa-solid fa-book-open-reader",
          text: "This is the file delivered to readers and Google Drive.",
        },
        {
          icon: "fa-solid fa-download",
          text: "The Download PDF link lights up when the render finishes.",
        },
      ],
      footnote: "About a minute. The page stays usable while it renders.",
      confirmLabel: "Generate",
    });
    if (!go) return;
    const idle = genPdfBtn.innerHTML;
    genPdfBtn.disabled = true;
    // Spinner while the render runs (fa-spin; stilled under reduced motion in CSS).
    genPdfBtn.innerHTML =
      '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Rendering PDF…';
    // The download link stays DISABLED until the PDF is actually generated —
    // during a render the on-disk file is about to be overwritten, so offering
    // it would hand out a stale or mid-write download.
    const pdfLink = document.querySelector<HTMLAnchorElement>("#cx-pdf-link");
    const priorHref = pdfLink?.getAttribute("href") ?? null;
    if (pdfLink) {
      pdfLink.setAttribute("aria-disabled", "true");
      pdfLink.setAttribute("tabindex", "-1");
      pdfLink.removeAttribute("href");
    }
    try {
      const data = await apiFetch<{
        kb?: number;
        relPath?: string;
        filename?: string;
      }>("/api/studio/generate-book-pdf", { method: "POST", body: { slug } });
      genPdfBtn.innerHTML = idle;
      genPdfBtn.disabled = false;
      // The PDF now actually exists — enable the link, pointing at the fresh file.
      if (pdfLink && data.relPath) {
        pdfLink.href = `/api/library/file?slug=${encodeURIComponent(slug)}&path=${encodeURIComponent(data.relPath)}`;
        if (data.filename) pdfLink.setAttribute("download", data.filename);
        pdfLink.innerHTML = `<i class="fa-solid fa-download" aria-hidden="true"></i> Download PDF (${data.kb ?? "?"} KB)`;
        pdfLink.setAttribute("aria-disabled", "false");
        pdfLink.removeAttribute("tabindex");
        // One attention pulse so the fresh link is noticed; the class is
        // animation-only and removed when it ends.
        pdfLink.classList.remove("cx-pdf-link--fresh");
        void pdfLink.offsetWidth; // restart the animation on back-to-back renders
        pdfLink.classList.add("cx-pdf-link--fresh");
        pdfLink.addEventListener(
          "animationend",
          () => pdfLink.classList.remove("cx-pdf-link--fresh"),
          { once: true },
        );
      }
    } catch (err) {
      genPdfBtn.innerHTML = idle;
      genPdfBtn.disabled = false;
      // Failed render: the file on disk (if any) is whatever it was before —
      // restore the prior link rather than leaving a dead control.
      if (pdfLink && priorHref) {
        pdfLink.setAttribute("href", priorHref);
        pdfLink.setAttribute("aria-disabled", "false");
        pdfLink.removeAttribute("tabindex");
      }
      await noticeDialog({
        title: "PDF generation failed",
        body: String((err as Error).message ?? err),
        danger: true,
      });
    }
  });

  // A tinted passage is the entry point to its explanation, in BOTH modes: the
  // read body wraps a span and the edit canvas paints a decoration, and one
  // delegated listener over the preview column covers each of them.
  root.querySelector(".composer-preview")?.addEventListener("click", (e) => {
    // The Arabic control first, and it RETURNS: a tinted passage can sit inside a
    // paragraph whose reveal is open, and without this both handlers would fire —
    // opening the Scholar panel every time the reader asked for the Arabic.
    const tab = (e.target as HTMLElement)?.closest<HTMLElement>(".cx-ar-tab");
    if (tab) {
      const aside = tab.closest<HTMLElement>(".cx-ar-reveal");
      const fp = aside?.dataset.fp;
      if (!fp) return;
      const opening = arabicRevealed !== fp;
      // Inserting ABOVE pushes the paragraph down by the panel's height. Hold the
      // clicked paragraph still, or the reader loses their line — and the
      // Companion's visibility sweep fires and yanks its panel to another card.
      const para = aside?.nextElementSibling as HTMLElement | null;
      const before = para?.getBoundingClientRect().top ?? 0;
      // Opening one closes whichever was open — the assignment IS the close.
      arabicRevealed = opening ? fp : null;
      const body = currentChapterEl()?.querySelector<HTMLElement>(".cx-body");
      if (body) {
        stripArabicReveals(body);
        applyArabicReveals();
      }
      const reopened = body?.querySelector<HTMLElement>(
        `.cx-ar-reveal[data-fp="${CSS.escape(fp)}"]`,
      );
      const after =
        (
          reopened?.nextElementSibling as HTMLElement | null
        )?.getBoundingClientRect().top ?? before;
      window.scrollBy({
        top: after - before,
        behavior: "instant" as ScrollBehavior,
      });
      reopened?.querySelector<HTMLButtonElement>(".cx-ar-tab")?.focus();
      return;
    }
    const mark = (e.target as HTMLElement)?.closest<HTMLElement>(".cx-note-hl");
    const id = mark?.dataset.note;
    if (!id) return;
    setPanel("scholar");
    focusNonce += 1;
    focusNote = { id, nonce: focusNonce };
    renderScholar();
    revealPassage(id);
  });

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
  // `userMode` remembers the choice the human actually made WITHIN this visit, so
  // returning from the Podcast lane restores it. It is NOT read off setModeVisual:
  // the flip's own leave() drops the view to Read on its way out, which would make
  // every return land in Read regardless of where the user came from.
  //
  // Every load starts in Edit (Asif, 2026-08-01). This used to seed from
  // `composeMode.read(slug)` — what the book was last left in — which meant a book
  // closed in Read reopened in Read days later, and the markup's Edit default only
  // ever applied to a book never opened before. Edit is the working mode; Read is
  // one click away. `composeMode` went with the seed: once nothing reads the
  // stored mode, the writes that fed it are a localStorage key nobody consults.
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

  // Which lane this book was last in — set by a deliberate flip, and equally by
  // a flip whose leave() reloaded the page (prose had changed, so the preview
  // re-renders from the authoritative book.md). Honour it instead of dropping
  // the user back into the book lane's editor.
  const restoreLane = pendingLane(slug);
  if (composeLane && restoreLane === "podcast") {
    void composeLane.setLane("podcast");
  } else {
    setMode(userMode);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
