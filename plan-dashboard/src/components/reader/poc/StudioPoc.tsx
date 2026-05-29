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
import { useState, useRef, useMemo, useCallback } from 'react';
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

const TAGS = [
  { id: 'esoteric', label: 'Esoteric' },
  { id: 'reality', label: 'Reality' },
  { id: 'sharia', label: 'Sharia' },
  { id: 'delete', label: 'Delete' },
  { id: 'improve', label: 'Improve' },
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
// "Surah X, verses 7 to 8" | "Surah X, verse 110"
const SURAH_VERSE_RE = /Surah ([A-Z][\w'’-]+),?\s+verses?\s+(\d+)(?:\s*(?:to|–|-)\s*(\d+))?/g;

// FC-1: append a compact chapter:verse CHIP after the reference (prose untouched).
const QuranRefChips = Extension.create({
  name: 'quranRefChips',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('quranRefChips'),
        props: {
          decorations(state) {
            const decos: Decoration[] = [];
            state.doc.descendants((node, pos) => {
              if (!node.isText || !node.text) return;
              SURAH_VERSE_RE.lastIndex = 0;
              let m: RegExpExecArray | null;
              while ((m = SURAH_VERSE_RE.exec(node.text))) {
                const num = SURAH_MAP[m[1].replace(/’/g, "'")];
                if (!num) continue;
                const label = m[3] ? `${num}:${m[2]}–${m[3]}` : `${num}:${m[2]}`;
                const end = pos + m.index + m[0].length;
                decos.push(
                  Decoration.widget(end, () => {
                    const chip = document.createElement('span');
                    chip.className = 'ref-quran sp-vchip';
                    chip.textContent = label;
                    chip.setAttribute('data-surah', String(num));
                    chip.setAttribute('data-verse', m![2]);
                    return chip;
                  }, { side: 1 }),
                );
              }
            });
            return DecorationSet.create(state.doc, decos);
          },
        },
      }),
    ];
  },
});

interface Props {
  html: string;
  chapterTitle: string;
  glossary?: GlossaryEntry[];
}

export default function StudioPoc({ html, chapterTitle, glossary = [] }: Props) {
  const [selection, setSelection] = useState('');
  const [arabicOn, setArabicOn] = useState(false);
  const [, setTick] = useState(0);
  const refresh = () => setTick((t) => t + 1);

  const originalRef = useRef<string[]>([]);            // original text per top-level node
  const paraTagsRef = useRef<Map<number, string[]>>(new Map()); // node index -> tag ids
  const arabicRef = useRef(false);                     // mirror of arabicOn for the plugin
  arabicRef.current = arabicOn;

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

                  let i = 0;
                  state.doc.forEach((node, offset) => {
                    const idx = i++;
                    if (offset === activeTop) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: 'para-active' }));
                    }
                    // Token tag left-border.
                    const t = tags.get(idx);
                    if (t && t.length) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: `para-tagged tag-${t[0]}` }));
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
                          const re = new RegExp(`\\b${e.phonetic.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g');
                          let mm: RegExpExecArray | null;
                          while ((mm = re.exec(child.text!))) {
                            const from = base + mm.index;
                            const to = from + mm[0].length;
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
    extensions: [StarterKit, MarkerHighlight, QuranRefChips, StudioDecos],
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

  // Force a decoration recompute when Arabic mode flips.
  const toggleArabic = useCallback(() => {
    setArabicOn((v) => !v);
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

  const tagCurrentParagraph = useCallback(
    (tagId: string) => {
      if (!editor) return;
      const { from } = editor.state.selection;
      let i = 0;
      let idx = -1;
      editor.state.doc.forEach((node, offset) => {
        if (from >= offset && from <= offset + node.nodeSize) idx = i;
        i++;
      });
      if (idx < 0) return;
      const map = paraTagsRef.current;
      const cur = map.get(idx) || [];
      map.set(idx, cur.includes(tagId) ? cur.filter((x) => x !== tagId) : [...cur, tagId]);
      editor.view.dispatch(editor.state.tr.setMeta('refreshTags', true));
      refresh();
    },
    [editor],
  );

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
        <EditorContent editor={editor} />
      </main>

      <aside className="studio-poc__inspector" aria-label="Contextual inspector">
        <div className="sp-insp-block">
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
        </div>

        <div className="sp-insp-block">
          <h3 className="sp-insp-sub">View</h3>
          <div className="sp-toolbar">
            <button
              type="button"
              className={`sp-tagbtn sp-arabic-btn ${arabicOn ? 'is-on' : ''}`}
              aria-pressed={arabicOn}
              onClick={toggleArabic}
            >
              <span lang="ar" dir="rtl">ع</span> Arabic script {arabicOn ? 'On' : 'Off'}
            </button>
          </div>
        </div>

        <div className="sp-insp-block">
          <h3 className="sp-insp-sub">Tag paragraph</h3>
          <div className="sp-toolbar">
            {TAGS.map((t) => (
              <button key={t.id} type="button" className={`sp-tagbtn tag-${t.id}`} onClick={() => tagCurrentParagraph(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="sp-insp-block">
          <h3 className="sp-insp-sub">Edit</h3>
          <div className="sp-toolbar" role="toolbar" aria-label="Edit actions">
            <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleBlockquote().run()}>Quote</button>
            <button type="button" onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
            <button type="button" onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
          </div>
        </div>

        <div className="sp-insp-block sp-insp-block--markers">
          <h3 className="sp-insp-sub">Markers</h3>
          {renderGroup('Quran', group('Quran'), 'quran')}
          {renderGroup('Hadith', group('Hadith'), 'hadith')}
          {renderGroup('Works', group('Work'), 'work')}
        </div>
      </aside>
    </div>
  );
}
