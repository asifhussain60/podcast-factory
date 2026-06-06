/**
 * StudioPoc.tsx — WC8 Studio (spike → real build). TipTap/ProseMirror foundation.
 *
 * Feel-check feedback FC-1/FC-3/FC-4 applied (2026-05-29):
 *   FC-1  Verse refs render as a COMPACT chapter:verse chip (e.g. 99:7-8) appended
 *         after the natural-language reference — the prose is NEVER mutated (so the
 *         NotebookLM source still reads "Surah Az-Zalzalah, verses 7 to 8"). The chip
 *         is the hover target (data-surah/data-verse → reused QuranPopover).
 *   FC-3  Change-tracking is Microsoft-Word track-changes: jsdiff WORD-level insertions
 *         (underlined) + deletions (strikethrough widget), persisted off-cursor. Every
 *         paragraph shows a hover affordance (CSS); clicking selects only that paragraph
 *         (active-paragraph decoration).
 *   FC-4  Arabic toggle: when on, glossary phonetic tokens are swapped to Arabic script
 *         (clean Amiri webfont, distinct colour) via decorations — non-destructive.
 *
 * Manual actions (edits, tags) are the learning-loop training signal. External CSS only.
 * Library policy frozen: @tiptap/* + @floating-ui/react + diff(jsdiff) — no new libs.
 */
import { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as PMNode } from '@tiptap/pm/model';
import { diffWords } from 'diff';
import { stageRole } from '../../../lib/reader/stage-roles';
import type { EnrichmentSummary } from '../../../lib/reader/enrichment-ledger';
import TransformationDashboard from './TransformationDashboard';

// Inline reference markers: inspector inventory + inline chips for Hadith/Works.
// Quran verse refs are handled separately as FC-1 chips, so mk-quran is skipped here.
const MARKER_PATTERNS: { re: RegExp; cls: string; kind: string; chip?: string }[] = [
  { re: /Surah [A-Z][\w'-]+/g,                  cls: 'mk-quran',  kind: 'Quran' },
  { re: /verses? \d+(?:\s*(?:to|–|-)\s*\d+)?/gi, cls: 'mk-quran',  kind: 'Quran' },
  { re: /Prophet Muhammad/gi,                     cls: 'mk-hadith', kind: 'Hadith', chip: 'Hadith' },
  { re: /peace and blessings of Allah/gi,         cls: 'mk-hadith', kind: 'Hadith' },
  { re: /Ihya(?:\s+Ulum\s+al-Din)?/g,             cls: 'mk-term',   kind: 'Work',   chip: 'Ihya' },
  { re: /Kimiya(?:\s+al-Sa'?ada)?/g,              cls: 'mk-term',   kind: 'Work',   chip: 'Kimiya' },
  { re: /Jawahir al-Quran/g,                      cls: 'mk-term',   kind: 'Work',   chip: 'Jawahir' },
  { re: /Minhaj al-Abidin/g,                      cls: 'mk-term',   kind: 'Work',   chip: 'Minhaj' },
];

// Each tag carries a distinct ICON so the meaning is recognizable without memorizing colour.
const TAGS = [
  { id: 'esoteric', label: 'Esoteric', icon: '🔮' },
  { id: 'reality', label: 'Reality', icon: '💎' },
  { id: 'sharia', label: 'Sharia', icon: '⚖️' },
  { id: 'history', label: 'History', icon: '📜' },
  { id: 'delete', label: 'Delete', icon: '🗑️' },
  { id: 'improve', label: 'Improve', icon: '✏️' },
];

interface GlossaryEntry {
  phonetic: string;
  transliteration: string;
  arabic_script: string;
}

function scanMarkers(text: string): { kind: string; text: string }[] {
  const out: { kind: string; text: string }[] = [];
  for (const { re, kind } of MARKER_PATTERNS) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) out.push({ kind, text: m[0] });
  }
  return out;
}

// Hadith + Works: inline highlight + visible chip pill. Quran verse refs become FC-1 chips.
const MarkerHighlight = Extension.create({
  name: 'markerHighlight',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('markerHighlight'),
        props: {
          decorations(state) {
            const decos: Decoration[] = [];
            state.doc.descendants((node, pos) => {
              if (!node.isText || !node.text) return;
              for (const { re, cls, chip } of MARKER_PATTERNS) {
                if (cls === 'mk-quran') continue; // handled as FC-1 chips
                re.lastIndex = 0;
                let m: RegExpExecArray | null;
                while ((m = re.exec(node.text))) {
                  const from = pos + m.index;
                  const to   = from + m[0].length;
                  decos.push(Decoration.inline(from, to, { class: `mk ${cls}` }));
                  if (chip) {
                    const label = chip;
                    const kind  = cls.replace('mk-', '');
                    decos.push(
                      Decoration.widget(to, () => {
                        const span = document.createElement('span');
                        span.className = `mk-chip mk-chip--${kind}`;
                        span.textContent = label;
                        span.setAttribute('aria-label', label);
                        return span;
                      }, { side: 1, key: `mkchip-${from}` }),
                    );
                  }
                }
              }
            });
            return DecorationSet.create(state.doc, decos);
          },
        },
      }),
    ];
  },
});

// Surah name -> number (subset; expand to all 114 in the real build via the corpus).
const SURAH_MAP: Record<string, number> = {
  'Al-Fatihah': 1, 'Al-Baqarah': 2, "Al-A'raf": 7, 'Al-Anfal': 8, 'At-Tawbah': 9,
  'Yusuf': 12, 'Al-Isra': 17, 'Al-Kahf': 18, 'Maryam': 19, 'Ta-Ha': 20,
  'Al-Muminun': 23, 'An-Nur': 24, 'Al-Furqan': 25, 'Luqman': 31, 'Ya-Sin': 36,
  'Adh-Dhariyat': 51, 'Ar-Rahman': 55, 'Al-Hashr': 59, 'Al-Mulk': 67,
  "Al-A'la": 87, 'Ash-Shams': 91, 'Az-Zalzalah': 99, 'Al-Asr': 103, 'Al-Ikhlas': 112,
};
// "Surah X, verses 7 to 8" | "Surah X, verse 110". The verse-ref chip that REPLACES this
// phrase is built inside StudioDecos (so it can coordinate with the Arabic overlay).
const SURAH_VERSE_RE = /Surah ([A-Z][\w'’-]+),?\s+verses?\s+(\d+)(?:\s*(?:to|–|-)\s*(\d+))?/g;

interface Stage {
  id: string;
  label: string;
  slice: string;
  available: boolean;
  html: string;
  augMeta?: string | null;
}

interface StageMetric {
  id: string;
  available: boolean;
  words: number;
  chars: number;
  sentences: number;
  deltaPct: number | null;
  comparedTo: string | null;
}

interface Chapter {
  slug: string;
  title: string;
  stages: Stage[];
  metrics: StageMetric[];
  reviewed: Record<string, { approved: boolean; approved_at?: string | null }>;
  finalized?: { at: string } | null;
}

/** A coherent stage set under one root. 'current' is the live rebuild; archived
 *  lineages (earlier full-stage runs) are view-only and never editable. */
export interface Lineage {
  id: string;
  label: string;
  chapters: Chapter[];
}

/** A pipeline phase (Intake → Source Review → Edit & Enrich → Publish), shown
 *  as the top tier of the left rail so the rail is the single pipeline timeline
 *  (the top horizontal stepper is suppressed on the Edit page). */
interface PipelineStep {
  id: string;
  label: string;
  state: string;   // 'done' | 'active' | 'pending' | 'blocked'
  detail: string;
}

interface Props {
  slug: string;
  chapters: Chapter[];
  glossary?: GlossaryEntry[];
  initialChapIdx?: number;
  contentProfile?: string;
  /** Archived view-only stage lineages (e.g. an earlier episode structure). */
  archivedLineages?: Lineage[];
  /** Pipeline phases for the left-rail timeline. */
  pipelineSteps?: PipelineStep[];
  /** The phase this page represents (the rail expands its versions here). */
  activeStep?: string;
  /** Book-level enrichment summary for the transformation dashboard. */
  enrichment?: EnrichmentSummary | null;
  /** Count of Arabic-overlay glossary terms (transformation dashboard footnote). */
  glossaryCount?: number;
}

// ── Module-level depth picker singleton ─────────────────────────────────────
// Placed outside the React component to avoid ref-timing issues; the decoration
// plugin closure can call openDepthPicker() directly at any point after import.

type SaveDepthFn = (ord: number, slug: string, level: string, tags: string[]) => void;
type DepthLevel = { readonly key: string; readonly label: string };

const DEPTH_LEVELS_BY_PROFILE: Record<string, readonly DepthLevel[]> = {
  islamic_scholarly: [
    { key: 'narrative', label: 'Narrative' },
    { key: 'sharia',    label: 'Sharia'    },
    { key: 'esoteric',  label: 'Esoteric'  },
    { key: 'origins',   label: 'Origins'   },
    { key: 'reality',   label: 'Reality'   },
  ],
  consumer_explainer: [
    { key: 'website',     label: 'Website'     },
    { key: 'application', label: 'Application' },
    { key: 'platform',    label: 'Platform'    },
    { key: 'api',         label: 'API'         },
  ],
  technical: [
    { key: 'coding',       label: 'Coding'       },
    { key: 'agentic_ai',   label: 'Agentic AI'   },
    { key: 'architecture', label: 'Architecture' },
    { key: 'devops',       label: 'DevOps'       },
    { key: 'security',     label: 'Security'     },
    { key: 'data_ml',      label: 'Data / ML'    },
  ],
  fiction: [
    { key: 'narrative',    label: 'Narrative'    },
    { key: 'character',    label: 'Character'    },
    { key: 'theme',        label: 'Theme'        },
    { key: 'world',        label: 'World'        },
    { key: 'conflict',     label: 'Conflict'     },
    { key: 'voice',        label: 'Voice'        },
  ],
};
const DEFAULT_DEPTH_PROFILE = 'islamic_scholarly';

// Scroll lock: prevent body scroll while any picker is open.
let _scrollLockCount = 0;
let _savedBodyOverflow = '';
function _lockScroll() {
  if (_scrollLockCount++ === 0) {
    _savedBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
  }
}
function _unlockScroll() {
  if (--_scrollLockCount <= 0) {
    _scrollLockCount = 0;
    document.body.style.overflow = _savedBodyOverflow;
    _savedBodyOverflow = '';
  }
}

let _dpEl: HTMLDivElement | null = null;
let _dpSaveFn: SaveDepthFn = () => {};
let _dpOrd = 0;
let _dpSection = '';
let _dpOutside: ((e: MouseEvent) => void) | null = null;
let _dpKey: ((e: KeyboardEvent) => void) | null = null;

// Section-level editorial tags — same vocabulary as paragraph TAGS (minus icons)
const SECTION_TAGS = [
  { id: 'esoteric', label: 'Esoteric' },
  { id: 'reality',  label: 'Reality'  },
  { id: 'sharia',   label: 'Sharia'   },
  { id: 'narrative', label: 'Narrative' },
  { id: 'origins',  label: 'Origins'  },
  { id: 'delete',   label: 'Delete'   },
  { id: 'improve',  label: 'Improve'  },
];

// Active tag set is tracked in the picker's DOM dataset so it survives open/close cycles
// without needing React state.
let _dpCurrentTags: string[] = [];

function _buildDepthPicker(levels: readonly DepthLevel[]): HTMLDivElement {
  const pop = document.createElement('div');
  pop.className = 'sp-depth-popover';
  pop.setAttribute('role', 'dialog');
  pop.setAttribute('aria-label', 'Set section depth and tags');

  // ── Zone 1: depth level (single-select) ───────────────────────────────────
  const depthTitle = document.createElement('div');
  depthTitle.className = 'sp-depth-popover__title';
  depthTitle.textContent = 'Depth level';
  pop.appendChild(depthTitle);

  const grid = document.createElement('div');
  grid.className = 'sp-depth-popover__grid';
  pop.appendChild(grid);

  for (const { key, label } of levels) {
    const opt = document.createElement('button');
    opt.type = 'button';
    opt.className = `sp-depth-popover__opt sp-depth-${key}`;
    opt.setAttribute('data-depth-level', key);
    opt.textContent = label;
    grid.appendChild(opt);
  }

  const clearBtn = document.createElement('button');
  clearBtn.type = 'button';
  clearBtn.className = 'sp-depth-popover__clear';
  clearBtn.setAttribute('data-depth-level', '');
  clearBtn.textContent = '∅ clear depth';
  pop.appendChild(clearBtn);

  // ── Event handling (depth only — tags have their own picker) ──────────────
  pop.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const depthBtn = target.closest('[data-depth-level]') as HTMLElement | null;
    if (depthBtn) {
      const level = depthBtn.dataset.depthLevel;
      if (level !== undefined) {
        _dpSaveFn(_dpOrd, _dpSection, level, _dpCurrentTags);
        closeDepthPicker();
      }
    }
  });

  document.body.appendChild(pop);
  return pop;
}

function closeDepthPicker() {
  if (!_dpEl?.classList.contains('is-open')) return;
  _dpEl.classList.remove('is-open');
  if (_dpOutside) { document.removeEventListener('mousedown', _dpOutside, true); _dpOutside = null; }
  if (_dpKey)     { document.removeEventListener('keydown',   _dpKey,     true); _dpKey = null; }
  _unlockScroll();
}

function openDepthPicker(
  anchorEl: HTMLElement,
  saveFn: SaveDepthFn,
  ord: number,
  sectionText: string,
  currentLevel: string | undefined,
  levels: readonly DepthLevel[],
  currentTags: string[],
) {
  _dpSaveFn      = saveFn;
  _dpOrd         = ord;
  _dpSection     = sectionText;
  _dpCurrentTags = [...currentTags];

  if (!_dpEl) _dpEl = _buildDepthPicker(levels);
  const pop = _dpEl;

  pop.querySelectorAll('[data-depth-level]').forEach((el) => {
    const k = (el as HTMLElement).dataset.depthLevel;
    el.classList.toggle('is-active', !!k && k === currentLevel);
  });

  const rect = anchorEl.getBoundingClientRect();
  const popW = 258;
  let left = rect.left;
  if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
  pop.style.top  = `${rect.bottom + 6}px`;
  pop.style.left = `${Math.max(8, left)}px`;
  pop.classList.add('is-open');
  _lockScroll();

  if (_dpOutside) document.removeEventListener('mousedown', _dpOutside, true);
  if (_dpKey)     document.removeEventListener('keydown',   _dpKey,     true);

  _dpOutside = (ev) => { if (!pop.contains(ev.target as Node) && ev.target !== anchorEl) closeDepthPicker(); };
  _dpKey     = (ev) => { if (ev.key === 'Escape') closeDepthPicker(); };

  requestAnimationFrame(() => {
    document.addEventListener('mousedown', _dpOutside!, true);
    document.addEventListener('keydown',   _dpKey!,     true);
  });
}
// ── Tag Picker (separate floating popover, distinct from depth picker) ───────
const CONTENT_SECTION_TAGS = SECTION_TAGS.filter((t) => !['delete', 'improve'].includes(t.id));
const WORKFLOW_SECTION_TAGS = SECTION_TAGS.filter((t) => ['delete', 'improve'].includes(t.id));

let _tpEl: HTMLDivElement | null = null;
let _tpSaveFn: SaveDepthFn = () => {};
let _tpOrd = 0;
let _tpSection = '';
let _tpCurrentDepth = '';
let _tpCurrentTags: string[] = [];
let _tpOutside: ((e: MouseEvent) => void) | null = null;
let _tpKey: ((e: KeyboardEvent) => void) | null = null;

function _syncTpButtons(pop: HTMLDivElement): void {
  pop.querySelectorAll('[data-section-tag]').forEach((el) => {
    const tid = (el as HTMLElement).dataset.sectionTag!;
    el.classList.toggle('is-active', _tpCurrentTags.includes(tid));
  });
}

function _buildTagPicker(): HTMLDivElement {
  const pop = document.createElement('div');
  pop.className = 'sp-tag-popover';
  pop.setAttribute('role', 'dialog');
  pop.setAttribute('aria-label', 'Set section tags');

  const contentTitle = document.createElement('div');
  contentTitle.className = 'sp-tag-popover__group-title';
  contentTitle.textContent = 'Content labels';
  pop.appendChild(contentTitle);

  const contentGrid = document.createElement('div');
  contentGrid.className = 'sp-tag-popover__grid';
  for (const { id, label } of CONTENT_SECTION_TAGS) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `sp-tag-popover__tag sp-tag-popover__tag--${id}`;
    btn.setAttribute('data-section-tag', id);
    btn.textContent = label;
    contentGrid.appendChild(btn);
  }
  pop.appendChild(contentGrid);

  const sep = document.createElement('hr');
  sep.className = 'sp-tag-popover__sep';
  pop.appendChild(sep);

  const workflowTitle = document.createElement('div');
  workflowTitle.className = 'sp-tag-popover__group-title sp-tag-popover__group-title--workflow';
  workflowTitle.textContent = 'Editorial flags';
  pop.appendChild(workflowTitle);

  const workflowGrid = document.createElement('div');
  workflowGrid.className = 'sp-tag-popover__grid sp-tag-popover__grid--workflow';
  for (const { id, label } of WORKFLOW_SECTION_TAGS) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `sp-tag-popover__tag sp-tag-popover__tag--${id}`;
    btn.setAttribute('data-section-tag', id);
    btn.textContent = label;
    workflowGrid.appendChild(btn);
  }
  pop.appendChild(workflowGrid);

  pop.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const tagBtn = target.closest('[data-section-tag]') as HTMLElement | null;
    if (tagBtn) {
      const tid = tagBtn.dataset.sectionTag!;
      if (_tpCurrentTags.includes(tid)) {
        _tpCurrentTags = _tpCurrentTags.filter((t) => t !== tid);
      } else {
        _tpCurrentTags = [..._tpCurrentTags, tid];
      }
      _syncTpButtons(pop);
      _tpSaveFn(_tpOrd, _tpSection, _tpCurrentDepth, _tpCurrentTags);
    }
  });

  document.body.appendChild(pop);
  return pop;
}

function closeTagPicker() {
  if (!_tpEl?.classList.contains('is-open')) return;
  _tpEl.classList.remove('is-open');
  if (_tpOutside) { document.removeEventListener('mousedown', _tpOutside, true); _tpOutside = null; }
  if (_tpKey)     { document.removeEventListener('keydown',   _tpKey,     true); _tpKey = null; }
  _unlockScroll();
}

function openTagPicker(
  anchorEl: HTMLElement,
  saveFn: SaveDepthFn,
  ord: number,
  sectionText: string,
  currentTags: string[],
  currentDepth: string,
) {
  _tpSaveFn       = saveFn;
  _tpOrd          = ord;
  _tpSection      = sectionText;
  _tpCurrentDepth = currentDepth;
  _tpCurrentTags  = [...currentTags];

  if (!_tpEl) _tpEl = _buildTagPicker();
  const pop = _tpEl;

  _syncTpButtons(pop);

  const rect = anchorEl.getBoundingClientRect();
  const popW = 244;
  let left = rect.left;
  if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
  pop.style.top  = `${rect.bottom + 6}px`;
  pop.style.left = `${Math.max(8, left)}px`;
  pop.classList.add('is-open');
  _lockScroll();

  if (_tpOutside) document.removeEventListener('mousedown', _tpOutside, true);
  if (_tpKey)     document.removeEventListener('keydown',   _tpKey,     true);

  _tpOutside = (ev) => { if (!pop.contains(ev.target as Node) && ev.target !== anchorEl) closeTagPicker(); };
  _tpKey     = (ev) => { if (ev.key === 'Escape') closeTagPicker(); };

  requestAnimationFrame(() => {
    document.addEventListener('mousedown', _tpOutside!, true);
    document.addEventListener('keydown',   _tpKey!,     true);
  });
}
// ────────────────────────────────────────────────────────────────────────────

export default function StudioPoc({ slug, chapters, glossary = [], initialChapIdx = 0, contentProfile, archivedLineages = [], pipelineSteps = [], activeStep = 'edit', enrichment = null, glossaryCount = 0 }: Props) {
  const depthLevels = DEPTH_LEVELS_BY_PROFILE[contentProfile ?? DEFAULT_DEPTH_PROFILE]
    ?? DEPTH_LEVELS_BY_PROFILE[DEFAULT_DEPTH_PROFILE];

  // Lineage = a coherent stage set. 'current' is the live rebuild; archived
  // lineages (earlier full-stage runs) are view-only. The timeline rail swaps
  // between them; archived lineages are never editable.
  const lineages = useMemo<Lineage[]>(
    () => [{ id: 'current', label: 'Current rebuild', chapters }, ...archivedLineages],
    [chapters, archivedLineages],
  );
  const [activeLineageId, setActiveLineageId] = useState('current');
  const activeLineage = lineages.find((l) => l.id === activeLineageId) ?? lineages[0];
  const isArchivedView = activeLineage.id !== 'current';
  const viewChapters = activeLineage.chapters;

  // B: chapter switcher — pick which chapter's stages the editor shows.
  const [chapIdx, setChapIdx] = useState(initialChapIdx);
  const chap = viewChapters[chapIdx] ?? viewChapters[0];
  const stages = chap.stages;
  const metrics = chap.metrics;
  const chapter = chap.slug;
  const chapterTitle = chap.title;

  // The timeline's top step ("Review") is the last AVAILABLE stage — the one under
  // human review (editable); every older stage is a read-only comparison view.
  // Archived lineages are wholly read-only.
  const editableStageId = [...stages].reverse().find((s) => s.available)?.id ?? stages[0]?.id;
  const [stageId, setStageId] = useState<string>(editableStageId);
  const stage = stages.find((s) => s.id === stageId) ?? stages[0];
  const html = stage?.html ?? '';
  const isReadOnlyStage = stageId !== editableStageId || isArchivedView;

  // Switch lineage: reset to its first chapter (chapter boundaries differ between lineages).
  const switchLineage = useCallback((id: string) => {
    setActiveLineageId(id);
    setChapIdx(0);
  }, []);

  // WC8 write-back loop: which stages are approved (seeded from disk, updated on approve).
  const [approvedStages, setApprovedStages] = useState<Record<string, boolean>>(
    () => Object.fromEntries(Object.entries(chap.reviewed).map(([k, v]) => [k, !!v?.approved])),
  );
  // Chapter-level finalize flag (Publish button). Seeded from disk, updated on finalize.
  const [finalized, setFinalized] = useState<{ at: string } | null>(chap.finalized ?? null);
  // On chapter/lineage switch: reset to that chapter's editable stage + reload approvals +
  // finalize flag, and tell the editorial cockpit (Slice 5b) to follow this chapter.
  useEffect(() => {
    setStageId([...chap.stages].reverse().find((s) => s.available)?.id ?? chap.stages[0]?.id);
    setApprovedStages(Object.fromEntries(Object.entries(chap.reviewed).map(([k, v]) => [k, !!v?.approved])));
    setFinalized(chap.finalized ?? null);
    window.dispatchEvent(new CustomEvent('studio:chapter-change', { detail: { chapter: chap.slug } }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapIdx, activeLineageId]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  // Per-paragraph comments: index → text. Stored in a ref for the PM plugin,
  // mirrored in state so the inspector panel re-renders.
  const commentsRef = useRef<Map<number, string>>(new Map());
  const [, setCommentsKey] = useState(0);
  const refreshComments = () => setCommentsKey((k) => k + 1);

  // Active paragraph index (inspector drives the comment textarea + tag panel).
  const [activeParaIdx, setActiveParaIdx] = useState<number | null>(null);
  // Active section ordinal (0-based h2 index) — drives AI actions and section highlight.
  const [activeSectionOrdinal, setActiveSectionOrdinal] = useState<number | null>(null);
  const activeSectionOrdinalRef = useRef<number | null>(null);
  activeSectionOrdinalRef.current = activeSectionOrdinal;

  // M-1 — Inspector tab state (Details · Comment · AI · References).
  const [inspectorTab, setInspectorTab] = useState<'details' | 'comment' | 'ai' | 'refs'>('details');

  // Option A — section-level depth + tags (pipeline guesses, human corrects).
  // Maps section ordinal → depth_level code string.
  const [sectionDepths, setSectionDepths] = useState<Record<number, string>>({});
  const sectionDepthsRef = useRef<Record<number, string>>({});
  sectionDepthsRef.current = sectionDepths;
  // Maps section ordinal → string[] of section tag IDs.
  const [sectionTagsMap, setSectionTagsMap] = useState<Record<number, string[]>>({});
  const sectionTagsRef = useRef<Record<number, string[]>>({});
  sectionTagsRef.current = sectionTagsMap;
  // Load section depths + tags from the API when chapter changes.
  useEffect(() => {
    if (!slug || !chapter) return;
    let cancelled = false;
    fetch(`/api/studio/section-depth?book=${encodeURIComponent(slug)}&chapter=${encodeURIComponent(chapter)}`)
      .then((r) => r.ok ? r.json() : null)
      .then((json) => {
        if (cancelled || !json?.sections) return;
        const depthMap: Record<number, string> = {};
        const tagsMap: Record<number, string[]> = {};
        for (const s of json.sections) {
          depthMap[s.section_ordinal] = s.depth_level;
          tagsMap[s.section_ordinal] = Array.isArray(s.section_tags) ? s.section_tags : [];
        }
        setSectionDepths(depthMap);
        setSectionTagsMap(tagsMap);
      })
      .catch(() => { /* offline-friendly */ });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, chapter]);

  // editorRef: stable ref to the editor instance so non-React callbacks (PM widgets)
  // can dispatch transactions without capturing a stale `editor` closure.
  const editorRef = useRef<ReturnType<typeof useEditor>>(null);

  // Persist a section depth change (human override).
  // Directly mutates sectionDepthsRef then dispatches a PM transaction so the
  // decoration plugin recomputes immediately — setSectionDepths alone is not enough
  // because React batching means the ref isn't updated until after the next render.
  const saveSectionDepthRef = useRef<SaveDepthFn>(() => {});
  saveSectionDepthRef.current = (ordinal: number, slug_label: string, depthLevel: string, tags: string[]) => {
    sectionDepthsRef.current = { ...sectionDepthsRef.current, [ordinal]: depthLevel };
    sectionTagsRef.current   = { ...sectionTagsRef.current,  [ordinal]: tags };
    setSectionDepths({ ...sectionDepthsRef.current });
    setSectionTagsMap({ ...sectionTagsRef.current });
    editorRef.current?.view.dispatch(editorRef.current.state.tr.setMeta('refreshDepth', true));
    fetch('/api/studio/section-depth', {
      method: 'PATCH', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ book: slug, chapter, ordinal, slug: slug_label, depth_level: depthLevel, tags }),
    }).catch(() => { /* non-blocking */ });
  };

  // Wave L-8 — AI assist panel + Finalize state.
  const [aiBusy, setAiBusy] = useState(false);
  const [aiKind, setAiKind] = useState('');
  const [aiResult, setAiResult] = useState('');       // research / autotag plain text
  const [aiOptions, setAiOptions] = useState<string[]>([]);  // rewrite option cards
  const [aiError, setAiError] = useState('');
  const [finalizeMsg, setFinalizeMsg] = useState('');

  // serializeToMarkdown / saveAndApprove / discardChanges declared after useEditor (below).

  // "View all chapters" mode — combines every chapter's current-tab content in the editor.
  // Dropdown is disabled; editor is read-only; Save/Approve hidden.
  const [viewAll, setViewAll] = useState(false);

  const buildCombinedHtml = useCallback(
    (sid: string) =>
      viewChapters
        .map((ch, i) => {
          const s =
            ch.stages.find((st) => st.id === sid && st.available) ??
            ch.stages.filter((st) => st.available).at(-1);
          const body = s?.html ?? '<p><em>Stage not yet produced for this chapter.</em></p>';
          const sep = i < viewChapters.length - 1 ? '<hr>' : '';
          return `<h2>${ch.title}</h2>${body}${sep}`;
        })
        .join(''),
    [viewChapters],
  );

  const [selection, setSelection] = useState('');
  const [arabicOn, setArabicOn] = useState(false);
  const [, setTick] = useState(0);
  const refresh = () => setTick((t) => t + 1);

  const originalRef = useRef<string[]>([]);            // original text per top-level node
  const paraTagsRef = useRef<Map<number, string[]>>(new Map()); // node index -> tag ids
  const arabicRef = useRef(false);                     // mirror of arabicOn for the plugin
  const hasFocusRef = useRef(false);                   // tracks editor DOM focus for para-active
  const editorContainerRef = useRef<HTMLElement | null>(null);
  const railRef = useRef<HTMLElement | null>(null);        // left pipeline rail
  const inspectorRef = useRef<HTMLElement | null>(null);   // right inspector (height-matched to rail)
  arabicRef.current = arabicOn;
  // Per-stage diff: when a read-only step is selected, the decoration plugin can diff each
  // paragraph against the PREVIOUS stage's text (prevStageTextsRef) instead of the human-edit
  // original — so "Show changes from {prev stage}" highlights what THAT step changed.
  const showPrevDiffRef = useRef(false);
  const prevStageTextsRef = useRef<string[]>([]);
  const [showPrevDiff, setShowPrevDiff] = useState(false);
  // Index-based tag toggle, called from the floating per-paragraph icon toolbar (a PM widget
  // built outside React). Held in a ref so the widget always calls the latest closure.
  const tagFnRef = useRef<(idx: number, tagId: string) => void>(() => {});
  // Section-level AI action ref: called from the section h2 floating toolbar.
  const runAiFnRef = useRef<(kind: string) => void>(() => {});

  // Glossary -> word-boundary regex (longest first), reused by the overlay plugin.
  const glossarySorted = useMemo(
    () => [...glossary].filter((e) => e.phonetic && e.arabic_script).sort((a, b) => b.phonetic.length - a.phonetic.length),
    [glossary],
  );

  // FC-3 + FC-4 + active paragraph: one decoration plugin reading the refs.
  const StudioDecos = useMemo(
    () =>
      Extension.create({
        name: 'studioDecos',
        addProseMirrorPlugins() {
          return [
            new Plugin({
              key: new PluginKey('studioDecos'),
              props: {
                decorations(state) {
                  const orig = originalRef.current;
                  const tags = paraTagsRef.current;
                  const decos: Decoration[] = [];

                  // Section-level activation: read from ref (updated synchronously in onSelectionUpdate).
                  const activeSec = hasFocusRef.current ? activeSectionOrdinalRef.current : null;

                  // FC-1: Quran verse refs REPLACE their phrase with a compact chip. The
                  // underlying prose is NOT mutated (display:none decoration), so the
                  // NotebookLM source still reads "Surah Al-Kahf, verse 110". Collect the
                  // ranges so the Arabic overlay doesn't double-render inside them.
                  const refRanges: [number, number][] = [];
                  state.doc.descendants((tn, tpos) => {
                    if (!tn.isText || !tn.text) return;
                    SURAH_VERSE_RE.lastIndex = 0;
                    let rm: RegExpExecArray | null;
                    while ((rm = SURAH_VERSE_RE.exec(tn.text))) {
                      const num = SURAH_MAP[rm[1].replace(/’/g, "'")];
                      if (!num) continue;
                      const verse = rm[2];
                      const label = rm[3] ? `${num}:${verse}–${rm[3]}` : `${num}:${verse}`;
                      const from = tpos + rm.index;
                      const to = from + rm[0].length;
                      refRanges.push([from, to]);
                      decos.push(Decoration.inline(from, to, { class: 'ref-hidden' }));
                      decos.push(
                        Decoration.widget(from, () => {
                          const chip = document.createElement('span');
                          chip.className = 'ref-quran sp-vchip';
                          chip.textContent = label;
                          chip.setAttribute('data-surah', String(num));
                          chip.setAttribute('data-verse', verse);
                          return chip;
                        }, { side: -1 }),
                      );
                    }
                  });
                  const inRef = (p: number) => refRanges.some(([a, b]) => p >= a && p < b);

                  // Wave N: track h2 ordinal (section index, 0-based) for depth markers.
                  let sectionOrdinal = 0;
                  let currentSectionIdx = -1; // ordinal of the section paragraphs currently belong to
                  let i = 0;
                  state.doc.forEach((node, offset) => {
                    const idx = i++;
                    const t = tags.get(idx) || [];

                    // Option A: section depth badge + tag chips next to every h2.
                    if (node.type.name === 'heading' && node.attrs.level === 2) {
                      const ord = sectionOrdinal++;
                      currentSectionIdx = ord; // paragraphs following this h2 belong to section `ord`
                      const depthLevel = sectionDepthsRef.current[ord];
                      const secTags = sectionTagsRef.current[ord] ?? [];
                      const sectionSlug = node.textContent.slice(0, 60).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
                      const tagKey = secTags.join(',');
                      decos.push(
                        Decoration.widget(offset + node.nodeSize - 1, () => {
                          const wrap = document.createElement('span');
                          wrap.className = 'sp-section-annotation';
                          wrap.contentEditable = 'false';

                          // Depth badge
                          const btn = document.createElement('button');
                          btn.type = 'button';
                          btn.className = `sp-section-depth-btn${depthLevel ? ` sp-depth-${depthLevel}` : ' sp-depth-none'}`;
                          const label = depthLevel
                            ? (depthLevels.find((l) => l.key === depthLevel)?.label ?? depthLevel)
                            : '∅ depth';
                          btn.title = `Depth: ${label} — click to change`;
                          btn.textContent = label;
                          btn.addEventListener('mousedown', (ev) => {
                            ev.preventDefault(); ev.stopPropagation();
                            openDepthPicker(btn, saveSectionDepthRef.current, ord, sectionSlug, depthLevel, depthLevels, secTags);
                          });
                          wrap.appendChild(btn);

                          // Separate tag picker button
                          const tagPickerBtn = document.createElement('button');
                          tagPickerBtn.type = 'button';
                          tagPickerBtn.className = `sp-section-tag-btn${secTags.length ? ' has-tags' : ''}`;
                          tagPickerBtn.title = secTags.length ? `Tags: ${secTags.join(', ')} — click to edit` : 'Add section tags';
                          tagPickerBtn.textContent = '#';
                          tagPickerBtn.addEventListener('mousedown', (ev) => {
                            ev.preventDefault(); ev.stopPropagation();
                            openTagPicker(tagPickerBtn, saveSectionDepthRef.current, ord, sectionSlug, secTags, depthLevel ?? '');
                          });
                          wrap.appendChild(tagPickerBtn);

                          // Tag chips (inline, display only)
                          for (const tid of secTags) {
                            const chip = document.createElement('span');
                            chip.className = `sp-section-tag-chip sp-tag-${tid}`;
                            chip.textContent = SECTION_TAGS.find((t) => t.id === tid)?.label ?? tid;
                            chip.title = `Tag: ${tid}`;
                            wrap.appendChild(chip);
                          }

                          // Edit button: moves cursor into section body, activates section-level editing.
                          const editBtn = document.createElement('button');
                          editBtn.type = 'button';
                          editBtn.className = 'sp-section-edit-btn';
                          editBtn.textContent = '✏ Edit';
                          editBtn.title = 'Click to edit this section';
                          editBtn.addEventListener('mousedown', (ev) => {
                            ev.preventDefault(); ev.stopPropagation();
                            const ed = editorRef.current;
                            if (!ed) return;
                            let bodyStart = -1;
                            let sec = -1;
                            ed.state.doc.forEach((n, o) => {
                              if (n.type.name === 'heading' && n.attrs.level === 2) {
                                sec++;
                                if (sec === ord) bodyStart = o + n.nodeSize;
                              }
                            });
                            if (bodyStart >= 0) {
                              ed.commands.setTextSelection(bodyStart + 1);
                              ed.view.focus();
                            }
                          });
                          wrap.appendChild(editBtn);

                          return wrap;
                        }, { side: 1, key: `sec-annot-${ord}-${depthLevel ?? 'none'}-${tagKey}` }),
                      );

                      // AI toolbar on active section's h2 (right-aligned, above heading).
                      if (activeSec === ord) {
                        decos.push(
                          Decoration.widget(offset + 1, () => {
                            const bar = document.createElement('div');
                            bar.contentEditable = 'false';
                            bar.className = 'sp-para-tools sp-para-tools--palette sp-para-tools--ai';
                            const AI_ACTIONS = [
                              { kind: 'rewrite',  label: '↺', title: 'Rewrite section' },
                              { kind: 'research', label: '🔍', title: 'Research context' },
                              { kind: 'autotag',  label: '🏷', title: 'Auto-tag section' },
                            ];
                            for (const action of AI_ACTIONS) {
                              const b = document.createElement('button');
                              b.type = 'button';
                              b.className = 'sp-ptool sp-ptool--ai';
                              b.title = action.title;
                              b.textContent = action.label;
                              b.addEventListener('mousedown', (ev) => {
                                ev.preventDefault(); ev.stopPropagation();
                                runAiFnRef.current(action.kind);
                              });
                              bar.appendChild(b);
                            }
                            return bar;
                          }, { side: -1, key: `sec-tools-${ord}` }),
                        );
                      }
                    }

                    // Section-active: h2 gets accent border via CSS; paragraphs get warm tint.
                    if (activeSec !== null && currentSectionIdx === activeSec) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: 'section-active' }));
                    }

                    // Tagged paragraphs: marks toolbar only (tag icons, toggleable).
                    if (t.length) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: `para-tagged tag-${t[0]}` }));
                      decos.push(
                        Decoration.widget(offset + 1, () => {
                          const bar = document.createElement('div');
                          bar.contentEditable = 'false';
                          bar.className = 'sp-para-tools sp-para-tools--marks';
                          const shown = TAGS.filter((tag) => t.includes(tag.id));
                          for (const tag of shown) {
                            const b = document.createElement('button');
                            b.type = 'button';
                            b.className = `sp-ptool tag-${tag.id} is-on`;
                            b.title = `${tag.label} (click to remove)`;
                            b.textContent = tag.icon;
                            b.addEventListener('mousedown', (ev) => {
                              ev.preventDefault(); ev.stopPropagation();
                              tagFnRef.current(idx, tag.id);
                            });
                            bar.appendChild(b);
                          }
                          return bar;
                        }, { side: -1, key: `tools-${idx}-marks-${t.join(',')}` }),
                      );
                    }
                    // FC-3 Word-level track changes vs the original snapshot.
                    // In prev-stage-diff mode: diff current node against the PREVIOUS stage's
                    // paragraph instead (showing what THIS step changed, not human edits).
                    const prevDiff = showPrevDiffRef.current;
                    const before = prevDiff ? (prevStageTextsRef.current[idx] ?? '') : orig[idx];
                    const insClass = prevDiff ? 'aug-ins' : 'tc-ins';
                    const delClass = prevDiff ? 'aug-del' : 'tc-del';
                    const after = node.textContent;
                    if (before !== undefined && before !== after) {
                      let cursor = offset + 1; // content start of a textblock
                      for (const part of diffWords(before, after)) {
                        const len = part.value.length;
                        if (part.added) {
                          decos.push(Decoration.inline(cursor, cursor + len, { class: insClass }));
                          cursor += len;
                        } else if (part.removed) {
                          const text = part.value;
                          decos.push(
                            Decoration.widget(cursor, () => {
                              const del = document.createElement('span');
                              del.className = delClass;
                              del.textContent = text;
                              return del;
                            }, { side: -1 }),
                          );
                        } else {
                          cursor += len;
                        }
                      }
                    }

                    // FC-4 Arabic overlay (non-destructive): hide the English run, inject Arabic.
                    if (arabicRef.current && glossarySorted.length) {
                      node.descendants((child, childPos) => {
                        if (!child.isText || !child.text) return;
                        const base = offset + 1 + childPos;
                        for (const e of glossarySorted) {
                          // Don't fire inside compounds/possessives: skip if adjacent to a
                          // letter, hyphen, or apostrophe (so "al-Quran"/"Ghazali's" stay English).
                          const re = new RegExp(`(?<![\\w-])${e.phonetic.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![\\w'’-])`, 'g');
                          let mm: RegExpExecArray | null;
                          while ((mm = re.exec(child.text!))) {
                            const from = base + mm.index;
                            const to = from + mm[0].length;
                            if (inRef(from)) continue; // verse-ref phrase is already replaced by a chip
                            decos.push(Decoration.inline(from, to, { class: 'ar-hidden' }));
                            const script = e.arabic_script;
                            decos.push(
                              Decoration.widget(from, () => {
                                const s = document.createElement('span');
                                s.className = 'ar-script-chip';
                                s.setAttribute('lang', 'ar');
                                s.setAttribute('dir', 'rtl');
                                s.textContent = script;
                                return s;
                              }, { side: -1 }),
                            );
                          }
                        }
                      });
                    }
                  });
                  return DecorationSet.create(state.doc, decos);
                },
              },
            }),
          ];
        },
      }),
    [glossarySorted],
  );

  const editor = useEditor({
    extensions: [StarterKit, MarkerHighlight, StudioDecos],
    content: html,
    onCreate({ editor }) {
      const texts: string[] = [];
      editor.state.doc.forEach((n) => texts.push(n.textContent));
      originalRef.current = texts;
    },
    onFocus({ editor }) {
      hasFocusRef.current = true;
      // Dispatch an empty transaction so the decoration plugin re-evaluates.
      editor.view.dispatch(editor.state.tr);
    },
    onBlur({ editor }) {
      hasFocusRef.current = false;
      setActiveParaIdx(null);
      activeSectionOrdinalRef.current = null;
      setActiveSectionOrdinal(null);
      editor.view.dispatch(editor.state.tr);
    },
    onUpdate() { refresh(); },
    onSelectionUpdate({ editor }) {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, ' ').trim());
      // Track active paragraph index (for comment/tag panels) and active section ordinal (for AI).
      const $head = editor.state.selection.$head;
      let paraIdx = -1;
      let secOrd = -1;
      let curSec = -1;
      let i = 0;
      editor.state.doc.forEach((node, offset) => {
        if (node.type.name === 'heading' && node.attrs.level === 2) curSec++;
        const depth1End = offset + (editor.state.doc.child(i)?.nodeSize ?? 0);
        if ($head.pos >= offset && $head.pos < depth1End) {
          paraIdx = i;
          secOrd = curSec;
        }
        i++;
      });
      const newSecOrd = secOrd >= 0 ? secOrd : null;
      activeSectionOrdinalRef.current = newSecOrd; // update ref immediately so the plugin sees it
      setActiveSectionOrdinal(newSecOrd);
      setActiveParaIdx(paraIdx >= 0 ? paraIdx : null);
      refresh(); // re-evaluate section decoration on caret moves
    },
  });

  // Keep editorRef in sync so depth-save dispatch always has the live editor.
  editorRef.current = editor;

  // Click outside the editor container → blur the editor DOM element.
  // The onBlur callback above handles clearing hasFocusRef + dispatching the decoration update.
  useEffect(() => {
    const onMouseDown = (e: MouseEvent) => {
      if (editorContainerRef.current && !editorContainerRef.current.contains(e.target as Node)) {
        editor?.view.dom.blur();
      }
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [editor]);

  // Match the right inspector's height to the left pipeline rail so the two side
  // panels are balanced. The rail height is dynamic (version count, lineage
  // switch), so a ResizeObserver keeps them in sync. Side-by-side only — when the
  // grid collapses to one column (≤1100px) the height is released to natural flow.
  useEffect(() => {
    const rail = railRef.current;
    const insp = inspectorRef.current;
    if (!rail || !insp) return;
    const sync = () => {
      if (window.matchMedia('(max-width: 1100px)').matches) {
        insp.style.height = '';
      } else {
        insp.style.height = `${rail.offsetHeight}px`;
      }
    };
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(rail);
    window.addEventListener('resize', sync);
    return () => { ro.disconnect(); window.removeEventListener('resize', sync); };
  }, []);

  // Switch the editor to the selected stage: load its text, re-snapshot redline originals,
  // clear stage-specific tags, and make only the under-review stage editable (upstream = read-only).
  useEffect(() => {
    if (!editor || !stage) return;
    if (viewAll) {
      editor.commands.setContent(buildCombinedHtml(stageId));
      originalRef.current = [];
      paraTagsRef.current = new Map();
      editor.setEditable(false);
    } else {
      editor.commands.setContent(stage.html);
      const texts: string[] = [];
      editor.state.doc.forEach((n) => texts.push(n.textContent));
      originalRef.current = texts;
      paraTagsRef.current = new Map();
      editor.setEditable(!isReadOnlyStage);
    }
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageId, chapIdx, activeLineageId, viewAll, editor]);

  // (Re-)populate the previous-stage diff baseline whenever the selected step / chapter /
  // lineage changes, and set a sensible default for the "show changes" toggle: ON for a
  // read-only step with a moderate delta, OFF for the editable step or a huge compression
  // (a near-total rewrite would just be a wall of strikethrough).
  useEffect(() => {
    const m = metrics.find((x) => x.id === stageId);
    const prevId = m?.comparedTo ?? null;
    prevStageTextsRef.current = [];
    if (prevId) {
      const prevStage = stages.find((s) => s.id === prevId);
      if (prevStage?.html) {
        const div = document.createElement('div');
        div.innerHTML = prevStage.html;
        prevStageTextsRef.current = Array.from(div.children).map((el) => el.textContent ?? '');
      }
    }
    const big = m?.deltaPct != null && Math.abs(m.deltaPct) >= 60;
    const next = isReadOnlyStage && !!prevId && !big;
    showPrevDiffRef.current = next;
    setShowPrevDiff(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageId, chapIdx, activeLineageId]);

  // ── Serialize / save / discard — declared here so editor is in scope ────────

  // Walk a ProseMirror text node and emit its content with inline mark syntax preserved.
  // Handles italic (*), bold (**), bold+italic (***) — the only marks used in stage files.
  const serializeInline = useCallback((node: PMNode): string => {
    let out = '';
    node.forEach((child: PMNode) => {
      if (!child.isText || !child.text) return;
      const text = child.text;
      const marks = child.marks.map((m) => m.type.name);
      const isBold   = marks.includes('bold');
      const isItalic = marks.includes('italic');
      if (isBold && isItalic) out += `***${text}***`;
      else if (isBold)        out += `**${text}**`;
      else if (isItalic)      out += `*${text}*`;
      else                    out += text;
    });
    return out;
  }, [editor]);

  const serializeToMarkdown = useCallback((): string => {
    if (!editor) return '';
    const lines: string[] = [];
    editor.state.doc.forEach((node) => {
      const type = node.type.name;
      if (type === 'heading') {
        const level = node.attrs.level as number;
        lines.push('#'.repeat(level) + ' ' + serializeInline(node));
      } else if (type === 'blockquote') {
        lines.push('> ' + serializeInline(node).split('\n').join('\n> '));
      } else {
        lines.push(serializeInline(node));
      }
      lines.push('');
    });
    return lines.join('\n').trimEnd() + '\n';
  }, [editor, serializeInline]);

  const saveAndApprove = useCallback(async () => {
    if (!stage || !editor) return;
    setSaving(true);
    setSaveError('');
    try {
      const content = serializeToMarkdown();
      const comments = Object.fromEntries(
        [...commentsRef.current.entries()]
          .filter(([, v]) => v.trim())
          .map(([k, v]) => [String(k), v.trim()]),
      );
      const saveRes = await fetch('/api/studio/save-stage', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, chapter, stage: stage.id, content, comments }),
      });
      if (!saveRes.ok) {
        const err = await saveRes.json().catch(() => ({}));
        setSaveError((err as { error?: string }).error ?? `Save failed (${saveRes.status})`);
        return;
      }
      const approveRes = await fetch('/api/studio/review', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, chapter, stage: stage.id, approved: true }),
      });
      if (approveRes.ok) {
        setApprovedStages((m) => ({ ...m, [stage.id]: true }));
        const texts: string[] = [];
        editor.state.doc.forEach((n) => texts.push(n.textContent));
        originalRef.current = texts;
        refresh();
      }
    } catch (e) {
      setSaveError(`Network error: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }, [slug, chapter, stage, editor, serializeToMarkdown]);

  const discardChanges = useCallback(() => {
    if (!editor || !stage) return;
    editor.commands.setContent(stage.html);
    const texts: string[] = [];
    editor.state.doc.forEach((n) => texts.push(n.textContent));
    originalRef.current = texts;
    paraTagsRef.current = new Map();
    commentsRef.current = new Map();
    refreshComments();
    refresh();
  }, [editor, stage]);

  // Force a decoration recompute when Arabic mode flips. Set the ref BEFORE dispatching
  // (React state is async — the plugin reads arabicRef synchronously during the recompute).
  const toggleArabic = useCallback(() => {
    const next = !arabicRef.current;
    arabicRef.current = next;
    setArabicOn(next);
    if (editor) editor.view.dispatch(editor.state.tr.setMeta('arabic', true));
  }, [editor]);

  // Toggle the "changes from previous stage" redline (read-only steps). Ref-before-dispatch
  // so the decoration plugin sees the new value synchronously during the recompute.
  const togglePrevDiff = useCallback(() => {
    const next = !showPrevDiffRef.current;
    showPrevDiffRef.current = next;
    setShowPrevDiff(next);
    if (editor) editor.view.dispatch(editor.state.tr.setMeta('prevDiff', true));
  }, [editor]);

  // ── Wave L-8: AI assist + Finalize ──────────────────────────────────────
  // Text of the paragraph at a given doc index (kept for finalize/compat).
  const paragraphText = useCallback((idx: number): string => {
    if (!editor) return '';
    let i = 0;
    let out = '';
    editor.state.doc.forEach((n) => {
      if (i === idx) out = n.textContent;
      i++;
    });
    return out;
  }, [editor]);

  // All text (heading + paragraphs) of a section, joined by double newline.
  const sectionText = useCallback((ordinal: number | null): string => {
    if (!editor || ordinal === null) return '';
    const parts: string[] = [];
    let curSec = -1;
    editor.state.doc.forEach((node) => {
      if (node.type.name === 'heading' && node.attrs.level === 2) curSec++;
      if (curSec === ordinal) {
        const t = node.textContent.trim();
        if (t) parts.push(t);
      }
    });
    return parts.join('\n\n');
  }, [editor]);

  // Run an AI action on the active section. `kind` selects the route + model.
  const runAi = useCallback(async (kind: string) => {
    const text = sectionText(activeSectionOrdinal);
    if (!text.trim()) return;
    setAiBusy(true); setAiKind(kind); setAiResult(''); setAiOptions([]); setAiError('');
    setInspectorTab('ai'); // auto-switch so result is visible immediately
    try {
      let res: Response;
      if (kind === 'rewrite') {
        res = await fetch('/api/ai/rewrite', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ text }),
        });
      } else if (kind === 'research') {
        res = await fetch('/api/ai/research', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            paragraphText: text,
            instruction: 'Research this passage and provide scholarly context with web-sourced information.',
            bookTitle: chapterTitle,
            actionType: 'research',
          }),
        });
      } else if (kind === 'autotag') {
        res = await fetch('/api/ai/claude', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ task: 'categorise', text }),
        });
      } else {
        setAiBusy(false); return;
      }
      const json = await res.json();
      if (!res.ok || json.ok === false) {
        setAiError(json.error ?? `Request failed (${res.status})`);
      } else if (kind === 'autotag') {
        const { tag, reason } = json.data ?? {};
        setAiResult(`Suggested tag: ${tag}${reason ? ` — ${reason}` : ''}`);
      } else if (kind === 'rewrite') {
        let opts = (json.data?.options ?? json.options ?? []) as string[];
        // Fallback fix: if opts[0] is a raw JSON string (from API error path), re-parse it.
        if (opts.length === 1 && typeof opts[0] === 'string' && opts[0].trimStart().startsWith('{')) {
          try {
            const inner = JSON.parse(opts[0]) as { options?: string[] };
            if (Array.isArray(inner.options) && inner.options.length > 0) opts = inner.options;
          } catch { /* keep opts as-is */ }
        }
        setAiOptions(opts.slice(0, 3).map((o) => String(o).trim()));
      } else if (kind === 'research') {
        const body = json.fullText ?? json.prompt ?? '';
        const sources = (json.sources as string[] | undefined) ?? [];
        const sourced = sources.length ? `\n\nSources:\n${sources.map((s) => `• ${s}`).join('\n')}` : '';
        setAiResult(body + sourced);
      } else {
        setAiResult(typeof json.data === 'string' ? json.data : JSON.stringify(json.data));
      }
    } catch (e) {
      setAiError(String(e));
    } finally {
      setAiBusy(false);
    }
  }, [activeSectionOrdinal, sectionText, chapterTitle, setInspectorTab]);

  // Apply a rewrite option to the active section: replaces all body paragraphs.
  const applySection = useCallback((newText: string) => {
    if (!editor || activeSectionOrdinal === null) return;
    let bodyFrom = -1;
    let bodyTo = editor.state.doc.content.size;
    let curSec = -1;
    let foundSection = false;
    editor.state.doc.forEach((node, offset) => {
      if (node.type.name === 'heading' && node.attrs.level === 2) {
        curSec++;
        if (curSec === activeSectionOrdinal) {
          bodyFrom = offset + node.nodeSize;
          foundSection = true;
        } else if (foundSection) {
          bodyTo = offset;
          foundSection = false;
        }
      }
    });
    if (bodyFrom < 0) return;
    const schema = editor.state.schema;
    const paragraphs = newText.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
    const nodes = paragraphs.length > 0
      ? paragraphs.map((p) => schema.nodes.paragraph.create(null, schema.text(p)))
      : [schema.nodes.paragraph.create()];
    editor.view.dispatch(editor.state.tr.replaceWith(bodyFrom, bodyTo, nodes));
    refresh();
  }, [editor, activeSectionOrdinal]);

  // Finalize: gather paragraphs + tags + comments → Claude brief → clipboard.
  const finalize = useCallback(async () => {
    if (!editor) return;
    setFinalizeMsg('Generating brief…');
    const paragraphs: { idx: number; text: string; tags: string[]; comment: string }[] = [];
    let i = 0;
    editor.state.doc.forEach((n) => {
      const tags = paraTagsRef.current.get(i) ?? [];
      const comment = commentsRef.current.get(i) ?? '';
      if (tags.length || comment.trim()) {
        paragraphs.push({ idx: i, text: n.textContent.slice(0, 400), tags, comment });
      }
      i++;
    });
    try {
      const res = await fetch('/api/ai/claude', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ task: 'finalize', slug, chapter, paragraphs }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false) {
        setFinalizeMsg(`Failed: ${json.error ?? res.status}`);
        return;
      }
      const brief = json.data?.brief ?? '';
      await navigator.clipboard.writeText(brief);
      setFinalizeMsg('Brief copied — paste into Claude Code IDE to continue.');
    } catch (e) {
      setFinalizeMsg(`Failed: ${String(e)}`);
    }
  }, [editor, slug, chapter]);

  // Publish = mark THIS chapter finalized (reuses the per-chapter review JSON via
  // POST /api/studio/review {finalize}). Reversible. Disabled in archived view.
  const [publishing, setPublishing] = useState(false);
  const toggleFinalized = useCallback(async () => {
    if (isArchivedView) return;
    const next = finalized ? false : true;
    setPublishing(true);
    try {
      const res = await fetch('/api/studio/review', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, chapter, finalize: next }),
      });
      if (res.ok) {
        const json = await res.json().catch(() => ({}));
        setFinalized(next ? (json?.data?.finalized ?? { at: new Date().toISOString() }) : null);
      }
    } catch { /* non-blocking */ } finally {
      setPublishing(false);
    }
  }, [slug, chapter, finalized, isArchivedView]);

  // Persist a paragraph comment to SQLite (annotations API) on blur.
  const persistComment = useCallback((idx: number, note: string) => {
    fetch('/api/annotations', {
      method: 'PATCH', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ book: slug, chapter, paraIdx: idx, note }),
    }).catch(() => { /* non-blocking; comment is also saved with the stage */ });
  }, [slug, chapter]);

  // Pre-load saved paragraph comments from SQLite when the chapter changes.
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/annotations?book=${encodeURIComponent(slug)}&chapter=${encodeURIComponent(chapter)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => {
        if (cancelled || !json) return;
        const notes = json.data?.notes ?? json.notes ?? {};
        for (const [idx, note] of Object.entries(notes)) {
          if (typeof note === 'string' && note.trim()) {
            commentsRef.current.set(Number(idx), note);
          }
        }
        refreshComments();
      })
      .catch(() => { /* offline-friendly; stage-saved comments still load */ });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, chapter]);

  let changedCount = 0;
  if (editor) {
    let i = 0;
    editor.state.doc.forEach((n) => {
      if (originalRef.current[i] !== undefined && n.textContent !== originalRef.current[i]) changedCount++;
      i++;
    });
  }
  let taggedCount = 0;
  paraTagsRef.current.forEach((t) => { if (t.length) taggedCount++; });

  const tagByIdx = useCallback(
    (idx: number, tagId: string) => {
      if (!editor) return;
      const map = paraTagsRef.current;
      const cur = map.get(idx) || [];
      map.set(idx, cur.includes(tagId) ? cur.filter((x) => x !== tagId) : [...cur, tagId]);
      editor.view.dispatch(editor.state.tr.setMeta('refreshTags', true));
      refresh();
    },
    [editor],
  );
  tagFnRef.current = tagByIdx;
  runAiFnRef.current = (kind: string) => void runAi(kind);

  const rawMarkers = scanMarkers(html.replace(/<[^>]+>/g, ' '));
  const seen = new Map<string, { kind: string; text: string; count: number }>();
  for (const m of rawMarkers) {
    const key = `${m.kind}|${m.text}`;
    const e = seen.get(key);
    if (e) e.count += 1;
    else seen.set(key, { ...m, count: 1 });
  }
  const markers = [...seen.values()];
  const group = (kind: string) => markers.filter((m) => m.kind === kind);

  const renderGroup = (label: string, items: typeof markers, cls: string) =>
    items.length > 0 && (
      <div className="sp-mgroup">
        <h4 className="sp-mgroup-title">
          <span className={`sp-chip sp-chip--${cls}`}>{label}</span>
          <span className="sp-mgroup-count">{items.length}</span>
        </h4>
        <ul className="sp-marker-list">
          {items.map((m, i) => (
            <li key={i}>
              <span className="sp-marker-text">{m.text}</span>
              {m.count > 1 && <span className="sp-marker-count">×{m.count}</span>}
            </li>
          ))}
        </ul>
      </div>
    );

  // Timeline rail items: the full transformation chain UP TO the editable Review
  // (latest at top, descending into older steps). Uncaptured intermediate stages
  // are shown muted + non-interactive so the whole journey is visible even when a
  // run didn't write every stage. Stages AFTER the editable top (e.g. narrator
  // not yet run) are omitted — they're not part of "the journey that led here".
  const editableIdx = stages.findIndex((s) => s.id === editableStageId);
  const railStages = stages.slice(0, editableIdx >= 0 ? editableIdx + 1 : stages.length).reverse();
  const hasUncaptured = railStages.some((s) => !s.available);

  // Pipeline phases for the rail's spine. Fallback to a lone "Edit" node so the
  // rail still renders if phases weren't supplied.
  const phases: PipelineStep[] = pipelineSteps.length
    ? pipelineSteps
    : [{ id: 'edit', label: 'Edit & Enrich', state: 'active', detail: '' }];

  return (
    <div className="studio-poc">
      {/* Left rail: TWO clean modules — (1) the book-level pipeline spine
          (Intake → … → Publish, contiguous, never interrupted), then (2) this
          chapter's draft versions as a separate module. Different granularities,
          not interleaved. */}
      <nav className="st-rail" aria-label="Pipeline timeline" ref={railRef}>
        {/* Companion reading edition — a peer deliverable to the podcast (not a
            per-chapter version, not a pipeline phase), so it gets its own zone
            pinned above the timeline. */}
        <div className="st-deliverable">
          <a
            className="st-book-link"
            href={`/studio/${slug}/book`}
            title="Open the companion reading edition (the book)"
          >
            <span className="st-book-glyph" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5z" />
                <path d="M4 19.5A1.5 1.5 0 0 1 5.5 18H20v3H5.5A1.5 1.5 0 0 1 4 19.5z" />
              </svg>
            </span>
            <span className="st-book-text">
              <span className="st-book-label">Reading edition</span>
              <span className="st-book-meta">the companion book</span>
            </span>
          </a>
        </div>

        <div className="st-rail-head">
          <span className="st-rail-eyebrow">Pipeline</span>
        </div>

        <ol className="st-phases">
          {phases.map((step) => {
            const isCurrent = step.id === activeStep;
            const glyph = step.state === 'done' ? '✓' : step.state === 'blocked' ? '!' : '';
            return (
              <li key={step.id} className={`st-phase st-phase--${step.state}${isCurrent ? ' is-current' : ''}`}>
                <a
                  className="st-phase-link"
                  href={`/studio/${slug}/${step.id}`}
                  aria-current={isCurrent ? 'page' : undefined}
                  title={`${step.label}${step.detail ? ` — ${step.detail}` : ''}`}
                >
                  <span className="st-phase-dot" aria-hidden="true">{glyph}</span>
                  <span className="st-phase-text">
                    <span className="st-phase-label">{step.label}</span>
                    {step.detail && <span className="st-phase-detail">{step.detail}</span>}
                  </span>
                </a>
              </li>
            );
          })}
        </ol>

        <div className="st-versions-module">
          <div className="st-versions-head">Transformation · this chapter</div>
          <ol className="st-list">
            {railStages.map((s) => {
              const isTop = s.id === editableStageId && !isArchivedView;
              const m = metrics.find((x) => x.id === s.id);
              const active = s.id === stageId;
              const role = stageRole(s.id);
              const badge = role.role ? (
                <span className={`st-role st-role--${role.kind}`}>{role.role}</span>
              ) : null;

              // Uncaptured stage: a muted, non-interactive rung so the full
              // journey is visible without offering a click that shows empty text.
              if (!s.available) {
                return (
                  <li key={s.id} className="st-item is-uncaptured">
                    <span className="st-link is-static">
                      <span className="st-dot" aria-hidden="true" />
                      <span className="st-text">
                        <span className="st-label">
                          {s.label}
                          {badge}
                        </span>
                        <span className="st-meta">not captured in this run</span>
                      </span>
                    </span>
                  </li>
                );
              }

              return (
                <li key={s.id} className={`st-item${active ? ' is-active' : ''}${isTop ? ' is-editable' : ' is-readonly'}`}>
                  <button
                    type="button"
                    className="st-link"
                    aria-current={active ? 'step' : undefined}
                    onClick={() => setStageId(s.id)}
                    title={isTop ? 'Review — the editable version' : `${s.label} — click to view (read-only)`}
                  >
                    <span className="st-dot" aria-hidden="true" />
                    <span className="st-text">
                      <span className="st-label">
                        {isTop ? 'Review' : s.label}
                        {badge}
                        {isTop && <span className="st-edit-flag">editable</span>}
                      </span>
                      {m && (
                        <span className="st-meta">
                          {m.words.toLocaleString()} words
                          {m.deltaPct !== null && (
                            <span className={`st-delta ${m.deltaPct < 0 ? 'is-down' : m.deltaPct > 0 ? 'is-up' : ''}`}>
                              {m.deltaPct > 0 ? '+' : ''}{m.deltaPct}%
                            </span>
                          )}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          {hasUncaptured && !isArchivedView && archivedLineages.length > 0 && (
            <p className="st-uncaptured-hint">
              Earlier stages weren't kept for this run — open the archived journey below to see the full chain.
            </p>
          )}

          {archivedLineages.length > 0 && (
            <div className="st-lineage">
              {isArchivedView ? (
                <>
                  <button type="button" className="st-lineage-btn" onClick={() => switchLineage('current')}>
                    ← Current rebuild
                  </button>
                  <p className="st-lineage-note">{activeLineage.label} · view only</p>
                </>
              ) : (
                <button type="button" className="st-lineage-btn" onClick={() => switchLineage(archivedLineages[0].id)}>
                  View archived journey →
                </button>
              )}
            </div>
          )}
        </div>
      </nav>

      <main className="studio-poc__editor" ref={editorContainerRef}>
        {/* Consolidated editor header: chapter switcher · metrics · finalize. */}
        <div className="sp-editor-head">
          <div className="sp-chapsel">
            <label htmlFor="sp-chap">Chapter</label>
            <select
              id="sp-chap"
              value={chapIdx}
              disabled={viewAll}
              onChange={(e) => setChapIdx(Number(e.target.value))}
            >
              {viewChapters.map((c, i) => (
                <option key={c.slug} value={i}>{i + 1}. {c.title}</option>
              ))}
            </select>
            <button
              type="button"
              className={`sp-viewall-btn${viewAll ? ' is-on' : ''}`}
              onClick={() => setViewAll((v) => !v)}
              title={viewAll ? 'Return to single-chapter view' : 'Combine all chapters in this tab'}
            >
              {viewAll ? '← Single chapter' : 'All chapters →'}
            </button>
          </div>
          {!viewAll && (() => {
            const m = metrics.find((x) => x.id === stageId);
            if (!m || !m.available) return null;
            const priorLabel = stages.find((s) => s.id === m.comparedTo)?.label;
            const delta = m.deltaPct;
            return (
              <div className="sp-metrics">
                <span>{m.words.toLocaleString()} words · {m.sentences.toLocaleString()} sentences</span>
                {delta !== null && priorLabel && (
                  <span className={`sp-metric-delta ${delta < 0 ? 'is-down' : delta > 0 ? 'is-up' : ''}`}>
                    {delta > 0 ? '+' : ''}{delta}% vs {priorLabel}
                    {stageId === 'denoised' && m.comparedTo === 'core' && delta < 0 && ` (${Math.abs(delta)}% noise removed)`}
                  </span>
                )}
              </div>
            );
          })()}
          {!viewAll && !isArchivedView && (
            <button
              type="button"
              className={`sp-finalize-chapter${finalized ? ' is-done' : ''}`}
              onClick={toggleFinalized}
              disabled={publishing}
              title={finalized ? 'Chapter finalized — click to unlock' : 'Mark this chapter finalized'}
            >
              {finalized ? '✓ Finalized' : publishing ? 'Finalizing…' : 'Finalize chapter'}
            </button>
          )}
        </div>
        {!viewAll && (
          <TransformationDashboard
            chapterTitle={chap.title}
            stages={stages}
            metrics={metrics}
            enrichment={enrichment}
            glossaryCount={glossaryCount}
          />
        )}
        {viewAll && (
          <div className="sp-viewall-banner">
            Showing all {viewChapters.length} chapters · {stages.find((s) => s.id === stageId)?.label ?? stageId} stage · read-only
          </div>
        )}
        {!viewAll && stage && (() => {
          const m = metrics.find((x) => x.id === stageId);
          const prevLabel = stages.find((s) => s.id === m?.comparedTo)?.label;
          const role = stageRole(stage.id);
          const isReviewTop = stage.id === editableStageId && !isArchivedView;
          const displayName = isReviewTop ? 'Review' : stage.label;
          const delta = m?.deltaPct ?? null;
          let metricText: string | null = null;
          if (m?.available && delta !== null && prevLabel) {
            metricText =
              stage.id === 'denoised' && m.comparedTo === 'core' && delta < 0
                ? `${Math.abs(delta)}% noise removed`
                : `${delta > 0 ? '+' : ''}${delta}% vs ${prevLabel}`;
          }
          return (
            <div className={`sp-stage-card sp-stage-card--${role.kind}`}>
              <div className="sp-stage-card-main">
                <span className="sp-stage-card-name">{displayName}</span>
                {role.role && <span className={`sp-stage-card-role sp-stage-card-role--${role.kind}`}>{role.role}</span>}
                {role.tool && <span className="sp-stage-card-tool">{role.tool}</span>}
                {isReviewTop ? (
                  <span className="sp-stage-card-flag is-editable">editable</span>
                ) : (
                  <span className="sp-stage-card-flag is-readonly">
                    read-only{isArchivedView ? ` · ${activeLineage.label}` : ''}
                  </span>
                )}
                {metricText && <span className="sp-stage-card-metric">{metricText}</span>}
              </div>
              {isReadOnlyStage && prevLabel && (
                <div className="sp-stage-card-diff">
                  <button
                    type="button"
                    className={`sp-augdiff-toggle${showPrevDiff ? ' is-on' : ''}`}
                    onClick={togglePrevDiff}
                    title={showPrevDiff ? 'Hide the changes' : `Highlight what changed from ${prevLabel}`}
                  >
                    {showPrevDiff ? 'Hide changes' : `Show changes from ${prevLabel}`}
                  </button>
                  {showPrevDiff && (
                    <span className="sp-augdiff-legend">
                      <span className="aug-ins sp-augdiff-swatch">added</span>
                      <span className="aug-del sp-augdiff-swatch">removed</span>
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })()}
        <EditorContent editor={editor} />
      </main>

      <aside className="studio-poc__inspector" aria-label="Contextual inspector" ref={inspectorRef}>
        {/* M-1 — Slim global action strip: Arabic toggle · Save & Approve · Finalize */}
        <div className="sp-global-strip">
          <span className="sp-global-arabic">
            <span lang="ar" dir="rtl">ع</span>
            <button
              type="button"
              role="switch"
              aria-checked={arabicOn}
              className={`sp-arabic-btn${arabicOn ? ' is-on' : ''}`}
              onClick={toggleArabic}
              title={arabicOn ? 'Hide Arabic script' : 'Show Arabic script'}
            >
              {arabicOn ? 'Arabic On' : 'Arabic'}
            </button>
          </span>
          {!viewAll && !isReadOnlyStage && stage && (
            <>
              <div className="sp-strip-sep" aria-hidden="true" />
              <button
                type="button"
                className={`sp-approve sp-approve--strip${approvedStages[stage.id] ? ' is-done' : ''}`}
                onClick={saveAndApprove}
                disabled={saving || approvedStages[stage.id]}
              >
                {approvedStages[stage.id]
                  ? `✓ ${stage.label} approved`
                  : saving ? 'Saving…'
                  : `Save & Approve`}
              </button>
              {changedCount > 0 && !approvedStages[stage.id] && (
                <button
                  type="button"
                  className="sp-discard"
                  onClick={discardChanges}
                  disabled={saving}
                  title="Discard all edits and revert to original"
                >
                  Discard
                </button>
              )}
            </>
          )}
          {!viewAll && !isArchivedView && (
            <>
              <div className="sp-strip-sep" aria-hidden="true" />
              <button type="button" className="sp-finalize" onClick={finalize} title="Generate Claude brief from tagged paragraphs">
                ⎘ Brief
              </button>
            </>
          )}
        </div>
        {saveError && <p className="sp-save-error">{saveError}</p>}
        {finalizeMsg && <p className="sp-finalize-msg" aria-live="polite">{finalizeMsg}</p>}

        {/* M-1 — Tabbed panel: Details · Comment · AI · References */}
        <div className="sp-panel-card">
          <div className="sp-tab-bar" role="tablist" aria-label="Inspector tabs">
            {(['details', 'comment', 'ai', 'refs'] as const).map((tab) => {
              const labels: Record<string, string> = { details: 'Details', comment: 'Comment', ai: 'AI', refs: 'References' };
              const hasDot = tab === 'ai' && (!!aiResult || aiOptions.length > 0 || aiBusy);
              return (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  id={`sp-tab-${tab}`}
                  aria-controls="sp-tab-panel"
                  aria-selected={inspectorTab === tab}
                  data-tab={tab}
                  className={`sp-tab-btn${inspectorTab === tab ? ' is-active' : ''}`}
                  onClick={() => setInspectorTab(tab)}
                >
                  {labels[tab]}
                  {hasDot && <span className="sp-tab-dot" aria-label="result ready" />}
                </button>
              );
            })}
          </div>

          <div className="sp-tab-pane" role="tabpanel" id="sp-tab-panel" aria-labelledby={`sp-tab-${inspectorTab}`} tabIndex={0}>
            {/* ── Details tab: chapter overview + tag buttons for active paragraph ── */}
            {inspectorTab === 'details' && (
              <>
                {selection ? (
                  <blockquote className="sp-insp-sel">{selection}</blockquote>
                ) : (
                  <dl className="sp-insp-meta">
                    <dt>Chapter</dt>
                    <dd>{chapterTitle}</dd>
                    <dt>Changes</dt>
                    <dd>{changedCount} edited · {taggedCount} tagged</dd>
                    <dt>Comments</dt>
                    <dd>{commentsRef.current.size > 0 ? `${commentsRef.current.size} paragraph${commentsRef.current.size !== 1 ? 's' : ''}` : '—'}</dd>
                  </dl>
                )}
                {activeParaIdx !== null && !isReadOnlyStage && (
                  <div>
                    <p className="sp-insp-hint">Tags · paragraph {activeParaIdx + 1}</p>
                    <div className="sp-insp-tags" role="toolbar" aria-label="Editorial tags">
                      {TAGS.map((tag) => {
                        const isOn = (paraTagsRef.current.get(activeParaIdx) ?? []).includes(tag.id);
                        return (
                          <button
                            key={tag.id}
                            type="button"
                            className={`sp-insp-tagbtn tag-${tag.id}${isOn ? ' is-on' : ''}`}
                            title={isOn ? `Remove ${tag.label}` : `Apply ${tag.label}`}
                            onClick={() => tagByIdx(activeParaIdx, tag.id)}
                          >
                            {tag.icon} {tag.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ── Comment tab: per-paragraph comment textarea ── */}
            {inspectorTab === 'comment' && (
              activeParaIdx !== null && !isReadOnlyStage ? (
                <div className="sp-comment-panel">
                  <label className="sp-comment-label" htmlFor="sp-comment-input">
                    Comment on paragraph {activeParaIdx + 1}
                  </label>
                  <textarea
                    id="sp-comment-input"
                    className="sp-comment-input"
                    rows={5}
                    placeholder="Note for the pipeline (saved with stage)…"
                    value={commentsRef.current.get(activeParaIdx) ?? ''}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v.trim()) commentsRef.current.set(activeParaIdx, v);
                      else commentsRef.current.delete(activeParaIdx);
                      refreshComments();
                    }}
                    onBlur={(e) => persistComment(activeParaIdx, e.target.value.trim())}
                  />
                </div>
              ) : (
                <p className="sp-insp-hint">{isReadOnlyStage ? 'Read-only stage.' : 'Click a paragraph to add a comment.'}</p>
              )
            )}

            {/* ── AI tab: section-level Rewrite / Research / Auto-tag ── */}
            {inspectorTab === 'ai' && (
              <div className="sp-ai-panel">
                {activeSectionOrdinal !== null && !isReadOnlyStage && (
                  <div className="sp-ai-tab-actions" role="toolbar" aria-label="AI actions">
                    <button type="button" className="sp-ai-tab-btn" disabled={aiBusy}
                      onClick={() => runAi('rewrite')}>↺ Rewrite</button>
                    <button type="button" className="sp-ai-tab-btn" disabled={aiBusy}
                      onClick={() => runAi('research')}>🔍 Research</button>
                    <button type="button" className="sp-ai-tab-btn" disabled={aiBusy}
                      onClick={() => runAi('autotag')}>🏷 Auto-tag</button>
                  </div>
                )}
                {aiBusy && <p className="sp-ai-status">Working… ({aiKind})</p>}
                {aiError && <p className="sp-ai-status sp-ai-status--error">{aiError}</p>}
                {/* Rewrite option cards — each with an Apply button */}
                {aiOptions.length > 0 && (
                  <div className="sp-ai-options">
                    {aiOptions.map((opt, i) => (
                      <div key={i} className="sp-ai-option-card">
                        <span className="sp-ai-option-num">{i + 1}</span>
                        <p className="sp-ai-option-text">{opt}</p>
                        <button
                          type="button"
                          className="sp-ai-option-apply"
                          onClick={() => applySection(opt)}
                          disabled={activeSectionOrdinal === null}
                          title="Replace section body with this rewrite"
                        >
                          Apply →
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {/* Research / autotag plain-text result */}
                {aiResult && <div className="sp-ai-result">{aiResult}</div>}
                {!aiBusy && aiOptions.length === 0 && !aiResult && !aiError && (
                  <p className="sp-insp-hint">Click into a section, then use the buttons above — or click ↺ 🔍 🏷 in the toolbar that appears above the section heading.</p>
                )}
              </div>
            )}

            {/* ── References tab: inline markers by category ── */}
            {inspectorTab === 'refs' && (
              <div className="sp-insp-markers">
                {stage?.augMeta && (
                  <p className="sp-aug-meta" title="Extracted from the augmented stage knowledge block">
                    {stage.augMeta}
                  </p>
                )}
                <ul className="sp-legend" aria-label="Inline highlight key">
                  <li className="sp-legend-row"><span className="sp-legend-dot sp-legend-dot--quran" />Quran chips</li>
                  <li className="sp-legend-row"><span className="sp-legend-dot sp-legend-dot--hadith" />Hadith</li>
                  <li className="sp-legend-row"><span className="sp-legend-dot sp-legend-dot--work" />al-Ghazali works</li>
                </ul>
                {renderGroup('Quran', group('Quran'), 'quran')}
                {renderGroup('Hadith', group('Hadith'), 'hadith')}
                {renderGroup('Works', group('Work'), 'work')}
              </div>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
