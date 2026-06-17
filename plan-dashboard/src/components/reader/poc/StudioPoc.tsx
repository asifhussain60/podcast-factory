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

// ── Deferred AI action-item registry ────────────────────────────────────────
// Single source of truth for every action the human can stamp on a paragraph or
// a selected term (edit mode only). A later CLI pass drains the queued marks.
// Add a button HERE and it appears in the palette, the queue, and the inline
// badges; the API allow-list in /api/studio/action-items mirrors these kinds.
// `scope` decides where the action shows: 'term' needs a text selection,
// 'paragraph' acts on the active paragraph, 'both' appears in either palette.
type ActionScope = 'paragraph' | 'term' | 'both';
type ActionGroup = 'core' | 'transform' | 'knowledge';
interface ActionDef {
  kind: string;
  label: string;
  icon: string;   // Font Awesome solid class
  scope: ActionScope;
  group: ActionGroup;
  hint: string;   // tooltip — what the CLI will do with this mark
  // 'deferred' (default) = stamp a mark for the CLI drain pass; 'immediate' = run
  // AI now and apply in-place (e.g. Arabic term replacement), never queued.
  applyMode?: 'deferred' | 'immediate';
}
const ACTION_REGISTRY: readonly ActionDef[] = [
  // Core
  { kind: 'arabic',    label: 'Arabic',        icon: 'fa-language',                            scope: 'term',      group: 'core',      hint: 'Replace this term with the correct contextual Arabic (AI, confirm first)', applyMode: 'immediate' },
  { kind: 'replace',   label: 'Replace',       icon: 'fa-right-left',                          scope: 'term',      group: 'core',      hint: 'Find & replace this phrase across this chapter or the whole book', applyMode: 'immediate' },
  { kind: 'explain',   label: 'Explain',       icon: 'fa-lightbulb',                           scope: 'term',      group: 'core',      hint: 'Replace the selection with a clearer, fuller explanation (AI, in chapter context)', applyMode: 'immediate' },
  { kind: 'noise',     label: 'Noise',         icon: 'fa-eraser', scope: 'term', group: 'core', hint: 'Mark the selection as noise -> generalise to a pattern -> strip every match across this chapter or the whole book', applyMode: 'immediate' },
  { kind: 'etymology', label: 'Etymology',     icon: 'fa-book-bookmark',                       scope: 'term',      group: 'core',      hint: 'Resolve the root-history of this term (shared wisdom corpus)' },
  { kind: 'rewrite',   label: 'Rewrite',       icon: 'fa-arrows-rotate',                       scope: 'paragraph', group: 'core',      hint: 'Rewrite this paragraph' },
  { kind: 'rephrase',  label: 'Rephrase',      icon: 'fa-pen-nib',                             scope: 'paragraph', group: 'core',      hint: 'Rephrase while keeping the meaning' },
  { kind: 'improve',   label: 'Improve',       icon: 'fa-wand-magic-sparkles',                 scope: 'paragraph', group: 'core',      hint: 'Improve clarity and craft' },
  // Transform
  { kind: 'expand',    label: 'Expand',        icon: 'fa-up-right-and-down-left-from-center',  scope: 'paragraph', group: 'transform', hint: 'Elaborate — add depth or an example' },
  { kind: 'condense',  label: 'Condense',      icon: 'fa-compress',                            scope: 'paragraph', group: 'transform', hint: 'Tighten without losing meaning' },
  { kind: 'simplify',  label: 'Simplify',      icon: 'fa-feather',                             scope: 'paragraph', group: 'transform', hint: 'Plain-language version for a lay listener' },
  // Knowledge
  { kind: 'define',    label: 'Define',        icon: 'fa-spell-check',                         scope: 'term',      group: 'knowledge', hint: 'Short glossary gloss for this term' },
  { kind: 'xref',      label: 'Cross-ref',     icon: 'fa-link',                                scope: 'both',      group: 'knowledge', hint: 'Find related passages in this book or the corpus' },
  { kind: 'addcorpus', label: 'Add to corpus', icon: 'fa-database',                            scope: 'both',      group: 'knowledge', hint: 'Promote this passage or term into the wisdom knowledge base' },
  { kind: 'visualize', label: 'Visualization', icon: 'fa-diagram-project',                     scope: 'paragraph', group: 'knowledge', hint: 'Flag this passage for a visual diagram in the PDF reading edition' },
];
const ACTION_BY_KIND: Record<string, ActionDef> = Object.fromEntries(ACTION_REGISTRY.map((a) => [a.kind, a]));

// One action-item mark as held client-side (mirrors the action_items table row).
interface ClientActionItem {
  id: number;            // negative = optimistic (not yet persisted)
  scope: 'paragraph' | 'term';
  para_ordinal: number;
  term_text: string;     // '' for paragraph scope
  anchor_text: string;
  action_kind: string;
  status: string;
}

function truncate(s: string, n = 40): string {
  const t = s.trim();
  return t.length > n ? `${t.slice(0, n - 1)}…` : t;
}

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
  /** Which stages have an unapproved autosaved draft (mutated locally on approve). */
  drafted?: Record<string, boolean>;
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

// Section-level editorial tags — the content-classification vocabulary carried by
// the section depth picker on each h2 (distinct from the action-item registry above)
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
  // Does this chapter+stage have an unapproved draft on disk? (Seeded server-side;
  // the editor's current content already IS the draft when this is true.)
  const hasDraftForStage = !!(stage && (chap.drafted?.[stage.id] ?? false));

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

  // Draft autosave state: edits are persisted to a per-stage draft (debounced) so
  // they survive a refresh until the chapter is approved. 'saved' = a draft is on
  // disk (seeded true when the loaded content already came from a draft).
  const [draftState, setDraftState] = useState<'idle' | 'saving' | 'saved' | 'error'>(
    hasDraftForStage ? 'saved' : 'idle',
  );
  // Debounce timer + indirection ref for the autosave scheduler (the scheduler is
  // defined after useEditor; onUpdate reaches it through this ref). Mirrors the
  // runAiFnRef / removeActionFnRef pattern used elsewhere in this component.
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleAutosaveRef = useRef<() => void>(() => {});
  // Set true right before an intentional reload (discard) so the beforeunload
  // flush can't recreate the draft we just deleted.
  const suppressFlushRef = useRef(false);

  // Per-paragraph comments: index → text. Stored in a ref for the PM plugin,
  // mirrored in state so the inspector panel re-renders.
  const commentsRef = useRef<Map<number, string>>(new Map());
  const [, setCommentsKey] = useState(0);
  const refreshComments = () => setCommentsKey((k) => k + 1);

  // Deferred AI action-item marks for the active chapter (persisted in the
  // knowledge DB; the CLI drain pass reads them). Held in a ref so PM widgets
  // built outside React always see the latest, mirrored to state for re-render.
  const actionsRef = useRef<ClientActionItem[]>([]);
  const [, setActionsKey] = useState(0);
  const refreshActions = () => setActionsKey((k) => k + 1);

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

  // Load action-item marks when the chapter changes. Clear synchronously first so
  // the previous chapter's marks never flash on the new chapter.
  useEffect(() => {
    if (!slug || !chapter) return;
    let cancelled = false;
    actionsRef.current = [];
    refreshActions();
    fetch(`/api/studio/action-items?book=${encodeURIComponent(slug)}&chapter=${encodeURIComponent(chapter)}`)
      .then((r) => r.ok ? r.json() : null)
      .then((json) => {
        if (cancelled || !json?.ok || !Array.isArray(json.items)) return;
        actionsRef.current = json.items as ClientActionItem[];
        refreshActions();
        editorRef.current?.view.dispatch(editorRef.current.state.tr.setMeta('refreshTags', true));
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

  // "Arabic" immediate action — AI proposes a contextual Arabic term for the
  // highlighted text; the human confirms before it replaces the selection.
  // Positions are captured at propose-time and re-verified before applying.
  const [arabicProposal, setArabicProposal] = useState<
    { from: number; to: number; original: string; arabic: string; gloss: string; kind: string } | null
  >(null);
  const [arabicBusy, setArabicBusy] = useState(false);
  const [arabicError, setArabicError] = useState('');
  // Result line after an across-chapter / across-book Arabic replace.
  const [arabicDone, setArabicDone] = useState('');

  // "Explain" immediate action — AI rewrites the highlighted excerpt into a
  // clearer, fuller version (kept in chapter context); the human reviews/edits
  // the proposed text before it replaces the selection.
  const [explainProposal, setExplainProposal] = useState<
    { from: number; to: number; original: string; text: string } | null
  >(null);
  const [explainBusy, setExplainBusy] = useState(false);
  const [explainError, setExplainError] = useState('');

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
  const [arabicOn, setArabicOn] = useState(true);   // Arabic overlay ON by default (Islamic review default)
  const [, setTick] = useState(0);
  const refresh = () => setTick((t) => t + 1);

  const originalRef = useRef<string[]>([]);            // original text per top-level node
  const arabicRef = useRef(true);                      // mirror of arabicOn for the plugin (ON by default)
  const hasFocusRef = useRef(false);                   // tracks editor DOM focus for para-active
  const editorContainerRef = useRef<HTMLElement | null>(null);
  const inspectorRef = useRef<HTMLElement | null>(null);   // right inspector panel
  arabicRef.current = arabicOn;
  // Per-stage diff: when a read-only step is selected, the decoration plugin can diff each
  // paragraph against the PREVIOUS stage's text (prevStageTextsRef) instead of the human-edit
  // original — so "Show changes from {prev stage}" highlights what THAT step changed.
  const showPrevDiffRef = useRef(false);
  const prevStageTextsRef = useRef<string[]>([]);
  const [showPrevDiff, setShowPrevDiff] = useState(false);
  // Remove an action-item mark by id, called from the inline per-paragraph badge
  // toolbar (a PM widget built outside React). Held in a ref so the widget always
  // calls the latest closure.
  const removeActionFnRef = useRef<(id: number) => void>(() => {});
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
                  // Group action-item marks by paragraph ordinal for inline badges.
                  const actsByPara = new Map<number, ClientActionItem[]>();
                  for (const a of actionsRef.current) {
                    const arr = actsByPara.get(a.para_ordinal);
                    if (arr) arr.push(a); else actsByPara.set(a.para_ordinal, [a]);
                  }
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
                    const t = actsByPara.get(idx) || [];

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

                    // Action-item marks: inline badge row (icons, click to remove).
                    if (t.length) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: `para-marked act-${t[0].action_kind}` }));
                      decos.push(
                        Decoration.widget(offset + 1, () => {
                          const bar = document.createElement('div');
                          bar.contentEditable = 'false';
                          bar.className = 'sp-para-tools sp-para-tools--marks';
                          bar.setAttribute('role', 'toolbar');
                          bar.setAttribute('aria-label', 'Paragraph action marks');
                          for (const item of t) {
                            const def = ACTION_BY_KIND[item.action_kind];
                            if (!def) continue;
                            const b = document.createElement('button');
                            b.type = 'button';
                            b.className = `sp-ptool act-${item.action_kind} is-on`;
                            b.title = `${def.label}${item.term_text ? ` · "${item.term_text}"` : ''} (click to remove)`;
                            const ic = document.createElement('i');
                            ic.className = `fa-solid ${def.icon}`;
                            ic.setAttribute('aria-hidden', 'true');
                            b.appendChild(ic);
                            b.addEventListener('mousedown', (ev) => {
                              ev.preventDefault(); ev.stopPropagation();
                              removeActionFnRef.current(item.id);
                            });
                            bar.appendChild(b);
                          }
                          return bar;
                        }, { side: -1, key: `tools-${idx}-marks-${t.map((x) => x.id).join(',')}` }),
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

                    // Para-dirty: warm background on blocks the user has edited vs the original.
                    // Only shown in human-edit mode (not prev-stage diff) so it tracks real changes.
                    if (!prevDiff && orig[idx] !== undefined && orig[idx] !== after) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: 'para-dirty' }));
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

                    // Raw Arabic (typed straight into the prose, not a glossary
                    // token): colour every Arabic-LETTER run with the accent so it
                    // matches the glossary overlays — same naskh (from the editor
                    // font stack), same colour. Honorific / presentation-form glyphs
                    // (e.g. ﷺ, U+FDFA) fall outside these ranges, so they stay ink and
                    // read as prose rather than as terms.
                    node.descendants((child, childPos) => {
                      if (!child.isText || !child.text) return;
                      const base = offset + 1 + childPos;
                      const arRe = /[؀-ۿݐ-ݿࢠ-ࣿ](?:[؀-ۿݐ-ݿࢠ-ࣿ\s]*[؀-ۿݐ-ݿࢠ-ࣿ])?/g;
                      let am: RegExpExecArray | null;
                      while ((am = arRe.exec(child.text!))) {
                        const from = base + am.index;
                        const to = from + am[0].length;
                        decos.push(Decoration.inline(from, to, { class: 'ar-raw' }));
                      }
                    });
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
    onUpdate() { refresh(); scheduleAutosaveRef.current(); },
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

  // Switch the editor to the selected stage: load its text, re-snapshot redline
  // originals, and make only the under-review stage editable (upstream = read-only).
  // Action-item marks are chapter-level (not stage-level) — they reload on chapter
  // change and are intentionally NOT cleared here.
  useEffect(() => {
    if (!editor || !stage) return;
    if (viewAll) {
      editor.commands.setContent(buildCombinedHtml(stageId));
      originalRef.current = [];
      editor.setEditable(false);
    } else {
      editor.commands.setContent(stage.html);
      const texts: string[] = [];
      editor.state.doc.forEach((n) => texts.push(n.textContent));
      originalRef.current = texts;
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

  // ── Draft autosave — persist in-progress edits so they survive a refresh ────
  // Writes the editable stage's current content to a per-stage draft (not the
  // canonical chapter — that only happens on approve). Skipped for read-only
  // stages and archived lineages.
  const autosaveDraft = useCallback(async () => {
    if (!stage || isReadOnlyStage || !editor) return;
    const content = serializeToMarkdown();
    if (!content.trim()) return;
    setDraftState('saving');
    try {
      const res = await fetch('/api/studio/draft', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, chapter, stage: stage.id, content }),
      });
      setDraftState(res.ok ? 'saved' : 'error');
    } catch {
      setDraftState('error');
    }
  }, [slug, chapter, stage, isReadOnlyStage, editor, serializeToMarkdown]);

  // Debounced scheduler — onUpdate reaches this through scheduleAutosaveRef.
  const scheduleAutosave = useCallback(() => {
    if (isReadOnlyStage) return;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(() => { void autosaveDraft(); }, 1200);
  }, [autosaveDraft, isReadOnlyStage]);
  useEffect(() => { scheduleAutosaveRef.current = scheduleAutosave; }, [scheduleAutosave]);

  // Flush any pending draft when leaving the page/tab so nothing in the debounce
  // window is lost, and reset the indicator when switching chapter/stage.
  useEffect(() => {
    const flush = () => { if (suppressFlushRef.current) return; if (autosaveTimer.current) { clearTimeout(autosaveTimer.current); void autosaveDraft(); } };
    const onVisibility = () => { if (document.visibilityState === 'hidden') flush(); };
    window.addEventListener('beforeunload', flush);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('beforeunload', flush);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [autosaveDraft]);
  useEffect(() => {
    setDraftState(hasDraftForStage ? 'saved' : 'idle');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapIdx, stageId, activeLineageId]);

  const saveAndApprove = useCallback(async () => {
    if (!stage || !editor) return;
    // Cancel any pending autosave so it can't recreate the draft after approval
    // promotes-and-deletes it on the server.
    if (autosaveTimer.current) { clearTimeout(autosaveTimer.current); autosaveTimer.current = null; }
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
        // Draft was promoted to the chapter + deleted server-side; clear the
        // indicator and the locally-cached draft flag for this stage.
        setDraftState('idle');
        if (chap.drafted) chap.drafted[stage.id] = false;
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

  const discardChanges = useCallback(async () => {
    if (!editor || !stage) return;
    // Cancel pending autosave and suppress the unload-flush, delete the draft,
    // then reload so the canonical (last-approved) chapter text is shown. ?ch=
    // keeps the open chapter; reload also clears local edits not yet autosaved.
    if (autosaveTimer.current) { clearTimeout(autosaveTimer.current); autosaveTimer.current = null; }
    suppressFlushRef.current = true;
    try {
      await fetch('/api/studio/draft', {
        method: 'DELETE',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, chapter, stage: stage.id }),
      });
    } catch { /* reload regardless — server keeps the canonical on failure */ }
    const url = new URL(window.location.href);
    url.searchParams.set('ch', chapter);
    window.location.href = url.toString();
  }, [editor, stage, slug, chapter]);

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
  const markedCount = actionsRef.current.length;
  // "Approved" only counts while the stage is unchanged — any fresh edit reverts
  // the footer to "Save & Approve" so the new edit can be saved.
  // "Approved" holds only while the stage is unchanged AND has no outstanding
  // draft — any draft (even from a prior visit) reverts the footer to "Save &
  // Approve" so the in-progress edits can be committed.
  const approvedClean = !!(stage && approvedStages[stage.id]) && changedCount === 0 && draftState !== 'saved';
  // Chapter's marks, ordered for the queue list (by paragraph, then insertion).
  const chapterActions = [...actionsRef.current].sort((a, b) => a.para_ordinal - b.para_ordinal || a.id - b.id);

  // Remove one action-item mark (optimistic; DELETE only if it was persisted).
  const removeAction = useCallback((id: number) => {
    actionsRef.current = actionsRef.current.filter((a) => a.id !== id);
    editorRef.current?.view.dispatch(editorRef.current.state.tr.setMeta('refreshTags', true));
    refreshActions(); refresh();
    if (id < 0) return; // optimistic-only, never hit the server
    fetch('/api/studio/action-items', {
      method: 'DELETE', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ book: slug, chapter, id }),
    }).catch(() => { /* non-blocking */ });
  }, [slug, chapter]);

  // Stamp an action item on the active paragraph (or the selected term). Toggles:
  // an identical existing mark is removed. Anchor text is stored so the CLI never
  // depends on the paragraph ordinal staying stable.
  const stampAction = useCallback((def: ActionDef, useSelection: boolean) => {
    if (!editor || activeParaIdx === null || isReadOnlyStage) return;
    const scope: 'paragraph' | 'term' = useSelection ? 'term' : 'paragraph';
    const termText = useSelection ? selection.trim() : '';
    if (scope === 'term' && !termText) return;
    let paraText = '';
    let i = 0;
    editor.state.doc.forEach((n) => { if (i === activeParaIdx) paraText = n.textContent; i++; });
    const anchorText = scope === 'term' ? termText : paraText;
    const existing = actionsRef.current.find(
      (a) => a.para_ordinal === activeParaIdx && a.action_kind === def.kind && a.term_text === termText,
    );
    if (existing) { removeAction(existing.id); return; }
    const tempId = -Date.now();
    actionsRef.current = [
      ...actionsRef.current,
      { id: tempId, scope, para_ordinal: activeParaIdx, term_text: termText, anchor_text: anchorText, action_kind: def.kind, status: 'pending' },
    ];
    editor.view.dispatch(editor.state.tr.setMeta('refreshTags', true));
    refreshActions(); refresh();
    fetch('/api/studio/action-items', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ book: slug, chapter, scope, paraOrdinal: activeParaIdx, termText, anchorText, actionKind: def.kind }),
    })
      .then((r) => r.ok ? r.json() : null)
      .then((json) => {
        if (json?.ok && json.item) {
          actionsRef.current = actionsRef.current.map((a) => (a.id === tempId ? (json.item as ClientActionItem) : a));
          refreshActions();
        }
      })
      .catch(() => { /* non-blocking; optimistic mark stays visible */ });
  }, [editor, activeParaIdx, isReadOnlyStage, selection, slug, chapter, removeAction]);

  removeActionFnRef.current = removeAction;
  runAiFnRef.current = (kind: string) => void runAi(kind);

  // Paragraph text containing the current selection — context for the Arabic AI call.
  const selectionContext = useCallback((): string => {
    if (!editor) return '';
    const headPos = editor.state.selection.$head.pos;
    let ctx = '';
    let pos = 0;
    editor.state.doc.forEach((n) => {
      const nodeEnd = pos + n.nodeSize;
      if (headPos >= pos && headPos < nodeEnd) ctx = n.textContent;
      pos = nodeEnd;
    });
    return ctx;
  }, [editor]);

  // Propose an Arabic term for the highlighted selection (does NOT edit yet).
  const proposeArabic = useCallback(async () => {
    if (!editor || isReadOnlyStage) return;
    const { from, to } = editor.state.selection;
    const original = editor.state.doc.textBetween(from, to, ' ').trim();
    if (!original || from === to) return;
    setArabicBusy(true); setArabicError(''); setArabicProposal(null); setArabicDone('');
    try {
      const res = await fetch('/api/ai/arabic-term', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: original, context: selectionContext(), bookTitle: chapterTitle }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false || !json.arabic) {
        setArabicError(json.error ?? `Request failed (${res.status})`);
      } else {
        setArabicProposal({ from, to, original, arabic: json.arabic, gloss: json.gloss ?? '', kind: json.kind ?? 'translation' });
      }
    } catch (e) {
      setArabicError(String(e));
    } finally {
      setArabicBusy(false);
    }
  }, [editor, isReadOnlyStage, selectionContext, chapterTitle]);

  // Apply the confirmed proposal: replace the original range with the Arabic term,
  // but only if the text at those positions is unchanged since proposing.
  const applyArabic = useCallback(() => {
    if (!editor || !arabicProposal) return;
    const { from, to, original, arabic } = arabicProposal;
    const text = arabic.trim();
    if (!text) { setArabicError('Enter the Arabic text first.'); return; }
    const current = editor.state.doc.textBetween(from, to, ' ').trim();
    if (current !== original) {
      setArabicError('Selection changed — highlight the word again.');
      setArabicProposal(null);
      return;
    }
    editor.view.dispatch(editor.state.tr.replaceWith(from, to, editor.state.schema.text(text)));
    setArabicProposal(null); setArabicError('');
    refresh();
  }, [editor, arabicProposal]);

  const cancelArabic = useCallback(() => { setArabicProposal(null); setArabicError(''); setArabicDone(''); }, []);

  // Propose a clearer, fuller version of the highlighted excerpt (does NOT edit
  // yet). The whole chapter is sent as context so the AI stays inside it.
  const proposeExplain = useCallback(async () => {
    if (!editor || isReadOnlyStage) return;
    const { from, to } = editor.state.selection;
    const original = editor.state.doc.textBetween(from, to, ' ').trim();
    if (!original || from === to) return;
    let chapterText = '';
    editor.state.doc.forEach((n) => { chapterText += `${n.textContent}\n\n`; });
    setExplainBusy(true); setExplainError(''); setExplainProposal(null);
    try {
      const res = await fetch('/api/ai/explain', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: original, chapter: chapterText.trim(), bookTitle: chapterTitle }),
      });
      const json = await res.json();
      if (!res.ok || json.ok === false || !json.text) {
        setExplainError(json.error ?? `Request failed (${res.status})`);
      } else {
        setExplainProposal({ from, to, original, text: json.text });
      }
    } catch (e) {
      setExplainError(String(e));
    } finally {
      setExplainBusy(false);
    }
  }, [editor, isReadOnlyStage, chapterTitle]);

  // Apply the (edited) explanation: replace the original range, but only if the
  // text at those positions is unchanged since proposing.
  const applyExplain = useCallback(() => {
    if (!editor || !explainProposal) return;
    const { from, to, original, text } = explainProposal;
    const replacement = text.trim();
    if (!replacement) { setExplainError('The explanation is empty.'); return; }
    const current = editor.state.doc.textBetween(from, to, ' ').trim();
    if (current !== original) {
      setExplainError('Selection changed — highlight the passage again.');
      setExplainProposal(null);
      return;
    }
    editor.view.dispatch(editor.state.tr.replaceWith(from, to, editor.state.schema.text(replacement)));
    setExplainProposal(null); setExplainError('');
    refresh();
  }, [editor, explainProposal]);

  const cancelExplain = useCallback(() => { setExplainProposal(null); setExplainError(''); }, []);

  // ── Global find-and-replace ──────────────────────────────────────────────
  // Highlight a phrase → "Replace" opens this popup pre-filled with the
  // selection. Multiple find→replace pairs run in one pass; the scope checkbox
  // switches between this chapter and every chapter in the book. Preview counts
  // matches without writing; Apply rewrites the canonical chapter .txt files via
  // /api/studio/replace and mirrors the change into the live editor doc.
  const [replaceOpen, setReplaceOpen] = useState(false);
  const [replacePairs, setReplacePairs] = useState<{ find: string; replace: string }[]>([{ find: '', replace: '' }]);
  const [replaceScope, setReplaceScope] = useState<'chapter' | 'book'>('chapter');
  const [replacePreview, setReplacePreview] = useState<{ chapter: string; count: number }[] | null>(null);
  const [replaceTotal, setReplaceTotal] = useState(0);
  const [replaceBusy, setReplaceBusy] = useState(false);
  const [replaceError, setReplaceError] = useState('');
  const [replaceDone, setReplaceDone] = useState('');

  const openReplace = useCallback(() => {
    setReplacePairs([{ find: selection.trim(), replace: '' }]);
    setReplaceScope('chapter');
    setReplacePreview(null); setReplaceTotal(0); setReplaceError(''); setReplaceDone('');
    setReplaceOpen(true);
  }, [selection]);
  const closeReplace = useCallback(() => setReplaceOpen(false), []);
  const updatePair = (i: number, field: 'find' | 'replace', val: string) =>
    setReplacePairs((ps) => ps.map((p, j) => (j === i ? { ...p, [field]: val } : p)));
  const addPair = () => setReplacePairs((ps) => [...ps, { find: '', replace: '' }]);
  const removePair = (i: number) => setReplacePairs((ps) => (ps.length > 1 ? ps.filter((_, j) => j !== i) : ps));

  // Friendly "N. Title" label for a chapter id (falls back to the raw id).
  const chapterLabel = useCallback((id: string): string => {
    const idx = chapters.findIndex((c) => c.slug === id);
    return idx >= 0 ? `${idx + 1}. ${chapters[idx].title}` : id;
  }, [chapters]);

  // Mirror the confirmed replacements into the live editor doc so the current
  // chapter updates instantly. Pairs apply in order (a later pair sees earlier
  // results), matching the server. Each pair is swept high→low so positions
  // stay valid as text is replaced.
  const replaceInEditorDoc = useCallback((pairs: { find: string; replace: string }[]) => {
    if (!editor) return;
    for (const { find, replace } of pairs) {
      if (!find) continue;
      const hits: { from: number; to: number }[] = [];
      editor.state.doc.descendants((node, pos) => {
        if (!node.isText || !node.text) return;
        let idx = node.text.indexOf(find);
        while (idx !== -1) {
          const from = pos + idx;
          hits.push({ from, to: from + find.length });
          idx = node.text.indexOf(find, idx + find.length);
        }
      });
      if (!hits.length) continue;
      hits.sort((a, b) => b.from - a.from);
      let tr = editor.state.tr;
      for (const h of hits) {
        tr = replace ? tr.replaceWith(h.from, h.to, editor.state.schema.text(replace)) : tr.delete(h.from, h.to);
      }
      editor.view.dispatch(tr);
    }
  }, [editor]);

  // Replace EVERY occurrence of the original term with the (edited) Arabic — across
  // this chapter or the whole book — via the same canonical-file replace endpoint
  // used by find-and-replace, then mirror the change into the live editor doc.
  const applyArabicAcross = useCallback(async (scope: 'chapter' | 'book') => {
    if (!editor || !arabicProposal) return;
    const replace = arabicProposal.arabic.trim();
    if (!replace) { setArabicError('Enter the Arabic text first.'); return; }
    const find = arabicProposal.original;
    setArabicBusy(true); setArabicError('');
    try {
      const res = await fetch('/api/studio/replace', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, scope, chapter, pairs: [{ find, replace }], apply: true }),
      });
      const j = await res.json();
      if (!res.ok || j.ok === false) { setArabicError(j.error ?? `Request failed (${res.status})`); return; }
      if (!isReadOnlyStage) replaceInEditorDoc([{ find, replace }]);
      const nCh = (j.results ?? []).length;
      const total = j.total ?? 0;
      setArabicDone(
        total === 0
          ? 'No matches found — nothing changed.'
          : `Replaced ${total} instance${total === 1 ? '' : 's'} across ${nCh} chapter${nCh === 1 ? '' : 's'}.`,
      );
      refresh();
    } catch (e) {
      setArabicError(String(e));
    } finally {
      setArabicBusy(false);
    }
  }, [editor, arabicProposal, slug, chapter, isReadOnlyStage, replaceInEditorDoc]);

  const runReplace = useCallback(async (apply: boolean) => {
    const pairs = replacePairs
      .map((p) => ({ find: p.find, replace: p.replace }))
      .filter((p) => p.find.trim() !== '');
    if (pairs.length === 0) { setReplaceError('Enter at least one phrase to find.'); return; }
    setReplaceBusy(true); setReplaceError(''); setReplaceDone('');
    try {
      const res = await fetch('/api/studio/replace', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, scope: replaceScope, chapter, pairs, apply }),
      });
      const j = await res.json();
      if (!res.ok || j.ok === false) {
        setReplaceError(j.error ?? `Request failed (${res.status})`);
        return;
      }
      setReplacePreview(j.results ?? []); setReplaceTotal(j.total ?? 0);
      if (apply) {
        if (!isReadOnlyStage) replaceInEditorDoc(pairs);
        const nCh = (j.results ?? []).length;
        setReplaceDone(
          j.total === 0
            ? 'No matches found — nothing changed.'
            : `Replaced ${j.total} instance${j.total === 1 ? '' : 's'} across ${nCh} chapter${nCh === 1 ? '' : 's'}.` +
              (replaceScope === 'book' && nCh > 1 ? ' Other chapters update when you open them.' : ''),
        );
        refresh();
      }
    } catch (e) {
      setReplaceError(String(e));
    } finally {
      setReplaceBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, replaceScope, chapter, replacePairs, isReadOnlyStage, replaceInEditorDoc]);

  // ── Noise → pattern → denoise across chapters ────────────────────────────
  // Highlight a recurring artifact (a page header, an OCR scar, a stray marker)
  // → "Noise" opens this popup with a PATTERN generalised from the selection
  // (literal text, but digit-runs and whitespace loosened so one selection
  // catches its variants). Preview shows the count + a few real samples per
  // chapter before anything changes; Apply strips every match from the canonical
  // chapter .txt files via /api/studio/denoise (with .bak undo) and mirrors the
  // deletion into the live editor doc.
  const [noiseOpen, setNoiseOpen] = useState(false);
  const [noisePattern, setNoisePattern] = useState('');
  const [noiseScope, setNoiseScope] = useState<'chapter' | 'book'>('chapter');
  const [noisePreview, setNoisePreview] = useState<{ chapter: string; count: number; samples: string[] }[] | null>(null);
  const [noiseTotal, setNoiseTotal] = useState(0);
  const [noiseBusy, setNoiseBusy] = useState(false);
  const [noiseError, setNoiseError] = useState('');
  const [noiseDone, setNoiseDone] = useState('');

  // Rule-based generalisation: escape regex specials, then loosen runs of digits
  // (\d+) and whitespace (\s+) so "[Page 12]" and "[Page 137]" collapse to one
  // pattern. The user can hand-edit the result before previewing.
  const deriveNoisePattern = useCallback((sel: string): string => {
    const escaped = sel.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return escaped.replace(/\d+/g, '\\d+').replace(/\s+/g, '\\s+');
  }, []);

  const openNoise = useCallback(() => {
    setNoisePattern(deriveNoisePattern(selection));
    setNoiseScope('chapter');
    setNoisePreview(null); setNoiseTotal(0); setNoiseError(''); setNoiseDone('');
    setNoiseOpen(true);
  }, [selection, deriveNoisePattern]);
  const closeNoise = useCallback(() => setNoiseOpen(false), []);

  // Mirror the confirmed pattern deletion into the live editor doc so the current
  // chapter updates instantly. Swept high→low so positions stay valid.
  const denoiseInEditorDoc = useCallback((pattern: string) => {
    if (!editor) return;
    let re: RegExp;
    try { re = new RegExp(pattern, 'g'); } catch { return; }
    const hits: { from: number; to: number }[] = [];
    editor.state.doc.descendants((node, pos) => {
      if (!node.isText || !node.text) return;
      re.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = re.exec(node.text))) {
        if (m[0] === '') { re.lastIndex += 1; continue; }
        const from = pos + m.index;
        hits.push({ from, to: from + m[0].length });
      }
    });
    if (!hits.length) return;
    hits.sort((a, b) => b.from - a.from);
    let tr = editor.state.tr;
    for (const h of hits) tr = tr.delete(h.from, h.to);
    editor.view.dispatch(tr);
  }, [editor]);

  const runDenoise = useCallback(async (apply: boolean) => {
    const pattern = noisePattern.trim();
    if (pattern === '') { setNoiseError('Enter a pattern to strip.'); return; }
    setNoiseBusy(true); setNoiseError(''); setNoiseDone('');
    try {
      const res = await fetch('/api/studio/denoise', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, scope: noiseScope, chapter, pattern, apply }),
      });
      const j = await res.json();
      if (!res.ok || j.ok === false) { setNoiseError(j.error ?? `Request failed (${res.status})`); return; }
      setNoisePreview(j.results ?? []); setNoiseTotal(j.total ?? 0);
      if (apply) {
        if (!isReadOnlyStage) denoiseInEditorDoc(pattern);
        const nCh = (j.results ?? []).length;
        setNoiseDone(
          j.total === 0
            ? 'No matches found — nothing changed.'
            : `Stripped ${j.total} match${j.total === 1 ? '' : 'es'} across ${nCh} chapter${nCh === 1 ? '' : 's'}.` +
              (noiseScope === 'book' && nCh > 1 ? ' Other chapters update when you open them.' : ''),
        );
        refresh();
      }
    } catch (e) {
      setNoiseError(String(e));
    } finally {
      setNoiseBusy(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, noiseScope, chapter, noisePattern, isReadOnlyStage, denoiseInEditorDoc]);

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
  return (
    <div className="studio-poc">
      {/* Two columns: the editor and the contextual inspector. The left pipeline
          rail was removed (redundant nav — pipeline phases live in the breadcrumb
          and book-page tabs); the editor column widened and the reading-edition
          link moved into the editor head below. */}
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
          <a
            className="sp-book-link"
            href={`/studio/${slug}/book`}
            title="Open the companion reading edition (the book)"
          >
            <span className="sp-book-glyph" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5z" />
                <path d="M4 19.5A1.5 1.5 0 0 1 5.5 18H20v3H5.5A1.5 1.5 0 0 1 4 19.5z" />
              </svg>
            </span>
            Reading edition
          </a>
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
        {/* View controls — Arabic overlay toggle + link to the phonetic map. */}
        {glossaryCount > 0 && (
          <div className="sp-global-strip">
            <button
              type="button"
              role="switch"
              aria-checked={arabicOn}
              aria-label={`Toggle Arabic script — currently ${arabicOn ? 'on' : 'off'}`}
              className={`sp-arabic-btn${arabicOn ? ' is-on' : ''}`}
              onClick={toggleArabic}
              title={arabicOn ? 'Hide Arabic script in the chapter' : 'Show Arabic script in the chapter'}
            >
              <i className={`fa-solid ${arabicOn ? 'fa-toggle-on' : 'fa-toggle-off'}`} aria-hidden="true" />
              <span className="sp-arabic-label">Toggle Arabic</span>
            </button>
            <a
              className="sp-phonetic-map"
              href={`/studio/${slug}/arabic-review#${chapter}`}
              title="Open the phonetic map (full Arabic review) for this chapter"
            >
              <i className="fa-solid fa-language" aria-hidden="true" /> Phonetic Map
            </a>
          </div>
        )}

        {/* M-1 — Tabbed panel: Details · Comment · AI · References */}
        <div className="sp-panel-card">
          <div className="sp-tab-bar" role="tablist" aria-label="Inspector tabs">
            {(['details', 'ai', 'refs', 'comment'] as const).map((tab) => {
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
                    <dd>{changedCount} edited · {markedCount} marked</dd>
                    <dt>Comments</dt>
                    <dd>{commentsRef.current.size > 0 ? `${commentsRef.current.size} paragraph${commentsRef.current.size !== 1 ? 's' : ''}` : '—'}</dd>
                  </dl>
                )}
                {/* Action items — deferred marks for the CLI drain pass (edit mode only). */}
                {!isReadOnlyStage && (
                  <div className="sp-actions-block">
                    {/* One control panel — every action stays visible; buttons that
                        cannot run in the current context are disabled, never hidden. */}
                    <p className="sp-insp-hint">
                      Actions · {selection.trim()
                        ? `"${truncate(selection, 32)}"`
                        : activeParaIdx !== null
                          ? `paragraph ${activeParaIdx + 1}`
                          : 'click a paragraph or select a word'}
                    </p>
                    <div className="sp-action-palette" role="toolbar" aria-label="Editor actions">
                      {ACTION_REGISTRY.map((def) => {
                        const sel = selection.trim();
                        const hasSel = !!sel;
                        const hasPara = activeParaIdx !== null;
                        // A 'both'-scope action targets the highlighted word when one
                        // exists, otherwise the active paragraph.
                        const onTerm = def.scope === 'term' || (def.scope === 'both' && hasSel);
                        const enabled = def.scope === 'term' ? hasSel : def.scope === 'paragraph' ? hasPara : (hasSel || hasPara);
                        const busy = (def.kind === 'arabic' && arabicBusy) || (def.kind === 'explain' && explainBusy);
                        const isOn = def.applyMode === 'immediate'
                          ? false
                          : actionsRef.current.some((a) => a.para_ordinal === activeParaIdx && a.action_kind === def.kind && a.term_text === (onTerm ? sel : ''));
                        return (
                          <button key={def.kind} type="button"
                            className={`sp-action-btn act-${def.kind}${isOn ? ' is-on' : ''}`}
                            title={enabled ? def.hint : (def.scope === 'term' ? 'Select a word to enable' : 'Click a paragraph to enable')}
                            disabled={!enabled || busy}
                            aria-pressed={def.applyMode === 'immediate' ? undefined : isOn}
                            onClick={() => {
                              if (def.applyMode === 'immediate') {
                                if (def.kind === 'arabic') void proposeArabic();
                                else if (def.kind === 'explain') void proposeExplain();
                                else if (def.kind === 'replace') openReplace();
                                else if (def.kind === 'noise') openNoise();
                              } else {
                                stampAction(def, onTerm);
                              }
                            }}>
                            <i className={`fa-solid ${def.icon}`} aria-hidden="true" /> <span className="sp-action-label">{def.label}</span>
                          </button>
                        );
                      })}
                    </div>
                        {explainBusy && <p className="sp-ai-status">Writing a clearer explanation…</p>}
                        {explainError && <p className="sp-ai-status sp-ai-status--error">{explainError}</p>}
                        {explainProposal && (
                          <div className="sp-explain-confirm">
                            <p className="sp-explain-confirm__label">Clearer explanation — edit before replacing:</p>
                            <textarea
                              className="sp-explain-confirm__text"
                              value={explainProposal.text}
                              rows={6}
                              onChange={(e) => setExplainProposal({ ...explainProposal, text: e.target.value })}
                              aria-label="Explanation — edit before replacing"
                            />
                            <div className="sp-arabic-confirm__actions">
                              <button type="button" className="sp-arabic-confirm__apply" onClick={applyExplain} disabled={!explainProposal.text.trim()}>
                                <i className="fa-solid fa-check" aria-hidden="true" /> Replace
                              </button>
                              <button type="button" className="sp-arabic-confirm__cancel" onClick={cancelExplain}>Cancel</button>
                            </div>
                          </div>
                        )}
                        {arabicBusy && <p className="sp-ai-status">Finding the Arabic term…</p>}
                        {arabicError && <p className="sp-ai-status sp-ai-status--error">{arabicError}</p>}
                        {arabicProposal && (
                          <div className="sp-arabic-confirm">
                            <p className="sp-arabic-confirm__row">
                              <span className="sp-arabic-confirm__en">{truncate(arabicProposal.original, 28)}</span>
                              <i className="fa-solid fa-arrow-right-long" aria-hidden="true" />
                            </p>
                            <input
                              type="text"
                              className="sp-arabic-confirm__input"
                              lang="ar"
                              dir="rtl"
                              value={arabicProposal.arabic}
                              onChange={(e) => setArabicProposal({ ...arabicProposal, arabic: e.target.value })}
                              aria-label="Arabic term — edit before replacing"
                            />
                            {arabicProposal.gloss && <p className="sp-arabic-confirm__gloss">{arabicProposal.gloss}</p>}
                            {arabicDone ? (
                              <>
                                <p className="sp-arabic-confirm__doneline">
                                  <i className="fa-solid fa-circle-check" aria-hidden="true" /> {arabicDone}
                                </p>
                                <div className="sp-arabic-confirm__actions">
                                  <button type="button" className="sp-arabic-confirm__cancel" onClick={cancelArabic}>Close</button>
                                </div>
                              </>
                            ) : (
                              <>
                                <p className="sp-arabic-confirm__scopehint">Replace where?</p>
                                <div className="sp-arabic-scope">
                                  <button type="button" className="sp-arabic-scope__btn sp-arabic-scope__btn--primary"
                                    disabled={!arabicProposal.arabic.trim() || arabicBusy} onClick={applyArabic}>
                                    <i className="fa-solid fa-check" aria-hidden="true" /> This instance
                                  </button>
                                  <button type="button" className="sp-arabic-scope__btn"
                                    disabled={!arabicProposal.arabic.trim() || arabicBusy} onClick={() => void applyArabicAcross('chapter')}>
                                    <i className="fa-solid fa-file-lines" aria-hidden="true" /> This chapter
                                  </button>
                                  <button type="button" className="sp-arabic-scope__btn"
                                    disabled={!arabicProposal.arabic.trim() || arabicBusy} onClick={() => void applyArabicAcross('book')}>
                                    <i className="fa-solid fa-book" aria-hidden="true" /> All chapters
                                  </button>
                                </div>
                                <div className="sp-arabic-confirm__actions">
                                  <button type="button" className="sp-arabic-confirm__cancel" onClick={cancelArabic}>
                                    {arabicBusy ? 'Replacing…' : 'Cancel'}
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        )}

                    {chapterActions.length > 0 && (
                      <div className="sp-action-queue">
                        <p className="sp-insp-hint">Queued for the pipeline · {chapterActions.length}</p>
                        <ul className="sp-action-queue-list">
                          {chapterActions.map((item) => {
                            const def = ACTION_BY_KIND[item.action_kind];
                            return (
                              <li key={item.id} className={`sp-aq-item act-${item.action_kind}`}>
                                <i className={`fa-solid ${def?.icon ?? 'fa-circle'}`} aria-hidden="true" />
                                <span className="sp-aq-label">{def?.label ?? item.action_kind}</span>
                                <span className="sp-aq-target">{item.term_text ? `"${truncate(item.term_text, 24)}"` : `¶ ${item.para_ordinal + 1}`}</span>
                                <button type="button" className="sp-aq-remove" title="Remove this mark"
                                  aria-label={`Remove ${def?.label ?? item.action_kind} mark`} onClick={() => removeAction(item.id)}>
                                  <i className="fa-solid fa-xmark" aria-hidden="true" />
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
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
                      onClick={() => runAi('rewrite')}><i className="fa-solid fa-arrows-rotate" aria-hidden="true" /> Rewrite</button>
                    <button type="button" className="sp-ai-tab-btn" disabled={aiBusy}
                      onClick={() => runAi('research')}><i className="fa-solid fa-magnifying-glass" aria-hidden="true" /> Research</button>
                    <button type="button" className="sp-ai-tab-btn" disabled={aiBusy}
                      onClick={() => runAi('autotag')}><i className="fa-solid fa-tag" aria-hidden="true" /> Auto-tag</button>
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

        {saveError && <p className="sp-save-error" role="alert">{saveError}</p>}
        {!viewAll && !isReadOnlyStage && stage && draftState !== 'idle' && (
          <p className={`sp-draft-status sp-draft-status--${draftState}`} role="status">
            {draftState === 'saving'
              ? <><i className="fa-solid fa-cloud-arrow-up" aria-hidden="true" /> Saving draft…</>
              : draftState === 'error'
              ? <><i className="fa-solid fa-triangle-exclamation" aria-hidden="true" /> Draft not saved — check connection</>
              : <><i className="fa-solid fa-pen" aria-hidden="true" /> Draft saved · not yet approved</>}
          </p>
        )}
        {!viewAll && !isReadOnlyStage && stage && (
          <div className="sp-action-footer">
            {(changedCount > 0 || draftState === 'saved') && (
              <button
                type="button"
                className="sp-discard"
                onClick={discardChanges}
                disabled={saving}
                title="Discard the draft and revert to the approved chapter"
              >
                <i className="fa-solid fa-rotate-left" aria-hidden="true" /> Discard
              </button>
            )}
            <button
              type="button"
              className={`sp-approve${approvedClean ? ' is-done' : ''}`}
              onClick={saveAndApprove}
              disabled={saving || approvedClean}
            >
              {approvedClean
                ? `✓ ${stage.label} approved`
                : saving ? 'Saving…'
                : 'Save & Approve'}
            </button>
          </div>
        )}
      </aside>

      {/* ── Global find-and-replace popup ── */}
      {replaceOpen && (
        <div className="sp-replace-backdrop" role="dialog" aria-modal="true" aria-label="Find and replace">
          <div className="sp-replace-modal">
            <header className="sp-replace-head">
              <h3 className="sp-replace-title"><i className="fa-solid fa-right-left" aria-hidden="true" /> Find &amp; replace</h3>
              <button type="button" className="sp-replace-close" onClick={closeReplace} aria-label="Close">
                <i className="fa-solid fa-xmark" aria-hidden="true" />
              </button>
            </header>

            <div className="sp-replace-body">
              {replacePairs.map((p, i) => (
                <div key={i} className="sp-replace-row">
                  <input className="sp-replace-input" placeholder="Find…" value={p.find}
                    aria-label={`Find phrase ${i + 1}`}
                    onChange={(e) => { updatePair(i, 'find', e.target.value); setReplacePreview(null); setReplaceDone(''); }} />
                  <i className="fa-solid fa-arrow-right-long sp-replace-arrow" aria-hidden="true" />
                  <input className="sp-replace-input" placeholder="Replace with…" value={p.replace}
                    aria-label={`Replacement ${i + 1}`}
                    onChange={(e) => { updatePair(i, 'replace', e.target.value); setReplacePreview(null); setReplaceDone(''); }} />
                  <button type="button" className="sp-replace-row-rm" onClick={() => removePair(i)}
                    disabled={replacePairs.length === 1} aria-label={`Remove replacement ${i + 1}`}>
                    <i className="fa-solid fa-xmark" aria-hidden="true" />
                  </button>
                </div>
              ))}

              <button type="button" className="sp-replace-add" onClick={addPair}>
                <i className="fa-solid fa-plus" aria-hidden="true" /> Add another replacement
              </button>

              <label className="sp-replace-scope">
                <input type="checkbox" checked={replaceScope === 'book'}
                  onChange={(e) => { setReplaceScope(e.target.checked ? 'book' : 'chapter'); setReplacePreview(null); setReplaceDone(''); }} />
                <span>Apply to <strong>all chapters</strong> in this book {replaceScope === 'book' ? '' : '(otherwise this chapter only)'}</span>
              </label>

              {replaceError && <p className="sp-replace-msg sp-replace-msg--error">{replaceError}</p>}
              {replaceDone && <p className="sp-replace-msg sp-replace-msg--ok">{replaceDone}</p>}

              {replacePreview && !replaceDone && (
                <div className="sp-replace-preview">
                  <p className="sp-replace-preview-total">
                    {replaceTotal} match{replaceTotal === 1 ? '' : 'es'}
                    {replacePreview.length > 0 ? ` across ${replacePreview.length} chapter${replacePreview.length === 1 ? '' : 's'}` : ''}
                  </p>
                  {replacePreview.length > 0 && (
                    <ul className="sp-replace-preview-list">
                      {replacePreview.map((r) => (
                        <li key={r.chapter}><span>{chapterLabel(r.chapter)}</span><span className="sp-replace-preview-n">{r.count}</span></li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            <footer className="sp-replace-foot">
              <button type="button" className="sp-replace-btn sp-replace-btn--ghost" onClick={() => void runReplace(false)} disabled={replaceBusy}>
                {replaceBusy ? 'Working…' : 'Preview'}
              </button>
              <button type="button" className="sp-replace-btn sp-replace-btn--apply"
                onClick={() => void runReplace(true)}
                disabled={replaceBusy || (replacePreview !== null && replaceTotal === 0)}>
                {replacePreview && !replaceDone ? `Replace ${replaceTotal}` : 'Replace'}
              </button>
            </footer>
          </div>
        </div>
      )}

      {noiseOpen && (
        <div className="sp-replace-backdrop" role="dialog" aria-modal="true" aria-label="Mark as noise">
          <div className="sp-replace-modal">
            <header className="sp-replace-head">
              <h3 className="sp-replace-title"><i className="fa-solid fa-eraser" aria-hidden="true" /> Mark as noise</h3>
              <button type="button" className="sp-replace-close" onClick={closeNoise} aria-label="Close">
                <i className="fa-solid fa-xmark" aria-hidden="true" />
              </button>
            </header>

            <div className="sp-replace-body">
              <p className="sp-noise-hint">
                The selection is generalised to a <strong>pattern</strong> (digits and spacing
                loosened so variants match). Edit it if needed, <strong>preview</strong> what
                it catches, then strip every match. Removed text is backed up per file.
              </p>
              <input className="sp-replace-input sp-noise-pattern" value={noisePattern}
                aria-label="Noise pattern (regular expression)" spellCheck={false}
                onChange={(e) => { setNoisePattern(e.target.value); setNoisePreview(null); setNoiseDone(''); }} />

              <label className="sp-replace-scope">
                <input type="checkbox" checked={noiseScope === 'book'}
                  onChange={(e) => { setNoiseScope(e.target.checked ? 'book' : 'chapter'); setNoisePreview(null); setNoiseDone(''); }} />
                <span>Strip from <strong>all chapters</strong> in this book {noiseScope === 'book' ? '' : '(otherwise this chapter only)'}</span>
              </label>

              {noiseError && <p className="sp-replace-msg sp-replace-msg--error">{noiseError}</p>}
              {noiseDone && <p className="sp-replace-msg sp-replace-msg--ok">{noiseDone}</p>}

              {noisePreview && !noiseDone && (
                <div className="sp-replace-preview">
                  <p className="sp-replace-preview-total">
                    {noiseTotal} match{noiseTotal === 1 ? '' : 'es'}
                    {noisePreview.length > 0 ? ` across ${noisePreview.length} chapter${noisePreview.length === 1 ? '' : 's'}` : ' — nothing to strip'}
                  </p>
                  {noisePreview.length > 0 && (
                    <ul className="sp-replace-preview-list">
                      {noisePreview.map((r) => (
                        <li key={r.chapter}>
                          <span>{chapterLabel(r.chapter)}</span>
                          <span className="sp-replace-preview-n">{r.count}</span>
                          {r.samples?.length > 0 && (
                            <span className="sp-noise-samples">
                              {r.samples.map((s, k) => <code key={k} className="sp-noise-sample">{s}</code>)}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            <footer className="sp-replace-foot">
              <button type="button" className="sp-replace-btn sp-replace-btn--ghost" onClick={() => void runDenoise(false)} disabled={noiseBusy}>
                {noiseBusy ? 'Working…' : 'Preview'}
              </button>
              <button type="button" className="sp-replace-btn sp-replace-btn--apply"
                onClick={() => void runDenoise(true)}
                disabled={noiseBusy || noisePreview === null || noiseTotal === 0}>
                {noisePreview && !noiseDone ? `Strip ${noiseTotal}` : 'Strip noise'}
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}
