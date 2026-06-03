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
}

interface Props {
  slug: string;
  chapters: Chapter[];
  glossary?: GlossaryEntry[];
  initialChapIdx?: number;
}

export default function StudioPoc({ slug, chapters, glossary = [], initialChapIdx = 0 }: Props) {
  // B: chapter switcher — pick which chapter's stages the editor shows.
  const [chapIdx, setChapIdx] = useState(initialChapIdx);
  const chap = chapters[chapIdx] ?? chapters[0];
  const stages = chap.stages;
  const metrics = chap.metrics;
  const chapter = chap.slug;
  const chapterTitle = chap.title;

  // Stage tabs (SN-5): the last AVAILABLE stage is the one under review (editable); upstream
  // stages are read-only comparison views. Tabs for not-yet-produced stages render disabled.
  const editableStageId = [...stages].reverse().find((s) => s.available)?.id ?? stages[0]?.id;
  const [stageId, setStageId] = useState<string>(editableStageId);
  const stage = stages.find((s) => s.id === stageId) ?? stages[0];
  const html = stage?.html ?? '';
  const isReadOnlyStage = stageId !== editableStageId;

  // WC8 write-back loop: which stages are approved (seeded from disk, updated on approve).
  const [approvedStages, setApprovedStages] = useState<Record<string, boolean>>(
    () => Object.fromEntries(Object.entries(chap.reviewed).map(([k, v]) => [k, !!v?.approved])),
  );
  // On chapter switch: reset to that chapter's editable stage + reload its approvals, and tell
  // the editorial cockpit (Slice 5b) to follow this chapter.
  useEffect(() => {
    setStageId([...chap.stages].reverse().find((s) => s.available)?.id ?? chap.stages[0]?.id);
    setApprovedStages(Object.fromEntries(Object.entries(chap.reviewed).map(([k, v]) => [k, !!v?.approved])));
    window.dispatchEvent(new CustomEvent('studio:chapter-change', { detail: { chapter: chap.slug } }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapIdx]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  // Per-paragraph comments: index → text. Stored in a ref for the PM plugin,
  // mirrored in state so the inspector panel re-renders.
  const commentsRef = useRef<Map<number, string>>(new Map());
  const [, setCommentsKey] = useState(0);
  const refreshComments = () => setCommentsKey((k) => k + 1);

  // Active paragraph index (inspector drives the comment textarea).
  const [activeParaIdx, setActiveParaIdx] = useState<number | null>(null);

  // M-1 — Inspector tab state (Details · Comment · AI · References).
  const [inspectorTab, setInspectorTab] = useState<'details' | 'comment' | 'ai' | 'refs'>('details');

  // Wave L-8 — AI assist panel + Finalize state.
  const [aiBusy, setAiBusy] = useState(false);
  const [aiKind, setAiKind] = useState('');
  const [aiResult, setAiResult] = useState('');
  const [aiError, setAiError] = useState('');
  const [finalizeMsg, setFinalizeMsg] = useState('');

  // serializeToMarkdown / saveAndApprove / discardChanges declared after useEditor (below).

  // "View all chapters" mode — combines every chapter's current-tab content in the editor.
  // Dropdown is disabled; editor is read-only; Save/Approve hidden.
  const [viewAll, setViewAll] = useState(false);

  const buildCombinedHtml = useCallback(
    (sid: string) =>
      chapters
        .map((ch, i) => {
          const s =
            ch.stages.find((st) => st.id === sid && st.available) ??
            ch.stages.filter((st) => st.available).at(-1);
          const body = s?.html ?? '<p><em>Stage not yet produced for this chapter.</em></p>';
          const sep = i < chapters.length - 1 ? '<hr>' : '';
          return `<h2>${ch.title}</h2>${body}${sep}`;
        })
        .join(''),
    [chapters],
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
  arabicRef.current = arabicOn;
  // Aug-diff mode: compare Augmented text against Normalized to show what the pipeline added.
  const showAugDiffRef = useRef(false);
  const normTextsRef = useRef<string[]>([]);
  const [showAugDiff, setShowAugDiff] = useState(false);
  // Index-based tag toggle, called from the floating per-paragraph icon toolbar (a PM widget
  // built outside React). Held in a ref so the widget always calls the latest closure.
  const tagFnRef = useRef<(idx: number, tagId: string) => void>(() => {});
  // M-1 — AI action ref: called from the per-paragraph floating toolbar's AI buttons.
  // Accepts an optional paraIdx so the toolbar can pass the hovered paragraph directly.
  const runAiFnRef = useRef<(kind: string, paraIdx?: number) => void>(() => {});

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

                  // Active paragraph (FC-3): only highlight when editor has DOM focus.
                  const headPos = state.selection.$head;
                  const activeTop = hasFocusRef.current && headPos.depth >= 1 ? headPos.before(1) : -1;

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

                  let i = 0;
                  state.doc.forEach((node, offset) => {
                    const idx = i++;
                    const isActive = offset === activeTop;
                    const t = tags.get(idx) || [];

                    if (isActive) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: 'para-active' }));
                    }
                    if (t.length) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: `para-tagged tag-${t[0]}` }));
                    }

                    // Floating icon toolbar at the paragraph's top-left:
                    //  - active paragraph -> AI-action palette (M-1: Rewrite/Research/Auto-tag)
                    //  - tagged but not active -> persistent marks (assigned icons only)
                    if (isActive || t.length) {
                      const palette = isActive;
                      decos.push(
                        Decoration.widget(offset + 1, () => {
                          const bar = document.createElement('div');
                          bar.contentEditable = 'false';
                          if (palette) {
                            // M-1: AI actions only (tags move to inspector Details tab).
                            bar.className = 'sp-para-tools sp-para-tools--palette sp-para-tools--ai';
                            const AI_ACTIONS = [
                              { kind: 'rewrite',  label: '↺', title: 'Rewrite paragraph' },
                              { kind: 'research', label: '🔍', title: 'Research context' },
                              { kind: 'autotag',  label: '🏷', title: 'Auto-tag paragraph' },
                            ];
                            for (const action of AI_ACTIONS) {
                              const b = document.createElement('button');
                              b.type = 'button';
                              b.className = 'sp-ptool sp-ptool--ai';
                              b.title = action.title;
                              b.textContent = action.label;
                              b.addEventListener('mousedown', (ev) => {
                                ev.preventDefault();
                                ev.stopPropagation();
                                runAiFnRef.current(action.kind, idx);
                              });
                              bar.appendChild(b);
                            }
                          } else {
                            // Marks mode: show assigned tag icons (visual-only, still toggleable).
                            bar.className = 'sp-para-tools sp-para-tools--marks';
                            const shown = TAGS.filter((tag) => t.includes(tag.id));
                            for (const tag of shown) {
                              const b = document.createElement('button');
                              b.type = 'button';
                              b.className = `sp-ptool tag-${tag.id} is-on`;
                              b.title = `${tag.label} (click to remove)`;
                              b.textContent = tag.icon;
                              b.addEventListener('mousedown', (ev) => {
                                ev.preventDefault();
                                ev.stopPropagation();
                                tagFnRef.current(idx, tag.id);
                              });
                              bar.appendChild(b);
                            }
                          }
                          return bar;
                        }, { side: -1, key: `tools-${idx}-${palette ? 'ai' : 'marks'}-${t.join(',')}` }),
                      );
                    }
                    // FC-3 Word-level track changes vs the original snapshot.
                    // In aug-diff mode: diff current node against the Normalized paragraph
                    // instead (showing what the augmentation pipeline added, not human edits).
                    const augDiff = showAugDiffRef.current;
                    const before = augDiff ? (normTextsRef.current[idx] ?? '') : orig[idx];
                    const insClass = augDiff ? 'aug-ins' : 'tc-ins';
                    const delClass = augDiff ? 'aug-del' : 'tc-del';
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
      editor.view.dispatch(editor.state.tr);
    },
    onUpdate() { refresh(); },
    onSelectionUpdate({ editor }) {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, ' ').trim());
      // Track active paragraph index for the comment panel.
      const $head = editor.state.selection.$head;
      let paraIdx = -1;
      let i = 0;
      editor.state.doc.forEach((_, offset) => {
        const depth1Start = offset;
        const depth1End = offset + (editor.state.doc.child(i)?.nodeSize ?? 0);
        if ($head.pos >= depth1Start && $head.pos < depth1End) paraIdx = i;
        i++;
      });
      setActiveParaIdx(paraIdx >= 0 ? paraIdx : null);
      refresh(); // re-evaluate active-paragraph decoration on caret moves
    },
  });

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
  }, [stageId, chapIdx, viewAll, editor]);

  // Reset aug-diff and (re-)populate normTexts whenever the tab or chapter changes.
  useEffect(() => {
    showAugDiffRef.current = false;
    setShowAugDiff(false);
    const normStage = stages.find((s) => s.id === 'normalized');
    normTextsRef.current = [];
    if (normStage?.html) {
      const div = document.createElement('div');
      div.innerHTML = normStage.html;
      normTextsRef.current = Array.from(div.children).map((el) => el.textContent ?? '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageId, chapIdx]);

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

  // Toggle augmentation diff (Normalized → Augmented word-level diff). Same ref-before-dispatch
  // pattern as Arabic toggle so the decoration plugin sees the new value synchronously.
  const toggleAugDiff = useCallback(() => {
    const next = !showAugDiffRef.current;
    showAugDiffRef.current = next;
    setShowAugDiff(next);
    if (editor) editor.view.dispatch(editor.state.tr.setMeta('augDiff', true));
  }, [editor]);

  // ── Wave L-8: AI assist + Finalize ──────────────────────────────────────
  // Text of the paragraph at a given doc index (for AI actions on the selection).
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

  // Run an AI action on a paragraph. `kind` selects the route + model.
  // M-1: accepts optional paraIdx for invocation from the PM floating toolbar widget.
  const runAi = useCallback(async (kind: string, paraIdx?: number) => {
    const idx = paraIdx ?? activeParaIdx;
    if (idx === null || idx === undefined) return;
    const text = paragraphText(idx);
    if (!text.trim()) return;
    setAiBusy(true); setAiKind(kind); setAiResult(''); setAiError('');
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
          body: JSON.stringify({ text, context: chapterTitle }),
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
        if (tag && TAGS.some((t) => t.id === tag)) tagFnRef.current?.(idx, tag);
      } else if (kind === 'rewrite') {
        const opts = (json.data?.options ?? json.options ?? []) as string[];
        setAiResult(opts.map((o, i) => `${i + 1}. ${o}`).join('\n\n'));
      } else {
        setAiResult(typeof json.data === 'string' ? json.data : JSON.stringify(json.data));
      }
    } catch (e) {
      setAiError(String(e));
    } finally {
      setAiBusy(false);
    }
  }, [activeParaIdx, paragraphText, chapterTitle, setInspectorTab]);

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
  runAiFnRef.current = (kind: string, paraIdx?: number) => void runAi(kind, paraIdx);

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

  return (
    <div className="studio-poc">
      <main className="studio-poc__editor" ref={editorContainerRef}>
        {/* B: chapter switcher + all-chapters view toggle. */}
        <div className="sp-chapsel">
          <label htmlFor="sp-chap">Chapter</label>
          <select
            id="sp-chap"
            value={chapIdx}
            disabled={viewAll}
            onChange={(e) => setChapIdx(Number(e.target.value))}
          >
            {chapters.map((c, i) => (
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
        {/* Stage tabs (SN-5): Source -> Core -> Denoised -> Normalized -> Augmented. */}
        <div className="sp-tabs" role="tablist" aria-label="Pipeline stages">
          {stages.map((s) => (
            <button
              key={s.id}
              type="button"
              role="tab"
              aria-selected={s.id === stageId}
              disabled={!s.available}
              className={`sp-tab${s.id === stageId ? ' is-active' : ''}${s.available ? '' : ' is-pending'}`}
              title={s.available ? `${s.label} stage${approvedStages[s.id] ? ' — approved' : ''}` : `Pending — produced by ${s.slice}`}
              onClick={() => s.available && setStageId(s.id)}
            >
              {s.label}{approvedStages[s.id] && <span className="sp-tab-ok" aria-label="approved"> ✓</span>}
            </button>
          ))}
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
        {viewAll && (
          <div className="sp-viewall-banner">
            Showing all {chapters.length} chapters · {stages.find((s) => s.id === stageId)?.label ?? stageId} stage · read-only
          </div>
        )}
        {!viewAll && isReadOnlyStage && (
          <div className="sp-stage-note">Read-only — viewing the {stage?.label} stage for comparison.</div>
        )}
        {!viewAll && stageId === 'augmented' && stages.find((s) => s.id === 'normalized')?.available && (
          <div className="sp-augdiff-row">
            <button
              type="button"
              className={`sp-augdiff-toggle${showAugDiff ? ' is-on' : ''}`}
              onClick={toggleAugDiff}
              title={showAugDiff ? 'Hide augmentation diff' : 'Highlight what the augmentation step added vs Normalized'}
            >
              {showAugDiff ? 'Hide augmentation diff' : 'Show augmentation diff'}
            </button>
            {showAugDiff && (
              <span className="sp-augdiff-legend">
                <span className="aug-ins sp-augdiff-swatch">added</span>
                <span className="aug-del sp-augdiff-swatch">removed</span>
              </span>
            )}
          </div>
        )}
        <EditorContent editor={editor} />
      </main>

      <aside className="studio-poc__inspector" aria-label="Contextual inspector">
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
          {!viewAll && (
            <>
              <div className="sp-strip-sep" aria-hidden="true" />
              <button type="button" className="sp-finalize" onClick={finalize} title="Generate Claude brief from tagged paragraphs">
                ⎘ Finalize
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
              const hasDot = tab === 'ai' && (!!aiResult || aiBusy);
              return (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={inspectorTab === tab}
                  className={`sp-tab-btn${inspectorTab === tab ? ' is-active' : ''}`}
                  onClick={() => setInspectorTab(tab)}
                >
                  {labels[tab]}
                  {hasDot && <span className="sp-tab-dot" aria-label="result ready" />}
                </button>
              );
            })}
          </div>

          <div className="sp-tab-pane">
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

            {/* ── AI tab: results from Rewrite / Research / Auto-tag ── */}
            {inspectorTab === 'ai' && (
              <div className="sp-ai-panel">
                {activeParaIdx !== null && !isReadOnlyStage && (
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
                {aiResult && <pre className="sp-ai-result">{aiResult}</pre>}
                {!aiBusy && !aiResult && !aiError && (
                  <p className="sp-insp-hint">Hover a paragraph and click ↺ 🔍 🏷 in the toolbar above it, or use the buttons here when a paragraph is selected.</p>
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
