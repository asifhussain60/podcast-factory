/**
 * AskChapter — chapter-grounded chat in the right rail.
 *
 * The chapter text is supplied at mount (server-rendered into a JSON
 * blob). Conversation lives in memory; cleared on navigation.
 *
 * Streams replies via /api/ai/ask-chapter (SSE).
 */

import { useEffect, useRef, useState } from 'react';

interface Props {
  book: string;
  chapterTitle: string;
  chapterText: string;
}

interface Msg { role: 'user' | 'model'; text: string; }

export default function AskChapter({ book, chapterTitle, chapterText }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput('');
    const history = messages.slice();
    setMessages([...history, { role: 'user', text: q }, { role: 'model', text: '' }]);
    setBusy(true);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = await fetch('/api/ai/ask-chapter', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          chapterText, chapterTitle, bookContext: book,
          history: history.map((m) => ({ role: m.role, text: m.text })),
          question: q,
        }),
        signal: abortRef.current.signal,
      });
      if (!res.ok || !res.body) throw new Error(`AI ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      let acc = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const events = buf.split('\n\n');
        buf = events.pop() ?? '';
        for (const ev of events) {
          const dataLine = ev.split('\n').find((l) => l.startsWith('data:'));
          if (!dataLine) continue;
          try {
            const payload = JSON.parse(dataLine.slice(5).trim());
            if (payload.text) {
              acc += payload.text;
              setMessages((m) => {
                const copy = m.slice();
                copy[copy.length - 1] = { role: 'model', text: acc };
                return copy;
              });
            }
          } catch { /* skip */ }
        }
      }
    } catch (e) {
      setMessages((m) => {
        const copy = m.slice();
        copy[copy.length - 1] = { role: 'model', text: `_Error: ${(e as Error).message}_` };
        return copy;
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-6 border-t border-stone-200 pt-4 dark:border-stone-700">
      <button
        onClick={() => setOpen((v) => !v)}
        className="mb-3 flex w-full items-center justify-between font-ui text-[10px] font-semibold uppercase tracking-wider text-stone-500 hover:text-amber-700"
        aria-expanded={open}
      >
        <span>Ask this chapter</span>
        <span className="text-[14px]">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="space-y-2">
          <div
            ref={scrollRef}
            className="max-h-[40vh] overflow-y-auto rounded border border-stone-200 bg-stone-50/60 p-2 text-[12px] leading-snug dark:border-stone-700 dark:bg-stone-800/40"
            style={{ minHeight: messages.length === 0 ? '0' : '60px' }}
          >
            {messages.length === 0 && (
              <div className="px-1 py-2 text-stone-400">
                Ask a question grounded in this chapter. The model only sees what's on this page.
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={'mb-2 ' + (m.role === 'user' ? 'text-stone-900 dark:text-stone-100' : 'text-stone-600 dark:text-stone-300')}>
                <span className="mr-1 font-ui text-[9px] font-semibold uppercase tracking-wider text-stone-400">
                  {m.role === 'user' ? 'You' : 'Gemini'}
                </span>
                <span className="whitespace-pre-wrap">{m.text || (busy && i === messages.length - 1 ? '…' : '')}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-1">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="What does ‘Hujjah’ mean here?"
              className="flex-1 rounded border border-stone-300 bg-white px-2 py-1 text-[12px] focus:border-amber-400 focus:outline-none dark:border-stone-600 dark:bg-stone-800"
              disabled={busy}
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              className="rounded bg-amber-600 px-2 py-1 text-[11px] font-semibold text-white transition disabled:opacity-40 hover:bg-amber-700"
            >
              {busy ? '…' : 'Ask'}
            </button>
          </div>
          {messages.length > 0 && (
            <button onClick={() => setMessages([])} className="font-ui text-[10px] text-stone-400 hover:text-stone-700">
              clear conversation
            </button>
          )}
        </div>
      )}
    </div>
  );
}
