/**
 * StudioPoc.tsx — WC8 Studio (spike → real build). TipTap/ProseMirror foundation.
 *
 * Step 1 capabilities (this iteration):
 *   - Non-destructive reference MARKERS as decorations (Quran/hadith/works), grouped.
 *   - CHANGE-TRACKING REDLINE: edited paragraphs stay highlighted green (preserve from
 *     the existing ChapterEditor); live changed-count.
 *   - PER-PARAGRAPH TOKEN TAGS: tag the current paragraph (esoteric/reality/sharia/
 *     delete/improve); the paragraph gets a coloured left-border + the tag is captured.
 *   - Contextual INSPECTOR that follows selection; viewer left, panel right.
 *
 * These manual actions (edits, tags) are the training signal for the learning loop:
 * the pipeline will pre-apply learned patterns before review (tiered: deterministic
 * auto-applied, judgment pre-marked). External CSS only (repo DoD).
 */
import { useState, useRef, useMemo, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

const MARKER_PATTERNS: { re: RegExp; cls: string; kind: string }[] = [
  { re: /Surah [A-Z][\w'-]+/g, cls: 'mk-quran', kind: 'Quran' },
  { re: /verses? \d+(?:\s*(?:to|–|-)\s*\d+)?/gi, cls: 'mk-quran', kind: 'Quran' },
  { re: /Prophet Muhammad|peace and blessings of Allah/gi, cls: 'mk-hadith', kind: 'Hadith' },
  { re: /Ihya Ulum al-Din|Kimiya al-Sa'ada|Jawahir al-Quran|Minhaj al-Abidin/g, cls: 'mk-term', kind: 'Work' },
];

// The five token tags (mirror the existing annotation_tags defaults).
const TAGS = [
  { id: 'esoteric', label: 'Esoteric' },
  { id: 'reality', label: 'Reality' },
  { id: 'sharia', label: 'Sharia' },
  { id: 'delete', label: 'Delete' },
  { id: 'improve', label: 'Improve' },
];

function scanMarkers(text: string): { kind: string; text: string }[] {
  const out: { kind: string; text: string }[] = [];
  for (const { re, kind } of MARKER_PATTERNS) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) out.push({ kind, text: m[0] });
  }
  return out;
}

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

// Surah name -> number (subset; expand to all 114 in the real build). Lets prose like
// "Surah Az-Zalzalah, verses 7 to 8" become a hoverable 99:7 ref.
const SURAH_MAP: Record<string, number> = {
  'Al-Fatihah': 1, 'Al-Baqarah': 2, "Al-A'raf": 7, 'Al-Anfal': 8, 'At-Tawbah': 9,
  'Yusuf': 12, 'Al-Isra': 17, 'Al-Kahf': 18, 'Maryam': 19, 'Ta-Ha': 20,
  'Al-Muminun': 23, 'An-Nur': 24, 'Al-Furqan': 25, 'Luqman': 31, 'Ya-Sin': 36,
  'Adh-Dhariyat': 51, 'Ar-Rahman': 55, 'Al-Hashr': 59, 'Al-Mulk': 67,
  "Al-A'la": 87, 'Ash-Shams': 91, 'Az-Zalzalah': 99, 'Al-Asr': 103, 'Al-Ikhlas': 112,
};
const SURAH_VERSE_RE = /Surah ([A-Z][\w'’-]+),?\s+verses?\s+(\d+)/g;

// Emit .ref-quran spans (data-surah/data-verse) so the reused QuranPopover shows the
// verse + translation + audio on hover. Source today = /api/quran/verse; swaps to the
// wisdom MCP/corpus per D13 once KQUR is ingested.
const QuranRefs = Extension.create({
  name: 'quranRefs',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('quranRefs'),
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
                decos.push(
                  Decoration.inline(pos + m.index, pos + m.index + m[0].length, {
                    class: 'ref-quran',
                    'data-surah': String(num),
                    'data-verse': m[2],
                  }),
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
}

export default function StudioPoc({ html, chapterTitle }: Props) {
  const [selection, setSelection] = useState('');
  const [, setTick] = useState(0);
  const refresh = () => setTick((t) => t + 1);

  const originalRef = useRef<string[]>([]);          // original text per top-level node
  const paraTagsRef = useRef<Map<number, string[]>>(new Map()); // node index -> tag ids

  // Redline + tag decorations (recomputed each state change; refs hold the truth).
  const ChangeTracker = useMemo(
    () =>
      Extension.create({
        name: 'changeTracker',
        addProseMirrorPlugins() {
          return [
            new Plugin({
              key: new PluginKey('changeTracker'),
              props: {
                decorations(state) {
                  const orig = originalRef.current;
                  const tags = paraTagsRef.current;
                  const decos: Decoration[] = [];
                  let i = 0;
                  state.doc.forEach((node, offset) => {
                    const idx = i++;
                    if (orig[idx] !== undefined && node.textContent !== orig[idx]) {
                      decos.push(Decoration.node(offset, offset + node.nodeSize, { class: 'edit-changed' }));
                    }
                    const t = tags.get(idx);
                    if (t && t.length) {
                      decos.push(
                        Decoration.node(offset, offset + node.nodeSize, { class: `para-tagged tag-${t[0]}` }),
                      );
                    }
                  });
                  return DecorationSet.create(state.doc, decos);
                },
              },
            }),
          ];
        },
      }),
    [],
  );

  const editor = useEditor({
    extensions: [StarterKit, MarkerHighlight, QuranRefs, ChangeTracker],
    content: html,
    onCreate({ editor }) {
      const texts: string[] = [];
      editor.state.doc.forEach((n) => texts.push(n.textContent));
      originalRef.current = texts;
    },
    onUpdate() {
      refresh();
    },
    onSelectionUpdate({ editor }) {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, ' ').trim());
    },
  });

  // Live changed-paragraph count for the inspector.
  let changedCount = 0;
  if (editor) {
    let i = 0;
    editor.state.doc.forEach((n) => {
      if (originalRef.current[i] !== undefined && n.textContent !== originalRef.current[i]) changedCount++;
      i++;
    });
  }
  const tagged = paraTagsRef.current;
  let taggedCount = 0;
  tagged.forEach((t) => { if (t.length) taggedCount++; });

  // Tag the paragraph at the cursor (toggle).
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
      editor.view.dispatch(editor.state.tr.setMeta('refreshTags', true)); // recompute decorations
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

        {/* Tag the current paragraph (token tags — training signal). */}
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

        {/* Edit actions (flex-wraps for 10-15). */}
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
