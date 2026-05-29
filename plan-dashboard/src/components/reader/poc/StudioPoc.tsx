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
  const markers = scanMarkers(html.replace(/<[^>]+>/g, ' '));

  const editor = useEditor({
    extensions: [StarterKit, MarkerHighlight],
    content: html,
    onSelectionUpdate({ editor }) {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, ' ').trim());
    },
  });

  return (
    <div className="studio-poc">
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
              <dt>Detected markers</dt>
              <dd>{markers.length}</dd>
            </dl>
          )}
        </div>

        <div className="sp-insp-block">
          <h3 className="sp-insp-sub">Markers in this chapter</h3>
          <ul className="sp-marker-list">
            {markers.slice(0, 12).map((m, i) => (
              <li key={i}>
                <span className={`sp-chip sp-chip--${m.kind.toLowerCase()}`}>{m.kind}</span>
                <span className="sp-marker-text">{m.text}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="sp-insp-block">
          <h3 className="sp-insp-sub">Actions (demo)</h3>
          <div className="sp-toolbar" role="toolbar" aria-label="Marking actions">
            <button type="button" onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</button>
            <button type="button" onClick={() => editor?.chain().focus().toggleBlockquote().run()}>Quote</button>
            <button type="button" onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
            <button type="button" onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
          </div>
        </div>
      </aside>

      <main className="studio-poc__editor">
        <EditorContent editor={editor} />
      </main>
    </div>
  );
}
