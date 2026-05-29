/**
 * StudioPoc.tsx — WC8 Slice 0 proof-of-concept (THROWAWAY, feel-check only).
 *
 * Proves the Studio editor engine on a real Ayyuhal Walad chapter:
 *   - TipTap (ProseMirror): real editable prose, real undo/redo, transactions.
 *   - Non-destructive MARKERS as ProseMirror decorations (reference-like spans),
 *     NOT edits to the text — the mechanism divergence/annotation markers will use.
 *   - A contextual INSPECTOR that follows the selection (the R-2 pattern).
 *   - A minimal marking toolbar (one-click actions) to prove commands.
 *
 * This is a disposable spike to let Asif feel the engine before the full build.
 * Styling is external (studio-poc.css) per the repo DoD — no inline styles.
 */
import { useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

// Demo marker patterns — illustrate corpus-verified-style reference markers.
const MARKER_PATTERNS: { re: RegExp; cls: string; kind: string }[] = [
  { re: /Surah [A-Z][\w'-]+/g, cls: 'mk-quran', kind: 'Quran' },
  { re: /verses? \d+(?:\s*(?:to|–|-)\s*\d+)?/gi, cls: 'mk-quran', kind: 'Quran' },
  { re: /Prophet Muhammad|peace and blessings of Allah/gi, cls: 'mk-hadith', kind: 'Hadith' },
  { re: /Ihya Ulum al-Din|Kimiya al-Sa'ada|Jawahir al-Quran|Minhaj al-Abidin/g, cls: 'mk-term', kind: 'Work' },
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
                  decos.push(
                    Decoration.inline(pos + m.index, pos + m.index + m[0].length, { class: `mk ${cls}` }),
                  );
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

interface Props {
  html: string;
  chapterTitle: string;
}

export default function StudioPoc({ html, chapterTitle }: Props) {
  const [selection, setSelection] = useState('');
  const rawMarkers = scanMarkers(html.replace(/<[^>]+>/g, ' '));
  // Dedupe repeats (the same surah/phrase recurs) so the list scales to 50+ cleanly.
  const seen = new Map<string, { kind: string; text: string; count: number }>();
  for (const m of rawMarkers) {
    const key = `${m.kind}|${m.text}`;
    const e = seen.get(key);
    if (e) e.count += 1;
    else seen.set(key, { ...m, count: 1 });
  }
  const markers = [...seen.values()];

  const editor = useEditor({
    extensions: [StarterKit, MarkerHighlight],
    content: html,
    onSelectionUpdate({ editor }) {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, ' ').trim());
    },
  });

  const quran = markers.filter((m) => m.kind === 'Quran');
  const hadith = markers.filter((m) => m.kind === 'Hadith');
  const works = markers.filter((m) => m.kind === 'Work');

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
      {/* Viewer LEFT (right-handed: panel on the right). */}
      <main className="studio-poc__editor">
        <EditorContent editor={editor} />
      </main>

      <aside className="studio-poc__inspector" aria-label="Contextual inspector">
        <div className="sp-insp-block">
          <h2 className="sp-insp-title">Inspector</h2>
          <p className="sp-insp-hint">
            {selection
              ? 'Selection (paragraph-level context):'
              : 'Nothing selected — chapter-level context:'}
          </p>
          {selection ? (
            <blockquote className="sp-insp-sel">{selection}</blockquote>
          ) : (
            <dl className="sp-insp-meta">
              <dt>Chapter</dt>
              <dd>{chapterTitle}</dd>
              <dt>Markers</dt>
              <dd>{rawMarkers.length} ({markers.length} unique)</dd>
            </dl>
          )}
        </div>

        {/* Actions ABOVE markers; flex-wrap supports 10-15 buttons. */}
        <div className="sp-insp-block">
          <h3 className="sp-insp-sub">Actions</h3>
          <div className="sp-toolbar" role="toolbar" aria-label="Marking actions">
            <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleBlockquote().run()}>Quote</button>
            <button type="button" onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
            <button type="button" onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
          </div>
        </div>

        <div className="sp-insp-block sp-insp-block--markers">
          <h3 className="sp-insp-sub">Markers</h3>
          {renderGroup('Quran', quran, 'quran')}
          {renderGroup('Hadith', hadith, 'hadith')}
          {renderGroup('Works', works, 'work')}
        </div>
      </aside>
    </div>
  );
}
