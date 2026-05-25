/**
 * ChapterInstructionPanel — docked AI instruction textarea in the
 * right rail (below the mini-TOC).
 *
 * The reader types a free-form instruction ("shorten paragraph 3",
 * "fix the Sayyidina transliteration", "split that long opening
 * paragraph into two"). On send: posts to /api/ai/instruct with the
 * chapter's block-by-block contents, then dispatches an
 * `chapter-editor:apply-edits` event that ChapterEditor consumes to
 * apply the edits in-place with a flash animation.
 *
 * Always visible. Compact when idle, grows when typing.
 */

import { useEffect, useRef, useState } from 'react';

interface HistoryItem { id: string; instruction: string; note?: string; editCount: number; }

export default function ChapterInstructionPanel() {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const taRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow textarea
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
    <div className="mt-4 border-t border-stone-200 pt-4 dark:border-stone-700">
      <div className="mb-2 flex items-center gap-2">
        <span aria-hidden className="text-amber-600">✦</span>
        <span className="font-ui text-[12px] font-semibold tracking-wide text-stone-600">Instruct the editor</span>
      </div>
      <textarea
        ref={taRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKey}
        rows={6}
        placeholder={'e.g. "shorten paragraph 3"\n   "fix Sayyidina transliteration"\n   "split the long opening into two"'}
        className="w-full resize-none rounded-lg border border-stone-300 bg-white px-3 py-2 text-[12.5px] leading-snug placeholder:text-stone-400 focus:border-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-100 dark:border-stone-600 dark:bg-stone-900 dark:focus:ring-amber-900/30"
        disabled={busy}
      />
      <div className="mt-1.5 flex items-center justify-between">
        <span className="font-ui text-[10px] text-stone-400">⌘↵ to send · Gemini Pro</span>
        <button
          onClick={send}
          disabled={busy || !text.trim()}
          className="rounded-md bg-amber-600 px-3 py-1 text-[11px] font-semibold text-white shadow-sm transition disabled:opacity-40 hover:bg-amber-700"
        >
          {busy ? 'Applying…' : 'Apply'}
        </button>
      </div>
      {error && <div className="mt-1.5 text-[11px] text-rose-600">{error}</div>}
      {history.length > 0 && (
        <div className="mt-3 space-y-1.5">
          <div className="font-ui text-[11px] font-semibold tracking-wide text-stone-500">Recent</div>
          {history.map((h) => (
            <div key={h.id} className="rounded-md border border-stone-200 bg-stone-50/60 px-2 py-1 text-[11px] dark:border-stone-700 dark:bg-stone-800/40">
              <div className="text-stone-700 dark:text-stone-200">{h.instruction}</div>
              <div className="mt-0.5 flex items-center justify-between font-ui text-[9px] uppercase tracking-wider text-stone-400">
                <span>{h.editCount === 0 ? 'no change' : `${h.editCount} edit${h.editCount === 1 ? '' : 's'}`}</span>
                {h.note && <span className="truncate italic normal-case tracking-normal" title={h.note}>{h.note.slice(0, 40)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
