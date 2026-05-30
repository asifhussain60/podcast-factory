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
import { diffWords } from 'diff';

// Inline reference markers kept for the inspector inventory + subtle in-text hinting.
// Quran verse refs are handled separately (FC-1 chip), so they are NOT highlighted here.
const MARKER_PATTERNS: { re: RegExp; cls: string; kind: string }[] = [
  { re: /Surah [A-Z][\w'-]+/g, cls: 'mk-quran', kind: 'Quran' },
  { re: /verses? \d+(?:\s*(?:to|–|-)\s*\d+)?/gi, cls: 'mk-quran', kind: 'Quran' },
  { re: /Prophet Muhammad|peace and blessings of Allah/gi, cls: 'mk-hadith', kind: 'Hadith' },
  { re: /Ihya Ulum al-Din|Kimiya al-Sa'ada|Jawahir al-Quran|Minhaj al-Abidin/g, cls: 'mk-term', kind: 'Work' },
];

// Each tag carries a distinct ICON so the meaning is recognizable without memorizing colour.
const TAGS = [
  { id: 'esoteric', label: 'Esoteric', icon: '🔮' },
  { id: 'reality', label: 'Reality', icon: '💎' },
  { id: 'sharia', label: 'Sharia', icon: '⚖️' },
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

// Hadith + Works inline highlight only (Quran verse refs become chips, see QuranRefs).
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
              for (const { re, cls } of MARKER_PATTERNS) {
                if (cls === 'mk-quran') continue; // handled as chips
                re.lastIndex = 0;
                let m: RegExpExecArray | null;
                while ((m = re.exec(node.text))) {
                  decos.push(Decoration.inline(pos + m.index, pos + m.index + m[0].length, { class: `mk ${cls}` }));
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
}

export default function StudioPoc({ slug, chapters, glossary = [] }: Props) {
  // B: chapter switcher — pick which chapter's stages the editor shows.
  const [chapIdx, setChapIdx] = useState(0);
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
  const approveStage = useCallback(async () => {
    if (!stage) return;
    setSaving(true);
    try {
      const res = await fetch('/api/studio/review', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ slug, chapter, stage: stage.id, approved: true }),
      });
      if (res.ok) setApprovedStages((m) => ({ ...m, [stage.id]: true }));
    } catch { /* surfaced by the unchanged button state */ } finally {
      setSaving(false);
    }
  }, [slug, chapter, stage]);

  const [selection, setSelection] = useState('');
  const [arabicOn, setArabicOn] = useState(false);
  const [, setTick] = useState(0);
  const refresh = () => setTick((t) => t + 1);

  const originalRef = useRef<string[]>([]);            // original text per top-level node
  const paraTagsRef = useRef<Map<number, string[]>>(new Map()); // node index -> tag ids
  const arabicRef = useRef(false);                     // mirror of arabicOn for the plugin
  arabicRef.current = arabicOn;
  // Index-based tag toggle, called from the floating per-paragraph icon toolbar (a PM widget
  // built outside React). Held in a ref so the widget always calls the latest closure.
  const tagFnRef = useRef<(idx: number, tagId: string) => void>(() => {});

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

                  // Active paragraph (FC-3): the top-level node holding the cursor.
                  const headPos = state.selection.$head;
                  const activeTop = headPos.depth >= 1 ? headPos.before(1) : -1;

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
                    //  - active paragraph -> full palette (all tags, assigned ones lit)
                    //  - tagged but not active -> persistent marks (assigned icons only)
                    if (isActive || t.length) {
                      const palette = isActive;
                      const shown = palette ? TAGS : TAGS.filter((tag) => t.includes(tag.id));
                      decos.push(
                        Decoration.widget(offset + 1, () => {
                          const bar = document.createElement('div');
                          bar.className = `sp-para-tools${palette ? ' sp-para-tools--palette' : ' sp-para-tools--marks'}`;
                          bar.contentEditable = 'false';
                          for (const tag of shown) {
                            const b = document.createElement('button');
                            b.type = 'button';
                            b.className = `sp-ptool tag-${tag.id}${t.includes(tag.id) ? ' is-on' : ''}`;
                            b.title = tag.label;
                            b.textContent = tag.icon;
                            b.addEventListener('mousedown', (ev) => {
                              ev.preventDefault();
                              ev.stopPropagation();
                              tagFnRef.current(idx, tag.id);
                            });
                            bar.appendChild(b);
                          }
                          return bar;
                        }, { side: -1, key: `tools-${idx}-${palette ? 'p' : 'm'}-${t.join(',')}` }),
                      );
                    }
                    // FC-3 Word-level track changes vs the original snapshot.
                    const before = orig[idx];
                    const after = node.textContent;
                    if (before !== undefined && before !== after) {
                      let cursor = offset + 1; // content start of a textblock
                      for (const part of diffWords(before, after)) {
                        const len = part.value.length;
                        if (part.added) {
                          decos.push(Decoration.inline(cursor, cursor + len, { class: 'tc-ins' }));
                          cursor += len;
                        } else if (part.removed) {
                          const text = part.value;
                          decos.push(
                            Decoration.widget(cursor, () => {
                              const del = document.createElement('span');
                              del.className = 'tc-del';
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
    onUpdate() { refresh(); },
    onSelectionUpdate({ editor }) {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, ' ').trim());
      refresh(); // re-evaluate active-paragraph decoration on caret moves
    },
  });

  // Switch the editor to the selected stage: load its text, re-snapshot redline originals,
  // clear stage-specific tags, and make only the under-review stage editable (upstream = read-only).
  useEffect(() => {
    if (!editor || !stage) return;
    editor.commands.setContent(stage.html);
    const texts: string[] = [];
    editor.state.doc.forEach((n) => texts.push(n.textContent));
    originalRef.current = texts;
    paraTagsRef.current = new Map();
    editor.setEditable(!isReadOnlyStage);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageId, chapIdx, editor]);

  // Force a decoration recompute when Arabic mode flips. Set the ref BEFORE dispatching
  // (React state is async — the plugin reads arabicRef synchronously during the recompute).
  const toggleArabic = useCallback(() => {
    const next = !arabicRef.current;
    arabicRef.current = next;
    setArabicOn(next);
    if (editor) editor.view.dispatch(editor.state.tr.setMeta('arabic', true));
  }, [editor]);

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
      <main className="studio-poc__editor">
        {/* B: chapter switcher. */}
        <div className="sp-chapsel">
          <label htmlFor="sp-chap">Chapter</label>
          <select id="sp-chap" value={chapIdx} onChange={(e) => setChapIdx(Number(e.target.value))}>
            {chapters.map((c, i) => (
              <option key={c.slug} value={i}>{i + 1}. {c.title}</option>
            ))}
          </select>
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
        {(() => {
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
        {isReadOnlyStage && (
          <div className="sp-stage-note">Read-only — viewing the {stage?.label} stage for comparison.</div>
        )}
        <EditorContent editor={editor} />
      </main>

      <aside className="studio-poc__inspector" aria-label="Contextual inspector">
        {/* Controls — at the top, its own bordered card. Arabic as a switch + the edit toolbar. */}
        <section className="sp-controls">
          <div className="sp-control-row">
            <span className="sp-control-label"><span lang="ar" dir="rtl">ع</span> Arabic script</span>
            <button
              type="button"
              role="switch"
              aria-checked={arabicOn}
              className={`sp-switch ${arabicOn ? 'is-on' : ''}`}
              onClick={toggleArabic}
              title={arabicOn ? 'Hide Arabic script' : 'Show Arabic script'}
            >
              <span className="sp-switch-thumb" />
            </button>
          </div>
          <div className="sp-edit">
            <span className="sp-control-label">Edit</span>
            <div className="sp-edit-row" role="toolbar" aria-label="Edit actions">
              <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()} title="Bold"><b>B</b></button>
              <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()} title="Italic"><i>I</i></button>
              <button type="button" onClick={() => editor?.chain().focus().toggleBlockquote().run()} title="Quote">”</button>
              <button type="button" onClick={() => editor?.chain().focus().undo().run()} title="Undo">↺</button>
              <button type="button" onClick={() => editor?.chain().focus().redo().run()} title="Redo">↻</button>
            </div>
          </div>
          {/* WC8 write-back: approve the stage under review -> releases the pipeline halt. */}
          {!isReadOnlyStage && stage && (
            <button
              type="button"
              className={`sp-approve ${approvedStages[stage.id] ? 'is-done' : ''}`}
              onClick={approveStage}
              disabled={saving || approvedStages[stage.id]}
            >
              {approvedStages[stage.id] ? `✓ ${stage.label} approved` : saving ? 'Saving…' : `Approve ${stage.label} stage`}
            </button>
          )}
        </section>

        {/* Inspector — its own bordered card; bounded height, scrolls internally. */}
        <section className="sp-inspector">
          <h2 className="sp-insp-title">Inspector</h2>
          {selection ? (
            <blockquote className="sp-insp-sel">{selection}</blockquote>
          ) : (
            <dl className="sp-insp-meta">
              <dt>Chapter</dt>
              <dd>{chapterTitle}</dd>
              <dt>Changes</dt>
              <dd>{changedCount} edited · {taggedCount} tagged</dd>
            </dl>
          )}
          <div className="sp-insp-markers">
            <h3 className="sp-insp-sub">References</h3>
            {renderGroup('Quran', group('Quran'), 'quran')}
            {renderGroup('Hadith', group('Hadith'), 'hadith')}
            {renderGroup('Works', group('Work'), 'work')}
          </div>
        </section>
      </aside>
    </div>
  );
}
