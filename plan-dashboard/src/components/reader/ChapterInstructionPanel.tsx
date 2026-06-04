/**
 * ChapterInstructionPanel — docked AI instruction textarea in the right rail.
 *
 * Posts to /api/ai/instruct with the chapter's block contents, then
 * dispatches `chapter-editor:apply-edits` that ChapterEditor consumes.
 * No Tailwind utility classes.
 */

import { useEffect, useRef, useState } from 'react';

interface HistoryItem { id: string; instruction: string; note?: string; editCount: number; }

export default function ChapterInstructionPanel() {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 220) + 'px';
  }, [text]);

  const send = async () => {
    const instruction = text.trim();
    if (!instruction || busy) return;
    const editorApi = (window as any).__chapterEditor;
    if (!editorApi) { setError('Editor not ready'); return; }
    const blocks = editorApi.collectBlocks();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch('/api/ai/instruct', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          instruction,
          blocks,
          bookContext: editorApi.bookContext,
          chapterTitle: editorApi.chapterTitle,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? `AI ${res.status}`);
      const edits = data.edits ?? [];
      window.dispatchEvent(new CustomEvent('chapter-editor:apply-edits', { detail: { edits } }));
      setHistory((h) => [
        { id: `i-${Date.now()}`, instruction, note: data.note, editCount: edits.length },
        ...h,
      ].slice(0, 8));
      setText('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); send(); }
  };

  return (
    <div className="rail-panel">
      <div className="rail-panel-head">
        <span aria-hidden className="rail-panel-icon">✦</span>
        <span className="rail-panel-label">Instruct the editor</span>
      </div>
      <textarea
        ref={taRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKey}
        rows={6}
        placeholder={'e.g. "shorten paragraph 3"\n   "fix Sayyidina transliteration"\n   "split the long opening into two"'}
        className="rail-textarea"
        disabled={busy}
      />
      <div className="rail-row">
        <span className="rail-hint">⌘↵ to send · Gemini Pro</span>
        <button
          onClick={send}
          disabled={busy || !text.trim()}
          className="rail-btn rail-btn-primary"
        >
          {busy ? 'Applying…' : 'Apply'}
        </button>
      </div>
      {error && <div className="rail-error">{error}</div>}
      {history.length > 0 && (
        <div className="rail-history">
          <div className="rail-history-label">Recent</div>
          {history.map((h) => (
            <div key={h.id} className="rail-history-item">
              <div className="rail-history-text">{h.instruction}</div>
              <div className="rail-history-meta">
                <span>{h.editCount === 0 ? 'no change' : `${h.editCount} edit${h.editCount === 1 ? '' : 's'}`}</span>
                {h.note && <span className="rail-history-note" title={h.note}>{h.note.slice(0, 40)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
